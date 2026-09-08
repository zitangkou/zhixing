#!/usr/bin/env python3
"""H5 全路由冒烟：逐页打开，收集 console error / 页面崩溃 / 明显空白。

用法:
  python3 scripts/smoke_h5_routes.py
  python3 scripts/smoke_h5_routes.py --base http://localhost:10087 --out /tmp/zk-smoke
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

# 与 src/app.config.ts pages 保持同步（hash 路由）
PAGES = [
    "pages/auth/login",
    "pages/auth/register",
    "pages/today/index",
    "pages/index/index",
    "pages/article/detail",
    "pages/article/mindmap",
    "pages/question/index",
    "pages/question/taking",
    "pages/question/article-pick",
    "pages/question/review",
    "pages/question/wrong",
    "pages/question/manual-list",
    "pages/question/manual-quiz",
    "pages/question/manual-edit",
    "pages/user/index",
    "pages/user/profile",
    "pages/user/signin",
    "pages/user/points",
    "pages/user/rank",
    "pages/user/growth",
    "pages/user/feedback",
    "pages/corpus/index",
    "pages/corpus/edit",
    "pages/plan/today",
    "pages/plan/review",
    "pages/plan/week",
    "pages/plan/day",
    "pages/knowledge/index",
    "pages/events/index",
    "pages/events/edit",
    "pages/review/hub",
    "pages/review/quiz",
    "pages/exam/list",
    "pages/exam/detail",
    "pages/exam/taking",
    "pages/exam/result",
    "pages/ziliao/index",
    "pages/ziliao/formulas",
    "pages/ziliao/formula-detail",
    "pages/ziliao/types",
    "pages/ziliao/type-detail",
    "pages/ziliao/tricks",
    "pages/ziliao/trick-detail",
    "pages/ziliao/drill",
    "pages/ziliao/result",
    "pages/rmrb/index",
    "pages/rmrb/article-list",
    "pages/rmrb/article-detail",
    "pages/rmrb/mines",
    "pages/rmrb/mine-edit",
    "pages/rmrb/terms",
    "pages/rmrb/drill",
]

IGNORE_CONSOLE = re.compile(
    r"(DevTools|favicon|Download the Vue DevTools|\[HMR\]|sass|deprecat)",
    re.I,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:10087")
    ap.add_argument("--out", default="/tmp/zk-smoke")
    ap.add_argument("--timeout", type=int, default=15000)
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("需要先安装: pip3 install playwright && python3 -m playwright install chromium", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        console_buf: list[str] = []
        page_errors: list[str] = []

        page.on(
            "console",
            lambda msg: console_buf.append(f"[{msg.type}] {msg.text}")
            if msg.type in ("error", "warning") and not IGNORE_CONSOLE.search(msg.text or "")
            else None,
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        for route in PAGES:
            console_buf.clear()
            page_errors.clear()
            url = f"{args.base}/#/{route}"
            started = time.time()
            status = "ok"
            detail = ""
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=args.timeout)
                page.wait_for_timeout(800)
                # Taro H5 通常有 #app
                body_text = page.locator("body").inner_text(timeout=3000) or ""
                if page_errors:
                    status = "pageerror"
                    detail = page_errors[0][:300]
                elif len(body_text.strip()) < 8:
                    status = "blank"
                    detail = "body nearly empty"
                shot = out / f"{route.replace('/', '_')}.png"
                page.screenshot(path=str(shot), full_page=False)
            except Exception as e:
                status = "fail"
                detail = str(e)[:300]
            elapsed = round((time.time() - started) * 1000)
            item = {
                "route": route,
                "status": status,
                "ms": elapsed,
                "detail": detail,
                "console": console_buf[:8],
            }
            results.append(item)
            mark = "✓" if status == "ok" else "✗"
            print(f"{mark} {status:10} {elapsed:5}ms  {route}  {detail}")

        browser.close()

    summary = {
        "base": args.base,
        "total": len(results),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "bad": [r for r in results if r["status"] != "ok"],
        "results": results,
    }
    report = out / "report.json"
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n汇总: {summary['ok']}/{summary['total']} ok")
    print(f"报告: {report}")
    return 0 if not summary["bad"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
