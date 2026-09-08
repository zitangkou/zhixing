"""知识节点抽查：只抽今日到期 + 少量未学新卡，不刷未到期内容。"""
from __future__ import annotations

import random
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import KnowledgeNode, utcnow
from app.schemas import (
    KnowledgeReviewAnswerOut,
    KnowledgeReviewCardOut,
    KnowledgeReviewDueOut,
    KnowledgeReviewSessionOut,
)
from app.services.srs import SRS_INTERVALS, now_naive, schedule_after_fail, schedule_after_success

# 每日最多引入多少「从未复习」的新节点进入队列
NEW_INTRO_CAP = 5

# again → 重置；hard/good/easy → 按档推进（映射到 SRS 成功，hard 用较短间隔）
_VALID_RESULTS = frozenset({"again", "hard", "good", "easy"})


def _has_reviewable_body(n: KnowledgeNode) -> bool:
    content = (n.content or "").strip()
    note = (n.my_note or "").strip()
    return bool(content or note)


def _card_from_node(n: KnowledgeNode) -> KnowledgeReviewCardOut:
    content = (n.content or "").strip()
    note = (n.my_note or "").strip()
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
        masteryLevel=n.mastery_level or "new",
        hint=hint,
    )


def _scheduled_due(db: Session) -> list[KnowledgeNode]:
    ts = now_naive()
    rows = (
        db.query(KnowledgeNode)
        .filter(
            KnowledgeNode.next_review_at.isnot(None),
            KnowledgeNode.next_review_at <= ts,
            KnowledgeNode.mastery_level != "mastered",
        )
        .order_by(KnowledgeNode.next_review_at.asc())
        .all()
    )
    return [n for n in rows if _has_reviewable_body(n)]


def _new_unreviewed(db: Session, exclude_ids: set[str] | None = None, limit: int | None = None) -> list[KnowledgeNode]:
    exclude_ids = exclude_ids or set()
    # 先在 SQL 侧缩小到有正文/备注的节点，避免 limit 抽到大量空壳标题
    from sqlalchemy import or_

    rows = (
        db.query(KnowledgeNode)
        .filter(
            KnowledgeNode.next_review_at.is_(None),
            KnowledgeNode.mastery_level.in_(("new", "learning", "familiar")),
            or_(
                KnowledgeNode.content != "",
                KnowledgeNode.my_note != "",
            ),
        )
        .order_by(KnowledgeNode.is_starred.desc(), KnowledgeNode.updated_at.desc())
        .limit(200)
        .all()
    )
    pool = [n for n in rows if n.id not in exclude_ids and _has_reviewable_body(n)]
    if limit is not None and len(pool) > limit:
        return pool[:limit]
    return pool


def _today_queue(db: Session) -> list[KnowledgeNode]:
    """今日复习队列 = 到期卡 + 有限新卡。"""
    due = _scheduled_due(db)
    new_cards = _new_unreviewed(db, {n.id for n in due}, NEW_INTRO_CAP)
    return due + new_cards


def get_due(db: Session, preview: int = 5) -> KnowledgeReviewDueOut:
    queue = _today_queue(db)
    return KnowledgeReviewDueOut(
        dueCount=len(queue),
        candidates=[_card_from_node(n) for n in queue[:preview]],
    )


def count_due(db: Session) -> int:
    return len(_today_queue(db))


def create_session(db: Session, count: int = 5) -> KnowledgeReviewSessionOut:
    count = max(1, min(int(count or 5), 20))
    queue = _today_queue(db)
    if len(queue) <= count:
        selected = list(queue)
    else:
        # 优先抽到期，再补新卡
        due = [n for n in queue if n.next_review_at is not None]
        fresh = [n for n in queue if n.next_review_at is None]
        selected = []
        if due:
            selected.extend(random.sample(due, min(len(due), count)))
        need = count - len(selected)
        if need > 0 and fresh:
            selected.extend(random.sample(fresh, min(len(fresh), need)))
    random.shuffle(selected)
    return KnowledgeReviewSessionOut(cards=[_card_from_node(n) for n in selected])


def answer_review(db: Session, node_id: str, result: str) -> KnowledgeReviewAnswerOut | None:
    result = (result or "").strip().lower()
    if result not in _VALID_RESULTS:
        return None
    n = db.get(KnowledgeNode, node_id)
    if not n:
        return None

    stage = int(n.review_count or 0)
    if result == "again":
        new_stage, next_at = schedule_after_fail()
        n.mastery_level = "learning"
        n.review_count = new_stage
        n.next_review_at = next_at
    else:
        # hard 不推进 stage，仅用较短间隔；good/easy 走成功档
        if result == "hard":
            n.mastery_level = "learning"
            n.next_review_at = now_naive() + timedelta(days=1)
            # review_count 不增加，仍停在当前档
        else:
            # easy 额外跳一档
            bump = 2 if result == "easy" else 1
            cur = stage
            next_at = None
            mastered = False
            for _ in range(bump):
                cur, next_at, mastered = schedule_after_success(cur)
                if mastered:
                    break
            n.review_count = cur
            n.next_review_at = next_at
            n.mastery_level = "mastered" if mastered else ("familiar" if result == "good" else "learning")
            if mastered:
                n.next_review_at = now_naive() + timedelta(days=SRS_INTERVALS[-1])

    n.last_reviewed_at = now_naive()
    n.updated_at = utcnow()
    db.commit()
    db.refresh(n)
    return KnowledgeReviewAnswerOut(
        id=n.id,
        masteryLevel=n.mastery_level or "new",
        nextReviewAt=n.next_review_at,
        reviewCount=int(n.review_count or 0),
        lastReviewedAt=n.last_reviewed_at,
    )
