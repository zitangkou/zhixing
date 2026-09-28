"""知识节点抽查：按用户状态表调度，只抽今日到期 + 少量未学新卡。"""
from __future__ import annotations

import random
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import KnowledgeNode, UserKnowledgeState, utcnow
from app.schemas import (
    KnowledgeReviewAnswerOut,
    KnowledgeReviewCardOut,
    KnowledgeReviewDueOut,
    KnowledgeReviewSessionOut,
)
from app.services.knowledge_doc_service import public_tree_keys, upsert_user_state
from app.services.srs import SRS_INTERVALS, now_naive, schedule_after_fail, schedule_after_success

NEW_INTRO_CAP = 5
_VALID_RESULTS = frozenset({"again", "hard", "good", "easy"})


def _has_reviewable_body(n: KnowledgeNode, st: UserKnowledgeState | None) -> bool:
    content = (n.content or "").strip()
    note = ((st.my_note if st else "") or "").strip()
    return bool(content or note)


def _card_from(n: KnowledgeNode, st: UserKnowledgeState | None) -> KnowledgeReviewCardOut:
    content = (n.content or "").strip()
    note = ((st.my_note if st else "") or "").strip()
    answer = content or note
    hint = None
    if answer:
        hint = answer[:12] + ("…" if len(answer) > 12 else "")
    return KnowledgeReviewCardOut(
        id=n.id,
        title=n.title,
        path=n.path or "",
        treeKey=n.tree_key,
        content=answer,
        myNote=note,
        masteryLevel=(st.mastery_level if st else None) or "new",
        hint=hint,
    )


def _scheduled_due(db: Session, user_id: str) -> list[tuple[KnowledgeNode, UserKnowledgeState]]:
    ts = now_naive()
    rows = (
        db.query(UserKnowledgeState, KnowledgeNode)
        .join(KnowledgeNode, KnowledgeNode.id == UserKnowledgeState.node_id)
        .filter(
            UserKnowledgeState.user_id == user_id,
            UserKnowledgeState.next_review_at.isnot(None),
            UserKnowledgeState.next_review_at <= ts,
            UserKnowledgeState.mastery_level != "mastered",
            KnowledgeNode.archived_at.is_(None),
            KnowledgeNode.tree_key.in_(public_tree_keys(db) or [""]),
        )
        .order_by(UserKnowledgeState.next_review_at.asc())
        .all()
    )
    out = []
    for st, n in rows:
        if _has_reviewable_body(n, st):
            out.append((n, st))
    return out


def _new_unreviewed(
    db: Session, user_id: str, exclude_ids: set[str], limit: int
) -> list[tuple[KnowledgeNode, UserKnowledgeState | None]]:
    stated = {
        r.node_id
        for r in db.query(UserKnowledgeState.node_id)
        .filter(UserKnowledgeState.user_id == user_id, UserKnowledgeState.next_review_at.isnot(None))
        .all()
    }
    visible = public_tree_keys(db) or [""]
    rows = (
        db.query(KnowledgeNode)
        .filter(
            KnowledgeNode.archived_at.is_(None),
            KnowledgeNode.tree_key.in_(visible),
            KnowledgeNode.content.isnot(None),
            KnowledgeNode.content != "",
        )
        .order_by(KnowledgeNode.updated_at.desc())
        .limit(300)
        .all()
    )
    # also include nodes with only user notes
    note_ids = {
        r.node_id
        for r in db.query(UserKnowledgeState)
        .filter(UserKnowledgeState.user_id == user_id, UserKnowledgeState.my_note != "")
        .limit(100)
        .all()
    }
    extra = []
    if note_ids:
        extra = (
            db.query(KnowledgeNode)
            .filter(
                KnowledgeNode.id.in_(note_ids),
                KnowledgeNode.archived_at.is_(None),
                KnowledgeNode.tree_key.in_(visible),
            )
            .all()
        )
    pool_nodes = {n.id: n for n in rows}
    for n in extra:
        pool_nodes[n.id] = n

    states = {
        s.node_id: s
        for s in db.query(UserKnowledgeState)
        .filter(UserKnowledgeState.user_id == user_id, UserKnowledgeState.node_id.in_(list(pool_nodes.keys()) or [""]))
        .all()
    }
    out: list[tuple[KnowledgeNode, UserKnowledgeState | None]] = []
    for nid, n in pool_nodes.items():
        if nid in exclude_ids or nid in stated:
            continue
        st = states.get(nid)
        if st and st.mastery_level == "mastered":
            continue
        if not _has_reviewable_body(n, st):
            continue
        out.append((n, st))
        if len(out) >= limit:
            break
    return out


def _today_queue(db: Session, user_id: str) -> list[tuple[KnowledgeNode, UserKnowledgeState | None]]:
    due = _scheduled_due(db, user_id)
    new_cards = _new_unreviewed(db, user_id, {n.id for n, _ in due}, NEW_INTRO_CAP)
    return due + new_cards  # type: ignore[return-value]


def get_due(db: Session, user_id: str, preview: int = 5) -> KnowledgeReviewDueOut:
    queue = _today_queue(db, user_id)
    return KnowledgeReviewDueOut(
        dueCount=len(queue),
        candidates=[_card_from(n, st) for n, st in queue[:preview]],
    )


def count_due(db: Session, user_id: str) -> int:
    return len(_today_queue(db, user_id))


def create_session(db: Session, user_id: str, count: int = 5) -> KnowledgeReviewSessionOut:
    count = max(1, min(int(count or 5), 20))
    queue = _today_queue(db, user_id)
    if len(queue) <= count:
        selected = list(queue)
    else:
        due = [(n, st) for n, st in queue if st and st.next_review_at is not None]
        fresh = [(n, st) for n, st in queue if not st or st.next_review_at is None]
        selected = []
        if due:
            selected.extend(random.sample(due, min(len(due), count)))
        need = count - len(selected)
        if need > 0 and fresh:
            selected.extend(random.sample(fresh, min(len(fresh), need)))
    random.shuffle(selected)
    return KnowledgeReviewSessionOut(cards=[_card_from(n, st) for n, st in selected])


def answer_review(db: Session, user_id: str, node_id: str, result: str) -> KnowledgeReviewAnswerOut | None:
    result = (result or "").strip().lower()
    if result not in _VALID_RESULTS:
        return None
    n = db.get(KnowledgeNode, node_id)
    if not n or n.archived_at is not None:
        return None
    st = upsert_user_state(db, user_id, node_id)
    if not st:
        return None

    stage = int(st.review_count or 0)
    if result == "again":
        new_stage, next_at = schedule_after_fail()
        st.mastery_level = "learning"
        st.review_count = new_stage
        st.next_review_at = next_at
    else:
        if result == "hard":
            st.mastery_level = "learning"
            st.next_review_at = now_naive() + timedelta(days=1)
        else:
            bump = 2 if result == "easy" else 1
            cur = stage
            next_at = None
            mastered = False
            for _ in range(bump):
                cur, next_at, mastered = schedule_after_success(cur)
                if mastered:
                    break
            st.review_count = cur
            st.next_review_at = next_at
            st.mastery_level = "mastered" if mastered else ("familiar" if result == "good" else "learning")
            if mastered:
                st.next_review_at = now_naive() + timedelta(days=SRS_INTERVALS[-1])

    st.last_reviewed_at = now_naive()
    st.updated_at = utcnow()
    db.commit()
    db.refresh(st)
    return KnowledgeReviewAnswerOut(
        id=n.id,
        masteryLevel=st.mastery_level or "new",
        nextReviewAt=st.next_review_at,
        reviewCount=int(st.review_count or 0),
        lastReviewedAt=st.last_reviewed_at,
    )
