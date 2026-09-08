"""公开接口聚合：域路由按原顺序挂载，/api 前缀保持不变。"""
from fastapi import APIRouter, Depends
from app.product import get_product_context
from app.api.public.article_quiz import router as article_quiz_router
from app.api.public.auth_user import router as auth_user_router
from app.api.public.corpus import router as corpus_router
from app.api.public.countdown import router as countdown_router
from app.api.public.data import router as data_router
from app.api.public.events import router as events_router
from app.api.public.exam import router as exam_router
from app.api.public.entry_attribution import router as entry_attribution_router
from app.api.public.guest_learning import router as guest_learning_router
from app.api.public.knowledge import router as knowledge_router
from app.api.public.manual_wrong import router as manual_wrong_router
from app.api.public.plan import router as plan_router
from app.api.public.practice import router as practice_router
from app.api.public.product import router as product_router
from app.api.public.rmrb import router as rmrb_router
from app.api.public.wechat_official import router as wechat_official_router
from app.api.public.ziliao import router as ziliao_router

router = APIRouter(
    prefix="/api",
    tags=["公开接口"],
    dependencies=[Depends(get_product_context)],
)
router.include_router(auth_user_router)
router.include_router(article_quiz_router)
router.include_router(plan_router)
router.include_router(practice_router)
router.include_router(product_router)
router.include_router(knowledge_router)
router.include_router(manual_wrong_router)
router.include_router(exam_router)
router.include_router(entry_attribution_router)
router.include_router(guest_learning_router)
router.include_router(rmrb_router)
router.include_router(wechat_official_router)
router.include_router(corpus_router)
router.include_router(events_router)
router.include_router(ziliao_router)
router.include_router(countdown_router)
router.include_router(data_router)
