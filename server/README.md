# 知行后端

全仓产品矩阵、H5/小程序功能、后台菜单及操作发布流程见[项目功能与操作手册](../docs/PROJECT_OPERATIONS_MANUAL.md)。

轻量级 **FastAPI + SQLite + APScheduler** 架构，支持数据持久化、定时爬取、管理后台 RBAC。

## 架构选型

| 组件 | 选型 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 轻量、异步、自带 Swagger |
| 数据库 | SQLite (WAL) | 零配置持久化，可换 PostgreSQL |
| ORM | SQLAlchemy 2.0 | 类型安全 |
| 认证 | JWT + RBAC | 管理端角色权限 |
| 定时任务 | APScheduler | 每日自动爬取文章 |
| 爬虫 | httpx + 可扩展 | 当前内置模拟源，可接 RSS/真实站点 |

## 快速启动

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 启动（默认 http://127.0.0.1:8001）
uvicorn app.main:app --reload --port 8001
```

- API 文档：http://127.0.0.1:8001/docs
- 健康检查：http://127.0.0.1:8001/health

## 默认管理员

- 用户名：`admin`
- 密码：`admin123`

## API 分组

### 公开接口 `/api/*`（对接 Taro 前端）

- `GET /api/articles/daily` — 今日推荐
- `GET /api/articles/{id}` — 文章详情
- `GET /api/questions?articleId=` — 题目列表
- `POST /api/answer` — 提交答案
- `POST /api/signin` — 签到
- `GET /api/points/log` — 积分流水
- `GET /api/rank?type=weekly` — 排行榜
- 等（与前端 Mock 契约一致）

移动端请求头：`X-User-Id: u-demo-001`（开发阶段标识用户）

### 管理接口 `/admin/*`（需 Bearer Token）

- `POST /admin/auth/login` — 登录
- 文章 CRUD `/admin/articles`
- 试题 CRUD `/admin/questions`
- 用户管理 `/admin/users`
- 系统设置 `/admin/settings`
- 角色权限 `/admin/roles`、`/admin/permissions`
- 爬虫 `POST /admin/crawler/run`、`GET /admin/crawler/logs`

## 角色权限

| 角色 | 权限 |
|------|------|
| super_admin | 全部 |
| editor | 文章/试题/爬虫/用户查看 |
| viewer | 只读 |

## 前端对接

默认已 **关闭 Mock**，直连 `http://127.0.0.1:8001`。

```bash
# 终端 1：后端
cd server && source .venv/bin/activate
uvicorn app.main:app --reload --port 8001

# 终端 2：H5 前端
npm run dev:h5

# 若需临时使用 Mock（含 rmrb/dushu/足迹等）：
USE_MOCK=true npm run dev:h5
```

冒烟测试（独立临时库）：

```bash
cd server && source .venv/bin/activate
python -m pytest tests/test_api_smoke.py -q
```

环境变量（可选）：

- `TARO_APP_API_URL` — API 地址（生产部署时改为 https://your-domain.com）
- `USE_MOCK=true` — 启用 Mock（生产勿开）

H5 开发时在 `.env` 的 `CORS_ORIGINS` 中加入前端地址（已含 10086/10087）。

### 新增用户数据 API（落库）

| 接口 | 说明 |
|------|------|
| `GET /api/user/me` | 用户信息、积分、签到日期 |
| `GET /api/study/records` | 学习记录 |
| `GET /api/study/section-reads` | 小节已读 |
| `POST /api/study/sections/read` | 标记小节已读 |
| `GET /api/wrong` | 错题本 |
| `POST /api/wrong/redo` | 错题重做 |
| `GET /api/review` | 复习任务（服务端计算） |

## 爬虫与文章结构

- **人民日报 RSS**：`politics.xml`、`legal.xml` 定时抓取
- 正文页解析后自动 **分章/节/段** 写入 `sections` JSON 字段
- 公开 API 返回 `sections` + 扁平 `content`（兼容出题）

手动触发：`POST /admin/crawler/run`

### 已退役历史说明：人民日报评论文章

管理端「人民日报 → 评论文章」复用全量电子报和客户端文章档案，先识别评论版及明确栏目名（如人民时评、今日谈、人民观点、金台随笔、和音、社论、微观等），再接收全量文章 AI 全文评估中高置信识别出的评论/社论稿。原文 Markdown/HTML 可预览；服务端 LLM 已启用时自动生成待审三刀解剖草稿（最多 2 篇并发），未启用时可逐篇手动提交。所有解剖稿都需人工编辑审核，通过后才标记为可用。文件存放在持久化数据目录 `server/data/rmrb/comments/`；不配置服务端 LLM 时，规则命中的原文归档仍可用。

管理端「人民日报 → 客户端评论 / 金句」单独采集客户端评论页最近 48 小时文章（以页面 `publishTime` 为准），列表支持分页，支持与电子报重复稿去重，并复用评论文章原文/三刀流程。审核顺序为先确认文章是否属于评论文章，再审核金句；排除文章会删除其金句。标题含明确栏目/系列前缀时，排除操作会建立同前缀自动过滤规则，并过滤当前及后续匹配文章；没有稳定前缀时仅排除本篇。金句采集优先读取来源网页的加粗标记，将标记对应到档案正文中的完整原句；无加粗标记时先按完整句切分，再由 AI 筛选所有符合申论迁移要求的候选句，保存时使用原文句子编号回填，避免模型截句或改写。候选保留来源类型，默认待人工审核；选择「不采用」会删除该金句。主题、适用场景和仿写示例由 AI 补充或人工完善。金句记录存于 `rmrb_comment_quotes`，排除规则存于 `rmrb_comment_exclusion_rules`。

管理端「人民日报 → 金句运营库」统一呈现已审核通过的金句，运营人员可按主题/关键词筛选，选择金句后建立每日运营包，生成并编辑小红书与公众号初稿，预览/导出中国红品牌 HTML 与纯文案。文案由规则模板生成，必须人工检查后发布；系统不连接外部平台发布接口。点击对应平台「标记已发布」后，该运营包金句计为已使用并从默认未使用池隐藏，防止重复运营；草稿不占用。运营包存于 `rmrb_quote_ops_packages`，金句关联存于 `rmrb_quote_ops_package_items`。

「人民日报 → 金句管理」是独立金句总库页面，分页展示全部已审核采用的评论金句，支持全文/来源文章搜索、主题与使用状态筛选，并显示出处、适用场景、仿写和已发布运营包记录。运营包制作与平台文案编辑仍在「金句运营库」完成。

### 已退役历史说明：人民日报全量文章 AI 评估

管理端「人民日报 → 全量文章」支持逐篇/批量全文评估、按评估状态筛选和查看报告；全量采集完成后会自动排队。需配置服务端 `LLM_ENABLED=true` 与 `LLM_API_KEY` 才会调用模型；未配置时记录保留为待评估。报告分别判断文章体裁和评论/观点属性，并包括申论关联、主题、适用场景、摘要、观点、结构、六项评分、原文证据和物料建议。评分按主题价值 20%、可迁移性 25%、事实素材 20%、表达质量 15%、论证结构 10%、时效性 10%折算。高/中关联文章保存正文文件版本，低关联正文仅用于本次评估并保留正文哈希与报告。AI 建议不直接覆盖最终分类；人工确认时核验原文证据，无法定位的证据会阻止确认。全文模型识别为评论/观点稿的文章可同步进入评论物料流程。评估结果存于 `rmrb_article_evaluations`，正文仍以档案文件版本存储，不放入 SQLite 正文列。

## 管理后台（admin-web）

管理 **UI** 与 **API** 路径分离，避免冲突，便于单进程部署：

| 用途 | 路径 |
|------|------|
| 管理页面 | `/manage/` |
| 管理 API | `/admin/*` |
| 移动端 API | `/api/*` |

### 开发

```bash
# 终端 1：后端
cd server && source .venv/bin/activate
uvicorn app.main:app --reload --port 8001

# 终端 2：管理前端
cd server/admin-web && npm run dev
# 访问 http://localhost:5173/manage/
```

Vite 仅将 `/admin` 代理到后端 API，页面由 dev server 在 `/manage/` 提供。

### 生产（单进程）

```bash
cd server/admin-web && npm run build   # 产出 server/admin-dist
cd server && uvicorn app.main:app --host 0.0.0.0 --port 8001
# 访问 http://your-host:8001/manage/
```

构建产物存在时，FastAPI 自动挂载 `admin-dist` 到 `/manage`。

## 生产部署

1. 将 `DATABASE_URL` 换为 PostgreSQL
2. 修改 `SECRET_KEY`、`ADMIN_PASSWORD`
3. 使用 gunicorn + uvicorn workers 或 Docker 部署
4. 爬虫模块替换 `CRAWL_SOURCES` 为真实 RSS/站点解析逻辑


## 每日金句库（2026-10-13，新代码；生产待发布）

后台只保留“人民日报 → 金句管理”。支持独立录入、编辑证据与多个主题仿写、日期筛选、JSON预检导入/去重/导出、确认与精选。LLM整理结果为待核对；全文仅临时驻留内存，保存的是逐句证据摘录及来源，错误日志不包含全文或模型响应。

配置（server/.env，不要提交密钥）：
- `DAILY_QUOTES_ENABLED=true`：启动独立定时任务；false只关闭自动运行。
- `DAILY_QUOTES_HOUR=6`、`DAILY_QUOTES_MINUTE=40`：北京时间；本阶段调度窗口截止08:00，应配置为08:00之前。
- `LLM_ENABLED=true`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`：复用服务端配置；未配置时页面提示，不伪报整理成功。
- 任务状态：queued/running/completed/partial/failed/empty；数据库防重，同日成功文章跳过，部分失败可重试。后台权限rmrb:read / rmrb:write。

旧采集与AI评估调度不再启动；旧/admin/rmrb-archive、/rmrb-comments、/rmrb-quotes接口已撤销，不能通过旧直链触发。学员端/api/rmrb与时评精拆不属于退役范围。

### 发布与旧数据清理

先备份并停止旧后端进程，再在server目录执行（脚本默认只预览）：

```bash
PYTHONPATH=. .venv/bin/python scripts/retire_rmrb_archive.py
PYTHONPATH=. .venv/bin/python scripts/retire_rmrb_archive.py --apply
```

脚本只支持SQLite，使用backup API创建一致快照，并备份data/rmrb专用目录。迁移已审核通过金句及来源/仿写，逐条核对后清空旧模块表与删除专用物料；不删除学员端独立表、uploads或其他产品数据。缺证据的旧金句保留待核对，不能误报已确认。旧数据不可迁移则中止清理。

备份在data/backups/rmrb-retirement-时间/，核对完成后30天内人工清理。数据库提交完成而文件清理失败时可再次运行脚本；不得为了重跑而删除新金句库。生产新版本启动自动建立三个新表，部署沿用仓库本地构建发布流程。

本地已清理旧档案数据并导入2026-10-13的30句/60例（待核对），这不表示生产库已清理或网站已上线。
