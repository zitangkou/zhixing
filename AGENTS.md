# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Commands

```bash
# ── 学员端（Taro 4 + Vue 3）──────────────
npm install
npm run dev:h5        # H5 开发 http://localhost:10087（watch 模式）
npm run build:h5      # H5 产物 → dist/
npm run dev:weapp     # 微信小程序（watch），用微信开发者工具打开 dist/
npm run build:weapp
npm run lint          # eslint src --ext .vue,.ts,.tsx
npm run format        # prettier src/**/*.{vue,ts,scss}

# ── 后端（FastAPI + SQLite）──────────────
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 含真实 DeepSeek key，gitignored，勿提交/勿 echo
uvicorn app.main:app --reload --port 8001   # http://127.0.0.1:8001/docs

# 后端测试（独立临时库 _smoke.db）
python3 -m pytest -q                       # 全部
python3 -m pytest tests/test_api_smoke.py -q   # 单个文件
# 注：直接跑独立脚本（如 scripts/ 下的验证脚本）需 PYTHONPATH=.

# ── 管理后台（server/admin-web，Vue3+Vite）──
cd server/admin-web && npm install
npm run dev          # http://localhost:5173/manage/，/admin 代理到后端
npm run build        # vue-tsc -b && vite build → 产出 server/admin-dist
```

**注意**：H5 构建（esbuild）不做类型检查——只有 admin-web 的 `build` 跑 `vue-tsc`；前端类型问题靠 `npm run lint` 兜底。

## Architecture

单体仓库、多前端入口：学员端（`src/`）、FastAPI 后端（`server/app/`）、Vue 管理后台（`server/admin-web/`）。生产用 Docker 构建 H5 + admin-web，Nginx 承载 H5，FastAPI 提供 `/api/*`、`/admin/*`、上传文件与 `/manage/` 静态后台。

### 学员端 `src/`（Taro 4，双端 H5 + weapp）

- **路由**：全部页面在 `src/app.config.ts` 集中注册；页面放 `src/pages/<module>/`，每个页面配 `.config.ts`（`definePageConfig`）。
- **TabBar 双轨制**：H5 用自定义 `src/components/AppTabBar.vue`（4 tab：今日/学习/练习/我的），小程序用 `app.config.ts` 的原生 `tabBar`。加 tab 页需同时改两处。
- **API**：`src/api/index.ts` 统一导出 `api` 对象，返回 `{ code, data, message }`，内置真实 API / Mock 切换、Token 注入。`USE_MOCK=true` 时启用 `src/mock/service.ts`（本地演示），`src/api/index.ts` 始终 import mockService。生产勿开 Mock。
- **状态**：Pinia store 在 `src/store/`（user/quiz/article/plan/settings/knowledge 等）。
- **页面约定**：`definePageConfig` 在 `<script setup>` 内声明；加载 `onMounted→load()`、`usePullDownRefresh`、tab 页 `useDidShow` 刷新、`useReachBottom` 分页。

### 设计系统（改动样式前必读）

`PROJECT_PROMPT.md` 是权威开发规范（新增功能/页面/组件时注入）。要点：

- 设计 token 唯一来源 `src/styles/variables.scss`，每个 `<style scoped>` 首行 `@import '@/styles/variables.scss'`。
- **禁止硬编码颜色**——文字/背景/边框用 `$` 变量（暗色自动切换），图标色用 `useBrandColor()`，品牌渐变用 `brand-gradient` mixin。
- 单位一律 px，禁 rpx；品牌 5 套主题、默认中国红 `#D0021B`（真值源 `src/constants/theme.ts`，CSS 变量 `--zk-*` 运行时切换）；非公考域已裁剪，仍有少量残留壳待清理，清单见 `OPTIMIZATION.md`。
- 反馈统一 `showToast`/`showConfirm`（`@/utils/platform`），禁止直调 `Taro.showToast`。

### 后端 `server/app/`（FastAPI + SQLAlchemy 2 + SQLite）

- **路由按域拆分**：`api/public/`（前缀 `/api`，对接学员端）与 `api/admin/`（前缀 `/admin`，需 JWT + RBAC）各拆为多个域文件，`routes.py` 负责聚合；新增接口按域放入对应文件。
- **模型 / schema 按域拆分**：ORM 模型在 `models/`（base + 域模块，`__init__.py` 统一 re-export），Pydantic schema 在 `schemas/`（16 个域模块，`__init__.py` 统一 re-export）；业务规则放 `services/<domain>_service.py`。改模型/加表按此放置，保持 `from app.models import X` / `from app.schemas import X` 兼容。
- 启动时 `Base.metadata.create_all(bind=engine)` 自动建新表 + 旧表兼容补列，无需迁移脚本。
- 开发期用户标识：学员端请求头 `X-User-Id: u-demo-001`。
- **行为事件**：`services/activity_service.py` 的 `record_event()` 是唯一写 `activity_events` 表的入口，各业务服务（签到、读文章、答题、套卷交卷、资料练习、申论开采）在 commit 后调用，payload 存 JSON。
- 管理后台生产模式由 FastAPI 挂载 `server/admin-dist` 到 `/manage`。

### 管理与业务文档

- `FEATURES.md` — 全量功能清单（4 tab、Today 驾驶舱、52 页路由、后端域）；`ARCHITECTURE.md` — 架构、模块边界、关键业务流；`PROJECT_PROMPT.md` — 前端开发规范。
- 环境变量默认值见 `ARCHITECTURE.md` §7.2：H5 端口 `10087`、后端 `8001`、`CORS_ORIGINS` 默认 `http://localhost:10087`。
