#!/usr/bin/env python3
"""把 docs/content/knowledge-framework/*.md 导入为草稿，可选直接 publish（不含图片）。

用法（在 server/ 下，PYTHONPATH=.）：
  python -m app.scripts.import_knowledge_md --dir ../docs/content/knowledge-framework --publish
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# allow `python -m app.scripts.import_knowledge_md`
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.db_compat import run_compat_migrations  # noqa: E402
from app.models import Base  # noqa: E402
from app.database import engine  # noqa: E402
from app.services.knowledge_doc_service import import_md_to_draft  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dir",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "docs" / "content" / "knowledge-framework",
    )
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", type=str, default="")
    args = ap.parse_args()

    Base.metadata.create_all(bind=engine)
    run_compat_migrations()

    if not args.dir.is_dir():
        raise SystemExit(f"目录不存在: {args.dir}")

    db = SessionLocal()
    try:
        files = sorted(args.dir.glob("*.md"))
        files = [f for f in files if f.name != "README.md"]
        if args.only:
            files = [f for f in files if f.stem == args.only]
        for f in files:
            md = f.read_text(encoding="utf-8")
            # title from first h1 if present
            title = f.stem
            for line in md.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip() or title
                    break
            result = import_md_to_draft(
                db,
                f.stem,
                title,
                md,
                admin_id="import-cli",
                publish=args.publish,
                force=args.force,
            )
            print(f"{f.name}: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
