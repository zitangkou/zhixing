from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ---- 系统设置 ----
@router.get("/settings")
def list_settings(_admin=Depends(require_permission("setting:read")), db: Session = Depends(get_db)):
    rows = db.query(SystemSetting).all()
    return ApiResponse.ok([SettingOut(key=r.key, value=r.value, description=r.description).model_dump() for r in rows])


@router.put("/settings/{key}")
def update_setting(key: str, body: SettingUpdate, _admin=Depends(require_permission("setting:write")), db: Session = Depends(get_db)):
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not row:
        raise HTTPException(404, "设置项不存在")
    row.value = body.value
    db.commit()
    return ApiResponse.ok(SettingOut(key=row.key, value=row.value, description=row.description).model_dump())


