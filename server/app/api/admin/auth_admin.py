from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()


@router.post("/auth/login")
def admin_login(body: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.username == body.username).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        return ApiResponse.fail("用户名或密码错误", code=401)
    if not admin.is_active:
        return ApiResponse.fail("账号已禁用", code=403)
    perms = parse_json(admin.role.permissions, [])
    token = create_access_token(admin.username)
    return ApiResponse.ok(
        AdminToken(
            access_token=token,
            username=admin.username,
            role=admin.role.code,
            permissions=perms,
        ).model_dump()
    )


@router.get("/auth/me")
def admin_me(admin: AdminUser = Depends(get_current_admin)):
    perms = parse_json(admin.role.permissions, [])
    return ApiResponse.ok(
        AdminUserOut(
            id=admin.id,
            username=admin.username,
            nickname=admin.nickname,
            role_code=admin.role.code,
            is_active=admin.is_active,
            created_at=admin.created_at,
            permissions=perms,
        ).model_dump()
    )


@router.put("/auth/password")
def admin_change_password(
    body: AdminPasswordChange,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员自助改密。

    播种逻辑只在 `admin_users` 为空时创建管理员（app/seed.py），因此已部署环境
    改 `.env` 的 ADMIN_PASSWORD 不会生效，必须走本接口。
    注意：令牌以用户名为载荷且无吊销机制，改密后旧令牌在有效期内仍可用，建议改完重新登录。
    """
    if not verify_password(body.oldPassword, admin.password_hash):
        return ApiResponse.fail("原密码不正确", code=401)
    if body.oldPassword == body.newPassword:
        return ApiResponse.fail("新密码不能与原密码相同", code=400)
    admin.password_hash = hash_password(body.newPassword)
    db.commit()
    return ApiResponse.ok(None)
