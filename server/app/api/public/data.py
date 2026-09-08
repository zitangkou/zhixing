from app.api.public._deps import *  # noqa: F401,F403
from app.schemas import DataImportIn
from app.services.data_transfer_service import export_core_data, import_core_data

router = APIRouter()


@router.get("/data/export")
def data_export(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    """导出当前用户核心学习进度（错题本/语料本/计划复习/积分）。"""
    return ApiResponse.ok(export_core_data(db, user.id))


@router.post("/data/import")
def data_import(body: DataImportIn, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    """导入核心学习进度（整表替换，事务内完成）。"""
    try:
        result = import_core_data(db, user.id, body.model_dump())
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(result)
