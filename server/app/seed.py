"""初始化数据库种子数据"""

import json

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import hash_password
from app.models import AdminUser, EnglishScene, EnglishUnit, Role, SystemSetting, gen_id
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
            ("site_name", "杜衡阁", "站点名称"),
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

    from app.services.wechat_reply_service import ensure_default_reply_configuration

    ensure_default_reply_configuration(db)

    _merge_role_permissions(db)
    _seed_english_content(db)


def _seed_english_content(db: Session) -> None:
    """提供可直接体验的公开样例；内容仍可在英语学习后台编辑。"""
    if db.query(EnglishScene).count():
        return
    examples = [
        ("日常社交", "从自我介绍和轻松寒暄开始练习。", "A1 入门", 1, "轻松介绍自己", 6,
         "用三句话介绍姓名、来自哪里和一个兴趣。",
         {"dialogue": [{"speaker": "Alex", "en": "Hey, I’m Alex. Nice to meet you.", "zh": "嗨，我叫 Alex。很高兴认识你。"}, {"speaker": "You", "en": "Nice to meet you too. I’m Mia.", "zh": "我也很高兴认识你。我叫 Mia。"}, {"speaker": "Alex", "en": "Where are you from?", "zh": "你来自哪里？"}, {"speaker": "You", "en": "I’m from Chengdu. I love hiking.", "zh": "我来自成都。我喜欢徒步。"}], "phrases": [{"en": "Nice to meet you.", "zh": "很高兴认识你。"}, {"en": "I’m from ...", "zh": "我来自……"}, {"en": "I love ...", "zh": "我喜欢……"}], "prompt": "请用自己的真实信息介绍姓名、所在城市和一个兴趣。"}),
        ("餐饮购物", "练习点单、表达偏好和礼貌确认。", "A1 入门", 2, "在咖啡店点单", 8,
         "点一杯饮品，并说明冷热和大小偏好。",
         {"dialogue": [{"speaker": "Barista", "en": "Hi! What can I get for you?", "zh": "你好，想来点什么？"}, {"speaker": "You", "en": "Could I have a small iced latte, please?", "zh": "请给我一杯小杯冰拿铁。"}, {"speaker": "Barista", "en": "Sure. Would you like anything else?", "zh": "好的，还需要别的吗？"}, {"speaker": "You", "en": "That’s all, thanks.", "zh": "就这些，谢谢。"}], "phrases": [{"en": "Could I have ..., please?", "zh": "礼貌点单：请给我……"}, {"en": "Would you like anything else?", "zh": "还需要别的吗？"}, {"en": "That’s all, thanks.", "zh": "就这些，谢谢。"}], "prompt": "现在换成一杯中杯热美式。请不看完整对话，说出你的点单。"}),
        ("出行旅行", "问路并确认步行方向和所需时间。", "A2 日常", 3, "问路与确认方向", 9,
         "礼貌询问地点，并确认步行方向。",
         {"dialogue": [{"speaker": "You", "en": "Excuse me, how do I get to the station?", "zh": "打扰一下，请问去车站怎么走？"}, {"speaker": "Local", "en": "Go straight and turn left at the lights.", "zh": "直走，在红绿灯处左转。"}, {"speaker": "You", "en": "Is it far from here?", "zh": "离这里远吗？"}, {"speaker": "Local", "en": "No, it’s about a ten-minute walk.", "zh": "不远，步行大约十分钟。"}], "phrases": [{"en": "How do I get to ...?", "zh": "请问去……怎么走？"}, {"en": "Is it far from here?", "zh": "离这里远吗？"}, {"en": "Go straight and turn ...", "zh": "直走，然后……转。"}], "prompt": "把目的地换成博物馆，再用自己的话问路并追问需要多久。"}),
    ]
    for scene_title, description, level, order, unit_title, duration, goal, content in examples:
        scene = EnglishScene(id=gen_id("ens"), title=scene_title, description=description, level=level, sort_order=order, is_published=True)
        db.add(scene)
        db.flush()
        db.add(EnglishUnit(id=gen_id("enu"), scene_id=scene.id, title=unit_title, level=level,
                           duration_min=duration, goal=goal, content_json=json.dumps(content, ensure_ascii=False),
                           sort_order=1, is_published=True))
    db.commit()


def _merge_role_permissions(db: Session) -> None:
    for code, perms in ROLE_PERMISSIONS.items():
        role = db.query(Role).filter(Role.code == code).first()
        if not role:
            continue
        try:
            current = set(json.loads(role.permissions or "[]"))
        except json.JSONDecodeError:
            current = set()
        needed = set(perms)
        if not needed <= current:
            role.permissions = json.dumps(sorted(current | needed), ensure_ascii=False)
            db.commit()
