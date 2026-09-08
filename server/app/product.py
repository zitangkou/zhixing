"""综合版产品上下文。"""

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
