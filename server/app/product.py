"""多产品上下文与首期静态配置。

Sprint 0 先用代码注册表保证配置可审查、可测试；需要运营后台动态维护时，
再迁移到 Product/ProductConfig 表，同时保持这里的读取接口不变。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Annotated

from fastapi import Header, HTTPException

from app.config import get_settings


@dataclass(frozen=True)
class ProductTab:
    key: str
    title: str
    route: str


@dataclass(frozen=True)
class ProductContext:
    key: str
    name: str
    short_name: str
    theme_key: str
    home_mode: str
    daily_target_min: int
    enabled_modules: tuple[str, ...]
    tabs: tuple[ProductTab, ...]

    def to_public_dict(self) -> dict:
        data = asdict(self)
        data["shortName"] = data.pop("short_name")
        data["themeKey"] = data.pop("theme_key")
        data["homeMode"] = data.pop("home_mode")
        data["dailyTargetMin"] = data.pop("daily_target_min")
        data["enabledModules"] = list(data.pop("enabled_modules"))
        return data


PRODUCTS: dict[str, ProductContext] = {
    "general": ProductContext(
        key="general",
        name="知行公考",
        short_name="知行",
        theme_key="red",
        home_mode="dashboard",
        daily_target_min=30,
        enabled_modules=("today", "learning", "quiz", "exam", "shenlun", "ziliao", "profile"),
        tabs=(
            ProductTab("today", "今日", "/pages/today/index"),
            ProductTab("learning", "学习", "/pages/index/index"),
            ProductTab("quiz", "练习", "/pages/question/index"),
            ProductTab("profile", "我的", "/pages/user/index"),
        ),
    ),
    "shenlun": ProductContext(
        key="shenlun",
        name="知行申论",
        short_name="申论",
        theme_key="red",
        home_mode="daily_training",
        daily_target_min=15,
        enabled_modules=("today", "shenlun_learning", "shenlun_practice", "review", "profile"),
        tabs=(
            ProductTab("today", "今日", "/pages/rmrb/index"),
            ProductTab("learning", "精读", "/pages/rmrb/article-list"),
            ProductTab("practice", "训练", "/pages/rmrb/drill"),
            ProductTab("profile", "我的", "/pages/user/index"),
        ),
    ),
    "theory": ProductContext(
        key="theory",
        name="知行日知",
        short_name="时政学习",
        theme_key="red",
        home_mode="daily_pack",
        daily_target_min=15,
        enabled_modules=("today", "theory_topics", "theory_quiz", "review", "profile"),
        tabs=(
            ProductTab("today", "今日", "/pages/theory/index"),
            ProductTab("topics", "专题", "/pages/index/index"),
            ProductTab("quiz", "复习", "/pages/question/index"),
            ProductTab("profile", "我的", "/pages/user/index"),
        ),
    ),
}


def resolve_product(product_key: str | None) -> ProductContext:
    settings = get_settings()
    key = (product_key or settings.default_product_key).strip().lower()
    if key not in settings.enabled_product_key_set:
        raise HTTPException(status_code=400, detail=f"产品未启用: {key}")
    product = PRODUCTS.get(key)
    if not product:
        raise HTTPException(status_code=400, detail=f"未知产品: {key}")
    return product


def get_product_context(
    x_product_key: Annotated[str | None, Header(alias="X-Product-Key")] = None,
) -> ProductContext:
    """FastAPI依赖：统一校验请求携带的产品键。"""
    return resolve_product(x_product_key)
