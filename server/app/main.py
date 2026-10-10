import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from app.api.admin.routes import router as admin_router
from app.api.public.routes import router as public_router
from app.config import get_settings
from app.database import SessionLocal, engine
from app.db_compat import run_compat_migrations
from app.models import Base

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_compat_migrations()
    from app.services.image_generation_jobs import fail_interrupted_image_jobs

    fail_interrupted_image_jobs()
    from app.seed import seed_if_empty

    db = SessionLocal()
    try:
        seed_if_empty(db)
        try:
            from app.services.image_style_service import ensure_image_style_setting

            ensure_image_style_setting(db)
        except Exception as e:
            print(f"[image-style] 风格配置初始化失败: {e}")
        # 知识框架改为管理端草稿/发布；禁止启动时用 md 覆盖 DB
        # 启动时确保 plan 模板有默认数据
        try:
            from app.services.plan_service import seed_default_templates

            seed_default_templates(db)
        except Exception as e:
            print(f"[plan] 模板初始化失败: {e}")
        # 资料分析资源库 + 样例材料组（force 刷新 latex 种子时可在 Admin 点覆盖）
        try:
            from app.services.ziliao_service import seed_sample_drill_paper, seed_ziliao_resources

            seed_ziliao_resources(db)
            seed_sample_drill_paper(db)
        except Exception as e:
            print(f"[ziliao] 资料分析初始化失败: {e}")
        try:
            from app.services.photography_service import seed_photography_content

            seed_photography_content(db)
        except Exception as e:
            print(f"[photography] 默认课程初始化失败: {e}")
    finally:
        db.close()

    from app.services.image_generation_service import cleanup_expired_image_results
    from app.services.image_generation_jobs import prune_old_image_jobs

    async def cleanup_image_results_loop():
        while True:
            cleanup_expired_image_results()
            prune_old_image_jobs()
            await asyncio.sleep(60 * 60)

    cleanup_task = asyncio.create_task(cleanup_image_results_loop())
    from app.services.rmrb_archive_service import rmrb_daily_scheduler_loop

    rmrb_scheduler_task = asyncio.create_task(rmrb_daily_scheduler_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        rmrb_scheduler_task.cancel()
        try:
            await asyncio.gather(cleanup_task, rmrb_scheduler_task, return_exceptions=True)
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="杜衡阁 API",
    description="杜衡阁后端服务 — 多产品学习内容、练习闭环、错题复习与内容运营",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_router)
app.include_router(admin_router)

_admin_dist = Path(__file__).resolve().parents[1] / "admin-dist"


class AdminSPAStaticFiles(StaticFiles):
    """Serve Vue history-mode routes from index.html while keeping missing assets 404."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            # Vue history routes have no file extension. Missing JS/CSS/images should
            # remain real 404s so stale deployments are visible instead of returning HTML.
            if exc.status_code == 404 and not Path(path).suffix:
                return await super().get_response("index.html", scope)
            raise


@app.get("/manage")
def manage_redirect():
    return RedirectResponse(url="/manage/")


@app.get("/health")
def health():
    return {"status": "ok", "service": "zhixing-gongkao-server"}


from app.upload_paths import UPLOADS_DIR

_uploads_dir = UPLOADS_DIR
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")

if _admin_dist.is_dir():
    app.mount("/manage", AdminSPAStaticFiles(directory=_admin_dist, html=True), name="admin-web")
