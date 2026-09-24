# 杜衡阁 · 全量规划清单（PRODUCT_ROADMAP）

> 更新：2026-09-25  
> 展示名：**杜衡阁** · 域名 / API：`https://zhixinggk.ltd`  
> 状态标签：`已完成` | `进行中` | `可扩展` | `待优化` | `规划中` | `后置`  
> 在用/隐藏以 [`FEATURE_INVENTORY.md`](./FEATURE_INVENTORY.md) 为准；本文件管优先级与后续动作。

---

## 近端建议顺序（约 2–4 周）

1. **认证与账号 · Phase 1.x 运维收口**：生产 `.env` 配置 `MINIPROGRAM_*`（仅服务器，不进 Git）→ 部署后真机验微信一键登录 → 微信后台 **request 合法域名** = `https://zhixinggk.ltd` → 品牌改版后按需重建 weapp（**用户主动要求时再打包**）。
2. **发布与运维核对**：对照 [`../release/agent-handoff-20260924.md`](../release/agent-handoff-20260924.md) 与线上 `.deployed-sha`；日常用开发机轻量部署，勿在 2G 云主机 `--build`。
3. **内容主线**：按 [`../plans/xingce-data-roadmap-2026.md`](../plans/xingce-data-roadmap-2026.md) 滚动答案接入 / 审核发布；政治理论每日物料 cron 保持可用。
4. **学员开露（有产品拍板再动开关）**：优先复用已实现隐藏模块，改 `featureVisibility` 并同步 INVENTORY，勿另起入口。
5. **工程债 W6（见缝插针）**：见 [`../plans/optimization-plan-2026-09.md`](../plans/optimization-plan-2026-09.md) §W6。

---

## 1. 认证与账号

**总状态：`进行中`（Phase 1 代码已落地，运维收口与 Phase 2 仍开放）**

### 已约定（产品决策 · 已与代码核对）

| 决策 | 说明 | 代码依据 |
|------|------|----------|
| Phase 1：微信一键登录（weapp） | **大体完成 / 可发运**：小程序登录页主按钮「微信一键登录」→ `Taro.login()` code → `POST /api/auth/wechat/login` → jscode2session → 按 `openid` 找/建 `AppUser` → 发学员 JWT | `src/pages/auth/login.vue`、`src/api/domains/auth.ts`、`server/app/api/public/auth_user.py`、`server/app/services/wechat_miniprogram_service.py` |
| 短信 / 手机号绑定 | **Phase 2 · 后置**：仓库内**无** SMS / 验证码 / 绑定手机流水线；`phone` 仅资料字段可选手填 | 全仓无短信发送实现；`updateProfile` 可选 `phone` |
| 密钥落点 | `MINIPROGRAM_APP_ID` / `MINIPROGRAM_APP_SECRET` **只写 gitignored `.env`**；未配置时接口 **503「微信登录未配置」**；文档与日志不得贴 Secret / session_key | `server/.env.example`、`Settings.miniprogram_*`、`miniprogram_login_configured` |
| 与公众号隔离 | 小程序登录只用 `MINIPROGRAM_*`，与 `WECHAT_OFFICIAL_*` 无关 | `wechat_miniprogram_service` 模块注释 |
| 游客模式 | 学习首页、时评列表/详情、文章详情等可逛；写进度/刷题等需登录；「先逛逛」走 `skipAuth` | `src/constants/guestAccess.ts`、`src/utils/auth.ts` |
| 「我的」游客 vs 已登录 | 未登录显示「游客浏览」+「登录 / 注册」；登录后昵称/积分/退出；Tab 回刷靠 `authEpoch` | `src/pages/user/index.vue`、`bumpAuthView` / `setToken` |
| 登录回跳 | 未登录拦截记 `LOGIN_REDIRECT_KEY`；成功后 `enterAfterAuth`（tab 用 `switchTab`） | `auth.ts`、`postAuthRoute.ts` |
| 品牌与域名 | 展示名 **杜衡阁**；API 域名仍 **zhixinggk.ltd** | `src/constants/brand.ts`、`product.ts`；发布文档 |

### Phase 拆解

#### Phase 1 — 微信一键登录（weapp） · `已完成`（代码）/ `进行中`（生产验收）

- [x] weapp UI：一键登录为主，账号密码可折叠展开
- [x] H5：账号密码登录 + 注册（受 `ALLOW_REGISTER` / `GET /api/config`）
- [x] 后端 `POST /api/auth/wechat/login` + 单测（mock jscode2session，不打外网）
- [x] 新建用户默认昵称「杜衡阁学员」、`openid` 唯一
- [ ] **生产验收清单（Phase 1.x，不发明新 API）**
  - [ ] 服务器 `.env` 写入 `MINIPROGRAM_APP_ID` / `MINIPROGRAM_APP_SECRET` 并重启/换镜像后生效
  - [ ] 真机：合法域名已配 → 一键登录成功拿 token → 「我的」变为已登录态
  - [ ] 未配置时前端应看到明确失败文案（503），而非静默失败
  - [ ] 杜衡阁品牌改版后：**用户要求时再**重建 weapp 正式包（见 `docs/release/weapp-build-guide.md`）

#### Phase 1.x — 运营与合规配套 · `进行中`

- [ ] 生产部署说明中保留「需配置微信小程序登录」提示（运维 checklist）
- [ ] 微信公众平台 → 开发设置 → **request 合法域名** = `https://zhixinggk.ltd`（与构建 `--api-url` 主机一致）
- [ ] 隐私政策 / 用户协议与体验账号材料：以 `docs/release/` 既有清单核对，缺项补齐
- [ ] 管理员登录仍独立：`POST /admin/auth/login`（与学员 JWT 分离）——保持现状即可

#### Phase 2 — 短信 / 手机绑定 · `后置`

- [ ] 产品未排期；**不要**先加假按钮或半截 API
- [ ] 若未来做：需单独方案（服务商、频率限制、与 openid 账号合并策略）；当前资料里的 `phone` 字段**不等于**已绑定手机登录

### 各端现状摘要

| 端 | 能力 | 状态 |
|----|------|------|
| weapp | 微信一键 + 可选账密 | Phase 1 代码完成；生产依赖密钥与域名 |
| H5 | 账密登录 / 注册 | 在用；注册开关服务端控制 |
| admin | 用户名密码 + 独立 token；可自助改密 | 在用 |
| 游客 | 可读部分内容；登录后合并游客练习快照 API 已有 | `GET/POST …/learning/guest-records`（合并需登录） |

---

## 2. 发布与运维 · `进行中`

> `docs/plans/optimization-plan-2026-09.md` 仍写「ICP 硬等待」——那是 **2026-09-05** 快照。  
> **2026-09 下旬交接备忘**已描述：宿主机 Nginx **HTTPS** → 容器、`zhixinggk.ltd`、开发机轻量部署已跑通。  
> 下文用「**核对现状**」：以线上实际与 release 文档为准，不臆造备案批文号或提审结果。

| 项 | 状态 | 备注 |
|----|------|------|
| 域名 HTTPS / 网关 | **核对现状** | 见 `docs/release/agent-handoff-20260924.md`、`cloud-server-deploy-guide.md` |
| 轻量部署（本机构建传镜像） | `已完成`（流程） | `scripts/deploy-from-local.sh`；禁止 2G 机上 `--build` |
| weapp 正式包构建指引 | `已完成`（文档） | `docs/release/weapp-build-guide.md`；打包仅当用户要求 |
| 微信合法域名 + 隐私指引 | `进行中` / **核对现状** | 与登录 Phase 1.x 绑定 |
| 生产 `.env`（密钥、`ALLOW_REGISTER`、MINIPROGRAM_*） | **核对现状** | 永不提交仓库 |
| 整包 data 备份 | `已完成`（能力） | 见 `DEPLOY.md` |

---

## 3. 内容与行测数据 · `进行中` / `可扩展`

摘要 + 执行细节外链，**不在此复制整份 roadmap**：

- 调度中枢：[`../plans/xingce-data-roadmap-2026.md`](../plans/xingce-data-roadmap-2026.md)
- 已有能力方向：真题 JSON schema v2、答案接入滚动、规律报告、生成题 pending_review → 审核发布门禁、政治理论每日出题 + 多渠道物料
- 近期待办仍以该文档与 `xingce-structured-data/` SOP 为准（解析册依赖、差异题、媒体等）

---

## 4. 学员学习模块开露 · `可扩展`

当前菜单策略（开关文件 `src/constants/featureVisibility.ts`）：

- **露出意图**：`SHOW_THEORY=true`、`SHOW_RMRB=true`（时政 / 时评主线；首页快捷区已硬编码时政练习、时评精拆、行测真题等）
- **已实现但菜单隐藏**：`SHOW_HOME_DOMAINS`、`SHOW_ZILIAO`、`SHOW_EXAM`、`SHOW_KNOWLEDGE`、`SHOW_EVENTS`、`SHOW_PLAN`、`SHOW_REVIEW_HUB`、`SHOW_MANUAL_WRONG`、`SHOW_CORPUS_MENU`、`SHOW_GROWTH`、`SHOW_EXAM_COUNTDOWN` 均为 `false`

开露原则：改开关 + 更新 INVENTORY；新入口优先进首页 `examDomains` 再开 `SHOW_HOME_DOMAINS`。

---

## 5. 出题引擎与审核 · `进行中`

- 五引擎 + 生成工作台 + 教研审核（approve → publish 门禁）已落地（见 PROGRESS / xingce roadmap）
- 积压题人工审核仍是关键路径；LLM 盲审依赖有效 key（optimization-plan W3）
- Admin 侧栏：生成/审核等当前多在 **隐藏** 路径（见 INVENTORY），直链可用

---

## 6. 运营物料与公众号 · `可扩展`

- 每日政治理论物料自动化、内容运营发布包 / 双审核等能力已有代码与文档
- 公众号回调：`WECHAT_OFFICIAL_*`（与小程序登录分离）；启用与否核对服务器配置
- 增强项（互动、短视频试点、cron 告警）见 optimization-plan W4 — 多为 `规划中`

---

## 7. 工程债与质量 · `待优化`

详见 [`../plans/optimization-plan-2026-09.md`](../plans/optimization-plan-2026-09.md) **W6**：

- lint warnings、python-jose `utcnow`、element-plus 体积、H5 本机构建环境、activity 统计页、足迹 Admin、mock 类型等
- 不阻塞登录与内容主线；每周固定批处理即可

---

## 8. 商业化与产品矩阵 · `后置`

- 真实支付 / 会员：无对接（原充值已移除）→ `后置`
- 多垂直 App 矩阵：历史战略见根目录旧 PLAN；现行以综合母应用 + 内容主线为准，不提前复制六套代码
- 爬虫重建：已删除；需要时另立项 → `后置`

---

## 维护

变更本清单时同步 [`FEATURE_INVENTORY.md`](./FEATURE_INVENTORY.md) 与 [`README.md`](./README.md) 维护约定。登录相关只记录**已存在**的路由与配置键，禁止在文档中粘贴任何 Secret。
