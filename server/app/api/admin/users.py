from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ---- 用户管理 ----
@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin=Depends(require_permission("user:read")),
    db: Session = Depends(get_db),
):
    q = db.query(AppUser).order_by(AppUser.created_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return ApiResponse.ok({
        "total": total,
        "items": [
            AppUserOut(
                id=u.id, nickname=u.nickname, avatar=u.avatar, points=u.points,
                is_member=u.is_member, is_active=u.is_active, created_at=u.created_at,
            ).model_dump()
            for u in rows
        ],
    })


@router.put("/users/{user_id}")
def update_user(user_id: str, body: AppUserUpdate, _admin=Depends(require_permission("user:write")), db: Session = Depends(get_db)):
    user = db.get(AppUser, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    return ApiResponse.ok(AppUserOut(
        id=user.id, nickname=user.nickname, avatar=user.avatar, points=user.points,
        is_member=user.is_member, is_active=user.is_active, created_at=user.created_at,
    ).model_dump())


