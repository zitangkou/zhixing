from pathlib import Path

from app.models import Base
from app.services.ops_service import seed_ops_catalog, start_pipeline_run
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_ops_catalog_and_wait_confirm(tmp_path, monkeypatch):
    db_path = tmp_path / "ops.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        seed_ops_catalog(db)
        from app.models.ops import OpsPipeline, OpsStep

        assert db.query(OpsStep).count() >= 10
        assert db.query(OpsPipeline).count() == 3
        pipe = db.query(OpsPipeline).filter(OpsPipeline.key == "shenlun.daily_screen").one()
        monkeypatch.setenv("OPS_MATERIAL_ROOT", str(tmp_path / "mat"))
        run = start_pipeline_run(db, pipe.id)
        assert run["status"] == "waiting_confirm"
    finally:
        db.close()
