"""初始化数据库种子数据"""

import json

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import hash_password
from app.models import AdminUser, Role, SystemSetting
from app.services.category_service import seed_default_categories
from app.services.featured_article import seed_featured_article

settings = get_settings()


def seed_if_empty(db: Session) -> None:
    if db.query(Role).count() == 0:
        for code, perms in ROLE_PERMISSIONS.items():
            names = {"super_admin": "超级管理员", "editor": "编辑", "viewer": "只读"}
            db.add(Role(code=code, name=names.get(code, code), permissions=json.dumps(perms)))

    db.flush()

    if db.query(AdminUser).count() == 0:
        role = db.query(Role).filter(Role.code == "super_admin").first()
        db.add(AdminUser(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            nickname="系统管理员",
            role_id=role.id,
        ))

    if db.query(SystemSetting).count() == 0:
        defaults = [
            ("site_name", "知行公考", "站点名称"),
            ("points_sign_base", "5", "签到基础积分"),
            ("points_read_article", "3", "阅读文章积分"),
            ("points_correct_answer", "2", "答对题目积分"),
        ]
        for key, value, desc in defaults:
            db.add(SystemSetting(key=key, value=value, description=desc))

    db.commit()

    seed_default_categories(db)
    db.commit()

    seed_featured_article(db)
    db.commit()

    from app.services.rmrb_meta_service import ensure_rmrb_meta_defaults

    ensure_rmrb_meta_defaults(db)

    from app.services.content_ops_service import ensure_content_ops_defaults

    ensure_content_ops_defaults(db)
