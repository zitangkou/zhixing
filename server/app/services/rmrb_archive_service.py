"""人民日报档案文章业务：元数据入库、正文版本文件和列表查询。"""
import asyncio
import hashlib
import json
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import SessionLocal
from app.models import RmrbArchiveArticle, RmrbArchiveBatch, RmrbArchiveIssue, RmrbArchivePage, RmrbArchiveRevision, RmrbArchiveSource, gen_id
from app.services.rmrb_peopleapp_source import fetch_channel_items
from app.upload_paths import DATA_DIR

BODY_ROOT = DATA_DIR / "rmrb" / "articles"


def _json(value) -> str:
    return json.dumps(value or [], ensure_ascii=False, separators=(",", ":"))


def _parse(value: str, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _validate_url(value: str) -> str:
    value = (value or "").strip()
    if value and urlparse(value).scheme not in {"https", "http"}:
        raise ValueError("来源链接必须使用 http 或 https")
    return value


def _write_body(article_id: str, issue_date: date, revision_no: int, text: str) -> tuple[str, str, int, Path]:
    raw = text.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    relative = Path("articles") / f"{issue_date:%Y}" / f"{issue_date:%m}" / article_id / f"rev-{revision_no:04d}.md"
    target = BODY_ROOT / relative.relative_to("articles")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".body-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return relative.as_posix(), digest, len(raw), target


def _save_revision(db: Session, article: RmrbArchiveArticle, body: str, note: str = "") -> None:
    if not body.strip():
        return
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    current = db.query(RmrbArchiveRevision).filter_by(article_id=article.id, revision_no=article.current_revision).first()
    if current and current.body_sha256 == digest:
        article.body_status = "full"
        return
    revision_no = article.current_revision + 1
    storage_key, sha, size, path = _write_body(article.id, article.issue_date, revision_no, body)
    try:
        revision = RmrbArchiveRevision(
            article_id=article.id,
            revision_no=revision_no,
            body_storage_key=storage_key,
            body_sha256=sha,
            body_size_bytes=size,
            body_status="full",
            parser_version="manual-v1",
            change_note=note or ("初次保存" if revision_no == 1 else "正文更新"),
        )
        db.add(revision)
        article.current_revision = revision_no
        article.body_status = "full"
        db.flush()
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _ensure_issue_page(db: Session, issue_date: date, page_no: str, page_name: str, page_title: str, page_kind: str, directory_url: str):
    issue = db.query(RmrbArchiveIssue).filter_by(issue_date=issue_date, publication_code="rmrb").first()
    if issue is None:
        issue = RmrbArchiveIssue(issue_date=issue_date, publication_code="rmrb")
        db.add(issue)
        db.flush()
    if not page_no:
        return issue, None
    page = db.query(RmrbArchivePage).filter_by(issue_id=issue.id, page_no=page_no).first()
    if page is None:
        page = RmrbArchivePage(issue_id=issue.id, page_no=page_no, page_name=page_name, page_title=page_title, page_kind=page_kind, directory_url=directory_url)
        db.add(page)
        db.flush()
    else:
        page.page_name = page_name or page.page_name
        page.page_title = page_title or page.page_title
        page.directory_url = directory_url or page.directory_url
    return issue, page


def _add_source(db: Session, article: RmrbArchiveArticle, url: str, channel: str, relation: str, title: str, evidence: str):
    url = _validate_url(url)
    if not url:
        return
    existing = db.query(RmrbArchiveSource).filter_by(article_id=article.id, source_url=url).first()
    if existing:
        # 同一稿件可能同时出现在客户端首页和评论页；来源 URL 去重，但保留两个入口的来源标记。
        if channel.startswith("peopleapp_") and existing.source_channel.startswith("peopleapp_"):
            channels = set(existing.source_channel.split(","))
            channels.add(channel)
            existing.source_channel = ",".join(sorted(channels))
        return
    db.add(RmrbArchiveSource(
        article_id=article.id, source_url=url, source_channel=channel, source_relation=relation,
        source_display_title=title, evidence_type=evidence,
    ))


def _out(article: RmrbArchiveArticle, *, include_body: bool = False) -> dict:
    current = next((rev for rev in article.revisions if rev.revision_no == article.current_revision), None)
    body_text = None
    if include_body and current:
        path = BODY_ROOT / Path(current.body_storage_key).relative_to("articles")
        try:
            body_text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            article.body_status = "failed"
            body_text = ""
    return {
        "id": article.id,
        "issueDate": article.issue_date,
        "pageNo": article.page_no,
        "pageName": article.page_name,
        "pageRefs": _parse(article.page_refs_json, []),
        "primarySourceUrl": article.primary_source_url,
        "sourceChannel": article.source_channel,
        "displayTitle": article.display_title,
        "headline": article.headline,
        "subtitle": article.subtitle,
        "columnLabel": article.column_label,
        "seriesLabel": article.series_label,
        "eyebrow": article.eyebrow,
        "authorLine": article.author_line,
        "editorLine": article.editor_line,
        "authors": _parse(article.authors_json, []),
        "publicationTime": article.publication_time,
        "recordClass": article.record_class,
        "sourceArticleType": article.source_article_type,
        "expressionModes": _parse(article.expression_modes_json, []),
        "topics": _parse(article.topics_json, []),
        "examRelevance": article.exam_relevance,
        "examRelevanceReasons": _parse(article.exam_relevance_reasons_json, []),
        "classificationSuggestion": _parse(article.classification_suggestion_json, {}),
        "classificationMethod": article.classification_method,
        "classificationFeatureKey": article.classification_feature_key,
        "classificationHistory": _parse(article.classification_history_json, []),
        "retentionTier": article.retention_tier,
        "bodyStatus": article.body_status,
        "sourceStatus": article.source_status,
        "rightsStatus": article.rights_status,
        "reviewStatus": article.review_status,
        "currentRevision": article.current_revision,
        "bodyText": body_text,
        "bodySizeBytes": current.body_size_bytes if current else 0,
        "bodySha256": current.body_sha256 if current else "",
        "sources": [{"id": s.id, "sourceChannel": s.source_channel, "sourceUrl": s.source_url, "sourceRelation": s.source_relation, "sourceDisplayTitle": s.source_display_title, "evidenceType": s.evidence_type, "fetchedAt": s.fetched_at} for s in article.sources],
        "revisions": [{"id": r.id, "revisionNo": r.revision_no, "bodyStorageKey": r.body_storage_key, "bodySha256": r.body_sha256, "bodySizeBytes": r.body_size_bytes, "bodyStatus": r.body_status, "parserVersion": r.parser_version, "changeNote": r.change_note, "createdAt": r.created_at} for r in sorted(article.revisions, key=lambda row: row.revision_no, reverse=True)],
        "createdAt": article.created_at,
        "updatedAt": article.updated_at,
    }


def list_articles(db: Session, *, issue_date: date | None = None, date_from: date | None = None, date_to: date | None = None,
                  page_no: str | None = None, page_name: str | None = None, title: str | None = None,
                  article_type: str | None = None, record_class: str | None = None, exam_relevance: str | None = None,
                  retention_tier: str | None = None, author: str | None = None, editor: str | None = None, body_status: str | None = None,
                  review_status: str | None = None, source_channel: str | None = None, page: int = 1, page_size: int = 20):
    query = db.query(RmrbArchiveArticle).filter(RmrbArchiveArticle.is_archived.is_(False))
    if issue_date: query = query.filter(RmrbArchiveArticle.issue_date == issue_date)
    if date_from: query = query.filter(RmrbArchiveArticle.issue_date >= date_from)
    if date_to: query = query.filter(RmrbArchiveArticle.issue_date <= date_to)
    if page_no:
        page_ref_match = f'%"pageNo":"{page_no.strip()}"%'
        query = query.filter(or_(RmrbArchiveArticle.page_no == page_no.strip(), RmrbArchiveArticle.page_refs_json.like(page_ref_match)))
    if page_name: query = query.filter(RmrbArchiveArticle.page_name.ilike(f"%{page_name.strip()}%"))
    if title: query = query.filter(or_(RmrbArchiveArticle.display_title.ilike(f"%{title.strip()}%"), RmrbArchiveArticle.headline.ilike(f"%{title.strip()}%"), RmrbArchiveArticle.subtitle.ilike(f"%{title.strip()}%")))
    if article_type: query = query.filter(RmrbArchiveArticle.source_article_type == article_type)
    if record_class: query = query.filter(RmrbArchiveArticle.record_class == record_class)
    if exam_relevance: query = query.filter(RmrbArchiveArticle.exam_relevance == exam_relevance)
    if retention_tier: query = query.filter(RmrbArchiveArticle.retention_tier == retention_tier)
    if author: query = query.filter(RmrbArchiveArticle.author_line.ilike(f"%{author.strip()}%"))
    if editor: query = query.filter(RmrbArchiveArticle.editor_line.ilike(f"%{editor.strip()}%"))
    if body_status: query = query.filter(RmrbArchiveArticle.body_status == body_status)
    if review_status: query = query.filter(RmrbArchiveArticle.review_status == review_status)
    if source_channel: query = query.filter(RmrbArchiveArticle.source_channel == source_channel)
    total = query.with_entities(func.count(RmrbArchiveArticle.id)).scalar() or 0
    rows = query.options(selectinload(RmrbArchiveArticle.sources), selectinload(RmrbArchiveArticle.revisions)).order_by(
        RmrbArchiveArticle.issue_date.desc(), RmrbArchiveArticle.page_no.asc(), RmrbArchiveArticle.id.asc()
    ).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_out(row) for row in rows], "total": total, "page": page, "pageSize": page_size}


def get_article(db: Session, article_id: str, include_body: bool = True):
    article = db.query(RmrbArchiveArticle).options(selectinload(RmrbArchiveArticle.sources), selectinload(RmrbArchiveArticle.revisions)).filter_by(id=article_id, is_archived=False).first()
    return _out(article, include_body=include_body) if article else None


def create_article(db: Session, data) -> dict:
    title = data.displayTitle.strip()
    primary_url = _validate_url(data.primarySourceUrl)
    if data.recordClass == "article" and not primary_url:
        raise ValueError("正式文章必须填写可回溯的原文链接")
    if data.retentionTier == "full_text" and not (data.bodyText or "").strip():
        raise ValueError("全文保存级别需要提供正文")
    if data.bodyText and data.retentionTier != "full_text":
        raise ValueError("仅完整正文保存等级可以保存文章正文")
    if data.reviewStatus == "auto_approved":
        raise ValueError("规则自动确认状态由系统生成，不能手动创建")
    if data.reviewStatus == "approved" and (data.sourceArticleType == "undetermined" or data.examRelevance == "pending"):
        raise ValueError("人工复核通过前，请确认稿件体裁和申论关联")
    issue, page = _ensure_issue_page(db, data.issueDate, data.pageNo.strip(), data.pageName.strip(), data.pageTitle, data.pageKind, _validate_url(data.directoryUrl))
    article = RmrbArchiveArticle(
        issue_id=issue.id, page_id=page.id if page else None, issue_date=data.issueDate,
        page_no=data.pageNo.strip(), page_name=data.pageName.strip(), primary_source_url=primary_url,
        source_channel=data.sourceChannel, display_title=title, headline=(data.headline or title).strip(), subtitle=data.subtitle.strip(),
        column_label=data.columnLabel.strip(), series_label=data.seriesLabel.strip(), eyebrow=data.eyebrow.strip(), author_line=data.authorLine.strip(), editor_line=data.editorLine.strip(),
        authors_json=_json(data.authors), publication_time=data.publicationTime.strip(), record_class=data.recordClass,
        source_article_type=data.sourceArticleType, expression_modes_json=_json(data.expressionModes), topics_json=_json(data.topics),
        exam_relevance=data.examRelevance, exam_relevance_reasons_json=_json(data.examRelevanceReasons), retention_tier=data.retentionTier,
        body_status="not_fetched", rights_status=data.rightsStatus, review_status=data.reviewStatus,
        extra_json=json.dumps(data.extra or {}, ensure_ascii=False),
    )
    db.add(article)
    db.flush()
    if data.reviewStatus == "approved":
        article.classification_method = "manual"
        article.classification_feature_key = _classification_feature(article)
        article.classification_history_json = json.dumps([{
            "source": "human", "reviewedAt": datetime.now(BEIJING).isoformat(timespec="seconds"),
            "sourceArticleType": article.source_article_type, "examRelevance": article.exam_relevance,
            "topics": _parse(article.topics_json, []), "reasons": _parse(article.exam_relevance_reasons_json, []),
            "featureKey": article.classification_feature_key, "suggestionMethod": "manual_create",
        }], ensure_ascii=False, separators=(",", ":"))
    else:
        _apply_classification_suggestion(db, article)
    if primary_url:
        _add_source(db, article, primary_url, data.sourceChannel, data.sourceRelation, title, "full_text" if data.bodyText else "directory")
    if data.directoryUrl:
        _add_source(db, article, data.directoryUrl, data.sourceChannel, "directory", title, "directory")
    if data.bodyText:
        _save_revision(db, article, data.bodyText, "初次保存")
    db.commit()
    return get_article(db, article.id)


def update_article(db: Session, article_id: str, data) -> dict | None:
    article = db.query(RmrbArchiveArticle).filter_by(id=article_id, is_archived=False).first()
    if not article:
        return None
    changes = data.model_dump(exclude_unset=True)
    body = changes.pop("bodyText", None)
    previous_review_status = article.review_status
    previous_labels = (article.source_article_type, article.exam_relevance)
    previous_url = article.primary_source_url
    json_fields = {"authors": "authors_json", "expressionModes": "expression_modes_json", "topics": "topics_json", "examRelevanceReasons": "exam_relevance_reasons_json", "extra": "extra_json"}
    field_map = {
        "pageNo": "page_no", "pageName": "page_name", "primarySourceUrl": "primary_source_url", "displayTitle": "display_title",
        "headline": "headline", "subtitle": "subtitle", "columnLabel": "column_label", "seriesLabel": "series_label", "eyebrow": "eyebrow",
        "authorLine": "author_line", "editorLine": "editor_line", "publicationTime": "publication_time", "recordClass": "record_class", "sourceArticleType": "source_article_type",
        "examRelevance": "exam_relevance", "retentionTier": "retention_tier", "rightsStatus": "rights_status", "reviewStatus": "review_status",
    }
    for key, value in changes.items():
        if key == "primarySourceUrl":
            value = _validate_url(value)
        if key in json_fields:
            value = json.dumps(value or {}, ensure_ascii=False) if key == "extra" else _json(value)
            key = json_fields[key]
        else:
            key = field_map.get(key, key)
        setattr(article, key, value)
    if article.record_class == "article" and not article.primary_source_url:
        raise ValueError("正式文章必须保留可回溯的原文链接")
    if body is not None:
        if changes.get("retentionTier", article.retention_tier) != "full_text":
            raise ValueError("仅完整正文保存等级可以保存文章正文")
        _save_revision(db, article, body, "管理端编辑正文")
    if article.retention_tier == "full_text" and article.current_revision == 0:
        raise ValueError("全文保存级别需要提供正文")
    if article.review_status == "approved":
        if article.source_article_type == "undetermined" or article.exam_relevance == "pending":
            raise ValueError("人工复核通过前，请确认稿件体裁和申论关联；暂不能判断时请保持待复核")
        if previous_review_status != "approved" or previous_labels != (article.source_article_type, article.exam_relevance):
            history = _parse(article.classification_history_json, [])
            suggestion = _parse(article.classification_suggestion_json, {})
            history.append({
                "source": "human", "reviewedAt": datetime.now(BEIJING).isoformat(timespec="seconds"),
                "sourceArticleType": article.source_article_type, "examRelevance": article.exam_relevance,
                "topics": _parse(article.topics_json, []), "reasons": _parse(article.exam_relevance_reasons_json, []),
                "featureKey": _classification_feature(article),
                "suggestionMethod": suggestion.get("method", "none"),
            })
            article.classification_history_json = json.dumps(history, ensure_ascii=False, separators=(",", ":"))
            article.classification_method = "manual"
            article.classification_feature_key = _classification_feature(article)
    if article.review_status == "auto_approved" and article.classification_method != "human_pattern_auto_v1":
        raise ValueError("规则自动确认只能由系统生成")
    if article.primary_source_url and article.primary_source_url != previous_url:
        _add_source(db, article, article.primary_source_url, article.source_channel, "updated_source", article.display_title, "manual")
    if article.review_status != "approved":
        _apply_classification_suggestion(db, article)
    db.commit()
    return get_article(db, article.id)


def archive_article(db: Session, article_id: str) -> bool:
    article = db.query(RmrbArchiveArticle).filter_by(id=article_id, is_archived=False).first()
    if not article:
        return False
    article.is_archived = True
    db.commit()
    return True

# -------- 每日电子报目录采集（正文仅按 retention_tier=full_text 另行保存） --------

BEIJING = ZoneInfo("Asia/Shanghai")
EPAPER_BASE = "https://paper.people.com.cn/rmrb/pc/layout/"
USER_AGENT = "Mozilla/5.0 (compatible; ZhixingRmrbArchive/1.0)"


def _fetch_layout(issue_date: date, page_no: str = "01") -> tuple[str, str]:
    url = f"{EPAPER_BASE}{issue_date:%Y%m}/{issue_date:%d}/node_{int(page_no):02d}.html"
    response = httpx.get(url, timeout=20, headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"}, follow_redirects=True)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return str(response.url), response.text


def _parse_index(issue_date: date, html: str, page_url: str):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    expected = f"{issue_date.year}年{issue_date.month}月{issue_date.day}日"
    date_pattern = rf"{issue_date.year}年0?{issue_date.month}月0?{issue_date.day}日"
    if not re.search(date_pattern, text):
        raise RuntimeError(f"当天电子报尚未就绪，页面未确认刊期 {expected}")
    pages: dict[str, dict] = {}
    for anchor in soup.find_all("a", href=True):
        # 首页同时含纸报版面导航和“手机版”入口；后者也叫 node_01，不能覆盖纸报 01 版。
        if "/pad/" in anchor["href"].replace("\\", "/"):
            continue
        match = re.search(r"node_(\d{1,2})\.html", anchor["href"])
        label = " ".join(anchor.stripped_strings)
        if match and "版" in label:
            number = f"{int(match.group(1)):02d}"
            page_name = re.sub(r"^\s*\d+版[：:]?\s*", "", label).strip()
            pages[number] = {"page_no": number, "page_name": page_name, "page_url": urljoin(page_url, anchor["href"])}
    if not pages:
        raise RuntimeError("已识别刊期，但没有解析到版面目录")
    return list(pages.values())


def _parse_page(page: dict):
    if "广告" in page["page_name"]:
        return page, []
    response = httpx.get(page["page_url"], timeout=20, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    found = {}
    for anchor in soup.find_all("a", href=True):
        title = " ".join(anchor.stripped_strings)
        href = anchor["href"].strip()
        if not title or title in {"导读", "版面导读"} or not re.search(r"content_\d+\.html(?:[?#].*)?$", href):
            continue
        if re.match(r"^(?:(?:本版|[一二三四五六七八九十\d]+版)?责编|责任编辑|版面编辑)\s*[：:]?", title):
            continue
        article_url = urljoin(str(response.url), href)
        found.setdefault(article_url, {"title": title, "url": article_url})
    return page, list(found.values())


def _normalize_title(title: str) -> str:
    normalized = re.sub(r"[\s\W_]+", "", (title or "").casefold())
    for label in ("今日谈", "人民时评", "人民论坛", "人民锐评", "锐评"):
        normalized = normalized.replace(label.casefold(), "")
    return normalized


def _classification_feature(article: RmrbArchiveArticle) -> str:
    """从栏目/系列名提取可复用审核特征，供后续基于人工确认结果学习。"""
    generic = {"要闻", "评论", "经济", "国际", "社会", "文化", "副刊", "体育", "理论", "综合"}
    suffix = re.search(r"[（(]([^（）()]{2,36})[）)]\s*$", article.display_title or "")
    for value in (article.series_label, suffix.group(1) if suffix else "", article.column_label):
        key = _normalize_title(value or "")
        if len(key) >= 3 and key not in generic:
            return key
    return ""


def _majority(values: list[str], minimum: int = 5, agreement: float = 0.9) -> tuple[str, int, float] | None:
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    if not counts:
        return None
    value, count = max(counts.items(), key=lambda item: item[1])
    share = count / sum(counts.values())
    return (value, count, share) if count >= minimum and share >= agreement else None


def _rule_classification(article: RmrbArchiveArticle) -> dict:
    title = " ".join((article.display_title or "", article.column_label or "", article.series_label or ""))
    compact = _normalize_title(title)
    result = {
        "sourceArticleType": "undetermined", "examRelevance": "pending", "confidence": 0.25,
        "method": "metadata_rules_v1", "reasons": ["当前档案未保存正文；标题和栏目不足以可靠判断申论适配度，需人工查看原文。"],
    }
    rules = [
        (r"^(图片报道|图片新闻|图说)$", "picture_report", 0.99, "标题明确标注为图片/图说报道"),
        (r"社论", "editorial", 0.97, "标题或栏目明确出现“社论”"),
        (r"今日谈|人民时评|人民论坛|人民锐评|国际论坛|和音", "commentary", 0.96, "栏目/标题属于明确的评论栏目"),
        (r"政策解读|政策问答|答记者问|权威访谈", "policy_qa", 0.93, "标题明确标注政策解读、问答或答记者问"),
        (r"理论文章|理论学习|理论研究", "theory", 0.91, "标题明确标注理论文章/学习/研究"),
        (r"专访|访谈|记者对话|对话", "interview", 0.89, "标题明确标注专访、访谈或对话"),
        (r"记者手记|记者观察|记者再走|调查报道|深度调查|田间探新|身边的创新", "feature_investigation", 0.87, "标题/系列名显示为现场、调查或深度报道"),
        (r"副刊|文学|散文|诗歌|小说", "cultural_work", 0.84, "标题/栏目显示为文化副刊或文学作品"),
    ]
    for pattern, article_type, confidence, reason in rules:
        if re.search(pattern, compact):
            result.update(sourceArticleType=article_type, confidence=confidence, reasons=[reason, result["reasons"][0]])
            break
    if result["sourceArticleType"] == "undetermined":
        result["reasons"].insert(0, "标题/栏目没有命中高置信度体裁规则，转人工复核。")
    return result


def _classification_suggestion(db: Session, article: RmrbArchiveArticle) -> dict:
    suggestion = _rule_classification(article)
    feature_key = _classification_feature(article)
    if not feature_key:
        return suggestion
    reviewed = db.query(RmrbArchiveArticle).filter(
        RmrbArchiveArticle.id != article.id,
        RmrbArchiveArticle.is_archived.is_(False),
        RmrbArchiveArticle.review_status == "approved",
        RmrbArchiveArticle.classification_method == "manual",
        RmrbArchiveArticle.classification_feature_key == feature_key,
    ).all()
    type_votes = [row.source_article_type for row in reviewed if row.source_article_type != "undetermined"]
    relevance_votes = [row.exam_relevance for row in reviewed if row.exam_relevance != "pending"]
    learned_type = _majority(type_votes)
    learned_relevance = _majority(relevance_votes)
    if learned_type:
        article_type, count, share = learned_type
        suggestion.update(sourceArticleType=article_type, confidence=round(share, 3), method="human_pattern_v1")
        suggestion["reasons"].insert(0, f"同栏目/系列已有 {len(type_votes)} 条人工确认样本，体裁一致率 {share:.0%}。")
    if learned_relevance:
        relevance, count, share = learned_relevance
        suggestion["examRelevance"] = relevance
        suggestion["confidence"] = min(suggestion["confidence"], round(share, 3)) if learned_type else round(share, 3)
        suggestion["reasons"].insert(0, f"同栏目/系列已有 {len(relevance_votes)} 条人工确认样本，申论关联一致率 {share:.0%}。")
    suggestion["featureKey"] = feature_key
    return suggestion


def _apply_classification_suggestion(db: Session, article: RmrbArchiveArticle) -> None:
    if article.review_status in {"approved", "auto_approved"}:
        return
    suggestion = _classification_suggestion(db, article)
    article.classification_suggestion_json = json.dumps(suggestion, ensure_ascii=False, separators=(",", ":"))
    article.classification_method = suggestion["method"]
    article.classification_feature_key = suggestion.get("featureKey", "")
    if suggestion["method"] == "human_pattern_v1" and suggestion["sourceArticleType"] != "undetermined" and suggestion["examRelevance"] != "pending" and suggestion["confidence"] >= 0.9:
        article.source_article_type = suggestion["sourceArticleType"]
        article.exam_relevance = suggestion["examRelevance"]
        article.exam_relevance_reasons_json = _json(suggestion["reasons"])
        article.review_status = "auto_approved"
        article.classification_method = "human_pattern_auto_v1"


def _record_page_ref(article: RmrbArchiveArticle, page: dict, item: dict, relation: str = "listed") -> None:
    refs = _parse(article.page_refs_json, [])
    ref = {
        "pageNo": page["page_no"], "pageName": page["page_name"],
        "directoryUrl": page["page_url"], "articleUrl": item["url"], "relation": relation,
    }
    key = (ref["pageNo"], ref["articleUrl"])
    if not any((x.get("pageNo"), x.get("articleUrl")) == key for x in refs):
        refs.append(ref)
        refs.sort(key=lambda x: (int(x.get("pageNo") or 999), x.get("articleUrl") or ""))
        article.page_refs_json = json.dumps(refs, ensure_ascii=False, separators=(",", ":"))


def _article_content_fingerprint(url: str) -> str:
    """仅对跨版同标题候选读取原文并计算指纹，不保存文章正文。"""
    response = httpx.get(url, timeout=20, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.select_one("#ozoom")
    if content is None:
        return ""
    normalized = re.sub(r"\s+", "", content.get_text(" ", strip=True))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""


def _peopleapp_original_titles(url: str) -> list[str]:
    """客户端稿件页通常保留“原标题”和正文标题，作为纸报版面关联证据。"""
    try:
        response = httpx.get(url, timeout=20, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.select_one(".newsContent")
        if content is None:
            return []
        parts = list(content.stripped_strings)
        titles = []
        for index, part in enumerate(parts[:3]):
            if part.startswith("原标题："):
                titles.append(part.removeprefix("原标题：").rstrip("—- "))
                if index + 1 < len(parts):
                    titles.append(parts[index + 1])
            elif index == 0 and len(part) < 120:
                titles.append(part)
        return [title for title in titles if title]
    except Exception:
        return []


def _merge_duplicate_article(db: Session, canonical: RmrbArchiveArticle, duplicate: RmrbArchiveArticle) -> RmrbArchiveArticle:
    if canonical.id == duplicate.id:
        return canonical
    if duplicate.current_revision or duplicate.revisions:
        raise ValueError("跨版重复记录已有正文版本，停止自动合并")
    for ref in _parse(duplicate.page_refs_json, []):
        _record_page_ref(canonical, {
            "page_no": ref.get("pageNo", ""), "page_name": ref.get("pageName", ""),
            "page_url": ref.get("directoryUrl", ""),
        }, {"url": ref.get("articleUrl", "")}, ref.get("relation", "same_content_on_other_page"))
    for source in list(duplicate.sources):
        existing = db.query(RmrbArchiveSource.id).filter_by(article_id=canonical.id, source_url=source.source_url).first()
        if existing:
            db.delete(source)
        else:
            source.article_id = canonical.id
            if source.source_channel == "people_daily_epaper":
                source.source_relation = "same_article_other_page"
    if not canonical.author_line and duplicate.author_line:
        canonical.author_line = duplicate.author_line
    if not canonical.editor_line and duplicate.editor_line:
        canonical.editor_line = duplicate.editor_line
    db.delete(duplicate)
    db.flush()
    return canonical


def create_manual_batch(db: Session, issue_date: date) -> dict:
    batch = RmrbArchiveBatch(
        run_key=f"manual:{gen_id('')}", issue_date=issue_date, trigger_mode="manual", status="queued",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch_to_out(batch)


def batch_to_out(batch: RmrbArchiveBatch) -> dict:
    return {
        "id": batch.id, "issueDate": batch.issue_date, "triggerMode": batch.trigger_mode, "status": batch.status,
        "expectedPageCount": batch.expected_page_count, "completedPageCount": batch.completed_page_count,
        "discoveredArticleCount": batch.discovered_article_count, "createdArticleCount": batch.created_article_count,
        "failedPageCount": batch.failed_page_count, "failedSourceCount": batch.failed_source_count, "errorSummary": batch.error_summary,
        "startedAt": batch.started_at, "finishedAt": batch.finished_at, "createdAt": batch.created_at,
    }


def list_batches(db: Session, limit: int = 30) -> list[dict]:
    rows = db.query(RmrbArchiveBatch).order_by(RmrbArchiveBatch.issue_date.desc(), RmrbArchiveBatch.created_at.desc()).limit(limit).all()
    return [batch_to_out(row) for row in rows]


def _set_batch_error(batch: RmrbArchiveBatch, message: str, status: str = "failed"):
    batch.status = status
    batch.error_summary = message[:4000]
    batch.finished_at = datetime.now(BEIJING).replace(tzinfo=None) if status != "waiting_for_source" else None


def run_collection_batch(batch_id: str) -> None:
    """后台线程执行；文章目录广覆盖，默认不抓全文以控制成本和正文留存量。"""
    db = SessionLocal()
    try:
        batch = db.get(RmrbArchiveBatch, batch_id)
        if not batch or batch.status in {"completed", "failed"}:
            return
        now = datetime.now(BEIJING).replace(tzinfo=None)
        claim = db.query(RmrbArchiveBatch).filter(RmrbArchiveBatch.id == batch_id).filter(
            or_(RmrbArchiveBatch.status != "running", RmrbArchiveBatch.started_at.is_(None), RmrbArchiveBatch.started_at < now - timedelta(minutes=30))
        ).update({"status": "running", "started_at": now, "finished_at": None, "error_summary": ""}, synchronize_session=False)
        if not claim:
            db.rollback()
            return
        db.commit()
        batch = db.get(RmrbArchiveBatch, batch_id)
        if not batch:
            return
        issue_date = batch.issue_date

        try:
            index_url, index_html = _fetch_layout(issue_date)
            pages = _parse_index(issue_date, index_html, index_url)
        except Exception as exc:
            _set_batch_error(batch, f"来源就绪检查失败：{exc}", "waiting_for_source")
            db.commit()
            return

        page_results = []
        failures = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(_parse_page, p) for p in pages]
            for future in as_completed(futures):
                try:
                    page_results.append(future.result())
                except Exception as exc:
                    failures.append(str(exc))
        page_results.sort(key=lambda item: int(item[0]["page_no"]))

        # 同一期同标题跨版列出时，先比对原文正文指纹；仅正文完全一致才合并为一篇、保留多个版面引用。
        # 泛化图片标题容易误合并，明确排除；标题相同但正文不同则继续作为不同稿件保存。
        title_groups: dict[str, list[dict]] = {}
        ignored_titles = {"图片报道", "图片新闻", "图说"}
        for page_data, article_rows in page_results:
            for item in article_rows:
                title_key = _normalize_title(item["title"])
                if title_key and item["title"].strip() not in ignored_titles:
                    title_groups.setdefault(title_key, []).append({**item, "page_no": page_data["page_no"]})
        cross_page_canonical: dict[str, str] = {}
        candidates = [rows for rows in title_groups.values() if len({row["page_no"] for row in rows}) > 1]
        fingerprint_urls = list({row["url"] for rows in candidates for row in rows})
        fingerprints: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_urls = {pool.submit(_article_content_fingerprint, url): url for url in fingerprint_urls}
            for future in as_completed(future_urls):
                url = future_urls[future]
                try:
                    fingerprints[url] = future.result()
                except Exception:
                    fingerprints[url] = ""
        for rows in candidates:
            by_fingerprint: dict[str, list[dict]] = {}
            for row in rows:
                fingerprint = fingerprints.get(row["url"], "")
                if fingerprint:
                    by_fingerprint.setdefault(fingerprint, []).append(row)
            for same_content in by_fingerprint.values():
                if len({row["page_no"] for row in same_content}) < 2:
                    continue
                same_content.sort(key=lambda row: (int(row["page_no"]), row["url"]))
                canonical_url = same_content[0]["url"]
                for row in same_content[1:]:
                    cross_page_canonical[row["url"]] = canonical_url

        issue, _ = _ensure_issue_page(db, issue_date, "", "", "", "regular", "")
        issue.expected_page_count = len(pages)
        issue.status = "partial" if failures else "directory_complete"
        created_count = 0
        discovered_count = 0
        completed_pages = 0
        for page_data, article_rows in page_results:
            page_row = db.query(RmrbArchivePage).filter_by(issue_id=issue.id, page_no=page_data["page_no"]).first()
            if page_row is None:
                page_row = RmrbArchivePage(issue_id=issue.id, page_no=page_data["page_no"])
                db.add(page_row)
                db.flush()
            page_row.page_name = page_data["page_name"]
            page_row.directory_url = page_data["page_url"]
            page_row.directory_status = "parsed"
            page_row.page_kind = "advertising" if "广告" in page_data["page_name"] else "regular"
            for item in article_rows:
                discovered_count += 1
                canonical_url = cross_page_canonical.get(item["url"], item["url"])
                article = db.query(RmrbArchiveArticle).filter_by(primary_source_url=canonical_url).first()
                if article is None and canonical_url != item["url"]:
                    article = db.query(RmrbArchiveArticle).filter_by(primary_source_url=item["url"]).first()
                    if article:
                        article.primary_source_url = canonical_url
                if article and canonical_url == item["url"]:
                    duplicate = db.query(RmrbArchiveArticle).filter(
                        RmrbArchiveArticle.primary_source_url != canonical_url,
                        RmrbArchiveArticle.issue_date == issue_date,
                        RmrbArchiveArticle.display_title == item["title"],
                    ).all()
                    for other in duplicate:
                        if cross_page_canonical.get(other.primary_source_url) == canonical_url:
                            _merge_duplicate_article(db, article, other)
                if article is None and item["title"].strip() not in {"图片报道", "图片新闻", "图说"}:
                    normalized_title = _normalize_title(item["title"])
                    client_candidates = db.query(RmrbArchiveArticle).filter(
                        RmrbArchiveArticle.issue_date == issue_date,
                        RmrbArchiveArticle.source_channel.in_(("peopleapp_home", "peopleapp_opinion")),
                    ).all()
                    article = next((candidate for candidate in client_candidates
                                    if normalized_title and _normalize_title(candidate.display_title) == normalized_title), None)
                if article is None:
                    article = RmrbArchiveArticle(
                        issue_id=issue.id, page_id=page_row.id, page_no=page_data["page_no"], page_name=page_data["page_name"],
                        issue_date=issue_date, primary_source_url=item["url"], source_channel="people_daily_epaper",
                        display_title=item["title"], headline=item["title"], record_class="article", source_article_type="undetermined",
                        exam_relevance="pending", retention_tier="metadata_only", body_status="not_fetched", source_status="directory_confirmed",
                        review_status="pending",
                    )
                    db.add(article)
                    db.flush()
                    created_count += 1
                else:
                    previous_primary_url = article.primary_source_url
                    if article.source_channel in {"peopleapp_home", "peopleapp_opinion"}:
                        for source in article.sources:
                            if source.source_url == previous_primary_url:
                                source.source_relation = "same_article"
                        article.primary_source_url = item["url"]
                        article.source_channel = "people_daily_epaper"
                        article.display_title = item["title"]
                        article.headline = item["title"]
                    if not article.page_no or int(page_data["page_no"]) < int(article.page_no):
                        article.page_id = page_row.id
                        article.page_no = page_data["page_no"]
                        article.page_name = page_data["page_name"]
                    article.issue_date = issue_date
                relation = "primary_source" if item["url"] == canonical_url else "same_article_other_page"
                _add_source(db, article, item["url"], "people_daily_epaper", relation, item["title"], "directory")
                _record_page_ref(article, page_data, item, "listed" if item["url"] == canonical_url else "same_content_on_other_page")
            completed_pages += 1

        page_failure_count = len(failures)
        source_failure_count = 0
        # 客户端首页/评论页用于补充发现和交叉验证；列表解析失败不影响电子报文章目录。
        # 两个页面共享同一个滚动 24 小时窗口，按明确的 publishTime 筛选，
        # 与本次电子报期号日期无关；跨午夜的文章按各自发布日期归档。
        peopleapp_window_end = datetime.now(BEIJING)
        peopleapp_window_start = peopleapp_window_end - timedelta(hours=24)
        for channel in ("peopleapp_home", "peopleapp_opinion"):
            try:
                client_items = fetch_channel_items(channel, peopleapp_window_start, peopleapp_window_end)
            except Exception as exc:
                failures.append(f"{channel}: {exc}")
                source_failure_count += 1
                continue
            for item in client_items:
                discovered_count += 1
                article = db.query(RmrbArchiveArticle).filter_by(primary_source_url=item["url"]).first()
                if article is None or (article.source_channel in {"peopleapp_home", "peopleapp_opinion"} and not article.page_no):
                    candidates = db.query(RmrbArchiveArticle).filter(RmrbArchiveArticle.issue_date == item["issue_date"]).all()
                    normalized_title = _normalize_title(item["title"])
                    if normalized_title:
                        match = next((candidate for candidate in candidates if candidate.source_channel == "people_daily_epaper" and _normalize_title(candidate.display_title) == normalized_title), None)
                        if match:
                            article = _merge_duplicate_article(db, match, article) if article and article.id != match.id else match
                        else:
                            match = next((candidate for candidate in candidates if candidate.id != (article.id if article else None) and candidate.source_channel in {"peopleapp_home", "peopleapp_opinion"} and _normalize_title(candidate.display_title) == normalized_title), None)
                            if match:
                                article = _merge_duplicate_article(db, match, article) if article else match
                    # 客户端标题可能是传播标题；优先用稿件页明确给出的原标题与电子报目录标题关联。
                    if article is None or (article.source_channel in {"peopleapp_home", "peopleapp_opinion"} and not article.page_no):
                        original_titles = {_normalize_title(title) for title in _peopleapp_original_titles(item["url"])}
                        original_titles.discard("")
                        for candidate in candidates:
                            paper_title = _normalize_title(candidate.display_title)
                            eligible = candidate.source_channel == "people_daily_epaper" or candidate.source_channel in {"peopleapp_home", "peopleapp_opinion"}
                            if eligible and candidate.id != (article.id if article else None) and len(paper_title) >= 8 and any(
                                paper_title == title or paper_title in title or title in paper_title for title in original_titles if len(title) >= 8
                            ):
                                article = _merge_duplicate_article(db, candidate, article) if article and article.id != candidate.id else candidate
                                break
                if article is None:
                    item_issue, _ = _ensure_issue_page(db, item["issue_date"], "", "", "", "regular", "")
                    article = RmrbArchiveArticle(
                        issue_id=item_issue.id, issue_date=item["issue_date"], page_no="", page_name="",
                        primary_source_url=item["url"], source_channel=channel, display_title=item["title"], headline=item["title"],
                        author_line=item["author_line"], publication_time=item["publication_time"], record_class="article",
                        source_article_type="undetermined", exam_relevance="pending", retention_tier="metadata_only",
                        body_status="not_fetched", source_status="metadata_confirmed", review_status="pending",
                    )
                    db.add(article)
                    db.flush()
                    created_count += 1
                _add_source(db, article, item["url"], channel, "same_article", item["title"], "client_card")
        for article in db.query(RmrbArchiveArticle).filter_by(issue_date=issue_date, is_archived=False).all():
            _apply_classification_suggestion(db, article)
        batch.expected_page_count = len(pages)
        batch.completed_page_count = completed_pages
        batch.discovered_article_count = discovered_count
        batch.created_article_count = created_count
        batch.failed_page_count = page_failure_count
        batch.failed_source_count = source_failure_count
        batch.status = "partial" if failures else "completed"
        batch.error_summary = "\n".join(failures[:50])
        batch.finished_at = datetime.now(BEIJING).replace(tzinfo=None)
        db.commit()
    except Exception as exc:
        db.rollback()
        batch = db.get(RmrbArchiveBatch, batch_id)
        if batch:
            _set_batch_error(batch, f"采集异常：{exc}")
            db.commit()
    finally:
        db.close()


def run_scheduled_issue(issue_date: date) -> None:
    db = SessionLocal()
    try:
        run_key = f"daily:{issue_date.isoformat()}"
        batch = db.query(RmrbArchiveBatch).filter_by(run_key=run_key).first()
        now = datetime.now(BEIJING).replace(tzinfo=None)
        if batch is None:
            batch = RmrbArchiveBatch(run_key=run_key, issue_date=issue_date, trigger_mode="scheduled", status="queued")
            db.add(batch)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                return
            db.refresh(batch)
        if batch.status == "completed":
            return
        if batch.status == "running" and batch.started_at and (now - batch.started_at) < timedelta(minutes=30):
            return
        batch.status = "queued"
        db.commit()
        batch_id = batch.id
    finally:
        db.close()
    run_collection_batch(batch_id)


async def rmrb_daily_scheduler_loop() -> None:
    """每天 06:10 开始检查，未发布时每 10 分钟重试至 08:00。"""
    while True:
        now = datetime.now(BEIJING)
        today_start = datetime.combine(now.date(), time(6, 10), tzinfo=BEIJING)
        today_cutoff = datetime.combine(now.date(), time(8, 0), tzinfo=BEIJING)
        if now < today_start:
            delay = (today_start - now).total_seconds()
        elif now <= today_cutoff:
            try:
                await asyncio.to_thread(run_scheduled_issue, now.date())
            except Exception:
                pass
            delay = 10 * 60
        else:
            tomorrow = now.date() + timedelta(days=1)
            next_run = datetime.combine(tomorrow, time(6, 10), tzinfo=BEIJING)
            delay = (next_run - now).total_seconds()
        await asyncio.sleep(max(1, delay))
