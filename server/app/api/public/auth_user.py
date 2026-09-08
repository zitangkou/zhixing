from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()

@router.get("/config")
def public_config(product=Depends(get_product_context)):
    """公开配置（无需登录），供前端控制注册入口等。"""
    from app.config import get_settings
    s = get_settings()
    return ApiResponse.ok({
        "allowRegister": bool(s.allow_register),
        "product": product.to_public_dict(),
    })


@router.post("/auth/register")
def app_register(body: AppRegisterBody, db: Session = Depends(get_db)):
    from app.config import get_settings
    if not get_settings().allow_register:
        return ApiResponse.fail("当前未开放注册，请联系管理员开通账号", code=403)
    user, err = register_user(db, body.username, body.password, body.passwordConfirm)
    if err or not user:
        return ApiResponse.fail(err or "注册失败", code=400)
    token = issue_app_token(user)
    me = build_user_me_out(db, user)
    return ApiResponse.ok(
        AppAuthToken(access_token=token, user=me).model_dump()
    )


@router.post("/auth/login")
def app_login(body: AppLoginBody, db: Session = Depends(get_db)):
    user, err = authenticate_user(db, body.username, body.password)
    if err or not user:
        return ApiResponse.fail(err or "登录失败", code=401)
    token = issue_app_token(user)
    me = build_user_me_out(db, user)
    return ApiResponse.ok(
        AppAuthToken(access_token=token, user=me).model_dump()
    )


@router.get("/user/me")
def user_me(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    return ApiResponse.ok(build_user_me_out(db, user).model_dump())


@router.put("/user/me")
def update_me(
    body: AppUserProfileUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    if not data:
        return ApiResponse.fail("没有需要更新的内容", code=400)
    updated, err = update_user_profile(db, user, **data)
    if err or not updated:
        return ApiResponse.fail(err or "更新失败", code=400)
    return ApiResponse.ok(build_user_me_out(db, updated).model_dump())


@router.post("/user/password")
def change_password(
    body: AppUserPasswordChange,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    err = change_user_password(
        db,
        user,
        body.oldPassword,
        body.newPassword,
        body.newPasswordConfirm,
    )
    if err:
        return ApiResponse.fail(err, code=400)
    return ApiResponse.ok({"ok": True})


@router.post("/user/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    from pathlib import Path
    from uuid import uuid4

    content_type = (file.content_type or "").lower()
    allowed = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    ext = allowed.get(content_type)
    if not ext:
        name = (file.filename or "").lower()
        if name.endswith(".png"):
            ext = ".png"
        elif name.endswith(".webp"):
            ext = ".webp"
        elif name.endswith(".gif"):
            ext = ".gif"
        elif name.endswith(".jpg") or name.endswith(".jpeg"):
            ext = ".jpg"
        else:
            return ApiResponse.fail("仅支持 jpg/png/webp/gif 图片", code=400)

    raw = await file.read()
    if not raw:
        return ApiResponse.fail("文件为空", code=400)
    if len(raw) > 2 * 1024 * 1024:
        return ApiResponse.fail("头像不能超过 2MB", code=400)

    avatar_dir = Path(__file__).resolve().parents[3] / "data" / "uploads" / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{user.id}_{uuid4().hex[:12]}{ext}"
    dest = avatar_dir / filename
    dest.write_bytes(raw)

    user.avatar = f"/uploads/avatars/{filename}"
    db.commit()
    db.refresh(user)
    return ApiResponse.ok(build_user_me_out(db, user).model_dump())
