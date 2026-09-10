"""管理端接口聚合：域路由按原顺序挂载，/admin 前缀保持不变。"""
from fastapi import APIRouter
from app.api.admin.articles import router as articles_router
from app.api.admin.auth_admin import router as auth_admin_router
from app.api.admin.categories import router as categories_router
from app.api.admin.exam import router as exam_router
from app.api.admin.knowledge import router as knowledge_router
from app.api.admin.misc import router as misc_router
from app.api.admin.plan import router as plan_router
from app.api.admin.questions import router as questions_router
from app.api.admin.rmrb import router as rmrb_router
from app.api.admin.roles import router as roles_router
from app.api.admin.settings import router as settings_router
from app.api.admin.theory_learning import router as theory_learning_router
from app.api.admin.users import router as users_router
from app.api.admin.ziliao import router as ziliao_router
from app.api.admin.content_ops import router as content_ops_router
from app.api.admin.feedbacks import router as feedbacks_router
from app.api.admin.question_bank import router as question_bank_router
from app.api.admin.analytics import router as analytics_router
from app.api.admin.generation import router as generation_router
from app.api.admin.ops import router as ops_router

router = APIRouter(prefix="/admin", tags=["管理后台"])
router.include_router(auth_admin_router)
router.include_router(articles_router)
router.include_router(questions_router)
router.include_router(categories_router)
router.include_router(users_router)
router.include_router(settings_router)
router.include_router(theory_learning_router)
router.include_router(roles_router)
router.include_router(knowledge_router)
router.include_router(plan_router)
router.include_router(exam_router)
router.include_router(rmrb_router)
router.include_router(ziliao_router)
router.include_router(misc_router)
router.include_router(content_ops_router)
router.include_router(feedbacks_router)
router.include_router(question_bank_router)
router.include_router(analytics_router)
router.include_router(generation_router)
router.include_router(ops_router)
