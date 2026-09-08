# 云服务器部署 Runbook（知行公考）

> v1 · 2026-09-05 · 基于阿里云 ECS 首次部署实战沉淀
> 适用：Docker 单容器方案——`deploy.sh` 构建 三套 H5（综合 `/` + 申论 `/shenlun/` + 理论 `/theory/`）+ admin-dist + FastAPI，监听 `127.0.0.1:8081`，宿主机 Nginx 网关转发（方案 B）。
> 服务器应对齐的版本：`origin/main`（当前 `bb29d1f`，已含国内镜像源修复）。

## 1. 一次性初始化（新服务器，8 步）

```bash
# ① 装 git
apt update && apt install -y git

# ② 生成部署密钥，公钥加到 GitHub 仓库 Settings → Deploy keys（只读即可）
ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 && cat ~/.ssh/id_ed25519.pub
ssh -T git@github.com   # 验证，看到 Hi 开头即通

# ③ 克隆
cd /opt && git clone git@github.com:zitangkou/zhixing-gongkao.git && cd zhixing-gongkao

# ④ 装 Docker（已装自动跳过）
bash deploy/setup-docker.sh

# ⑤ 先备 .env 再启动（⚠️ 模板默认 ALLOW_REGISTER=false，必须改）
cp .env.docker.example .env && nano .env
#   SECRET_KEY=（openssl rand -hex 32）
#   ADMIN_PASSWORD=（强口令，字母+数字≥8；首次启动播种 admin 用，免去改密接口）
#   ALLOW_REGISTER=true
#   HTTP_BIND=127.0.0.1（默认方案B，备案后宿主 nginx 按域名转发）

# ⑥ 部署（首次 30-50 分钟，之后有层缓存秒级-分钟级）
bash deploy.sh
curl http://127.0.0.1:8081/health   # 期望 200

# ⑦ 建体验账号（提审材料用，密码专用不复用）
curl -s -X POST http://127.0.0.1:8081/api/auth/register -H 'Content-Type: application/json' \
  -d '{"username":"review_rizhi","password":"***","passwordConfirm":"***"}'
curl -s -X POST http://127.0.0.1:8081/api/auth/register -H 'Content-Type: application/json' \
  -d '{"username":"review_celun","password":"***","passwordConfirm":"***"}'

# ⑧ 就绪复核（内容池/昵称残留/.env/网关四类）
cd server && python3 scripts/launch_readiness_check.py
```

## 2. 日常更新

```bash
cd /opt/zhixinggongkao && bash scripts/deploy-update.sh
# （git pull --ff-only，被本地改动阻塞时自动 reset --hard origin/main，.env 不受影响）
```

## 3. 故障排查表（2026-09-05 首次部署实战沉淀）

| 症状 | 根因 | 修复 |
|---|---|---|
| `npm ci` 报 `ETIMEDOUT`（Dockerfile admin-build） | 容器内直连 npmjs.org，国内不通 | ✅ 已修（`bb29d1f`）：Dockerfile 两个 node 阶段加 `ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com` |
| `apt-get update` 数十分钟爬几 MB | 直连 deb.debian.org 吞吐极差 | ✅ 已修（`bb29d1f`）：apt 换 mirrors.aliyun.com；存量机手动：`sed -i '/^FROM python:3.12-slim/a RUN sed -i "s/deb.debian.org/mirrors.aliyun.com/g" /etc/apt/sources.list.d/debian.sources 2>/dev/null \|\| true' Dockerfile` |
| 构建长时间（>10min）全静默、CPU≈0、网卡流量≈0 | docker bridge 网络死连接（MTU/DNS 类问题） | 合并写 `/etc/docker/daemon.json`：`{"registry-mirrors":[保留原有],"mtu":1400,"dns":["223.5.5.5","114.114.114.114"]}` → `systemctl restart docker` → 重跑 `deploy.sh`（⚠️ 先 `cat daemon.json` 保留原有 registry-mirrors，覆盖会丢镜像加速） |
| `vue-tsc -b` 阶段 build 突然 `failed` + 日志 `Killed` | 小内存机器 OOM | `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile` 后重跑 |
| 下载/构建整体奇慢（KB/s 级） | **先查云账户**：欠费限速、带宽包过期、突发性能实例 baseline；1Mbps 带宽下 500MB 下载 ≈ 1 小时 | 阿里云控制台查余额/带宽计费模式；必要时临时升带宽跑完构建再降回 |
| SSH 里粘贴多行命令/heredoc 被截断错乱 | 终端 bracketed-paste 与 heredoc 冲突 | **一律单行命令**；传文件用 `base64 -d > file` 单行 |

**判活三件套**（另开 SSH 窗口，区分"在算"还是"挂死"）：

```bash
ps aux --sort=-%cpu | head -8          # node/npm/vue-tsc CPU 90%+ = 在算
free -h && nproc                       # 内存顶满无 swap = OOM 风险
cat /proc/net/dev | grep eth0 && sleep 5 && cat /proc/net/dev | grep eth0   # 字节不动=网络死
```

## 4. 首次部署后待办（当前状态快照 · 2026-09-05）

- [ ] 服务器对齐 `origin/main`：`cd /opt/zhixinggongkao && git checkout -- Dockerfile && git pull`（校验 `grep -c NPM_CONFIG_REGISTRY Dockerfile` = 2、`grep -c mirrors.aliyun.com Dockerfile` = 1）
- [ ] 部署成功：`bash deploy.sh` → `curl 127.0.0.1:8081/health`
- [ ] 体验账号 ×2（命令见 §1⑦），账密登记到 [submission-materials.md](./submission-materials.md) §3 两处【待填】
- [ ] **内容池导入（空库！）**：理论刷题需要题目、申论今日需要文章——`server/scripts/` 下有 `import_xingce_2025.py`、`import_generated_questions.py`、`import_rmrb_article.py` 等；具体缺口跑 `launch_readiness_check.py` 后定
- [ ] 管理后台 `/manage` 用 `.env` 的 ADMIN_PASSWORD 登录验证
- [ ] 备案通过后：宿主 nginx 配 `deploy/nginx.conf` + certbot HTTPS + 微信后台合法域名

## 5. 中期部署优化路线（按收益排序）

1. **预构建镜像 + ACR**：本地或 CI 构建镜像推阿里云容器镜像服务，服务器只 `pull + up`——把三前端编译从 2 核小机彻底挪走，部署变分钟级、不受服务器算力/网络影响（推荐，接入时改 `deploy.sh` 支持 `DEPLOY_MODE=registry`）。
2. **CI 构建**：GitHub Actions 已有 lint/pytest/admin build 三门禁，加一条 docker build/push 即为 1 提供产物。
3. **SKIP_TYPECHECK**：Dockerfile 加 ARG 让服务器构建跳过 `vue-tsc -b`（类型检查由本地/CI 把关），admin 阶段从 20 分钟级降到构建 vite 本身。
4. **带宽**：若确认实例为固定小带宽，构建期临时升级带宽（按量）跑完再降，比换镜像源更治本。
