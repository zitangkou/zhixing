# 智能体交接备忘（2026-09-24 会话沉淀）

> 给**下一个接手本仓库的智能体/人**用：先读本页，再按链接下钻。  
> 仓库：`git@github.com:zitangkou/zhixing.git` · 本地常见路径：`~/Projects/zhixing`  
> 权威开发规范：根目录 `AGENTS.md` / `CLAUDE.md`、`PROJECT_PROMPT.md`、`ARCHITECTURE.md`、`FEATURES.md`

---

## 0. 30 秒结论（必读）

| 项 | 现状 |
|----|------|
| **日常上线方式** | **开发机轻量部署**：`bash scripts/deploy-from-local.sh`（本机构建镜像 → scp → 服务器 `load` + `up --no-build`） |
| **禁止** | 在 **≈2G 云主机**上执行 `docker compose --build` / `bash deploy.sh` / 无条件的 `deploy-update.sh` |
| **为什么** | 镜像构建含 H5 + admin（`vue-tsc`）+ Python；2G 机会 OOM / SSH banner 超时，看起来像「宕机」 |
| **服务器代码目录** | `/opt/zhixing-gongkao`，**当前无 `.git`**；线上版本看 `.deployed-sha` |
| **SSH 别名** | 本机 `~/.ssh/config` 里 `Host zhixing-aliyun` → `root@121.40.169.2`，密钥 `~/.ssh/zhixing_aliyun` |
| **生产形态** | Docker 单容器；宿主机 Nginx HTTPS → `127.0.0.1:8081`（容器映射）；**禁止** `docker compose down -v` |

详细步骤与故障表：**[cloud-server-deploy-guide.md](./cloud-server-deploy-guide.md)**（日常更新以该文档 §4 为准）。

---

## 1. 本会话做了什么（业务 + 运维）

### 1.1 业务侧（摘要）

- **行测**：入口改为「先套题、后题型」；相关页与 `xingce_quiz_service` / admin 行测等曾在 PR #1 合入 `main`。
- **时政 HTML 导入**：曾误改「一图读懂」解析，已回滚；运营约定导入用 `*_结构化HTML.html`（见运营物料文档与 admin `List.vue` 提示）。
- **微信小程序 / 包体**：分支 `feat/weapp-package-size` 等；包体与登录相关改动经 PR 合入或仍在特性分支——**以上线 `.deployed-sha` 为准**，勿假设本地分支 = 生产。
- **行测 JSON 导入**：材料链接去重等（PR #4 一带）。

### 1.2 运维侧（本会话核心教训）

1. **Cursor「提交一直转圈」**：多半在等 `COMMIT_EDITMSG` / 内置 git-editor，不是 hook；代码不会因此丢失。
2. **Sync Changes 失败**：本地与 `origin/main` **diverged**（各多 1 commit）+ 大量未提交改动；需 pull/merge/rebase，不是仓库损坏。
3. **云上 `deploy-update.sh` / `deploy.sh --build` 会把 2G 机打挂**：构建期内存顶满 → SSH `Connection timed out during banner exchange`，公网 HTTPS 也可能超时；**重启实例可恢复旧容器**，但未编完的新镜像不会上线。
4. **生产目录无 Git**：无法 `git pull`；曾用 rsync 同步源码，**正确日常方式改为只传镜像**（轻量部署）。服务器上 GitHub SSH 亦可能未配好（`Host key verification failed`）。
5. **轻量部署已跑通**：本机 `docker compose build`（`platform: linux/amd64`）→ `docker save | gzip`（约 80MB）→ scp → `docker load` → `compose up -d --no-build` → `/health`。
6. **`deploy-from-local.sh` 必须进 Git**：曾因未提交、切分支后丢失；接手后请确认文件存在并已跟踪。

---

## 2. 仓库与环境地图

```text
zhixing/
├── src/                 # 学员端 Taro4 + Vue3（H5 + weapp）
├── server/app/          # FastAPI 学员 API + admin API
├── server/admin-web/    # 管理后台 Vue3+Vite → 产出 admin-dist
├── Dockerfile           # 多阶段：h5-build + admin-build + python/nginx
├── docker-compose.yml   # platform: linux/amd64；数据卷 zhixing-gongkao-data
├── deploy.sh            # 服务器侧「构建并启动」（2G 应拒绝或仅 ALLOW_SERVER_BUILD=1）
├── scripts/
│   ├── deploy-from-local.sh   # ★ 日常上线（开发机）
│   └── deploy-update.sh       # 服务器 pull+build；2G 默认应拒绝
├── docs/release/        # 发布与部署文档（本文件所在目录）
├── AGENTS.md            # 智能体命令与架构入口
└── PROJECT_PROMPT.md    # 前端设计 token 规范
```

| 环境 | 说明 |
|------|------|
| 本地 H5 | `npm run dev:h5` → `http://localhost:10087` |
| 本地后端 | `uvicorn` → `8001`，头 `X-User-Id: u-demo-001` |
| 本地 admin | `server/admin-web` → `5173/manage/` |
| 云服务器 | 阿里云 ECS ≈ **1.7GiB RAM + 2G swap**；目录 `/opt/zhixing-gongkao`；容器名 `zhixing-gongkao` |
| 线上版本记录 | `/opt/zhixing-gongkao/.deployed-sha`（轻量部署写入的 `git rev-parse HEAD`） |
| 密钥 | 仅服务器 `.env`；**永不提交** `.env` / 真实 Token |

---

## 3. 轻量级部署（日常标准流程）

### 3.1 前置

- 本机已装 **Docker Desktop**，且能访问外网/npmmirror（构建内 `npm ci`）。
- 本机可：`ssh zhixing-aliyun 'echo ok'`（`BatchMode` 密钥登录）。
- 工作区就是要上线的提交（通常 `main` 已 push；特性分支上线须明确告知用户）。

### 3.2 一键

```bash
cd /path/to/zhixing
git status -sb          # 确认分支与脏工作区
bash scripts/deploy-from-local.sh
```

脚本步骤：

1. `docker compose build`（失败自动重试最多 3 次，常见 `ECONNRESET`）
2. `docker save … \| gzip` → `$TMPDIR/zhixing-gongkao.tar.gz`
3. `scp` 到服务器 `/opt/zhixing-gongkao.tar.gz`（并尽量同步部署脚本）
4. 远程：`docker load` → `compose up -d --no-build` → 写 `.deployed-sha` → 删服务器 tar → 轮询 `/health`
5. 本机清理：删 tar（`trap`）；`docker image prune -f`；`docker builder prune -f`（**保留当前镜像**以便下次增量）

环境变量（可选）：`DEPLOY_SSH_HOST`、`DEPLOY_REMOTE_DIR`、`DEPLOY_IMAGE`。

### 3.3 部署后验证

```bash
ssh zhixing-aliyun 'cat /opt/zhixing-gongkao/.deployed-sha; docker compose -f /opt/zhixing-gongkao/docker-compose.yml ps'
ssh zhixing-aliyun 'curl -fsS http://127.0.0.1:8081/health'
# 浏览器用正式域名测 / 与 /manage/（勿用 IP 验 HTTPS 证书）
```

刚切换容器时 `/health` 可能短暂 **502**，脚本会重试；十余秒内应变 **healthy + 200**。

### 3.4 注意事项（给智能体的硬约束）

1. **不要**在服务器上跑 `--build`「图省事」。
2. **不要** `docker compose down -v`。
3. **不要**假设 `/opt/zhixing-gongkao` 有 `.git` 或能 `git pull`。
4. **不要**把未跟踪的 `deploy-from-local.sh` 只留在工作区——切分支会丢；改完应提醒用户 commit 到 `main`。
5. Apple Silicon 本机构建依赖 compose 的 `platform: linux/amd64`；勿删该字段。
6. 本机磁盘：构建缓存会涨；脚本已 prune；仍过大时用户可手动 `docker builder prune -af`（下次全量变慢）。
7. SSH 若 `banner exchange` 超时：多半是云上又在构建或内存打满 → 控制台重启实例，恢复后**改走轻量部署**，不要再服务器构建。

---

## 4. 故障速查（本会话亲身踩过）

| 现象 | 含义 | 处理 |
|------|------|------|
| Cursor 提交转圈 / 打开 `COMMIT_EDITMSG` | 等编辑器结束 | 写说明并关 tab，或 `git commit -m`；勿 panic reset |
| Sync 提示看 log / diverged | 本地与远程分叉 | `git pull`/`rebase`；先 stash 脏工作区 |
| SSH banner timeout，HTTP 也挂 | 2G 构建打满 | 控制台重启；以后只用 `deploy-from-local.sh` |
| `deploy-from-local.sh: No such file` | 未进 Git / 切分支丢失 | 从文档恢复脚本或从 stash/历史检出 |
| 本机 `npm ci` `ECONNRESET` | 构建期网络 | 脚本会重试；再失败手动重跑 |
| 服务器 `NO_GIT` | 正常现状 | 只传镜像，勿强行 clone 覆盖（注意保留 `.env` 与 volume） |
| `/health` 200 但功能旧 | 只重启了旧容器 | 轻量部署换镜像；核对本机 SHA vs `.deployed-sha` |

---

## 5. 文档索引（接手顺序）

| 优先级 | 文档 | 用途 |
|--------|------|------|
| P0 | 本文件 | 会话结论 + 轻量部署约束 |
| P0 | [cloud-server-deploy-guide.md](./cloud-server-deploy-guide.md) | 云部署步骤真值（含 2G / 轻量） |
| P0 | [DEPLOY.md](../../DEPLOY.md) | 架构、`.env`、路由、备份 |
| P1 | [server-deploy-runbook.md](./server-deploy-runbook.md) | 首次上云故障表、中期 ACR 路线 |
| P1 | [weapp-build-guide.md](./weapp-build-guide.md) | 小程序构建与提审 |
| P1 | `AGENTS.md` / `ARCHITECTURE.md` / `FEATURES.md` | 代码与功能全景 |
| P2 | [政治理论每日出题运营物料…](../政治理论每日出题运营物料_会话沉淀_20260905.md) | 时政 HTML 物料格式 |
| P2 | [时评精拆原文HTML_知行导入约定.md](../时评精拆原文HTML_知行导入约定.md) | 导入约定 |

---

## 6. 建议的后续工程债（非本次必须）

1. 把 `deploy-from-local.sh` + 文档改动 **merge 进 `main` 并 push**。
2. `deploy.sh` / `deploy-update.sh` 在内存 &lt; 3G 时默认拒绝 `--build`（`ALLOW_SERVER_BUILD=1` 逃生舱）。
3. 中期：CI/ACR 推镜像，服务器只 `pull`（见 runbook §5）。
4. 可选：服务器恢复只读 deploy key + `.git`，便于对照；**仍不要在 2G 上 build**。

---

*沉淀日期：2026-09-24。若与脚本行为冲突，以仓库内 `scripts/deploy-from-local.sh` 源码为准。*
