"""按今日内容生成运营草稿；幂等执行，不自动送审或发布。"""
from __future__ import annotations

import argparse
import json
from datetime import datetime

from app.database import SessionLocal, engine
from app.db_compat import run_compat_migrations
from app.models import Article, Base, ContentOperationTemplate
from app.schemas import ContentPackageGenerateFromArticle
from app.services.content_ops_service import ensure_content_ops_defaults, generate_package_from_article
from app.timezone import today as today_str


def generate(date: str) -> list[dict]:
    results: list[dict] = []
    Base.metadata.create_all(bind=engine)
    run_compat_migrations()
    with SessionLocal() as db:
        ensure_content_ops_defaults(db)
        article = (
            db.query(Article)
            .filter(Article.status == "published", Article.is_published.is_(True))
            .order_by(Article.importance.desc(), Article.publish_date.desc())
            .first()
        )
        if not article:
            return [{"productKey": "general", "status": "skipped", "reason": "无已发布文章"}]
        template = (
            db.query(ContentOperationTemplate)
            .filter(ContentOperationTemplate.product_key.in_(["general", "theory"]))
            .first()
        )
        if not template:
            return [{"productKey": "general", "status": "skipped", "reason": "运营模板不存在"}]
        try:
            package = generate_package_from_article(
                db,
                ContentPackageGenerateFromArticle(
                    productKey="general",
                    templateId=template.id,
                    articleId=article.id,
                    campaignKey=f"daily-general-{date.replace('-', '')}",
                    deepLink=f"/#/pages/article/detail?id={article.id}",
                    plannedAt=datetime.fromisoformat(f"{date}T07:00:00"),
                ),
            )
            results.append(
                {
                    "productKey": "general",
                    "status": "created",
                    "packageId": package["id"],
                    "title": package["sourceTitle"],
                    "plannedAt": str(package["plannedAt"]),
                }
            )
        except ValueError as exc:
            results.append({"productKey": "general", "status": "skipped", "reason": str(exc)})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="生成综合版每日运营草稿")
    parser.add_argument("--date", default=today_str(), help="YYYY-MM-DD，默认今天")
    args = parser.parse_args()
    print(json.dumps({"date": args.date, "packages": generate(args.date)}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
