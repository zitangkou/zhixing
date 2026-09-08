"""统一时区工具：全部使用北京时间（Asia/Shanghai）

云服务器默认 UTC，业务日期（签到/清单/文章发布日）需按北京时间判断。
数据库里存的时间戳也是北京时间，对 SQLite 业务无影响。
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")


def now() -> datetime:
    """当前北京时间（带时区信息）"""
    return datetime.now(CST)


def today() -> str:
    """当前北京日期 YYYY-MM-DD"""
    return now().strftime("%Y-%m-%d")
