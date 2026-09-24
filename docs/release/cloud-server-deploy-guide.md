# 云服务器部署指南（知行公考）

> 与 [DEPLOY.md](../../DEPLOY.md) 配套。  
> **日常更新真值（2026-09-24 起）：开发机 `bash scripts/deploy-from-local.sh`。禁止在 ≈2G 云主机上 `docker compose --build`。**  
> 仓库：`git@github.com:zitangkou/zhixing.git` · 服务器路径：`/opt/zhixing-gongkao`  
> 智能体交接摘要：[agent-handoff-20260924.md](./agent-handoff-20260924.md)

---

## 1. 部署前：本机与要上线的提交对齐

```bash
cd /path/to/zhixing
git fetch origin
git status -sb
git log --oneline -3 HEAD
```

| 情况 | 做法 |
|------|------|
| 要上 `main` | 先 `git checkout main && git pull --ff-only origin main` |
| 要上特性分支 | 明确告知用户；`.deployed-sha` 会记该分支 HEAD |
| 有未提交改动且要进镜像 | 先 commit（或确认脏文件是否应进 Docker 上下文） |

**禁止**把 `.env`、真实 `SECRET_KEY`、`ADMIN_PASSWORD`、微信 Token/AppSecret 提交进 Git。

---

## 2. 服务器规格与为什么必须「轻量部署」

当前生产机约 **1.7GiB RAM + 2G swap**。`Dockerfile` 会在构建期跑：

- 学员端 `npm ci` + `build:h5`
- admin `npm ci` + `npm run build`（含 **`vue-tsc`**，最吃内存）
- Python `pip install`

在 2G 机上 `--build` 的典型后果：

- 日志停在 admin/`vue-tsc` 很久 → 随后 **SSH banner 超时**、站点超时（像宕机）
- 控制台重启后旧容器可恢复，**新代码并未上线**

| 规格 | 策略 |
|------|------|
| **≈2G（当前生产）** | **只**跑已编好的镜像：`deploy-from-local.sh` |
| **≥4G** | 仍推荐轻量部署；若坚持服务器构建：`ALLOW_SERVER_BUILD=1 bash deploy.sh`，并保持 swap |

### 2.1 Swap（建议常驻，构建逃生 / 运行余量）

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h && swapon --show
```

### 2.2 绝对不要做的事

- 在 2G 服务器上 `docker compose up -d --build` / 无门禁的 `deploy.sh`
- `docker compose down -v`（删 SQLite / uploads 卷）
- 覆盖服务器 `.env`
- 用公网 IP 测 HTTPS 证书是否匹配（应用域名）

---

## 3. 生产机实况（接手请先核实）

用本机 SSH 别名（示例配置）：

```text
Host zhixing-aliyun
  HostName 121.40.169.2
  User root
  IdentityFile ~/.ssh/zhixing_aliyun
  IdentitiesOnly yes
```

```bash
ssh zhixing-aliyun 'echo ok; free -h; cat /opt/zhixing-gongkao/.deployed-sha; \
  test -d /opt/zhixing-gongkao/.git && echo HAS_GIT || echo NO_GIT; \
  docker compose -f /opt/zhixing-gongkao/docker-compose.yml ps'
```

常见现状：

- 目录 **`NO_GIT`**：不靠 `git pull` 更新，靠镜像 load
- 容器监听 **`127.0.0.1:8081->80`**，前面有宿主机 Nginx 做 HTTPS
- 版本文件：**`.deployed-sha`**

---

## 4. 日常更新：轻量级部署（默认）

### 4.1 一键（推荐）

```bash
cd /path/to/zhixing
bash scripts/deploy-from-local.sh
```

等价流程：

```bash
docker compose build                          # linux/amd64（见 docker-compose.yml）
docker save zhixing-gongkao-zhixing-gongkao:latest | gzip > "$TMPDIR/zhixing-gongkao.tar.gz"
scp … zhixing-aliyun:/opt/zhixing-gongkao.tar.gz
# 服务器：
docker load -i /opt/zhixing-gongkao.tar.gz
cd /opt/zhixing-gongkao && docker compose up -d --no-build
# 写 .deployed-sha；删 tar；curl 127.0.0.1:${HTTP_PORT}/health
```

可选环境变量：`DEPLOY_SSH_HOST`、`DEPLOY_REMOTE_DIR`、`DEPLOY_IMAGE`。

### 4.2 脚本会清理什么

| 位置 | 清理 |
|------|------|
| 本机 tar.gz | `trap`：成功/失败都删 |
| 服务器 tar.gz | load 成功后删 |
| 本机 Docker | `image prune` + `builder prune`（保留当前镜像名以便下次增量） |

编译进程退出后 **内存归还系统**；慢涨的是磁盘上的 build cache。仍过大：`docker builder prune -af`（下次构建变慢）。

### 4.3 仅重启（不换代码镜像）

```bash
ssh zhixing-aliyun 'cd /opt/zhixing-gongkao && docker compose restart'
```

### 4.4 服务器侧旧脚本

- `scripts/deploy-update.sh`：设计为 pull + `deploy.sh`；**在无 `.git` 的机器上不可用**；2G 上即使有 Git 也不应使用。
- `deploy.sh`：含 `--build`；内存不足时应拒绝（见脚本内 `ALLOW_SERVER_BUILD` / MemTotal 门禁）。

---

## 5. 首次部署（新机器 / ≥4G 或可接受长构建）

仍可按旧路径：装 Docker → 配 `.env` →（2G 则**不要**本机构建，改用开发机首次 `deploy-from-local.sh` 灌镜像）。

若新机 ≥4G 且已 clone：

```bash
cd /opt/zhixing-gongkao
cp .env.docker.example .env   # 编辑密钥与 HTTP_BIND/PORT
ALLOW_SERVER_BUILD=1 bash deploy.sh   # 仅当确认内存充足
```

备案前 / HTTPS 阶段的 `HTTP_BIND`/`HTTP_PORT` 见 [DEPLOY.md](../../DEPLOY.md)。

---

## 6. 部署后验证

```bash
ssh zhixing-aliyun 'curl -fsS http://127.0.0.1:8081/health'
ssh zhixing-aliyun 'curl -fsS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/'
ssh zhixing-aliyun 'curl -fsS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/manage/'
ssh zhixing-aliyun 'curl -fsS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/api/config'
```

公网用**域名**打开 `/`、`/manage/`。可选：

```bash
python3 scripts/release-preflight.py --env-file .env --base-url https://你的域名
```

---

## 7. 备案后 HTTPS（方案 B）

1. `.env`：`HTTP_BIND=127.0.0.1`、`HTTP_PORT=8081`，域名 / CORS / 公众号 URL 改为 `https://…`
2. 换镜像上线（轻量部署）
3. 宿主机 Nginx：[deploy/nginx.conf](../../deploy/nginx.conf) + certbot
4. 微信后台回调：`https://域名/api/wechat/callback`

---

## 8. 备份与恢复

```bash
ssh zhixing-aliyun 'cd /opt/zhixing-gongkao && bash deploy/backup.sh'
```

恢复见 [DEPLOY.md §5](../../DEPLOY.md)。**永远不要** `down -v` 当「清缓存」。

---

## 9. 故障速查

| 症状 | 优先检查 |
|------|----------|
| SSH `banner exchange` 超时 | 是否又在服务器构建；控制台重启；改轻量部署 |
| 构建 `Killed` / OOM | 勿在 2G 构建；本机编 |
| 本机 `npm ci` `ECONNRESET` | 重跑 `deploy-from-local.sh`（脚本已重试） |
| `/health` 短暂 502 | 容器刚 Recreate，等 healthy |
| 功能仍是旧版 | 对比 `.deployed-sha` 与本机 `git rev-parse HEAD` |
| 管理端 HTML 预览异常 | 后端是否最新；物料是否 `*_结构化HTML.html` |
| Docker 构建静默 >10min、CPU≈0 | daemon.json MTU/DNS，见 [server-deploy-runbook.md](./server-deploy-runbook.md) §3 |

---

## 10. 相关文档

- [agent-handoff-20260924.md](./agent-handoff-20260924.md) — 会话沉淀与智能体约束  
- [DEPLOY.md](../../DEPLOY.md) — 架构、环境变量、本地开发  
- [server-deploy-runbook.md](./server-deploy-runbook.md) — 首次实战故障表、ACR 中期路线  
- [weapp-build-guide.md](./weapp-build-guide.md) — 小程序构建（与 H5 Docker 构建分开）  
- [scripts/deploy-from-local.sh](../../scripts/deploy-from-local.sh) — 日常上线脚本源码  
