# 知行公考

纯公考备考应用 — 基于 **Taro 4 + Vue 3 + TypeScript + NutUI + Pinia** 的跨端应用（微信小程序 + H5）。

Slogan：**以「上岸」为唯一目标**

## 功能

- 今日驾驶舱：考试倒计时、今日清单、复习提醒、昨日足迹
- 公考主线：时政阅读、资料分析、申论/人民日报、知识框架、真题套卷
- 练习闭环：多种刷题模式、错题本（文章/手动）、艾宾浩斯复习、复习中心
- 积分、签到、排行榜、知行足迹

**全量功能说明（各模块明细）→ [FEATURES.md](./FEATURES.md)** ｜ 项目进度 → [PROGRESS.md](./PROGRESS.md)

后续产品化方向：以本项目为能力母体，按申论、政治理论、资料分析、数量关系、言语理解、判断推理孵化独立垂直小程序，并共用内容运营中台。产品定义见 [PRODUCT_SPLIT_PLAN.md](./PRODUCT_SPLIT_PLAN.md)，结合 2025 国考真题资产的工程实施方案见 [DETAILED_IMPLEMENTATION_PLAN.md](./DETAILED_IMPLEMENTATION_PLAN.md)（两份均为 2026-08 历史战略文档）。

当前执行范围已收敛为政治理论、申论两个首发垂直产品。方案同时覆盖“简单而深入、简洁大气、方便优雅、连贯舒适”的体验规范、可扩展题型底座、账号内容运营闭环、具体 MVP、数据改造与 8–12 周排期，见 [TWO_PRODUCT_MVP_PLAN.md](./TWO_PRODUCT_MVP_PLAN.md)（Sprint 1 已执行完毕）。**现行执行计划**：[docs/plans/xingce-data-roadmap-2026.md](./docs/plans/xingce-data-roadmap-2026.md)（行测数据/出题调度中枢）、[docs/plans/optimization-plan-2026-09.md](./docs/plans/optimization-plan-2026-09.md)（项目级优化总盘）。

开发级需求文档：[`申论 PRD`](./docs/products/shenlun-prd.md)、[`政治理论 PRD`](./docs/products/theory-prd.md)、[`共享底座技术设计`](./docs/architecture/product-foundation.md)。

微信公众号订阅号、小红书、抖音、B站的固定栏目模板、跨平台内容包、双审核、内容日历和连续生产方案见 [CONTENT_OPERATIONS_PLAN.md](./CONTENT_OPERATIONS_PLAN.md)。其中公众号作为连接两个小程序的核心私域入口。

## 快速开始

```bash
cd ~/Projects/zhixing-gongkao
npm install
npm run dev:h5      # H5 开发 http://localhost:10087（默认连真实 API）
npm run dev:weapp   # 微信小程序，用开发者工具打开 dist 目录
```

后端另开终端：

```bash
cd server
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

## 部署（云服务器，一键）

```bash
# 服务器首次（一次性）
apt update && apt install -y git
cd /opt
git clone git@github.com:zitangkou/zhixing-gongkao.git   # 需先在 GitHub 添加服务器 SSH 公钥
cd zhixing-gongkao
bash deploy/setup-docker.sh    # 安装 Docker / Compose + 镜像加速（只跑一次）

# 一键部署：自动生成 .env → 构建 → 启动 → 健康检查
bash deploy.sh

# 配置域名网关（可选，正式运营推荐）
nano .env                      # 改 DOMAIN / CORS_ORIGINS / ALLOW_REGISTER
cp deploy/nginx.conf /etc/nginx/sites-available/zhixing-gongkao
# 编辑 server_name 与 proxy_pass 端口后：
ln -sf /etc/nginx/sites-available/zhixing-gongkao /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

- 访问：`http://<IP>:8081/`（H5）、`http://<IP>:8081/manage/`（管理后台）；有域名走网关后为 `http://<域名>/`
- 更新：`git pull && bash deploy.sh`；备份：`bash deploy/backup.sh`（每日定时：`bash deploy/install-backup.sh`）
- 与其它项目共存：compose 项目名 / 容器名 / 端口（8081）/ 数据卷均与 coffee-order 等隔离；服务器已有 Docker 时 `setup-docker.sh` 会自动跳过全局配置，不影响现有容器
- 完整手册（端口 / 路由 / HTTPS / 恢复）→ [DEPLOY.md](./DEPLOY.md)

## Mock 与真实 API

- **默认连真实 API**（`USE_MOCK` 未设置或非 `true`）
- 纯前端本地演示（不启后端）时：

```bash
USE_MOCK=true npm run dev:h5
```

此时 `src/mock/service.ts` 覆盖登录、文章、计划、人民日报、足迹、知识复习、错题、资料分析等接口。生产 / Docker **不要**开启 `USE_MOCK`。

## 技术说明

- 品牌主题：5 套主题（默认中国红 `#D0021B`，另有深蓝 / 墨绿 / 靛紫 / 琥珀橙），亮暗双模式
- 生产部署与数据备份见 [`DEPLOY.md`](./DEPLOY.md)

## 目录结构

```
src/
├── api/          # 接口封装
├── components/   # 公共组件
├── constants/    # 常量
├── mock/         # Mock 数据与服务
├── pages/        # 页面
├── store/        # Pinia 状态
├── styles/       # 全局样式
└── utils/        # 工具函数（记忆曲线、出题等）
```
