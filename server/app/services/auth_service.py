import re

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import AppUser, gen_id

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^1\d{10}$")


def validate_username(username: str) -> str | None:
    name = username.strip()
    if not USERNAME_PATTERN.match(name):
        return "用户名需为 3-32 位字母、数字或下划线"
    return None


def validate_password(password: str) -> str | None:
    if len(password) < 6:
        return "密码至少 6 位"
    if len(password) > 64:
        return "密码不能超过 64 位"
    return None


def validate_email(email: str) -> str | None:
    value = email.strip()
    if not value:
        return None
    if len(value) > 128:
        return "邮箱过长"
    if not EMAIL_PATTERN.match(value):
        return "邮箱格式不正确"
    return None


def validate_phone(phone: str) -> str | None:
    value = phone.strip()
    if not value:
        return None
    if not PHONE_PATTERN.match(value):
        return "手机号需为 11 位数字且以 1 开头"
    return None


def update_user_profile(
    db: Session,
    user: AppUser,
    *,
    nickname: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> tuple[AppUser | None, str | None]:
    if nickname is not None:
        name = nickname.strip()
        if not name:
            return None, "昵称不能为空"
        if len(name) > 32:
            return None, "昵称不能超过 32 字"
        user.nickname = name

    if email is not None:
        err = validate_email(email)
        if err:
            return None, err
        user.email = email.strip()

    if phone is not None:
        err = validate_phone(phone)
        if err:
            return None, err
        user.phone = phone.strip()

    db.commit()
    db.refresh(user)
    return user, None


def change_user_password(
    db: Session,
    user: AppUser,
    old_password: str,
    new_password: str,
    new_password_confirm: str,
) -> str | None:
    if not user.password_hash:
        return "当前账号不支持修改密码"
    if not verify_password(old_password, user.password_hash):
        return "原密码不正确"
    err = validate_password(new_password)
    if err:
        return err
    if new_password != new_password_confirm:
        return "两次输入的新密码不一致"
    if old_password == new_password:
        return "新密码不能与原密码相同"
    user.password_hash = hash_password(new_password)
    db.commit()
    return None


def register_user(db: Session, username: str, password: str, password_confirm: str) -> tuple[AppUser | None, str | None]:
    name = username.strip()
    err = validate_username(name)
    if err:
        return None, err
    err = validate_password(password)
    if err:
        return None, err
    if password != password_confirm:
        return None, "两次输入的密码不一致"

    exists = db.query(AppUser).filter(AppUser.username == name).first()
    if exists:
        return None, "用户名已被注册"

    user = AppUser(
        id=gen_id("u"),
        username=name,
        password_hash=hash_password(password),
        nickname=name,
        points=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, None


def authenticate_user(db: Session, username: str, password: str) -> tuple[AppUser | None, str | None]:
    name = username.strip()
    user = db.query(AppUser).filter(AppUser.username == name).first()
    if not user or not user.password_hash:
        return None, "用户名或密码错误"
    if not user.is_active:
        return None, "账号已被禁用"
    if not verify_password(password, user.password_hash):
        return None, "用户名或密码错误"
    return user, None


def issue_app_token(user: AppUser) -> str:
    return create_access_token(user.id)
