from app.api.admin._deps import *  # noqa: F401,F403

from app.services.image_style_service import SETTING_KEY as IMAGE_STYLE_SETTING_KEY

router = APIRouter()
# ---- 系统设置 ----
@router.get("/settings")
def list_settings(_admin=Depends(require_permission("setting:read")), db: Session = Depends(get_db)):
    rows = db.query(SystemSetting).filter(SystemSetting.key != IMAGE_STYLE_SETTING_KEY).all()
    return ApiResponse.ok([SettingOut(key=r.key, value=r.value, description=r.description).model_dump() for r in rows])


@router.put("/settings/{key}")
def update_setting(key: str, body: SettingUpdate, _admin=Depends(require_permission("setting:write")), db: Session = Depends(get_db)):
    if key == IMAGE_STYLE_SETTING_KEY:
        raise HTTPException(400, "请使用图片处理风格页面维护此配置")
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not row:
        raise HTTPException(404, "设置项不存在")
    row.value = body.value
    db.commit()
    return ApiResponse.ok(SettingOut(key=row.key, value=row.value, description=row.description).model_dump())

