"""按双产品今日学习任务生成四渠道运营草稿；幂等执行，不自动送审或发布。"""
from __future__ import annotations

import argparse
import json
from datetime import datetime

from app.database import SessionLocal, engine
from app.db_compat import run_compat_migrations
from app.models import Base, ContentOperationTemplate
from app.schemas import ContentPackageGenerateFromArticle
from app.services.content_ops_service import ensure_content_ops_defaults, generate_package_from_article
from app.services.shenlun_daily_service import ensure_shenlun_daily_task
from app.services.theory_daily_service import ensure_theory_daily_task
from app.timezone import today as today_str


PRODUCTS = {
    "shenlun": {
        "template": "shenlun_three_cut",
        "hour": 7,
        "deep_link": "/shenlun/#/pages/reading/detail?id={content_id}",
        "ensure": ensure_shenlun_daily_task,
    },
    "theory": {
        "template": "theory_current",
        "hour": 12,
        "deep_link": "/theory/#/pages/learning/index",
        "ensure": ensure_theory_daily_task,
    },
}


def generate(date: str, selected: set[str]) -> list[dict]:
    results: list[dict] = []
    Base.metadata.create_all(bind=engine)
    run_compat_migrations()
    with SessionLocal() as db:
        ensure_content_ops_defaults(db)
        for product, config in PRODUCTS.items():
            if product not in selected:
                continue
            task = config["ensure"](db, date)
            if not task:
                results.append({"productKey": product, "status": "skipped", "reason": "无合格今日教学内容"})
                continue
            template = db.query(ContentOperationTemplate).filter(ContentOperationTemplate.code == config["template"]).first()
            if not template:
                results.append({"productKey": product, "status": "skipped", "reason": "运营模板不存在"})
                continue
            try:
                package = generate_package_from_article(db, ContentPackageGenerateFromArticle(
                    productKey=product,
                    templateId=template.id,
                    articleId=task.content_id,
                    campaignKey=f"daily-{product}-{date.replace('-', '')}",
                    deepLink=config["deep_link"].format(content_id=task.content_id),
                    plannedAt=datetime.fromisoformat(f"{date}T{config['hour']:02d}:00:00"),
                ))
                results.append({"productKey": product, "status": "created", "packageId": package["id"], "title": package["sourceTitle"], "plannedAt": str(package["plannedAt"])})
            except ValueError as exc:
                results.append({"productKey": product, "status": "skipped", "reason": str(exc)})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="生成申论/政治理论每日运营草稿")
    parser.add_argument("--date", default=today_str(), help="YYYY-MM-DD，默认今天")
    parser.add_argument("--product", choices=["all", "shenlun", "theory"], default="all")
    args = parser.parse_args()
    selected = set(PRODUCTS) if args.product == "all" else {args.product}
    print(json.dumps({"date": args.date, "packages": generate(args.date, selected)}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
