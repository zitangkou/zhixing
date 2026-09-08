# 知行公考 · 云服务器一键部署

> 适用：一台独立云服务器（建议 Ubuntu 22.04 / Debian 12，2核4G+）部署整套 H5 + FastAPI + 管理后台。
> 当前默认：备案前由项目容器直接监听公网 80；备案和证书完成后切换为宿主机 Nginx HTTPS 网关。
> 更新：2026-09-08

## 快速命令速查

```bash
# ① 一次性：环境准备（每台服务器只跑一次）
apt update && apt install -y git
cd /opt && git clone git@github.com:zitangkou/zhixing-gongkao.git
cd zhixing-gongkao && bash deploy/setup-docker.sh   # Docker 已就绪时会自动跳过，不影响其它项目

# ② 首次部署 / 安全更新
bash deploy.sh
bash scripts/deploy-update.sh

# ③ 备案与证书完成后切换 HTTPS 域名网关
cp deploy/nginx.conf /etc/nginx/sites-available/zhixing-gongkao
ln -sf /etc/nginx/sites-available/zhixing-gongkao /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# ④ 备份 / 每日定时备份
bash deploy/backup.sh
bash deploy/install-backup.sh
```

## 当前部署模式：独立服务器

服务器重置后只运行本项目，不再保留为其他项目预留的 80 端口。部署分为两个阶段：

| 阶段 | `HTTP_BIND` | `HTTP_PORT` | 公网入口 | 用途 |
|---|---|---:|---|---|
| 备案前 | `0.0.0.0` | `80` | 容器直接监听 `http://公网IP` | H5、API、公众号明文回调联调 |
| 正式上线 | `127.0.0.1` | `8081` | 宿主机 Nginx 监听 80/443 | HTTPS H5、小程序 API、公众号安全回调 |

备案前注意：

1. 云安全组只放行 `22` 和 `80`，备案与证书完成后再放行 `443`。
2. HTTP 没有传输加密，不要在公共网络登录管理后台或传输敏感资料。
3. 公众号 Token 等密钥只写服务器 `.env`，不提交 Git。
4. 不要执行 `docker compose down -v`，它会删除本项目数据卷。

## 0. 部署架构（单机）

```text
备案前：公网 80 → 项目容器 Nginx
正式：公网 80/443 → 宿主机 Nginx → 127.0.0.1:8081 → 项目容器 Nginx
   ├── /          → 综合 H5 静态页
   ├── /api/      → FastAPI 学员端接口（uvicorn:8000）
   ├── /admin/    → FastAPI 管理端接口（JWT + RBAC）
   ├── /manage/   → 管理后台静态页（admin-dist）
   ├── /uploads/  → data/uploads（头像/错题图）
   └── /health    → 健康检查
```

## 1. 端口与路由约定

| 路由 | 说明 | 容器内处理 |
|---|---|---|
| `/` | 学员端 H5 | nginx 静态 `try_files` |
| `/api/*` | 学员端 API | nginx → uvicorn:8000 |
| `/admin/*` | 管理端 API | nginx → uvicorn:8000 |
| `/manage/*` | 管理后台 | nginx → FastAPI 挂载 admin-dist |
| `/uploads/*` | 上传文件 | nginx `alias` data/uploads |
| `/health` | 健康检查 | nginx → uvicorn |

生产域名网关不对公网开放 `/docs` 与 `/openapi.json`。需要排障时，应通过本机后端端口或 SSH 隧道访问。

宿主机监听由 `.env` 控制：独立服务器备案前默认 `HTTP_PORT=80`、`HTTP_BIND=0.0.0.0`。

两种对外方式：

- **阶段 A：公网 IP 直连**——使用默认值，访问 `http://公网IP/`。
- **阶段 B：HTTPS 域名网关**——把 `.env` 改为 `HTTP_BIND=127.0.0.1`、`HTTP_PORT=8081`，宿主机 Nginx 转发到 `127.0.0.1:8081`。

## 2. 服务器准备

- 安全组放行：备案前 `22`（SSH）和 `80`；正式 HTTPS 再增加 `443`。无需开放 `8000`、`8001`、`8081`。
- 连接服务器后安装 git：

```bash
apt update && apt install -y git
```

- 使用 **SSH 方式拉取**：先把服务器的 SSH 公钥添加到 GitHub（Settings → SSH and GPG keys → New SSH key）：

```bash
ssh-keygen -t ed25519 -C "server-zhixing-gongkao" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub    # 复制输出到 GitHub
ssh -T git@github.com        # 验证：Hi <用户名>! You've successfully authenticated...
```

## 3. 获取代码 + 一键部署

```bash
cd /opt
git clone git@github.com:zitangkou/zhixing-gongkao.git
cd zhixing-gongkao

# 一次性：安装 Docker / Compose + 配置镜像加速
bash deploy/setup-docker.sh

# 一键：生成 .env → 构建 → 启动 → 验证 H5、API 与管理后台
bash deploy.sh
```

部署完成后访问 `https://你的域名/`（H5）与 `https://你的域名/manage/`（管理后台）。

首次执行 `deploy.sh` 会自动生成 `.env`（随机 `SECRET_KEY` 与 `ADMIN_PASSWORD`，密码会打印在终端），随后建议：

```bash
nano .env    # 配置 DOMAIN、CORS_ORIGINS、ALLOW_REGISTER，确认 HTTP_BIND/HTTP_PORT
```

备案前部署公众号联调时，保持 `DOMAIN=`、`HTTP_BIND=0.0.0.0`、`HTTP_PORT=80`，并将 `WECHAT_OFFICIAL_PUBLIC_BASE_URL` 设置为 `http://公网IP`。

## 4. 配置域名网关（方案 B）

执行本节前先把 `.env` 改为：

```dotenv
HTTP_BIND=127.0.0.1
HTTP_PORT=8081
DOMAIN=你的正式域名
WECHAT_OFFICIAL_PUBLIC_BASE_URL=https://你的正式域名
```

重新执行 `bash deploy.sh`，确认容器只监听本机 8081 后，再配置宿主机 Nginx：

```bash
cp deploy/nginx.conf /etc/nginx/sites-available/zhixing-gongkao
# 编辑 server_name 为你的域名；确认 proxy_pass 端口与 .env 的 HTTP_PORT 一致
ln -sf /etc/nginx/sites-available/zhixing-gongkao /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# HTTPS（H5 / 小程序正式发布必需）：certbot --nginx -d 你的域名
```

## 5. 更新与运维

```bash
# 更新（只允许当前分支快进，不会自动覆盖服务器 tracked 修改）
bash scripts/deploy-update.sh

# 日志 / 重启 / 停止
docker compose logs -f zhixing-gongkao
docker compose restart
docker compose down

# 备份（整包 tar：SQLite + uploads + knowledge，单文件备份会丢图片）
bash deploy/backup.sh
# 每日 03:00 自动备份（保留 14 天，可配 BACKUP_DIR / BACKUP_RETENTION_DAYS）
bash deploy/install-backup.sh

# 恢复
docker compose exec -T zhixing-gongkao sh -c 'cd /app/server && tar -xzf -' < /opt/backups/zhixing-gongkao_xxx.tar.gz
```

> **禁止** `docker compose down -v`（会删除数据卷）。

## 6. 环境变量要点

| 变量 | 默认 | 说明 |
|---|---|---|
| `SECRET_KEY` | deploy.sh 自动生成 | JWT 密钥 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / 自动生成 | 管理后台账号 |
| `HTTP_PORT` / `HTTP_BIND` | `80` / `0.0.0.0` | 备案前公网直连；HTTPS 阶段改为 `8081` / `127.0.0.1` |
| `DOMAIN` | 空 | 对外域名（deploy.sh 汇总提示用） |
| `CORS_ORIGINS` | `*` | 同域部署可 `*` |
| `ALLOW_REGISTER` | `false` | 是否开放学员端自助注册 |
| `BACKUP_DIR` / `BACKUP_RETENTION_DAYS` | `/opt/backups` / `14` | 备份目录与保留天数 |
| `KNOWLEDGE_KB_DIR` | 空 | 知识框架本地目录（生产留空） |

## 7. 常见问题

- **Docker Hub 超时**：`setup-docker.sh` 已配置多源镜像加速；仍超时可在本机构建后 `docker save/load` 导入（见下）。
- **`npm ci` 报 ERESOLVE**：Dockerfile 会复制根目录 `.npmrc`（`legacy-peer-deps=true`），与本地行为一致。
- **端口被占**：改 `.env` 的 `HTTP_PORT` 后重跑 `bash deploy.sh`。
- **管理后台 404**：确认 `server/admin-dist` 已构建（Dockerfile 会自动构建；本地直接跑需先 `cd server/admin-web && npm run build`）。

## 8. Docker Hub 超时时：本地构建导入

```bash
docker compose build
docker save zhixing-gongkao-zhixing-gongkao:latest | gzip > zhengkao-image.tar.gz
scp zhengkao-image.tar.gz root@<IP>:/opt/
# 服务器
docker load < /opt/zhengkao-image.tar.gz
cd /opt/zhixing-gongkao && docker compose up -d
```

## 9. 本地开发

```bash
cd server && source .venv/bin/activate && uvicorn app.main:app --reload --port 8001
npm run dev:h5
cd server/admin-web && npm run dev
```

## 10. 发布产物与上线检查

综合版 H5 和微信小程序构建都会写入 `dist`，不能并行构建，也不能构建完两种目标后只取最后一个 `dist`。使用以下命令顺序构建并立即归档：

```bash
bash scripts/build-release-artifacts.sh --api-url https://你的正式域名
```

默认输出到系统临时目录，并包含：

```text
h5/index.html
weapp/project.config.json + dist
RELEASE.txt
```

检查源码 AppID 与产物：

```bash
python3 scripts/release-preflight.py
python3 scripts/release-preflight.py --artifact-dir /tmp/实际产物目录
```

服务器部署后检查环境和全部公开路由：

```bash
python3 scripts/release-preflight.py --env-file .env --base-url http://公网IP
# 备案、证书完成后最终检查
python3 scripts/release-preflight.py --env-file .env --base-url https://你的正式域名
```

公网 IP 的 HTTP 地址可以用于公众号服务器回调技术验证，但不能替代微信小程序的正式 HTTPS API 域名。检查工具只显示密钥是否安全配置，不会输出密钥内容。

## 11. 杜衡阁公众号回调联调

基础回调地址固定为：

```text
http://公网IP/api/wechat/callback
```

如果容器仍只监听 `127.0.0.1:8081`，应由宿主机 Nginx 的 80 端口转发；不要在微信后台填写容器内部端口。服务器 `.env` 增加：

```dotenv
WECHAT_OFFICIAL_ENABLED=true
WECHAT_OFFICIAL_TOKEN=至少16位随机Token
WECHAT_OFFICIAL_APP_ID=杜衡阁公众号AppID
WECHAT_OFFICIAL_PUBLIC_BASE_URL=http://公网IP
```

真实 Token、AppSecret 和 EncodingAESKey 不得提交到 Git。微信公众平台“服务器配置”中的 Token 必须与 `.env` 完全一致。

当前阶段使用明文模式验证 URL、关注回复和文字关键词；支持“今日、时政、申论、菜单”及短兜底。安全模式的 AES 消息会明确拒绝，完成加解密单元后再在公众号后台切换。

配置后先在服务器自检：

```bash
python3 scripts/release-preflight.py --env-file .env --base-url http://公网IP
```

备案与证书完成后，将公众号服务器 URL 和 `WECHAT_OFFICIAL_PUBLIC_BASE_URL` 同时切换到 `https://正式域名`。
