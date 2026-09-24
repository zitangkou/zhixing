# 云服务器部署指南（知行公考）

> 与 [DEPLOY.md](../../DEPLOY.md) 配套：本文侧重**完整步骤、2G 小内存注意项、Git 与验证**；命令真值以仓库内 `deploy.sh`、`scripts/deploy-update.sh` 为准。  
> 仓库：`git@github.com:zitangkou/zhixing.git` · 服务器推荐路径：`/opt/zhixing-gongkao`

## 1. 部署前：本地与 GitHub 对齐

在**本机**确认再让服务器拉代码：

```bash
cd /path/to/zhixing
git fetch origin
git status -sb
git log --oneline -3 HEAD
git log --oneline -3 origin/main
```

| 情况 | 做法 |
|------|------|
| `origin/main` 比本地新 | `git pull --ff-only origin main` |
| 本地有未提交改动还要上线 | 先 `git add` / `commit` / `git push origin main`，再登服务器更新 |
| 服务器 `git pull` 非快进 | 在服务器**不要**强推；本机理清分支后，服务器按 runbook 人工处理 |

**禁止**把 `.env`、真实 `SECRET_KEY`、`ADMIN_PASSWORD`、微信 Token/AppSecret 提交进 Git。

---

## 2. 服务器规格与 2G 内存（重要）

文档与脚本按 **单机 Docker 构建**（镜像内会跑：学员 H5 构建 + admin-web 的 `vue-tsc` + Vite + Python 依赖）。  

| 规格 | 说明 |
|------|------|
| **推荐** | 2 核 **4G** 及以上（[DEPLOY.md](../../DEPLOY.md) 默认假设） |
| **2G 可跑，但构建极易 OOM** | 首次 `bash deploy.sh` / `docker compose up --build` 前**务必加 swap** |

### 2.1 2G 机器：部署前加 swap（建议常驻）

在服务器执行（只需配置一次，重启后需在 fstab 持久化）：

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

期望：`Swap` 行约 2G，`swapon --show` 可见 `/swapfile`。

### 2.2 构建期判活（避免误杀长时间编译）

另开 SSH 窗口：

```bash
ps aux --sort=-%cpu | head -8    # node/vue-tsc 高 CPU = 仍在构建
free -h && swapon --show         # 内存顶满且无 swap = 即将 Killed
docker compose logs -f --tail=50 # 看构建阶段输出
```

常见现象：`vue-tsc` 或 `npm run build` 日志突然 `Killed` → **OOM**，加 swap 后重跑 `bash deploy.sh`。

### 2.3 网络与 Docker（国内 ECS）

- 镜像与 npm/apt 源：Dockerfile 已配国内镜像；仍慢时见 [server-deploy-runbook.md](./server-deploy-runbook.md) §3（MTU 1400、DNS、`registry-mirrors` **合并**写入，勿覆盖原有加速配置）。
- 带宽：1Mbps 级带宽下整镜像构建可能 **1 小时+**；可临时升带宽或改用「本地/CI 构建镜像再 `docker save/load`」（[DEPLOY.md §8](../../DEPLOY.md)）。

### 2.4 构建时不要做的事

- 不要在 2G 机上同时跑其他大内存任务（再开一套 `npm run dev`、全库导入等）。
- **禁止** `docker compose down -v`（会删 SQLite / uploads 数据卷）。
- 不要在公网 HTTP 阶段用管理后台传敏感资料（备案前无 HTTPS）。

---

## 3. 首次部署（新机器）

```bash
apt update && apt install -y git
# SSH 公钥加入 GitHub 后：
cd /opt && git clone git@github.com:zitangkou/zhixing.git zhixing-gongkao
cd zhixing-gongkao

bash deploy/setup-docker.sh

cp .env.docker.example .env
nano .env   # SECRET_KEY、ADMIN_PASSWORD、ALLOW_REGISTER、HTTP_BIND/PORT、域名等
# 2G 机器：先完成 §2.1 swap，再：

bash deploy.sh
curl -fsS "http://127.0.0.1:${HTTP_PORT:-80}/health"
```

备案前常用 `.env`：

- `HTTP_BIND=0.0.0.0`，`HTTP_PORT=80` → 公网 `http://IP/`、`http://IP/manage/`
- 安全组：放行 **22、80**（HTTPS 上线后再开 **443**）

---

## 4. 日常更新（重新部署代码）

在服务器项目根目录：

```bash
cd /opt/zhixing-gongkao
bash scripts/deploy-update.sh
```

脚本会：`git fetch` + **当前分支快进 pull** → 再执行 `bash deploy.sh`（重建并启动容器）。  
若提示「服务器存在未提交的 tracked 修改」，先 `git status` 处理，**不要**在未确认的情况下覆盖服务器上的改动。

仅重启、不拉代码：

```bash
docker compose restart
docker compose logs -f zhixing-gongkao
```

---

## 5. 部署后验证

```bash
# 健康检查
curl -fsS http://127.0.0.1/health    # 或按 .env 的 HTTP_PORT

# 路由（公网 IP 或域名）
curl -fsS -o /dev/null -w '%{http_code}\n' http://你的入口/
curl -fsS -o /dev/null -w '%{http_code}\n' http://你的入口/manage/

# 可选：发布前检查（不打印密钥内容）
python3 scripts/release-preflight.py --env-file .env --base-url http://你的入口
```

管理后台：浏览器打开 `/manage/`，用 `.env` 中 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 登录。

---

## 6. 备案后 HTTPS（方案 B）

1. `.env` 改为 `HTTP_BIND=127.0.0.1`、`HTTP_PORT=8081`，`DOMAIN`、CORS、公众号 `WECHAT_OFFICIAL_PUBLIC_BASE_URL` 改为 `https://域名`  
2. `bash deploy.sh`  
3. 宿主机 Nginx： [deploy/nginx.conf](../../deploy/nginx.conf) + certbot  
4. 微信后台 URL 改为 `https://域名/api/wechat/callback`

---

## 7. 备份与恢复

```bash
bash deploy/backup.sh
bash deploy/install-backup.sh   # 可选：每日 03:00，保留 14 天
```

恢复见 [DEPLOY.md §5](../../DEPLOY.md)。

---

## 8. 故障速查

| 症状 | 优先检查 |
|------|----------|
| 构建 `Killed` | §2.1 swap、`free -h` |
| `npm ci` / 拉镜像超时 | 网络、daemon.json MTU/DNS、账户带宽 |
| 管理端 HTML 预览异常 | 是否部署最新后端；粘贴的是否 `*_结构化HTML.html`（见 [政治理论每日出题运营物料](../政治理论每日出题运营物料_会话沉淀_20260905.md)） |
| `deploy-update.sh` 拒绝 pull | 服务器工作区有本地修改，需人工合并 |
| 502 / 连接拒绝 | `docker compose ps`、`HTTP_PORT` 与安全组是否一致 |

更细表格见 [server-deploy-runbook.md](./server-deploy-runbook.md) §3。

---

## 9. 相关文档

- [DEPLOY.md](../../DEPLOY.md) — 架构、环境变量、公众号回调、本地开发  
- [server-deploy-runbook.md](./server-deploy-runbook.md) — 首次实战沉淀、故障表  
- [deploy/nginx.conf](../../deploy/nginx.conf) — 正式域名 HTTPS 网关  
