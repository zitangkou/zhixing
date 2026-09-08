"""用户行为事件（M4 成长/能力雷达/里程碑统计的数据底座，本期仅写入）

事件类型约定：
- article_read   读文章段落
- quiz_done      完成一次套题练习
- exam_done      完成一次模考交卷
- drill_done     完成一次资料分析专项练习
- shenlun_mined  沉淀一次申论金句/素材
- sign_in        每日签到
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import ActivityEvent, gen_id
from app.timezone import today as today_str


def record_event(
    db: Session,
    user_id: str,
    event_type: str,
    payload: dict | None = None,
    *,
    commit: bool = True,
) -> ActivityEvent:
    """写入一条行为事件。

    - commit=True：事件单独提交（适合调用点无后续事务的情况）
    - commit=False：复用调用点稍后的 commit，避免多余事务
    """
    ev = ActivityEvent(
        id=gen_id("aev"),
        user_id=user_id,
        event_type=event_type,
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
        event_date=today_str(),
    )
    db.add(ev)
    if commit:
        db.commit()
    return ev
