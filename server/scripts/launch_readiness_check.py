#!/usr/bin/env python3
"""
发布就绪一键核查（只读，不写任何数据）。

对应 docs/release/wechat-miniapp-launch-plan.md §5 提审前逐项验收中需要"到服务器上才能确认"的部分：
  1. C1 内容池家底：文章 / 题库 / 发布包 / 反馈 / 用户 各表行数与状态分布
  2. A3 旧昵称残留：app_users 里 nickname='政考学员' 的行数（>0 给出 UPDATE 建议，不代执行）
  3. A5 生产 .env：关键变量是否已设置（只看变量名与布尔值，绝不打印密钥值）
  4. A5 网关收口：nginx 层 /docs 应 404/403，/health 应 200

在服务器仓库根目录执行：
  cd /opt/zhixinggongkao/server && python3 scripts/launch_readiness_check.py
可选参数：
  --db PATH        指定 SQLite 路径（默认 data/zhixing.db）
  --base-url URL   网关探测地址（默认 http://127.0.0.1，即 nginx）
仅用标准库。
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request

OK, WARN, BAD, NA = "✅", "🟡", "❌", "—"


def find_db(explicit: str | None) -> str | None:
    if explicit:
        return explicit if os.path.exists(explicit) else None
    here = os.path.dirname(os.path.abspath(__file__))          # server/scripts
    candidates = glob.glob(os.path.join(here, "..", "data", "*.db"))
    # 优先 zhixing.db（生产/主库命名），跳过空壳 app.db
    candidates.sort(key=lambda p: (0 if p.endswith("zhixing.db") else 1))
    for p in candidates:
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            n = con.execute("select count(*) from sqlite_master where type='table'").fetchone()[0]
            con.close()
            if n:
                return p
        except sqlite3.Error:
            continue
    return None


def check_db(path: str) -> None:
    print(f"\n== 1. 内容池家底（{os.path.basename(path)}，只读） ==")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    tables = [r[0] for r in con.execute("select name from sqlite_master where type='table' order by name")]
    counts = {}
    for t in tables:
        try:
            counts[t] = con.execute(f'select count(*) from "{t}"').fetchone()[0]
        except sqlite3.Error:
            pass
    if not any(v for v in counts.values()):
        print(f"{WARN} 库存在但全空——这可能不是生产库，请确认 --db 参数")
    for t in sorted(counts):
        if counts[t]:
            print(f"  {t}: {counts[t]}")

    print("\n== 2. 关键表状态分布 ==")
    for t in tables:
        if not counts.get(t):
            continue
        if not any(k in t for k in ("article", "question", "paper", "content_ops", "feedback", "rmrb", "exam")):
            continue
        try:
            cols = {r[1] for r in con.execute(f'pragma table_info("{t}")')}
        except sqlite3.Error:
            continue
        for col in ("status", "review_status", "state"):
            # SQLite 会把不存在的双引号标识符当字符串字面量返回假分布，必须先确认列存在
            if col not in cols:
                continue
            try:
                rows = con.execute(f'select "{col}", count(*) from "{t}" group by "{col}" order by 2 desc').fetchall()
            except sqlite3.Error:
                continue
            if rows:
                print(f"  {t}.{col}: {rows}")

    print("\n== 3. A3 旧昵称残留 ==")
    for t in tables:
        if "user" not in t:
            continue
        try:
            cols = [r[1] for r in con.execute(f'pragma table_info("{t}")')]
            if "nickname" not in cols:
                continue
            n = con.execute(f'select count(*) from "{t}" where nickname = ?', ("政考学员",)).fetchone()[0]
            if n:
                print(f"{BAD} {t}: {n} 行仍是「政考学员」——执行：")
                print(f"   sqlite3 {path} \"UPDATE {t} SET nickname='知行学员' WHERE nickname='政考学员';\"（先备份整库）")
            else:
                print(f"{OK} {t}: 无残留")
        except sqlite3.Error:
            continue
    con.close()


def check_env() -> None:
    print("\n== 4. A5 生产 .env 关键变量（不显示值） ==")
    here = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(here, "..", ".env")
    if not os.path.exists(env_path):
        print(f"{BAD} 未找到 {os.path.normpath(env_path)}")
        return
    env: dict[str, str] = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    for key in ("SECRET_KEY", "CORS_ORIGINS", "ALLOW_REGISTER", "ADMIN_PASSWORD", "LLM_ENABLED", "LLM_API_KEY"):
        if key not in env:
            print(f"{BAD} {key}: 缺失")
        elif key in ("ALLOW_REGISTER", "LLM_ENABLED"):
            print(f"{OK} {key} = {env[key]}")
        else:
            print(f"{OK} {key}: 已设置（长度 {len(env[key])}）")
    if env.get("ALLOW_REGISTER", "").lower() in ("true", "1", "yes"):
        print(f"{WARN} ALLOW_REGISTER=true：提审口径建议 false + 体验账号（纯账密注册无找回是拒审点）；若保持开放需先补忘记密码路径")
    if env.get("ADMIN_PASSWORD", "") in ("", "admin123"):
        print(f"{BAD} ADMIN_PASSWORD 仍为默认/空——注意：改 .env 对已播种库无效，需走 PUT /admin/auth/password 接口改密")


def check_http(base: str) -> None:
    print(f"\n== 5. 网关收口复验（{base}） ==")
    probes = [
        ("GET", f"{base}/health", "健康检查", {200}),
        ("GET", f"{base}/docs", "API 文档应已收口", {403, 404}),
        ("GET", f"{base}/openapi.json", "Schema 应已收口", {403, 404}),
    ]
    for method, url, label, expect in probes:
        req = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                code = resp.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            print(f"{BAD} {url} → 连接失败（{e.__class__.__name__}）；服务器本机探测失败需检查 nginx")
            continue
        mark = OK if code in expect else BAD
        print(f"{mark} {url} → {code}（期望 {'/'.join(map(str, sorted(expect)))}）{label}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--base-url", default="http://127.0.0.1")
    args = ap.parse_args()
    print("发布就绪核查（只读） · 对应 launch-plan §5")
    db = find_db(args.db)
    if db:
        check_db(db)
    else:
        print(f"\n{NA} 未找到可用 SQLite 库（data/*.db），跳过第 1–3 项——生产库不在本机时请在服务器上运行")
    check_env()
    check_http(args.base_url.rstrip("/"))
    print("\n完成。判定标准见 docs/release/wechat-miniapp-launch-plan.md §5。")


if __name__ == "__main__":
    sys.exit(main())
