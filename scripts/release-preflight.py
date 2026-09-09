#!/usr/bin/env python3
"""知行公考发布前只读检查，不输出任何密钥值。"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed: list[str] = []

    def ok(self, message: str) -> None:
        self.passed.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def print(self) -> None:
        for message in self.passed:
            print(f"[OK] {message}")
        for message in self.warnings:
            print(f"[WARN] {message}")
        for message in self.errors:
            print(f"[ERROR] {message}")
        print(f"\n结果: {len(self.passed)} 通过 / {len(self.warnings)} 警告 / {len(self.errors)} 阻断")


def parse_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def check_source(root: Path, report: Report) -> None:
    path = root / "project.config.json"
    if not path.is_file():
        report.error("缺少 project.config.json")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.error(f"project.config.json 无法读取: {exc}")
        return
    if data.get("compileType") != "miniprogram" or data.get("miniprogramRoot") != "dist/":
        report.error("小程序编译目录配置不正确")
    else:
        report.ok("小程序编译目录为 dist/")
    if data.get("setting", {}).get("urlCheck") is False:
        report.warn("urlCheck=false；本地联调可用，正式真机验收必须验证合法域名")
    if data.get("appid") in (None, "", "touristappid"):
        report.warn("AppID 仍为 touristappid；正式发布需填写真实 AppID")
    else:
        report.ok("AppID 已配置")


def check_env(path: Path, report: Report) -> None:
    if not path.is_file():
        report.error(f"环境文件不存在: {path}")
        return
    values = parse_env(path)
    secret = values.get("SECRET_KEY", "")
    admin_password = values.get("ADMIN_PASSWORD", "")
    if not secret or secret in {"please-change-me-use-openssl-rand-hex-32", "dev-secret-key-change-in-production"}:
        report.error("SECRET_KEY 仍为空或使用示例值")
    else:
        report.ok("SECRET_KEY 已配置（值不显示）")
    if not admin_password or admin_password in {"change-this-password", "admin123"}:
        report.error("ADMIN_PASSWORD 仍为空或使用示例值")
    else:
        report.ok("ADMIN_PASSWORD 已配置（值不显示）")
    if values.get("ALLOW_REGISTER", "").lower() not in {"true", "false"}:
        report.error("ALLOW_REGISTER 必须明确设置为 true 或 false")
    else:
        report.ok(f"ALLOW_REGISTER 已明确设置为 {values['ALLOW_REGISTER'].lower()}")
    if not values.get("DOMAIN"):
        report.warn("DOMAIN 尚未设置；可以先做公网 IP 回调联调，但不能完成小程序正式发布")
    if values.get("WECHAT_OFFICIAL_ENABLED", "false").lower() == "true":
        token = values.get("WECHAT_OFFICIAL_TOKEN", "")
        public_base_url = values.get("WECHAT_OFFICIAL_PUBLIC_BASE_URL", "")
        if not re.fullmatch(r"[A-Za-z0-9]{16,32}", token):
            report.error("公众号回调已启用，但 WECHAT_OFFICIAL_TOKEN 不是 16～32 位英文或数字")
        else:
            report.ok("公众号回调 Token 已配置（值不显示）")
        if not public_base_url.startswith(("http://", "https://")):
            report.error("公众号回调已启用，但 WECHAT_OFFICIAL_PUBLIC_BASE_URL 不是有效 HTTP(S) 地址")
        else:
            report.ok("公众号公开入口基地址已配置")
        if not values.get("WECHAT_OFFICIAL_APP_ID"):
            report.warn("WECHAT_OFFICIAL_APP_ID 尚未配置；明文被动回复可联调，主动接口暂不可用")


def check_artifacts(path: Path, report: Report) -> None:
    if not path.is_dir():
        report.error(f"发布产物目录不存在: {path}")
        return
    release_file = path / "RELEASE.txt"
    if release_file.is_file():
        report.ok("发布清单 RELEASE.txt 存在")
    else:
        report.error("发布清单 RELEASE.txt 缺失")
    if (path / "h5" / "index.html").is_file():
        report.ok("学员端 H5 产物存在")
    else:
        report.error("学员端 H5 缺少 index.html")
    mini_app = path / "weapp" / "dist" / "app.json"
    project = path / "weapp" / "project.config.json"
    if mini_app.is_file() and project.is_file():
        report.ok("微信小程序产物可导入")
    else:
        report.error("微信小程序产物不完整")


def check_url(base_url: str, report: Report) -> None:
    base = base_url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        report.error("--base-url 必须以 http:// 或 https:// 开头")
        return
    routes = {
        "/health": "健康检查",
        "/api/config": "学员 API",
        "/": "学员端 H5",
        "/manage/": "管理后台",
    }
    for route, label in routes.items():
        url = f"{base}{route}" if route != "/" else f"{base}/"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "zhixing-release-preflight/1.0"})
            with urllib.request.urlopen(request, timeout=15) as response:
                if 200 <= response.status < 400:
                    report.ok(f"{label} 可访问: {url}")
                else:
                    report.error(f"{label} 返回 HTTP {response.status}: {url}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            report.error(f"{label} 无法访问: {url} ({exc})")
    if base.startswith("http://"):
        report.warn("当前为 HTTP，只适合临时公网 IP 联调；H5/小程序正式发布必须使用 HTTPS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--env-file")
    parser.add_argument("--artifact-dir")
    parser.add_argument("--base-url")
    args = parser.parse_args()

    report = Report()
    root = Path(args.repo_root).resolve()
    check_source(root, report)
    if args.env_file:
        check_env(Path(args.env_file).resolve(), report)
    if args.artifact_dir:
        check_artifacts(Path(args.artifact_dir).resolve(), report)
    if args.base_url:
        check_url(args.base_url, report)
    report.print()
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
