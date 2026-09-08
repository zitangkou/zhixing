"""本地上传目录路径（与 Docker 卷 /app/server/data 对齐）"""
from pathlib import Path

# server/app/… → parents[1] = server/
_SERVER_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = _SERVER_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"


def uploads_subdir(*parts: str) -> Path:
    path = UPLOADS_DIR.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def detect_image_ext(content_type: str, filename: str, raw: bytes) -> str | None:
    """返回带点后缀，如 .jpg；不支持则 None。"""
    ct = (content_type or "").lower().strip()
    name = (filename or "").lower()

    # iPhone 原图常见 HEIC，明确拒绝并提示
    if "heic" in ct or "heif" in ct or name.endswith((".heic", ".heif")):
        return None
    if len(raw) >= 12 and raw[4:8] == b"ftyp":
        brand = raw[8:12]
        if brand in (b"heic", b"heix", b"mif1", b"msf1", b"hevc", b"hevx"):
            return None

    allowed = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    ext = allowed.get(ct)
    if ext:
        return ext
    if name.endswith(".png"):
        return ".png"
    if name.endswith(".webp"):
        return ".webp"
    if name.endswith(".gif"):
        return ".gif"
    if name.endswith(".jpg") or name.endswith(".jpeg"):
        return ".jpg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if raw[:3] == b"GIF":
        return ".gif"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return ".webp"
    if raw[:2] == b"\xff\xd8":
        return ".jpg"
    return None


def is_heic_like(content_type: str, filename: str, raw: bytes) -> bool:
    ct = (content_type or "").lower()
    name = (filename or "").lower()
    if "heic" in ct or "heif" in ct or name.endswith((".heic", ".heif")):
        return True
    if len(raw) >= 12 and raw[4:8] == b"ftyp":
        brand = raw[8:12]
        if brand in (b"heic", b"heix", b"mif1", b"msf1", b"hevc", b"hevx"):
            return True
    return False
