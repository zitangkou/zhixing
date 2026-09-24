"""行测真题管理：查看已入库试卷，并导入与脚本相同结构的 JSON。"""

from app.api.admin._deps import *  # noqa: F401,F403

from app.services import xingce_quiz_service as xingce
from scripts.import_xingce_2025 import PAPER_FILES, import_uploaded_paper

router = APIRouter(prefix="/xingce", tags=["行测真题"])


def _paper_type_from(raw: str | None, paper: dict) -> str:
    chosen = (raw or paper.get("paper_type") or paper.get("paperType") or "").strip()
    return chosen


@router.get("/overview")
def xingce_overview(
    _admin=Depends(require_permission("xingce:read")),
    db: Session = Depends(get_db),
):
    """学员端会看到的模块计数，以及库里每一卷的题位。"""
    return ApiResponse.ok(xingce.admin_overview(db))


@router.post("/import")
async def xingce_import_json(
    file: UploadFile = File(...),
    paperType: str | None = Query(default=None),
    _admin=Depends(require_permission("xingce:write")),
    db: Session = Depends(get_db),
):
    """上传一份试卷 JSON（结构同 import_xingce_2025.py 读取的卷文件）。"""
    name = file.filename or "upload.json"
    if not name.lower().endswith(".json"):
        return ApiResponse.fail("请上传 .json 文件", code=400)
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        return ApiResponse.fail("文件超过 20MB", code=400)
    try:
        paper = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ApiResponse.fail("JSON 无法解析", code=400)
    if not isinstance(paper, dict):
        return ApiResponse.fail("试卷 JSON 须为对象", code=400)
    paper_type = _paper_type_from(paperType, paper)
    if paper_type not in PAPER_FILES:
        allowed = "、".join(PAPER_FILES)
        return ApiResponse.fail(f"paperType 须为 {allowed}", code=400)
    try:
        stats = import_uploaded_paper(db, paper_type, paper, name)
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    except Exception as exc:
        db.rollback()
        return ApiResponse.fail(f"导入失败：{exc}", code=400)
    return ApiResponse.ok(stats, message="导入完成")
