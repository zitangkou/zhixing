from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.permissions import role_has_permission
from app.core.security import decode_token
from app.database import get_db
from app.models import AdminUser, AppUser
from app.services.serializers import parse_json

security = HTTPBearer(auto_error=False)
app_security = HTTPBearer()


def get_current_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> AdminUser:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    username = decode_token(creds.credentials)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
    admin = db.query(AdminUser).filter(AdminUser.username == username, AdminUser.is_active.is_(True)).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return admin


def require_permission(permission: str):
    def checker(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
        perms = parse_json(admin.role.permissions, [])
        role_code = admin.role.code
        if role_code != "super_admin" and permission not in perms and not role_has_permission(role_code, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限: {permission}")
        return admin

    return checker


def get_app_user(
    creds: HTTPAuthorizationCredentials = Depends(app_security),
    db: Session = Depends(get_db),
) -> AppUser:
    user_id = decode_token(creds.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效或已过期")
    user = db.get(AppUser, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请使用账号密码登录")
    return user
