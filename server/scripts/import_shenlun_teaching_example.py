"""导入已人工审核的申论三刀示范；默认仅保存草稿，发布必须显式指定。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.database import SessionLocal, engine
from app.models import RmrbArticle, ShenlunTeachingExample
from app.models.base import Base, gen_id
from app.services.shenlun_learning_service import teaching_example_out


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser(description="导入申论公共三刀教研示范")
    parser.add_argument("input", type=Path, help="人工审核后的 JSON 文件")
    parser.add_argument("--publish", action="store_true", help="通过完整性校验后立即公开发布")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    article_id = str(payload.get("articleId") or "").strip()
    version = str(payload.get("version") or "").strip()
    if not article_id or not version or len(version) > 32:
        parser.error("JSON 必须包含有效的 articleId 和 version（最多 32 字符）")

    teaching = {
        "sourceExcerpt": payload.get("sourceExcerpt"),
        "argument": payload.get("argument"),
        "terms": payload.get("terms"),
        "quotes": payload.get("quotes"),
        "verbs": payload.get("verbs"),
        "templates": payload.get("templates"),
        "practice": payload.get("practice"),
    }
    content_hash = hashlib.sha256(canonical_json(teaching).encode()).hexdigest()
    row = ShenlunTeachingExample(
        id=gen_id("ste"),
        article_id=article_id,
        version=version,
        source_excerpt=str(teaching["sourceExcerpt"] or ""),
        argument_json=canonical_json(teaching["argument"]),
        terms_json=canonical_json(teaching["terms"]),
        quotes_json=canonical_json(teaching["quotes"]),
        verbs_json=canonical_json(teaching["verbs"]),
        templates_json=canonical_json(teaching["templates"]),
        practice_json=canonical_json(teaching["practice"]),
        content_hash=content_hash,
        status="published" if args.publish else "draft",
    )
    if teaching_example_out(row) is None:
        parser.error("教研示范字段不完整，未写入数据库；请核对三刀结构和短练习")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.get(RmrbArticle, article_id):
            parser.error(f"文章不存在：{article_id}；请先导入原文")
        existing = db.query(ShenlunTeachingExample).filter(
            ShenlunTeachingExample.article_id == article_id,
            ShenlunTeachingExample.version == version,
        ).first()
        if existing:
            if existing.content_hash == content_hash and existing.status == row.status:
                print(json.dumps({"status": "skipped", "id": existing.id, "reason": "相同版本已存在"}, ensure_ascii=False))
                return
            parser.error("同一文章版本已存在且内容或状态不同；请使用新的 version，禁止覆盖已审版本")
        db.add(row)
        db.commit()
        print(json.dumps({
            "status": "created", "id": row.id, "articleId": article_id,
            "version": version, "published": args.publish,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
