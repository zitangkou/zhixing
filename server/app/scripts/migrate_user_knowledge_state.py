#!/usr/bin/env python3
"""把旧版写在 knowledge_nodes 上的「个人状态」迁到 user_knowledge_state（按用户隔离）。

旧实现把 my_note / is_starred / mastery_level / next_review_at / review_count /
last_reviewed_at 直接存在全局节点上（单用户时代）。新版读写 user_knowledge_state，
旧字段不再被读取，不迁移则这些数据对学员“消失”。

⚠️ 默认 dry-run，只打印计划；加 --apply 才写库。生产执行前须先 dry-run 并备份数据库。
   本脚本在本 PR 中 **未在生产执行**；归属用户（--user-id）待产品确认。

用法（在 server/ 下）：
  python -m app.scripts.migrate_user_knowledge_state --user-id <app_user_id>            # dry-run
  python -m app.scripts.migrate_user_knowledge_state --user-id <app_user_id> --apply    # 写入
  可选：--tree-key yanyu  只迁某棵树；--skip-archived 跳过已归档节点

合并规则（幂等，可重复执行）：
  - 目标用户在该节点无状态 → 直接复制旧值；
  - is_starred 取或；review_count 取较大值；
  - 复习进度（mastery_level / next_review_at / last_reviewed_at）取 last_reviewed_at 较新的一方；
  - my_note：一方为空取非空；两者都有且不同 → 保留较新的一方（旧值时间 = 节点 last_reviewed_at
    或 updated_at，新值时间 = 状态 updated_at），并计入 conflicts 供人工核对。
  - 不修改、不清空 knowledge_nodes 上的旧字段（回滚安全）。
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session  # noqa: E402

from app.models import AppUser, KnowledgeNode, UserKnowledgeState  # noqa: E402
from app.models.base import utcnow  # noqa: E402


@dataclass
class MigrationReport:
    user_id: str
    apply: bool
    scanned: int = 0
    with_legacy_state: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    conflicts: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "userId": self.user_id,
            "apply": self.apply,
            "scanned": self.scanned,
            "withLegacyState": self.with_legacy_state,
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "conflicts": self.conflicts,
        }


def _has_legacy_state(n: KnowledgeNode) -> bool:
    return bool(
        (n.my_note or "").strip()
        or n.is_starred
        or (n.mastery_level or "new") != "new"
        or (n.review_count or 0) > 0
        or n.next_review_at is not None
        or n.last_reviewed_at is not None
    )


def _newer(a: datetime | None, b: datetime | None) -> bool:
    """a 是否严格新于 b（None 视为最旧）。"""
    if a is None:
        return False
    if b is None:
        return True
    return a > b


def _merge(st: UserKnowledgeState, n: KnowledgeNode, report: MigrationReport) -> bool:
    changed = False
    legacy_note = n.my_note or ""
    if legacy_note.strip() and legacy_note != (st.my_note or ""):
        if not (st.my_note or "").strip():
            st.my_note = legacy_note
            changed = True
        else:
            legacy_ts = n.last_reviewed_at or n.updated_at
            keep_legacy = _newer(legacy_ts, st.updated_at)
            report.conflicts.append({
                "nodeId": n.id,
                "path": n.path,
                "field": "my_note",
                "kept": "legacy" if keep_legacy else "current",
            })
            if keep_legacy:
                st.my_note = legacy_note
                changed = True
    if n.is_starred and not st.is_starred:
        st.is_starred = True
        changed = True
    if (n.review_count or 0) > (st.review_count or 0):
        st.review_count = n.review_count
        changed = True
    if _newer(n.last_reviewed_at, st.last_reviewed_at) or (
        st.last_reviewed_at is None and n.last_reviewed_at is None
        and (st.mastery_level or "new") == "new" and (n.mastery_level or "new") != "new"
    ):
        for attr in ("mastery_level", "next_review_at", "last_reviewed_at"):
            if getattr(st, attr) != getattr(n, attr):
                setattr(st, attr, getattr(n, attr))
                changed = True
    return changed


def migrate(
    db: Session,
    user_id: str,
    *,
    apply: bool = False,
    tree_key: str | None = None,
    skip_archived: bool = False,
) -> MigrationReport:
    if not db.get(AppUser, user_id):
        raise ValueError(f"用户不存在: {user_id}")
    report = MigrationReport(user_id=user_id, apply=apply)
    q = db.query(KnowledgeNode)
    if tree_key:
        q = q.filter(KnowledgeNode.tree_key == tree_key)
    if skip_archived:
        q = q.filter(KnowledgeNode.archived_at.is_(None))
    nodes = q.order_by(KnowledgeNode.tree_key, KnowledgeNode.id).all()
    report.scanned = len(nodes)
    existing = {
        s.node_id: s
        for s in db.query(UserKnowledgeState).filter(UserKnowledgeState.user_id == user_id).all()
    }
    for n in nodes:
        if not _has_legacy_state(n):
            continue
        report.with_legacy_state += 1
        st = existing.get(n.id)
        if st is None:
            report.created += 1
            if apply:
                db.add(UserKnowledgeState(
                    user_id=user_id,
                    node_id=n.id,
                    tree_key=n.tree_key,
                    path=n.path or "",
                    my_note=n.my_note or "",
                    is_starred=bool(n.is_starred),
                    mastery_level=n.mastery_level or "new",
                    next_review_at=n.next_review_at,
                    review_count=n.review_count or 0,
                    last_reviewed_at=n.last_reviewed_at,
                    updated_at=utcnow(),
                ))
            continue
        if apply:
            changed = _merge(st, n, report)
        else:
            # dry-run：在游离副本上演算，避免脏写
            probe = UserKnowledgeState(
                my_note=st.my_note, is_starred=st.is_starred, mastery_level=st.mastery_level,
                next_review_at=st.next_review_at, review_count=st.review_count,
                last_reviewed_at=st.last_reviewed_at, updated_at=st.updated_at,
            )
            changed = _merge(probe, n, report)
        if changed:
            report.updated += 1
            if apply:
                st.tree_key = n.tree_key
                st.path = n.path or ""
                st.updated_at = utcnow()
        else:
            report.unchanged += 1
    if apply:
        db.commit()
    else:
        db.rollback()
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user-id", required=True, help="旧状态归属的 app_users.id（待产品确认）")
    ap.add_argument("--apply", action="store_true", help="真正写库；缺省为 dry-run")
    ap.add_argument("--tree-key", default=None)
    ap.add_argument("--skip-archived", action="store_true")
    args = ap.parse_args()

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        report = migrate(
            db, args.user_id, apply=args.apply, tree_key=args.tree_key, skip_archived=args.skip_archived
        )
    finally:
        db.close()
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, default=str))
    if not args.apply:
        print("\n[dry-run] 未写库。确认无误并备份后加 --apply 执行。", file=sys.stderr)


if __name__ == "__main__":
    main()
