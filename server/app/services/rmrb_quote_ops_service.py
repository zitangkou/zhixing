"""运营金句库与每日小红书/公众号物料编排。"""
from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models import RmrbCommentArticle, RmrbCommentQuote, RmrbQuoteOpsPackage, RmrbQuoteOpsPackageItem


def _json_list(value: str) -> list:
    try:
        result = json.loads(value or "[]")
        return result if isinstance(result, list) else []
    except (TypeError, ValueError):
        return []


def _quote_out(row: RmrbCommentQuote, used: bool = False) -> dict:
    record = row.comment_article
    article = record.article if record else None
    return {
        "id": row.id, "text": row.text, "quoteType": row.quote_type,
        "topics": _json_list(row.topics_json), "useCases": _json_list(row.use_cases_json),
        "applicationExample": row.application_example, "reviewStatus": row.review_status,
        "collectionMethod": row.collection_method, "reviewedBy": row.reviewed_by,
        "reviewedAt": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "used": used, "articleTitle": article.display_title if article else "",
        "articleDate": article.issue_date.isoformat() if article and article.issue_date else "",
        "author": article.author_line if article else "", "sourceUrl": article.primary_source_url if article else "",
    }


def list_ops_quotes(db: Session, q: str = "", topic: str = "", used: str = "unused", limit: int = 300) -> list[dict]:
    query = db.query(RmrbCommentQuote).join(RmrbCommentQuote.comment_article).options(
        joinedload(RmrbCommentQuote.comment_article).joinedload(RmrbCommentArticle.article)
    ).filter(RmrbCommentQuote.review_status == "approved")
    if q.strip():
        query = query.filter(or_(RmrbCommentQuote.text.contains(q.strip()), RmrbCommentQuote.application_example.contains(q.strip())))
    rows = query.order_by(RmrbCommentQuote.reviewed_at.desc(), RmrbCommentQuote.created_at.desc()).limit(limit).all()
    published_ids = {row[0] for row in db.query(RmrbQuoteOpsPackageItem.quote_id).join(
        RmrbQuoteOpsPackage, RmrbQuoteOpsPackage.id == RmrbQuoteOpsPackageItem.package_id
    ).filter(RmrbQuoteOpsPackage.status == "published").all()}
    result = [_quote_out(row, row.id in published_ids) for row in rows]
    if topic.strip():
        result = [item for item in result if topic.strip() in item["topics"]]
    if used == "unused":
        result = [item for item in result if not item["used"]]
    elif used == "used":
        result = [item for item in result if item["used"]]
    return result


def list_quote_library(db: Session, q: str = "", topic: str = "", used: str = "all",
                       page: int = 1, page_size: int = 20) -> dict:
    from app.models import RmrbArchiveArticle

    published_quote_ids = db.query(RmrbQuoteOpsPackageItem.quote_id).join(
        RmrbQuoteOpsPackage, RmrbQuoteOpsPackage.id == RmrbQuoteOpsPackageItem.package_id
    ).filter(RmrbQuoteOpsPackage.status == "published")
    query = db.query(RmrbCommentQuote).join(RmrbCommentArticle).join(
        RmrbArchiveArticle, RmrbArchiveArticle.id == RmrbCommentArticle.article_id
    ).options(joinedload(RmrbCommentQuote.comment_article).joinedload(RmrbCommentArticle.article)).filter(
        RmrbCommentQuote.review_status == "approved"
    )
    if q.strip():
        query = query.filter(or_(RmrbCommentQuote.text.contains(q.strip()),
                                 RmrbCommentQuote.application_example.contains(q.strip()),
                                 RmrbArchiveArticle.display_title.contains(q.strip())))
    if topic.strip():
        query = query.filter(RmrbCommentQuote.topics_json.contains(f'"{topic.strip()}"'))
    if used == "used":
        query = query.filter(RmrbCommentQuote.id.in_(published_quote_ids))
    elif used == "unused":
        query = query.filter(~RmrbCommentQuote.id.in_(published_quote_ids))
    total = query.with_entities(RmrbCommentQuote.id).count()
    rows = query.order_by(RmrbCommentQuote.reviewed_at.desc(), RmrbCommentQuote.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    ids = [row.id for row in rows]
    published_items = db.query(RmrbQuoteOpsPackageItem.quote_id, RmrbQuoteOpsPackage).join(
        RmrbQuoteOpsPackage, RmrbQuoteOpsPackage.id == RmrbQuoteOpsPackageItem.package_id
    ).filter(RmrbQuoteOpsPackage.status == "published", RmrbQuoteOpsPackageItem.quote_id.in_(ids)).all() if ids else []
    packages_by_quote: dict[str, list[dict]] = {}
    for quote_id, package in published_items:
        packages_by_quote.setdefault(quote_id, []).append({"date": package.issue_date.isoformat(), "title": package.title,
                                                           "channels": _json_list(package.channels_json)})
    items = []
    for row in rows:
        item = _quote_out(row, row.id in packages_by_quote)
        item["publishedPackages"] = packages_by_quote.get(row.id, [])
        items.append(item)
    return {"items": items, "total": total, "page": page, "pageSize": page_size}


def _package_out(db: Session, package: RmrbQuoteOpsPackage) -> dict:
    links = db.query(RmrbQuoteOpsPackageItem).filter_by(package_id=package.id).order_by(RmrbQuoteOpsPackageItem.sort_order).all()
    quotes = [db.query(RmrbCommentQuote).options(joinedload(RmrbCommentQuote.comment_article).joinedload(RmrbCommentArticle.article)).filter_by(id=link.quote_id).first() for link in links]
    return {"id": package.id, "issueDate": package.issue_date.isoformat(), "topic": package.topic,
            "title": package.title, "channels": _json_list(package.channels_json), "xhsTitle": package.xhs_title,
            "xhsContent": package.xhs_content, "wechatTitle": package.wechat_title,
            "wechatSummary": package.wechat_summary, "wechatContent": package.wechat_content,
            "status": package.status, "xhsPublishedAt": package.xhs_published_at.isoformat() if package.xhs_published_at else None,
            "wechatPublishedAt": package.wechat_published_at.isoformat() if package.wechat_published_at else None,
            "createdAt": package.created_at.isoformat() if package.created_at else None,
            "quotes": [_quote_out(q, package.status == "published") for q in quotes if q]}


def list_packages(db: Session, issue_date: date | None = None) -> list[dict]:
    query = db.query(RmrbQuoteOpsPackage)
    if issue_date:
        query = query.filter_by(issue_date=issue_date)
    return [_package_out(db, row) for row in query.order_by(RmrbQuoteOpsPackage.issue_date.desc(), RmrbQuoteOpsPackage.created_at.desc()).limit(100).all()]


def get_package(db: Session, package_id: str) -> dict | None:
    row = db.query(RmrbQuoteOpsPackage).filter_by(id=package_id).first()
    return _package_out(db, row) if row else None


def create_package(db: Session, data: dict, creator: str) -> dict:
    ids = list(dict.fromkeys(str(x) for x in data.get("quoteIds", []) if x))
    if not ids:
        raise ValueError("至少选择一条审核通过的金句")
    if len(ids) > 20:
        raise ValueError("单个运营内容包最多选择 20 条金句")
    quotes = db.query(RmrbCommentQuote).filter(RmrbCommentQuote.id.in_(ids), RmrbCommentQuote.review_status == "approved").all()
    if len(quotes) != len(ids):
        raise ValueError("所选金句中有未审核通过或已删除的记录，请刷新后重选")
    used_ids = {row[0] for row in db.query(RmrbQuoteOpsPackageItem.quote_id).join(
        RmrbQuoteOpsPackage, RmrbQuoteOpsPackage.id == RmrbQuoteOpsPackageItem.package_id
    ).filter(RmrbQuoteOpsPackage.status == "published", RmrbQuoteOpsPackageItem.quote_id.in_(ids)).all()}
    if used_ids:
        raise ValueError("所选金句已作为运营内容发布，不能重复选用")
    try:
        issue_date = date.fromisoformat(str(data.get("issueDate") or date.today().isoformat()))
    except ValueError as exc:
        raise ValueError("运营日期格式无效") from exc
    channels = [c for c in data.get("channels", ["wechat", "xiaohongshu"]) if c in {"wechat", "xiaohongshu"}]
    if not channels:
        raise ValueError("至少选择一个运营平台")
    row = RmrbQuoteOpsPackage(issue_date=issue_date, topic=str(data.get("topic") or "").strip()[:128],
                              title=str(data.get("title") or "").strip()[:256], channels_json=json.dumps(channels),
                              created_by=creator)
    db.add(row); db.flush()
    for index, quote in enumerate(quotes):
        db.add(RmrbQuoteOpsPackageItem(package_id=row.id, quote_id=quote.id, sort_order=index))
    db.commit(); db.refresh(row)
    return _package_out(db, row)


def update_package(db: Session, package_id: str, data: dict) -> dict | None:
    row = db.query(RmrbQuoteOpsPackage).filter_by(id=package_id).first()
    if not row:
        return None
    if row.status == "published":
        raise ValueError("已发布的运营包不可修改；如需修订请新建运营包")
    for key, field, maxlen in (("topic", "topic", 128), ("title", "title", 256), ("xhsTitle", "xhs_title", 256),
                               ("xhsContent", "xhs_content", None), ("wechatTitle", "wechat_title", 256),
                               ("wechatSummary", "wechat_summary", None), ("wechatContent", "wechat_content", None)):
        if key in data:
            value = str(data[key] or "")
            setattr(row, field, value[:maxlen] if maxlen else value)
    if "channels" in data:
        channels = [c for c in data["channels"] if c in {"wechat", "xiaohongshu"}]
        if not channels:
            raise ValueError("至少选择一个运营平台")
        row.channels_json = json.dumps(channels)
    db.commit(); db.refresh(row)
    return _package_out(db, row)


def generate_copy(db: Session, package_id: str) -> dict | None:
    row = db.query(RmrbQuoteOpsPackage).filter_by(id=package_id).first()
    if not row:
        return None
    if row.status == "published":
        raise ValueError("运营包已发布，不能重新生成覆盖已发布文案")
    data = _package_out(db, row)
    quotes = data["quotes"]
    if not quotes:
        raise ValueError("运营包没有关联金句")
    topic = row.topic or next((topic for quote in quotes for topic in quote["topics"]), "申论写作")
    title = row.title or f"申论素材积累｜{topic}主题金句"
    xhs_title = f"{topic}主题申论金句｜考场写作怎么用"[:20]
    xhs = [f"【{topic}主题素材】", "写申论时，观点要鲜明，论证也要落到具体场景。今天整理了几句可迁移表达："]
    wx = [f"围绕{topic}主题，整理今日可用于申论写作的表达。以下引文均保留原文，并附来源，供学习参考。"]
    for i, quote in enumerate(quotes, 1):
        topics = "、".join(quote["topics"]) or topic
        cases = "、".join(quote["useCases"]) or "分论点论证、结尾升华"
        xhs.extend([f"\n{i}. {quote['text']}", f"适用：{topics}；可放在{cases}。"])
        wx.extend([f"\n## {i}. {topics}", f"> {quote['text']}", f"**申论用法：**可用于{cases}。"])
        if quote["applicationExample"]:
            xhs.append(f"仿写参考：{quote['applicationExample']}")
            wx.append(f"**仿写参考（非原文）：**{quote['applicationExample']}")
        if quote["sourceUrl"]:
            wx.append(f"来源：{quote['articleTitle']}，人民日报客户端，{quote['articleDate']}。")
    xhs.extend(["\n收藏备用，写作时先判断题目主题与语境，再选择合适表达。", "#申论 #申论素材 #公务员考试 #申论金句"])
    wx.extend(["\n## 写作提醒", "引用素材要服务于观点，避免堆砌；仿写表达不可标注为原文。", "\n留言说说：你会把哪一句用于什么主题？"])
    row.title = title; row.xhs_title = xhs_title; row.xhs_content = "\n".join(xhs)
    row.wechat_title = title; row.wechat_summary = f"围绕{topic}整理{len(quotes)}条申论可用表达，附适用场景与写作提示。"[:80]
    row.wechat_content = "\n".join(wx)
    db.commit(); db.refresh(row)
    return _package_out(db, row)


def mark_published(db: Session, package_id: str, channel: str) -> dict | None:
    row = db.query(RmrbQuoteOpsPackage).filter_by(id=package_id).first()
    if not row:
        return None
    if channel not in {"wechat", "xiaohongshu"} or channel not in _json_list(row.channels_json):
        raise ValueError("平台不在该运营包的发布范围内")
    content = row.wechat_content if channel == "wechat" else row.xhs_content
    if not content.strip():
        raise ValueError("请先生成并审核该平台的发布内容")
    quote_ids = [link.quote_id for link in db.query(RmrbQuoteOpsPackageItem).filter_by(package_id=row.id).all()]
    already_used = {item[0] for item in db.query(RmrbQuoteOpsPackageItem.quote_id).join(
        RmrbQuoteOpsPackage, RmrbQuoteOpsPackage.id == RmrbQuoteOpsPackageItem.package_id
    ).filter(RmrbQuoteOpsPackage.status == "published", RmrbQuoteOpsPackage.id != row.id,
             RmrbQuoteOpsPackageItem.quote_id.in_(quote_ids)).all()}
    if already_used:
        raise ValueError("有金句已在其他运营包发布；请新建运营包并移除重复金句")
    now = datetime.utcnow()
    if channel == "wechat": row.wechat_published_at = now
    else: row.xhs_published_at = now
    row.status = "published"
    db.commit(); db.refresh(row)
    return _package_out(db, row)
