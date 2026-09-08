from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ---- 权限与角色 ----
@router.get("/roles")
def list_roles(_admin=Depends(require_permission("admin:read")), db: Session = Depends(get_db)):
    rows = db.query(Role).all()
    return ApiResponse.ok([
        RoleOut(id=r.id, code=r.code, name=r.name, permissions=parse_json(r.permissions, [])).model_dump()
        for r in rows
    ])


@router.get("/permissions")
def list_permissions(_admin=Depends(require_permission("admin:read"))):
    return ApiResponse.ok(PERMISSIONS)


@router.get("/roles/matrix")
def role_matrix(_admin=Depends(require_permission("admin:read"))):
    return ApiResponse.ok(ROLE_PERMISSIONS)


