# 杜衡阁 · 在用功能清单（FEATURE_INVENTORY）

> 更新：2026-09-25  
> **本文件 = 在用 / 隐藏状态的操作真相源**。模块怎么实现见 [`FEATURES.md`](../../FEATURES.md)；下一步见 [`PRODUCT_ROADMAP.md`](./PRODUCT_ROADMAP.md)。  
> 学员端开关源：`src/constants/featureVisibility.ts`。管理端侧栏：`server/admin-web/src/config/featureVisibility.ts`。  
> 展示名：**杜衡阁**（历史文稿或写「知行公考」）。域名：`https://zhixinggk.ltd`。

### 状态词汇

| 词 | 含义 |
|----|------|
| 在用露出 | 菜单 / Tab / 侧栏可见，用户可正常点进 |
| 已实现菜单隐藏 | 代码与路由仍在，开关关闭或未挂入口；深链可进 |
| 部分完成 | 主路径可用，仍有缺口或仅后端/脚本 |
| 规划中 | 有方向，未落地或未排期实现 |
| 已下线 | 明确移除，不再维护入口 |
| 后置 | 产品决定暂不做 |

### 列说明

功能名 | 端(weapp/H5/admin/API) | 状态 | 入口/路由 | featureVisibility | 备注

---

## 1. 认证与账号

| 功能名 | 端 | 状态 | 入口/路由 | featureVisibility | 备注 |
|--------|----|------|-----------|-------------------|------|
| 微信一键登录 | weapp / API | 在用露出（代码）；生产需核对密钥 | `pages/auth/login` → `POST /api/auth/wechat/login` | — | `Taro.login` code；`MINIPROGRAM_*` 仅 `.env` |
| 账号密码登录 | weapp/H5 / API | 在用露出 | `pages/auth/login` → `POST /api/auth/login` | — | weapp 上折叠为次入口 |
| 注册 | weapp/H5 / API | 在用露出（受开关） | `pages/auth/register` → `POST /api/auth/register` | — | `ALLOW_REGISTER` / `GET /api/config` |
| 游客浏览 | weapp/H5 | 在用露出 | `guestAccess` 白名单路径；登录页「先逛逛」 | — | 写操作需登录 |
| 登录回跳 | weapp/H5 | 在用露出 | `LOGIN_REDIRECT_KEY` + `enterAfterAuth` | — | Tab 用 `switchTab` |
| 「我的」游客/已登录态 | weapp/H5 | 在用露出 | `pages/user/index` | — | `authEpoch` 刷新 Tab |
| 个人资料 / 改密 / 头像 | weapp/H5 / API | 在用露出 | `pages/user/profile`；`/api/user/*` | — | `phone` 可选手填 ≠ 短信绑定 |
| 短信登录 / 手机绑定 | — | 后置 | — | — | 见 ROADMAP Phase 2；仓库无 SMS |
| 管理员登录 | admin / API | 在用露出 | `/manage/` Login；`POST /admin/auth/login` | — | 与学员 JWT 分离 |
| 管理员改密 | admin / API | 在用露出 | `PUT /admin/auth/password` | — | |
| 游客练习快照合并 | API | 部分完成 | `/api/learning/guest-records` | — | 登录后合并设备侧记录 |

---

## 2. 学员端在用（菜单/快捷露出）

| 功能名 | 端 | 状态 | 入口/路由 | featureVisibility | 备注 |
|--------|----|------|-----------|-------------------|------|
| 学习 Tab | weapp/H5 | 在用露出 | `pages/index/index` | — | 双 Tab 之一 |
| 我的 Tab | weapp/H5 | 在用露出 | `pages/user/index` | — | |
| 今日文章 / 最近文章 | weapp/H5 | 在用露出 | 学习首页卡片 → `pages/article/detail` 等 | `SHOW_THEORY=true`（意图旗标；首页未再 `v-if` 该常量） | 时政/时评推荐与兜底 |
| 时政练习 | weapp/H5 | 在用露出 | 快捷区 → `pages/question/article-pick` | 同上 | |
| 时政阅读 + 考点练习 | weapp/H5 | 在用露出 | `pages/article/detail` → taking | 同上 | 未登录阅读/练习会引导登录 |
| 时评精拆列表/详情 | weapp/H5 | 在用露出 | 快捷区 / 我的 → `pages/rmrb/article-list`、`article-detail` | `SHOW_RMRB=true`（意图旗标） | HTML 原文/解析 |
| 行测真题入口 | weapp/H5 | 在用露出 | 首页快捷 → `pages/question/xingce-hub` 等 | — | 先套题后题型；非 `SHOW_EXAM` |
| 签到 / 积分 / 排行 | weapp/H5 | 在用露出 | `pages/user/signin`、`points`、`rank` | — | |
| 文章错题 | weapp/H5 | 在用露出 | 我的 → `pages/question/wrong` | — | |
| 反馈建议 | weapp/H5 | 在用露出 | `pages/user/feedback` | — | |
| 主题 / 深色 | weapp/H5 | 在用露出 | 我的页开关 | — | |

---

## 3. 学员端隐藏（已实现，菜单关）

| 功能名 | 端 | 状态 | 入口/路由 | featureVisibility | 备注 |
|--------|----|------|-----------|-------------------|------|
| 学习入口宫格 | weapp/H5 | 已实现菜单隐藏 | `pages/index` `examDomains` | `SHOW_HOME_DOMAINS=false` | 开露时复用，勿另起入口 |
| 资料分析 | weapp/H5 | 已实现菜单隐藏 | `pages/ziliao/*` | `SHOW_ZILIAO=false` | |
| 真题套卷（exam 流） | weapp/H5 | 已实现菜单隐藏 | `pages/exam/*` | `SHOW_EXAM=false` | 与行测 xingce-hub 不同路由 |
| 知识框架 | weapp/H5 | 已实现菜单隐藏 | `pages/knowledge/index` | `SHOW_KNOWLEDGE=false` | |
| 时事印象 | weapp/H5 | 已实现菜单隐藏 | `pages/events/*` | `SHOW_EVENTS=false` | |
| 学习计划 | weapp/H5 | 已实现菜单隐藏 | `pages/plan/*` | `SHOW_PLAN=false` | |
| 混合复习中心 | weapp/H5 | 已实现菜单隐藏 | `pages/review/*` | `SHOW_REVIEW_HUB=false` | |
| 行测错题（手动） | weapp/H5 | 已实现菜单隐藏 | `pages/question/manual-*` | `SHOW_MANUAL_WRONG=false` | 我的内受该开关 |
| 语料本 | weapp/H5 | 已实现菜单隐藏 | `pages/corpus/*` | `SHOW_CORPUS_MENU=false` | |
| 知行足迹 | weapp/H5 | 已实现菜单隐藏 | `pages/user/growth` | `SHOW_GROWTH=false` | |
| 考试倒计时 | weapp/H5 | 已实现菜单隐藏 | 今日页组件 / API countdown | `SHOW_EXAM_COUNTDOWN=false` | 今日非 Tab |
| 今日 / 练习 Tab | weapp/H5 | 已实现菜单隐藏 | `pages/today/index`、`pages/question/index` | — | 路由仍注册，不挂 tabBar |
| 时评开采枢纽/词库/阶梯 | weapp/H5 | 已实现菜单隐藏 | `pages/rmrb/index`、`mines`、`terms`、`drill` | — | 快捷改走列表；深链可进 |
| 思维导图 | weapp/H5 | 已实现菜单隐藏 | `pages/article/mindmap` | — | |
| 数据导入导出页 | weapp/H5 | 已实现菜单隐藏 | `pages/user/data` | — | 菜单已关 |

---

## 4. 管理后台

侧栏可见路径集合：`VISIBLE_PATHS`（`server/admin-web/src/config/featureVisibility.ts`）。

| 功能名 | 端 | 状态 | 入口/路由 | featureVisibility | 备注 |
|--------|----|------|-----------|-------------------|------|
| 今日学员端 | admin | 在用露出 | `/today` | path 在 VISIBLE | 今日推荐一眼看 |
| 时政文章管理 | admin | 在用露出 | `/articles` | VISIBLE | HTML 导入等 |
| 分类管理 | admin | 在用露出 | `/categories` | VISIBLE | 含待收录 |
| 时评文章 | admin | 在用露出 | `/rmrb/articles` | VISIBLE | |
| 规范词/骨架/论证/句式 | admin | 在用露出 | `/rmrb/term-categories` 等 | VISIBLE | |
| 用户管理 | admin | 在用露出 | `/users` | VISIBLE | |
| 反馈建议 | admin | 在用露出 | `/feedbacks` | VISIBLE | |
| 行测管理 | admin | 在用露出 | `/xingce` | VISIBLE | |
| 系统设置 / 角色 | admin | 在用露出 | `/settings`、`/roles` | VISIBLE | |
| 账号运营 content-ops | admin | 已实现菜单隐藏 | `/content-ops` | 不在 VISIBLE | 路由可直开 |
| 知识/计划/试卷/题库/生成/审核 | admin | 已实现菜单隐藏 | `/knowledge`、`/plan`、`/exam`、`/question-bank/*`、`/generation*` | 不在 VISIBLE | |
| 资料分析 / 练习原型 | admin | 已实现菜单隐藏 | `/ziliao`、`/practice/proto` | 不在 VISIBLE | |
| 反馈看板 / 错因 | admin | 已实现菜单隐藏 | `/analytics/*` | 不在 VISIBLE | |
| 语料本 / 时事事件 | admin | 已实现菜单隐藏 | `/corpus`、`/events` | 不在 VISIBLE | |
| 时政学习入口 | admin | 已实现菜单隐藏 | `/theory-learning` | 不在 VISIBLE | |

---

## 5. 后端与运营自动化

| 功能名 | 端 | 状态 | 入口/路由 | featureVisibility | 备注 |
|--------|----|------|-----------|-------------------|------|
| 学员 JWT API 域 | API | 在用露出 | `/api/*`（文章、刷题、签到、RMRB…） | — | 详见 FEATURES §4 |
| 管理 API | API | 在用露出 | `/admin/*` | — | RBAC |
| 公开配置 | API | 在用露出 | `GET /api/config` | — | allowRegister + product |
| 微信 jscode2session 登录 | API | 部分完成 | `POST /api/auth/wechat/login` | — | 依赖生产 `MINIPROGRAM_*` |
| 公众号回调 | API | 部分完成 | `wechat_official` 相关；配置开关 | — | 与小程序密钥分离 |
| 行测导入 / 生成 / 审核发布 | API + 脚本 | 部分完成 | admin API + `scripts/xingce/*` | — | 见 xingce-data-roadmap |
| 政治理论每日出题+物料 | 脚本/cron | 部分完成 | 运营物料流水线 | — | 见 docs 政治理论会话沉淀 |
| 行为事件写入 | API | 部分完成 | `activity_events` | — | 无统计页（M4） |
| 支付 / 会员 | — | 已下线 / 后置 | — | — | 充值页已移除 |
| 爬虫 | — | 已下线 | — | — | 已删除 |

---

## 6. 发布与运维相关能力

| 功能名 | 端 | 状态 | 入口/路由 | featureVisibility | 备注 |
|--------|----|------|-----------|-------------------|------|
| 开发机轻量部署 | 运维 | 在用露出 | `scripts/deploy-from-local.sh` | — | 2G 云主机禁止 `--build` |
| Docker 单容器 + 宿主机 Nginx HTTPS | 运维 | 核对现状 | `docs/release/*` | — | 勿臆造备案状态 |
| weapp 正式包构建 | 运维 | 在用露出（文档） | `docs/release/weapp-build-guide.md` | — | **仅用户要求时打包** |
| request 合法域名 | 运维/微信后台 | 进行中 / 核对现状 | 主机 `https://zhixinggk.ltd` | — | 登录验收前置 |
| 整包 data 备份 | 运维 | 在用露出 | `deploy/backup.sh` 等 | — | 禁止 `down -v` |

---

## 维护提示

- 改 `SHOW_*` 或 admin `VISIBLE_PATHS` 后，**先改本表状态列**，再视需要改 FEATURES 明细与 ROADMAP。  
- `SHOW_THEORY` / `SHOW_RMRB` 当前为 `true` 但源码中几乎不被 `v-if` 引用；露出以首页快捷区与「我的」实际入口为准，旗标表示产品意图。若日后用旗标包入口，保持与本表一致。
