"""人民日报评论文章金句的 AI 提取、人工维护与原文校验。"""
from __future__ import annotations

import json
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models import RmrbArchiveArticle, RmrbArchiveSource, RmrbCommentArticle, RmrbCommentExclusionRule, RmrbCommentQuote
from app.services.ai.llm_client import chat_json
from app.services.rmrb_comments_service import _article_body


QUOTE_SYSTEM = "你是公务员考试申论教研编辑。只能从给定文章原文逐字摘录完整句子，不得拼接、润色、补写或编造引文。筛选有观点、有论证价值、能迁移到申论写作的句子。输出合法 JSON。"


def _loads(raw: str) -> list[str]:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


def _out(row: RmrbCommentQuote) -> dict:
    return {"id": row.id, "commentArticleId": row.comment_article_id, "text": row.text,
            "quoteType": row.quote_type, "topics": _loads(row.topics_json), "useCases": _loads(row.use_cases_json),
            "applicationExample": row.application_example, "sourceEvidence": row.source_evidence,
            "collectionMethod": row.collection_method, "reviewStatus": row.review_status,
            "reviewNote": row.review_note, "reviewedBy": row.reviewed_by, "reviewedAt": row.reviewed_at}


def list_quotes(db: Session, comment_article_id: str) -> list[dict]:
    rows = db.query(RmrbCommentQuote).filter_by(comment_article_id=comment_article_id).filter(
        RmrbCommentQuote.review_status != "rejected").order_by(RmrbCommentQuote.created_at, RmrbCommentQuote.id).all()
    return [_out(row) for row in rows]


def _require_article_approved(record: RmrbCommentArticle) -> None:
    if record.article_review_status != "approved":
        raise ValueError("请先审核确认该文章属于评论文章，再处理金句")


def _infer_title_prefix(title: str) -> str:
    match = re.match(r"^[“\"「『]?([^|｜:：·]{2,16}?)\s*[|｜:：·]", (title or "").strip())
    if not match:
        return ""
    value = match.group(1).strip().strip("“”\"「」『』 ")
    if value in {"评论", "人民时评", "人民论坛", "今日谈", "评论员", "本报评论员"}:
        return ""
    return value


def review_comment_article(db: Session, comment_article_id: str, decision: str, note: str, reviewer: str) -> dict | None:
    record = db.query(RmrbCommentArticle).filter_by(id=comment_article_id).first()
    if not record:
        return None
    if decision not in {"approved", "excluded"}:
        raise ValueError("文章审核决定无效")
    record.article_review_status = decision
    record.article_review_note = note
    record.article_reviewed_by = reviewer
    record.article_reviewed_at = datetime.utcnow()
    deleted_quotes = 0
    filtered_articles = 0
    prefix = ""
    if decision == "excluded":
        record.workflow_status = "excluded"
        deleted_quotes += db.query(RmrbCommentQuote).filter_by(comment_article_id=record.id).delete(synchronize_session=False)
        prefix = _infer_title_prefix(record.article.display_title)
        if prefix:
            rule = db.query(RmrbCommentExclusionRule).filter_by(rule_type="title_prefix", rule_value=prefix).first()
            if rule is None:
                rule = RmrbCommentExclusionRule(
                    rule_type="title_prefix", rule_value=prefix, source_article_id=record.article_id,
                    reason=note or "文章被人工判定不属于申论评论文章，按同一标题系列自动过滤",
                    created_by=reviewer, is_active=True,
                )
                db.add(rule)
            else:
                rule.is_active = True
            candidates = db.query(RmrbCommentArticle).join(RmrbArchiveArticle).join(
                RmrbArchiveSource, RmrbArchiveSource.article_id == RmrbArchiveArticle.id
            ).filter(
                RmrbCommentArticle.article_review_status == "pending",
                RmrbArchiveSource.source_channel.like("%peopleapp_opinion%"),
            ).options(joinedload(RmrbCommentArticle.article)).distinct().all()
            for candidate in candidates:
                if (candidate.article.display_title or "").strip().startswith(prefix):
                    candidate.article_review_status = "excluded"
                    candidate.article_review_note = f"命中已审核排除的标题系列前缀：{prefix}"
                    candidate.article_reviewed_by = "auto-rule"
                    candidate.article_reviewed_at = datetime.utcnow()
                    candidate.workflow_status = "excluded"
                    deleted_quotes += db.query(RmrbCommentQuote).filter_by(comment_article_id=candidate.id).delete(synchronize_session=False)
                    filtered_articles += 1
    db.commit()
    return {"id": record.id, "articleReviewStatus": record.article_review_status,
            "exclusionTitlePrefix": prefix, "filteredArticles": filtered_articles,
            "deletedQuotes": deleted_quotes}


def _normalize_quote(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip().strip("“”\"'「」"))


def _sentence_candidates(body: str) -> list[dict[str, str]]:
    """Split the archived text into complete, source-verifiable sentences."""
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for paragraph in re.split(r"\n+", body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        # Keep terminal punctuation and its closing quotation marks attached.
        for match in re.finditer(r"[^。！？!?]*[。！？!?]+[”’」』】）》）]*", paragraph):
            sentence = match.group(0).strip()
            normalized = _normalize_quote(sentence)
            if len(normalized) < 18 or normalized in seen:
                continue
            seen.add(normalized)
            candidates.append({"id": f"S{len(candidates) + 1:03d}", "text": sentence})
    return candidates


def _bold_markers(source_url: str) -> list[str]:
    """Read editorial emphasis from the source page; the archive body is plain text."""
    if not source_url:
        return []
    try:
        response = httpx.get(source_url, timeout=20, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; ZhixingRmrbArchive/1.0)"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        content = next((soup.select_one(selector) for selector in (
            ".newsContent", ".news-content", ".article-content", ".article_content",
            ".detail-content", ".detail_content", "article", ".content",
        ) if soup.select_one(selector)), None)
        if content is None:
            return []
        markers = []
        for node in content.select("strong, b, [style*='font-weight']"):
            style = (node.get("style") or "").replace(" ", "").lower()
            if node.name not in {"strong", "b"} and not re.search(r"font-weight:(?:bold|[6-9]00)", style):
                continue
            value = node.get_text("", strip=True)
            if value:
                markers.append(value)
        return markers
    except (httpx.HTTPError, ValueError):
        return []


def _bold_sentence_candidates(body: str, source_url: str) -> list[dict[str, str]]:
    markers = [_normalize_quote(value) for value in _bold_markers(source_url)]
    if not markers:
        return []
    return [candidate for candidate in _sentence_candidates(body)
            if any(marker and (marker in _normalize_quote(candidate["text"])
                               or _normalize_quote(candidate["text"]) in marker)
                   for marker in markers)]


def _save_quote(db: Session, comment_article_id: str, data: dict, method: str) -> RmrbCommentQuote:
    text = str(data.get("text") or "").strip()
    if len(_normalize_quote(text)) < 18:
        raise ValueError("金句至少保留 18 个字，避免断章取义")
    topics = data.get("topics") if isinstance(data.get("topics"), list) else []
    use_cases = data.get("useCases") if isinstance(data.get("useCases"), list) else []
    row = RmrbCommentQuote(
        comment_article_id=comment_article_id, text=text,
        quote_type=str(data.get("quoteType") or "argument")[:32],
        topics_json=json.dumps(topics, ensure_ascii=False),
        use_cases_json=json.dumps(use_cases, ensure_ascii=False),
        application_example=str(data.get("applicationExample") or ""),
        source_evidence=text, collection_method=method,
        review_status="pending",
    )
    db.add(row)
    return row


def collect_ai_quotes(db: Session, comment_article_id: str) -> list[dict]:
    settings = get_settings()
    record = db.query(RmrbCommentArticle).filter_by(id=comment_article_id).first()
    if not record:
        raise ValueError("评论文章记录不存在")
    _require_article_approved(record)
    body = _article_body(record.article)
    if not body:
        raise ValueError("未能获取文章正文，请先检查原文链接")
    source_url = record.article.primary_source_url
    # Some client-origin articles retain the page URL as an alternate source.
    for source in record.article.sources:
        if "peopleapp_opinion" in (source.source_channel or ""):
            source_url = source.source_url
            break
    bold_candidates = _bold_sentence_candidates(body, source_url)
    candidates = bold_candidates or _sentence_candidates(body)
    if not candidates:
        raise ValueError("正文中没有可供筛选的完整句子")
    llm_available = settings.llm_enabled and bool(settings.llm_api_key)
    if not bold_candidates and not llm_available:
        raise ValueError("该文章没有网页加粗标注，需启用 AI 才能筛选金句")
    candidate_lines = "\n".join(f"{item['id']}\t{item['text']}" for item in candidates)
    if bold_candidates:
        result = {}
        try:
            if not llm_available:
                raise RuntimeError("AI 元数据补充未启用")
            result = chat_json(QUOTE_SYSTEM, f'''为下列已由原文网页加粗标注的完整句补充申论标签。必须逐条返回所有编号，不得筛除；不得输出或修改句子原文。主题标签要具体，场景从大作文立意、分论点论证、提出对策、结尾升华、综合分析、素材积累中选择；仿写示例必须标明“仿写示例”，且不得伪装成原文。只输出 JSON：{{"items":[{{"id":"S001","quoteType":"论证","topics":["主题"],"useCases":["分论点论证"],"applicationExample":"仿写示例：……"}}]}}
标题：{record.article.display_title}
句子：
{candidate_lines}''', purpose='rmrb_comment_quote_enrichment')
        except Exception:
            # Editorial emphasis itself is useful provenance; keep the candidates even
            # when metadata enrichment is temporarily unavailable.
            result = {}
    else:
        selection_rule = "从编号句中选出所有达到金句标准的候选，不设固定条数上限。只返回编号，不得输出引文文本；优先观点明确、逻辑完整、有申论迁移价值且脱离原文仍不歧义的句子，排除空泛口号、纯事实句、语义残缺句。"
        result = chat_json(QUOTE_SYSTEM, f'''你是申论教研编辑。{selection_rule}
为每个入选编号补充主题标签、申论使用场景和明确标注“仿写示例”的应用示例。场景从大作文立意、分论点论证、提出对策、结尾升华、综合分析、素材积累中选择。返回 JSON：{{"items":[{{"id":"S001","quoteType":"论证","topics":["主题"],"useCases":["分论点论证"],"applicationExample":"仿写示例：……"}}]}}
标题：{record.article.display_title}
候选完整句（句号及引号均为原文的一部分）：
{candidate_lines}''', purpose='rmrb_comment_quote_selection')
    metadata = {str(item.get("id")): item for item in result.get("items", [])
                if isinstance(item, dict) and item.get("id")}
    selected_ids = {str(value) for value in result.get("selectedIds", [])} | set(metadata)
    # Bold-marked sentences are all retained. For unmarked articles, only the
    # model-selected IDs are used; quote text always comes from the exact source.
    added = []
    seen = {_normalize_quote(row.text) for row in db.query(RmrbCommentQuote).filter_by(comment_article_id=comment_article_id).all()}
    for candidate in candidates:
        if not bold_candidates and candidate["id"] not in selected_ids:
            continue
        text = candidate["text"]
        normalized = _normalize_quote(text)
        if len(normalized) < 18 or normalized not in _normalize_quote(body):
            continue
        if normalized in seen:
            continue
        item = metadata.get(candidate["id"], {})
        item = {**item, "text": text, "quoteType": item.get("quoteType") or "论证",
                "topics": item.get("topics") or [], "useCases": item.get("useCases") or [],
                "applicationExample": item.get("applicationExample") or ""}
        row = _save_quote(db, comment_article_id, item, "bold" if bold_candidates else "ai")
        added.append(row)
        seen.add(normalized)
    db.commit()
    return [_out(row) for row in added]


def create_manual_quote(db: Session, comment_article_id: str, data: dict) -> dict:
    record = db.query(RmrbCommentArticle).filter_by(id=comment_article_id).first()
    if not record:
        raise ValueError("评论文章记录不存在")
    _require_article_approved(record)
    body = _article_body(record.article)
    quote = _normalize_quote(str(data.get("text") or ""))
    if not body or quote not in _normalize_quote(body):
        raise ValueError("金句必须能在文章原文中逐字定位")
    row = _save_quote(db, comment_article_id, data, "manual")
    db.commit(); db.refresh(row)
    return _out(row)


def review_quote(db: Session, quote_id: str, decision: str, note: str, reviewer: str) -> dict | None:
    row = db.query(RmrbCommentQuote).filter_by(id=quote_id).first()
    if not row:
        return None
    if decision not in {"approved", "rejected", "changes_requested"}:
        raise ValueError("审核决定无效")
    record = row.comment_article
    _require_article_approved(record)
    if decision == "rejected":
        db.delete(row)
        db.commit()
        return {"id": quote_id, "deleted": True}
    body = _article_body(record.article)
    if decision == "approved" and _normalize_quote(row.text) not in _normalize_quote(body):
        raise ValueError("原文无法定位该金句，不能审核通过")
    row.review_status = decision
    row.review_note = note
    row.reviewed_by = reviewer
    row.reviewed_at = datetime.utcnow()
    db.commit(); db.refresh(row)
    return _out(row)


def update_manual_quote(db: Session, quote_id: str, data: dict) -> dict | None:
    row = db.query(RmrbCommentQuote).filter_by(id=quote_id).first()
    if not row:
        return None
    if row.collection_method != "manual":
        raise ValueError("AI 金句不允许直接覆盖，请重新采集后人工审核")
    _require_article_approved(row.comment_article)
    body = _article_body(row.comment_article.article)
    text = str(data.get("text", row.text)).strip()
    if len(_normalize_quote(text)) < 18 or _normalize_quote(text) not in _normalize_quote(body):
        raise ValueError("金句必须能在文章原文中逐字定位")
    for key, attr in (("text", "text"), ("quoteType", "quote_type"), ("applicationExample", "application_example")):
        if key in data:
            setattr(row, attr, str(data[key] or ""))
    if "topics" in data: row.topics_json = json.dumps(data["topics"] or [], ensure_ascii=False)
    if "useCases" in data: row.use_cases_json = json.dumps(data["useCases"] or [], ensure_ascii=False)
    row.source_evidence = row.text
    row.review_status = "pending"
    db.commit(); db.refresh(row)
    return _out(row)


def delete_quote(db: Session, quote_id: str) -> bool:
    row = db.query(RmrbCommentQuote).filter_by(id=quote_id).first()
    if not row: return False
    db.delete(row); db.commit()
    return True
