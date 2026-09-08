from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ---- 文章管理 ----
@router.get("/articles")
def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    _admin=Depends(require_permission("article:read")),
    db: Session = Depends(get_db),
):
    q = db.query(Article)
    if keyword:
        q = q.filter(Article.title.contains(keyword))
    if status:
        q = q.filter(Article.status == status)
    total = q.count()
    rows = q.order_by(Article.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ApiResponse.ok({
        "total": total,
        "items": [article_to_out(a).model_dump() for a in rows],
    })


@router.get("/articles/{article_id}")
def get_article(
    article_id: str,
    _admin=Depends(require_permission("article:read")),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文章不存在")
    return ApiResponse.ok(article_to_out(article).model_dump())


@router.post("/articles/infer-metadata")
def infer_article_metadata_api(
    body: ArticleInferMetadataBody,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    result = infer_article_metadata(db, content=body.content, title=body.title)
    return ApiResponse.ok({
        "title": result["title"],
        "content": result["content"],
        "source": result["source"],
        "sourceUrl": result["source_url"],
        "publishDate": result["publish_date"],
        "summary": result["summary"],
        "tags": result["tags"],
        "categoryId": result["category_id"],
        "categoryName": result["category_name"],
        "importance": result["importance"],
    })


@router.post("/articles")
def create_article(
    body: ArticleCreate,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    merged = merge_article_fields(
        db,
        title=body.title,
        source=body.source,
        source_url=body.source_url,
        publish_date=body.publish_date,
        summary=body.summary,
        content=body.content,
        tags=body.tags,
        category_id=body.category_id,
        importance=body.importance,
    )
    mind = body.mind_map or build_mind_map(merged["title"], merged["content"] or merged["summary"])
    sections = body.sections or build_sections_from_content(merged["title"], merged["content"] or merged["summary"])
    content = merged["content"] or sections_to_content(sections)
    article = Article(
        title=merged["title"],
        source=merged["source"],
        source_url=merged["source_url"],
        publish_date=merged["publish_date"],
        summary=merged["summary"],
        content=content,
        sections=json.dumps(sections, ensure_ascii=False),
        tags=json.dumps(merged["tags"], ensure_ascii=False),
        mind_map=json.dumps(mind, ensure_ascii=False),
        importance=merged["importance"],
        status=body.status,
        allow_quiz=body.allow_quiz,
        is_published=body.is_published,
        is_daily=body.is_daily,
    )
    db.add(article)
    db.flush()
    sync_article_category(db, article, merged["category_id"])
    if body.auto_generate_questions:
        add_generated_questions(db, article, pending=True, origin="manual")
    db.commit()
    db.refresh(article)
    return ApiResponse.ok(article_to_out(article).model_dump())


@router.post("/articles/import-markdown")
def import_article_markdown(
    body: ImportArticleMarkdownBody,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    try:
        parsed, parse_errors = parse_article_markdown(body.markdown)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)

    merged = merge_article_fields(
        db,
        title=parsed["title"],
        source=body.source,
        source_url="",
        publish_date=body.publish_date,
        summary=parsed["summary"],
        content=parsed["content"],
        tags=body.tags,
        category_id=body.category_id,
        importance=5 if body.is_featured else 3,
    )
    if body.is_featured and "重点必读" not in merged["tags"]:
        merged["tags"] = [*merged["tags"], "重点必读"]

    mind = build_mind_map(merged["title"], merged["content"] or merged["summary"])
    article = Article(
        title=merged["title"],
        source=merged["source"],
        source_url=merged["source_url"],
        publish_date=merged["publish_date"],
        summary=merged["summary"],
        content=parsed["content"],
        sections=json.dumps(parsed["sections"], ensure_ascii=False),
        tags=json.dumps(merged["tags"], ensure_ascii=False),
        mind_map=json.dumps(mind, ensure_ascii=False),
        importance=merged["importance"],
        status=body.status,
        allow_quiz=True,
        is_published=body.status == "published",
        is_daily=False,
        is_featured=body.is_featured,
    )
    db.add(article)
    db.flush()
    sync_article_category(db, article, merged["category_id"])
    db.commit()
    db.refresh(article)

    out = article_to_out(article).model_dump()
    out["stats"] = parsed["stats"]
    out["parse_warnings"] = parse_errors
    msg = (
        f"已导入：{parsed['stats']['chapters']} 章、"
        f"{parsed['stats']['sections']} 节、"
        f"{parsed['stats']['paragraphs']} 段"
    )
    if parse_errors:
        msg += f"（{len(parse_errors)} 条解析提示）"
    return ApiResponse.ok(out, message=msg)


@router.put("/articles/{article_id}")
def update_article(
    article_id: str,
    body: ArticleUpdate,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文章不存在")
    data = body.model_dump(exclude_unset=True)
    category_id = data.pop("category_id", None) if "category_id" in data else None
    has_category_update = "category_id" in body.model_dump(exclude_unset=True)
    if "tags" in data:
        article.tags = json.dumps(data.pop("tags"), ensure_ascii=False)
    if "mind_map" in data:
        article.mind_map = json.dumps(data.pop("mind_map"), ensure_ascii=False)
    if "sections" in data:
        sections = data.pop("sections")
        article.sections = json.dumps(sections, ensure_ascii=False)
        if "content" not in data:
            article.content = sections_to_content(sections)
    for k, v in data.items():
        setattr(article, k, v)
    if has_category_update:
        sync_article_category(db, article, category_id)
    if article.status == "published":
        article.is_published = True
    elif article.status in ("pending", "draft", "rejected"):
        article.is_published = False
        if article.status == "rejected":
            article.is_daily = False
    db.commit()
    return ApiResponse.ok(article_to_out(article).model_dump())


@router.post("/articles/{article_id}/approve")
def approve_article(
    article_id: str,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文章不存在")
    article.status = "published"
    article.is_published = True
    db.commit()
    return ApiResponse.ok(article_to_out(article).model_dump(), message="文章已发布")


@router.post("/articles/{article_id}/reject")
def reject_article(
    article_id: str,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文章不存在")
    article.status = "rejected"
    article.is_published = False
    article.is_daily = False
    db.commit()
    return ApiResponse.ok(article_to_out(article).model_dump(), message="文章已驳回")


@router.post("/articles/batch-approve")
def batch_approve_articles(
    body: ArticleBatchPublish,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    if not body.article_ids:
        return ApiResponse.ok({"article_count": 0, "question_count": 0})
    articles = db.query(Article).filter(Article.id.in_(body.article_ids)).all()
    q_count = 0
    for article in articles:
        article.status = "published"
        article.is_published = True
        if body.approve_questions:
            rows = (
                db.query(Question)
                .filter(Question.article_id == article.id, Question.status == "pending")
                .all()
            )
            for q in rows:
                q.status = "approved"
                q.is_active = True
            q_count += len(rows)
    db.commit()
    msg = f"已发布 {len(articles)} 篇文章"
    if body.approve_questions and q_count:
        msg += f"，并审核通过 {q_count} 道题目"
    return ApiResponse.ok({"article_count": len(articles), "question_count": q_count}, message=msg)


@router.post("/articles/batch-reject")
def batch_reject_articles(
    body: ArticleBatchIds,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    if not body.article_ids:
        return ApiResponse.ok({"count": 0})
    rows = db.query(Article).filter(Article.id.in_(body.article_ids)).all()
    for article in rows:
        article.status = "rejected"
        article.is_published = False
        article.is_daily = False
    db.commit()
    return ApiResponse.ok({"count": len(rows)}, message=f"已驳回 {len(rows)} 篇文章")


@router.post("/articles/batch-category")
def batch_set_article_category(
    body: ArticleBatchCategory,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    if not body.article_ids:
        return ApiResponse.ok({"count": 0})
    rows = db.query(Article).filter(Article.id.in_(body.article_ids)).all()
    for article in rows:
        sync_article_category(db, article, body.category_id)
    db.commit()
    return ApiResponse.ok({"count": len(rows)}, message=f"已更新 {len(rows)} 篇文章分类")


@router.post("/articles/batch-delete")
def batch_delete_articles(
    body: ArticleBatchIds,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    if not body.article_ids:
        return ApiResponse.ok({"count": 0})
    rows = db.query(Article).filter(Article.id.in_(body.article_ids)).all()
    for article in rows:
        delete_article_record(db, article)
    db.commit()
    return ApiResponse.ok({"count": len(rows)}, message=f"已删除 {len(rows)} 篇文章")


@router.post("/articles/{article_id}/approve-questions")
def approve_article_questions(
    article_id: str,
    _admin=Depends(require_permission("question:write")),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文章不存在")
    rows = (
        db.query(Question)
        .filter(Question.article_id == article_id, Question.status == "pending")
        .all()
    )
    for q in rows:
        q.status = "approved"
        q.is_active = True
    db.commit()
    return ApiResponse.ok({"count": len(rows)}, message=f"已通过 {len(rows)} 道题目")


@router.post("/articles/{article_id}/generate-questions-ai")
def generate_questions_ai(
    article_id: str,
    body: AiGenerateQuestionsBody,
    _admin=Depends(require_permission("question:write")),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文章不存在")
    total = body.single + body.multiple + body.judge
    if total <= 0:
        return ApiResponse.fail("请至少生成 1 道题", code=400)
    try:
        result = run_ai_question_generation(
            db,
            article,
            section_ids=body.section_ids,
            single=body.single,
            multiple=body.multiple,
            judge=body.judge,
        )
    except LlmError as e:
        return ApiResponse.fail(str(e), code=400)
    msg = f"已生成 {result['count']} 道待审核 AI 题目"
    if result.get("validation_warnings"):
        msg += f"（{len(result['validation_warnings'])} 条校验提示）"
    return ApiResponse.ok(result, message=msg)


@router.post("/articles/{article_id}/import-questions")
def import_questions(
    article_id: str,
    body: ImportQuestionsBody,
    _admin=Depends(require_permission("question:write")),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文章不存在")

    parsed, parse_errors = parse_questions_markdown(body.markdown)
    if not parsed:
        msg = "；".join(parse_errors[:8]) if parse_errors else "未解析到题目"
        return ApiResponse.fail(msg, code=400)

    if body.replace_existing:
        delete_questions_for_article(db, article_id)

    count = add_imported_questions(db, article, parsed, pending=body.pending)
    db.commit()
    result = {"count": count, "parse_warnings": parse_errors}
    msg = f"已导入 {count} 道题目"
    if parse_errors:
        msg += f"（{len(parse_errors)} 条解析提示）"
    return ApiResponse.ok(result, message=msg)


@router.delete("/articles/{article_id}")
def delete_article(article_id: str, _admin=Depends(require_permission("article:write")), db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文章不存在")
    delete_article_record(db, article)
    db.commit()
    return ApiResponse.ok(None, message="已删除")


