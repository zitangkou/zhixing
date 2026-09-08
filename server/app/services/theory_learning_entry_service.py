"""时政单篇学习入口编排；不创建或依赖套卷。"""

from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Article, Question, TheoryLearningEntry
from app.models.base import gen_id
from app.services.serializers import question_to_out
from app.timezone import today


def _loads(raw: str) -> list:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def normalize_parts(value: object, *, allow_empty: bool = False) -> list[dict]:
    if not isinstance(value, list):
        raise HTTPException(422, "分辑必须是数组")
    parts = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise HTTPException(422, "分辑格式不正确")
        raw_ids = item.get("questionIds")
        if not isinstance(raw_ids, list):
            raise HTTPException(422, "每个分辑必须包含题目 ID")
        ids = [str(question_id).strip() for question_id in raw_ids if str(question_id).strip()]
        if not ids or len(ids) > 5:
            raise HTTPException(422, "每个分辑须包含 1～5 题")
        if len(ids) != len(set(ids)) or any(question_id in seen for question_id in ids):
            raise HTTPException(422, "同一道题不能重复编入分辑")
        seen.update(ids)
        parts.append({
            "number": index + 1,
            "title": str(item.get("title") or f"第 {index + 1} 辑").strip()[:64],
            "questionIds": ids,
        })
    if not parts and not allow_empty:
        raise HTTPException(422, "至少配置一个五题分辑")
    return parts


def _question_ready(row: Question) -> bool:
    out = question_to_out(row).model_dump()
    options = out.get("options") or []
    answer = out["correctAnswer"]
    answers = answer if isinstance(answer, list) else [answer]
    return bool(
        row.is_active and row.status == "approved"
        and row.type in ("single", "multiple", "judge")
        and row.stem.strip() and row.analysis.strip() and row.source_sentence.strip()
        and len(options) >= 2 and len(set(options)) == len(options)
        and answers and all(answer_item in options for answer_item in answers)
        and len(set(answers)) == len(answers)
        and (len(answers) >= 2 if row.type == "multiple" else len(answers) == 1)
    )


def validate_published_entry(db: Session, row: TheoryLearningEntry) -> list[dict]:
    article = db.get(Article, row.article_id)
    if not article or not article.is_published or article.status != "published" or not article.allow_quiz:
        raise HTTPException(422, "文章未发布或未开放练习")
    if not row.is_daily and not row.is_evergreen:
        raise HTTPException(422, "至少选择今日内容或长期重点")
    if row.publish_start and row.publish_end and row.publish_start > row.publish_end:
        raise HTTPException(422, "入口结束日期不能早于开始日期")
    parts = normalize_parts(_loads(row.parts_json))
    ids = [question_id for part in parts for question_id in part["questionIds"]]
    questions = db.query(Question).filter(Question.id.in_(ids)).all()
    by_id = {question.id: question for question in questions}
    if len(by_id) != len(ids) or any(
        by_id[question_id].article_id != row.article_id or not _question_ready(by_id[question_id])
        for question_id in ids if question_id in by_id
    ):
        raise HTTPException(422, "分辑包含不属于该文章或尚未审核完整的题目")
    if row.collection_enabled:
        active = db.query(Question).filter(
            Question.article_id == row.article_id,
            Question.is_active.is_(True),
        ).all()
        if any(not _question_ready(question) for question in active) or {q.id for q in active} != set(ids):
            raise HTTPException(422, "开放全文合集前，全部有效题目必须审核完整并编入分辑")
    return parts


def _tags(article: Article) -> list[str]:
    value = _loads(article.tags)
    return [str(tag) for tag in value]


def _entry_out(row: TheoryLearningEntry, article: Article, parts: list[dict]) -> dict:
    return {
        "id": row.id,
        "articleId": article.id,
        "articleTitle": article.title,
        "title": row.title or article.title,
        "description": row.description or article.summary,
        "source": article.source,
        "publishDate": article.publish_date,
        "tags": _tags(article),
        "isDaily": row.is_daily,
        "isEvergreen": row.is_evergreen,
        "parts": parts,
        "questionCount": sum(len(part["questionIds"]) for part in parts),
        "collectionEnabled": row.collection_enabled,
        "status": row.status,
        "publishStart": row.publish_start,
        "publishEnd": row.publish_end,
        "sortOrder": row.sort_order,
    }


def _active_on(row: TheoryLearningEntry, date: str) -> bool:
    return row.status == "published" and (not row.publish_start or row.publish_start <= date) and (not row.publish_end or row.publish_end >= date)


def list_public_entries(db: Session) -> list[dict]:
    date = today()
    rows = db.query(TheoryLearningEntry, Article).join(Article, Article.id == TheoryLearningEntry.article_id).filter(
        TheoryLearningEntry.status == "published",
        Article.is_published.is_(True),
        Article.status == "published",
    ).order_by(TheoryLearningEntry.sort_order.desc(), Article.publish_date.desc()).all()
    output = []
    for row, article in rows:
        if not _active_on(row, date):
            continue
        try:
            parts = validate_published_entry(db, row)
        except HTTPException:
            continue
        output.append(_entry_out(row, article, parts))
    return output


def get_public_entry(db: Session, article_id: str) -> tuple[TheoryLearningEntry, list[dict]]:
    row = db.query(TheoryLearningEntry).filter(TheoryLearningEntry.article_id == article_id).first()
    if not row or not _active_on(row, today()):
        raise HTTPException(404, "学习入口尚未开放")
    try:
        return row, validate_published_entry(db, row)
    except HTTPException as error:
        raise HTTPException(404, "学习入口尚未开放") from error


def list_admin_entries(db: Session) -> list[dict]:
    rows = db.query(TheoryLearningEntry, Article).join(Article, Article.id == TheoryLearningEntry.article_id).order_by(
        TheoryLearningEntry.updated_at.desc(),
    ).all()
    output = []
    for row, article in rows:
        malformed = ""
        try:
            parts = normalize_parts(_loads(row.parts_json), allow_empty=True)
        except HTTPException as error:
            parts = []
            malformed = str(error.detail)
        item = _entry_out(row, article, parts)
        if malformed:
            item["validationError"] = malformed
        elif row.status == "published":
            try:
                validate_published_entry(db, row)
                item["validationError"] = ""
            except HTTPException as error:
                item["validationError"] = str(error.detail)
        else:
            item["validationError"] = ""
        output.append(item)
    return output


def save_entry(db: Session, article_id: str, data: dict) -> dict:
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文章不存在")
    row = db.query(TheoryLearningEntry).filter(TheoryLearningEntry.article_id == article_id).first()
    if not row:
        row = TheoryLearningEntry(id=gen_id("tle"), article_id=article_id)
        db.add(row)
    parts = normalize_parts(data["parts"], allow_empty=data["status"] != "published")
    row.title = data["title"].strip()
    row.description = data["description"].strip()
    row.is_daily = data["isDaily"]
    row.is_evergreen = data["isEvergreen"]
    row.parts_json = json.dumps(parts, ensure_ascii=False)
    row.collection_enabled = data["collectionEnabled"]
    row.status = data["status"]
    row.publish_start = data["publishStart"]
    row.publish_end = data["publishEnd"]
    row.sort_order = data["sortOrder"]
    if row.status == "published":
        validate_published_entry(db, row)
    db.commit()
    db.refresh(row)
    return _entry_out(row, article, parts)
