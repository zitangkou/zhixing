"""产品专题列表。

专题由 `system_settings` 下发（键 `topics.<product_key>`，值为 JSON 数组），
目的是让运营/管理员在**不发版**的前提下切换专题内容：

- 提审期：只放方法类专题（不含具体政治专题名），与「个人自学工具」定性一致；
- 过审后：把真实专题写进同一个设置项即可切换。

设置项缺失时按默认值自动补齐，因此首次调用就会出现在管理后台的设置列表里。
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import SystemSetting

SETTING_PREFIX = "topics."
SETTING_DESC = "产品专题列表（JSON 数组，每项含 no/title/desc）。提审期建议只保留方法类专题。"

#: 提审期默认专题：只讲方法，不含政治专题名与「时政」字样
REVIEW_TOPICS: dict[str, list[dict[str, str]]] = {
    "theory": [
        {"no": "读", "title": "理论文章怎么读", "desc": "抓主体、动作与关键表述，先建框架再记细节"},
        {"no": "辨", "title": "易混表述辨析", "desc": "相近说法逐条回到原文依据，辨清差别"},
        {"no": "记", "title": "规范表述积累", "desc": "把要点记成可复用的标准说法"},
    ],
    "shenlun": [
        {"no": "拆", "title": "材料怎么拆", "desc": "用三刀法标出要点、逻辑与对策"},
        {"no": "写", "title": "小题怎么写", "desc": "百字作答，要点齐全、表达规范"},
        {"no": "改", "title": "表达怎么改", "desc": "对照规范词库，把口语改成书面表述"},
    ],
    "general": [
        {"no": "学", "title": "学习方法与路径", "desc": "先建框架，再按专题补齐细节"},
        {"no": "练", "title": "每日练习与复盘", "desc": "作答、看反馈、把错处沉淀进复习"},
    ],
}


def setting_key(product_key: str) -> str:
    return f"{SETTING_PREFIX}{product_key}"


def default_topics(product_key: str) -> list[dict[str, str]]:
    return REVIEW_TOPICS.get(product_key) or REVIEW_TOPICS["general"]


def ensure_topic_setting(db: Session, product_key: str) -> SystemSetting:
    """取设置项；不存在则用默认专题播种一行。"""
    key = setting_key(product_key)
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row is None:
        row = SystemSetting(
            key=key,
            value=json.dumps(default_topics(product_key), ensure_ascii=False),
            description=SETTING_DESC,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _normalize(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        items.append(
            {
                "no": str(entry.get("no") or title[:1])[:2],
                "title": title[:64],
                "desc": str(entry.get("desc") or "").strip()[:128],
            }
        )
    return items


def list_topics(db: Session, product_key: str) -> list[dict[str, str]]:
    """返回该产品的专题列表；配置为空或 JSON 非法时回落到默认值，保证前端不出现空页。"""
    row = ensure_topic_setting(db, product_key)
    try:
        items = _normalize(json.loads(row.value))
    except (ValueError, TypeError):
        items = []
    return items or _normalize(default_topics(product_key))
