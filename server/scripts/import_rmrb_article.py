"""从审核后的 JSON 文件幂等导入人民日报申论学习材料。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.database import SessionLocal
from app.db_compat import run_compat_migrations
from app.models import RmrbArticle
from app.schemas import RmrbArticleCreate
from app.services.rmrb_service import create_article


def main() -> None:
    parser = argparse.ArgumentParser(description="导入申论学习材料")
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    body = RmrbArticleCreate.model_validate(payload)
    run_compat_migrations()
    with SessionLocal() as db:
        existing = db.query(RmrbArticle).filter(RmrbArticle.source_url == body.sourceUrl).first() if body.sourceUrl else None
        if existing:
            print(json.dumps({"status": "skipped", "id": existing.id, "reason": "原文链接已导入"}, ensure_ascii=False))
            return
        article = create_article(db, body)
        print(json.dumps({"status": "created", "id": article.id, "title": article.title}, ensure_ascii=False))


if __name__ == "__main__":
    main()
