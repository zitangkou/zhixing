"""ORM 模型公共依赖：Base、类型、时间与 ID 生成器。"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.timezone import now


def utcnow() -> datetime:
    """当前北京时间（保留旧名避免大量改名；DB 存的就是北京时间）"""
    return now()


def gen_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"
