from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

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
    from app.seed import seed_if_empty

    db = SessionLocal()
    try:
        seed_if_empty(db)
        # 启动时尝试同步 Obsidian 知识库（目录不存在则跳过）
        try:
            from app.services.knowledge_service import sync_knowledge

            sync_knowledge(db)
        except Exception as e:
            print(f"[knowledge] 启动同步失败: {e}")
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
    finally:
        db.close()

    yield


app = FastAPI(
    title="知行公考 API",
    description="知行公考后端服务 — 多产品学习内容、练习闭环、错题复习与内容运营",
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
    app.mount("/manage", StaticFiles(directory=_admin_dist, html=True), name="admin-web")
