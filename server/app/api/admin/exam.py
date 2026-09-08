from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 试卷题库管理 =====


@router.get("/exam/papers")
def admin_exam_papers(
    exam_type: str | None = None,
    subject: str | None = None,
    year: int | None = None,
    is_published: bool | None = None,
    _admin=Depends(require_permission("exam:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([p.model_dump() for p in list_exam_papers(
        db, exam_type=exam_type, subject=subject, year=year, is_published=is_published
    )])


@router.post("/exam/paper")
def admin_exam_create_paper(
    body: ExamPaperCreate,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    out = create_exam_paper(db, body)
    return ApiResponse.ok(out.model_dump())


@router.put("/exam/paper/{paper_id}")
def admin_exam_update_paper(
    paper_id: str,
    body: ExamPaperUpdate,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    out = update_exam_paper(db, paper_id, body)
    if not out:
        return ApiResponse.fail("试卷不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/exam/paper/{paper_id}")
def admin_exam_delete_paper(
    paper_id: str,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    if not delete_exam_paper(db, paper_id):
        return ApiResponse.fail("试卷不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.post("/exam/paper/{paper_id}/question")
def admin_exam_create_question(
    paper_id: str,
    body: ExamQuestionCreate,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    out = create_exam_question(db, paper_id, body)
    if not out:
        return ApiResponse.fail("试卷不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.put("/exam/question/{question_id}")
def admin_exam_update_question(
    question_id: str,
    body: ExamQuestionUpdate,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    out = update_exam_question(db, question_id, body)
    if not out:
        return ApiResponse.fail("题目不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/exam/question/{question_id}")
def admin_exam_delete_question(
    question_id: str,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    if not delete_exam_question(db, question_id):
        return ApiResponse.fail("题目不存在", code=404)
    return ApiResponse.ok({"ok": True})


class ExamImportPreviewBody(BaseModel):
    """不实际导入，先预览解析结果"""
    fileName: str
    content: str


@router.post("/exam/paper/{paper_id}/import-preview")
def admin_exam_import_preview(
    paper_id: str,
    body: ExamImportPreviewBody,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    p = get_exam_paper(db, paper_id)
    if not p:
        return ApiResponse.fail("试卷不存在", code=404)
    questions, errors = parse_exam_import(body.fileName, body.content)
    return ApiResponse.ok({
        "parsed": len(questions),
        "errors": errors,
        "preview": questions[:5],
        "totalCount": len(questions),
    })


class ExamImportConfirmBody(BaseModel):
    fileName: str
    content: str


@router.post("/exam/paper/{paper_id}/import")
def admin_exam_import(
    paper_id: str,
    body: ExamImportConfirmBody,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    p = get_exam_paper(db, paper_id)
    if not p:
        return ApiResponse.fail("试卷不存在", code=404)
    questions, errors = parse_exam_import(body.fileName, body.content)
    if not questions:
        return ApiResponse.fail(errors[0] if errors else "未解析到题目", code=400)
    result = batch_create_exam_questions(db, paper_id, questions)
    if not result.get("ok"):
        return ApiResponse.fail(result.get("error", "导入失败"), code=400)
    return ApiResponse.ok(result)


@router.post("/exam/paper/upload")
async def admin_exam_upload(
    file: UploadFile = File(...),
    _admin=Depends(require_permission("exam:write")),
):
    """上传题库文件（仅解析，不入库，返回解析结果供预览）"""
    raw = await file.read()
    if not raw:
        return ApiResponse.fail("文件为空", code=400)
    if len(raw) > 2 * 1024 * 1024:
        return ApiResponse.fail("文件不能超过 2MB", code=400)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gbk")
        except UnicodeDecodeError:
            return ApiResponse.fail("文件编码不支持，请用 UTF-8", code=400)
    questions, errors = parse_exam_import(file.filename or "", text)
    return ApiResponse.ok({
        "fileName": file.filename,
        "parsed": len(questions),
        "errors": errors,
        "preview": questions[:5],
        "totalCount": len(questions),
        "questions": questions,
    })


