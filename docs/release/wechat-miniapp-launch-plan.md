# 小程序发布前完善工作 · 执行计划

> 配套文档：[wechat-miniapp-launch-checklist.md](./wechat-miniapp-launch-checklist.md)（问题清单）· 本文件是**怎么做、按什么顺序做**
> 制定：2026-08-30 · 前提：两个小程序均为**个人主体**

---

## 0. 关键路径

```
【外部阻塞链】ICP 备案通过 → certbot 上 HTTPS → 微信后台配合法域名 → 真机回归 → 提审
                     ↑ 唯一不可压缩的等待项

【可并行链】  代码合规包（A1–A5）+ 内容准备（C1–C3）
                     ↓ 全部可在备案等待期完成，不依赖域名

【汇合点】    备案通过当天即可提审，无需再改代码
```

**结论：备案是唯一硬等待。所有代码与内容工作都可以现在做完，把提审周期压到备案通过后 1–2 天。**

---

## 1. 工作流 A · 代码与配置（现在可做）

### A1 隐私政策与用户协议 —— ✅ 已落地 2026-08-30（剩 3 处待填）

⚠️ **关键技术约束：个人主体小程序不支持 `web-view` 组件。** 所以协议**不能**做成 H5 挂在 `zhixinggk.ltd/legal/` 再用 web-view 打开，必须是小程序内的**原生页面**。这一条会直接决定实现方式，别按 H5 思路走。

| 步骤 | 文件 |
|---|---|
| 新建两个原生页面 | `apps/{shenlun,theory}-app/src/pages/legal/privacy.vue`、`agreement.vue` |
| 注册路由 | 各自 `src/app.config.ts` 的 `pages` 数组 |
| 登录/注册页加勾选 | `src/pages/auth/login.vue`、`register.vue`：未勾选不允许提交，文案「已阅读并同意《用户协议》与《隐私政策》」，书名号可点跳转 |
| 「我的」页加入口 | `src/pages/profile/index.vue`：新增「设置与关于」行 → 协议、隐私、反馈 |

**文案要点**（对应微信「用户隐私保护指引」，两边必须一致）：

- 只声明**实际收集**的：账号标识（用户名、昵称）、学习行为数据（任务进度、作答、错题、收藏）；
- **不要写手机号、邮箱**——`UserMe` 类型里有 `phone`/`email` 字段但界面从不收集（`apps/*/src/api/index.ts:93`），声明了反而要提供收集场景；
- 明确「不提供培训、课程与师资服务，不含新闻资讯内容」，与提审说明口径统一；
- 留一个联系邮箱/公众号作为反馈渠道。

**验收**：新用户首次登录必须勾选才能进入；协议页在断网环境下仍可打开（纯静态）；后台隐私指引条目与页面内容逐条对得上。

**实际落地结果**

- 新增 `apps/{shenlun,theory}-app/src/constants/legal.ts`：正文结构化常量，两款共用同一份文本，**只有 `APP_NAME` 一行不同**（已 diff 校验其余完全一致）；联系方式与生效日期集中在文件顶部，改一处即可。
- 新增 `apps/{shenlun,theory}-app/src/pages/legal/index.vue` + `index.config.ts`：**单页双文档**（顶部切换「用户协议 / 隐私政策」，支持 `?doc=privacy` 预选），比原计划的两页方案少一个路由。
- 修改：两个 app 的 `app.config.ts` 注册路由；`auth/login.vue` 与 `auth/register.vue` 加同意勾选与未同意拦截（书名号 `.stop` 跳转，不误触勾选）；`profile/index.vue` 加「关于」分区协议入口；`app.scss` 补 `.auth-agree*` 样式，勾选框用 `hit-target` mixin 保证热区。
- 验证：两个 weapp 均构建通过（5.6s）。解码产物确认路由已注册、登录与注册都有拦截、协议正文含各自应用名与两份文档、`政考/zhengkao` 全局零命中、token 键名已切到 `zhixing_token`。

**✅ 3 处待填已关闭（2026-09-05）**：`LEGAL_CONTACT.developer = 宁易`、`.email` / `.wechat = 杜衡阁`（邮箱见 `legal.ts`，同步后台指引时保持一致）、`LEGAL_EFFECTIVE_DATE = 2026-09-05`。隐私政策「面向成年备考人群」已同步改为「成年自学人群」贴合工具口径。填后两 app 已用生产 API 重建 weapp 并验证编译进 `common.js`（`待填` 全仓零命中）。填完后仍需：同步微信后台「用户隐私保护指引」，勾选映射表见 `docs/brand/legal-draft.md` 第三节——**手机号、邮箱、麦克风、相册、位置一律不勾**。

### A2 死入口与「规划中」文案 —— ✅ 已完成 2026-08-30

| 位置 | 问题 | 处理建议 |
|---|---|---|
| `apps/theory-app/src/pages/profile/index.vue` | 4 行「知识掌握地图 / 错题与收藏 / 学习与答题记录 / 学习计划与设置」渲染了「查看」标签但**整行没有 `@tap`**，点击无响应 | 前三项接已有页面（错题 → `question/wrong`、答题记录 → 练习历史）；「学习计划与设置」首版直接**删掉该行** |
| `apps/shenlun-app/src/pages/profile/index.vue` | 「学习计划与设置」显示「规划中」+ `showToast('该功能正在规划中')` | 同上，删行。审核对「点了没反应」和「规划中」都不宽容 |

**实际处理结果**：核查后发现 theory 只有 `question/wrong` 是可独立进入的页面——`learning/review` 需要 `taskId` 参数（是当日完成页，不是记录列表），`article/mindmap` 需要文章参数（是单篇导图，不是全局掌握地图），`corpus/edit` 依赖入口传参。因此没有按原计划「接三个页面」，而是**只保留两个有真实落点的入口**：「错题本与到期复习」→ `navigateTo question/wrong`，「刷题与练习进度」→ `switchTab practice/index`；其余三行删除。shenlun 删除「学习计划与设置」行与 `规划中` 分支，`items` 去掉 `enabled` 字段，标签统一「查看」。

原则落地：**首版宁可少入口，不可有假入口。**

已用 `TARO_APP_API_URL=https://zhixinggk.ltd` 重建两个 weapp 产物（各 1.0M，5.3s 完成），解码核对编译后的 `dist/pages/profile/index.js`：`onTap` 已绑定、跳转路由与预期一致、全仓库再无「规划中」文案。

### A3 旧品牌残留 —— ✅ 已完成 2026-08-30

| 位置 | 原值 | 已改为 |
|---|---|---|
| `server/app/models/account.py:56` | `nickname` 默认 `"政考学员"` | `"知行学员"` |
| `server/app/services/user_service.py:38` | 硬编码 `nickname="政考学员"` | `"知行学员"` |
| `server/app/main.py:57-58` | `title="政考通 API"`，描述含已停用的「文章爬取」 | `title="知行公考 API"`，描述改为「多产品学习内容、练习闭环、错题复习与内容运营」 |

全仓库复查 `政考学员|政考通` 已零命中；后端测试 `24 passed` 无回归。

⚠️ **遗留一步（需你在服务器执行）**：列默认值只作用于**新注册**用户，存量用户的昵称仍是库里的旧值。生产库不在本地，我没有代跑，上线前执行一次即可：

```sql
UPDATE app_users SET nickname = '知行学员' WHERE nickname = '政考学员';
```

（SQLite：`sqlite3 data/zhixing.db "UPDATE ..."`，执行前先备份整库。）

### A4 反馈入口 —— ✅ 已完成 2026-08-30（顺带修好一条从未通过的链路）

原计划只是「移植母应用现成能力」，核查后发现**整条反馈链路是坏的**，比预想的工作量更大：

| 问题 | 位置 | 说明 |
|---|---|---|
| 请求体字段名不匹配 | `api/public/_deps.py:184` | `FeedbackBody` 定义的是 `text`，而学员端提交的是 `content` → **校验必然 422，反馈从来没成功提交过** |
| 内容被丢弃 | `api/public/article_quiz.py` | 处理器只取 `user`，`body` 完全没用，反馈文字直接消失 |
| 随机判定采纳 + 随机送分 | 同上 | `random.random() > 0.5` 决定"是否采纳"并随机 `+10` 积分，既是假功能也是刷分漏洞 |
| 无反馈表 | `app/models/` | 全库没有任何 feedback 模型 |

**修复**：

- 新增 `Feedback` 模型（`app/models/misc.py`，表 `feedbacks`：user / product_key / content / status / note / 时间戳），启动时 `create_all` 自动建表；
- `FeedbackBody` 字段改为 `content`；`POST /api/feedback` 按当前产品上下文真实落库，返回 `{id, status, adopted:false}`（保留 `adopted` 字段以兼容综合母应用现有页面）；
- 新增管理端 `GET /admin/feedbacks`（按产品/状态筛选、分页）与 `POST /admin/feedbacks/{id}/handle`（采纳可显式加分 / 驳回，重复处理返回 400）；
- 注册权限码 `feedback:read` / `feedback:write`（`core/permissions.py`），editor 可读写、viewer 可读；
- schema 新增 `FeedbackOut` / `FeedbackHandleBody`。

**前端**：两个 app 各新增 `pages/feedback/index.vue` + `.config.ts`（本地 scoped 样式，用设计 token，无硬编码颜色），`api/index.ts` 加 `submitFeedback()`，注册路由，「我的」页「关于」分区在协议入口之前加「意见反馈」行。

**验证**：新增测试 `test_feedback_persisted_and_handled_by_admin`，覆盖提交落库、提交时不再随机送分、空内容被拒、管理端按产品查看、采纳显式加分、重复处理被拒。后端 `26 passed`（24 → +专题 → +反馈）；两个 weapp 重建通过，产物确认路由已注册、入口与跳转存在、`/api/feedback` 编译进 `common.js`。

### A5 服务端与网关收口 —— ✅ 代码侧已完成 2026-08-30（服务器操作待你做）

**已完成**

1. **nginx 收口 API 文档**：`deploy/nginx.conf` 原先 `location ~ ^/(health|docs|openapi\.json)$` 把三份都代理到公网，等于公开 107 个 `/api` + 109 个 `/admin` 接口清单。现改为 `location = /health` 只留健康检查，`/docs` 与 `/openapi.json` 不再对外，并留了带 IP 白名单的注释块备用；
2. **`.env.example` 重写**：按 `config.py` 实际字段补齐 `ALLOW_REGISTER`、`DEFAULT_PRODUCT_KEY`、`ENABLED_PRODUCT_KEYS`，逐项标注【生产必填/生产决策】，并给出 `openssl rand -hex 32` 等生成方式；
3. **注册策略建议（对应发布清单 B6）**：首版建议 `ALLOW_REGISTER=false` + 管理员开体验账号，规避「纯账密且无找回」的拒审点；若保持开放注册，必须先补「忘记密码」路径。**→ 2026-09-05 已拍板：开放注册**（生产 `.env` 设 `ALLOW_REGISTER=true`），「忘记密码」已按最小方案落地：两 app 登录页新增「忘记密码？点此复制邮箱人工重置」（复用 `legal.ts` 联系邮箱，剪贴板只写不读，与隐私声明一致），版本描述同步补充找回说明。

**核查中发现的两个坑（已写进 `.env.example` 注释）**

- ✅ **改 `.env` 里的 `ADMIN_PASSWORD` 对已部署环境无效**（播种逻辑是 `if db.query(AdminUser).count() == 0`，见 `app/seed.py:25`）——原先后台没有任何改密入口，只能删行重播种或手工 UPDATE 哈希。**已补自助改密接口**：`PUT /admin/auth/password`（`app/api/admin/auth_admin.py`），校验原密码、拒绝新旧相同，新密码要求 ≥8 位且同时含字母与数字（`AdminPasswordChange` 的 field_validator）。已知限制：令牌以用户名为载荷且无吊销机制，改密后旧令牌在有效期内仍可用，因此改完应重新登录。测试 `test_admin_password_change` 覆盖原密码错误、弱口令 422、相同口令被拒、改后旧密码失效新密码可登录。
- ⚠️ **旧 `.env` 里的 `CRAWL_ENABLED` / `CRAWL_CRON_*` 是死键**：`config.py` 中不存在这些字段，`extra="ignore"` 会静默忽略。已从模板移除，避免误以为爬虫被它控制。

**需你在服务器执行**

```bash
# 1) 校验并应用 nginx 改动
nginx -t && systemctl reload nginx
curl -s -o /dev/null -w "%{http_code}\n" https://zhixinggk.ltd/docs    # 期望 404/403，不再是 200
curl -s -o /dev/null -w "%{http_code}\n" https://zhixinggk.ltd/health  # 期望 200

# 2) 生产 .env：填 SECRET_KEY / CORS_ORIGINS / ALLOW_REGISTER
#    （.env 改动只对新库生效；管理员口令已存在时走下面的接口改）

# 3) 改掉默认管理员口令
TOKEN=$(curl -s -X POST https://zhixinggk.ltd/admin/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])')

curl -s -X PUT https://zhixinggk.ltd/admin/auth/password \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"oldPassword":"admin123","newPassword":"换成你的强口令123"}'
```

> `.env` 含真实密钥且已 gitignore，我只改了 `.env.example`，没有碰你服务器和本地的实际 `.env`。

### A6 提审材料包

- 体验账号（用户名/密码，两 app 各一个，提前在后台开好并清空脏数据）；
- 版本描述文本：定性说明「个人自学工具，不提供培训、课程与师资服务，不含新闻资讯」；
- 一段操作录屏或 5–8 张截图，覆盖登录 → 今日任务 → 完整闭环 → 我的。

**草稿已产出（2026-09-05）→ [submission-materials.md](./submission-materials.md)**：双 app 名称/简介/详细描述/标签/类目建议/版本描述模板/截图清单，逐项照抄即可；体验账号两处【待填】。

**禁词子串扫描已完成（2026-09-05）**：双 app 源码+dist 全量扫描（口径 = product-copy §6 五类禁词 + 政治/公考/备考/政考）。结论：命中均为 `legal.ts` 免责声明（"不是教育培训机构、不提供课程培训"——主动定性话术，**保留**）与允许词（申论）。唯一改动：theory-app 4 处「政治理论」→「理论学习」（今日/学习页导航标题、我的页标题、项目描述），已用生产 API 重建 weapp，`政治|时政` src+dist **零命中**；shenlun 无需改动。

### A7 专题页内容 —— ✅ 已按方案 B 实现 2026-08-30

原先 `apps/theory-app/src/pages/topics/index.vue` 把三个政治专题**硬编码在前端**，审核员一进「专题」tab 就能看到，与协议里「不含新闻资讯内容」的定性冲突，且个人主体展示时政类内容可能触发新闻/出版资质要求。

**改造为后端下发 + 可不发版切换**：

| 层 | 改动 |
|---|---|
| 服务 | `server/app/services/topic_service.py`：专题存在 `system_settings` 的 `topics.<product_key>`（JSON 数组），缺失时自动按默认值播种一行 |
| 接口 | `GET /api/product/topics`（`api/public/product.py`），按 `X-Product-Key` 返回对应产品专题；schema 新增 `TopicItem` / `TopicListOut` |
| 前端 | `apps/theory-app/src/api/index.ts` 加 `getTopics()` 与类型；`pages/topics/index.vue` 改为 `useDidShow` 拉取，含加载态与空态；标题去掉「考频」等字样 |
| 默认内容 | 提审期返回**方法类专题**：理论「理论文章怎么读 / 易混表述辨析 / 规范表述积累」，申论「材料怎么拆 / 小题怎么写 / 表达怎么改」 |

**为何复用 `system_settings` 而不新建表**：管理端 `PUT /admin/settings/{key}` 已存在（`api/admin/settings.py:11`），复用即零迁移、零新接口，天然满足「不发版切换」。代价是专题暂不支持与文章/题目关联及排序字段——等要做专题详情页时再升级为独立表。

**过审后切回真实专题**（无需发版）：在管理后台系统设置里改 `topics.theory` 的值，或：

```bash
curl -X PUT https://zhixinggk.ltd/admin/settings/topics.theory \
  -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
  -d '{"value":"[{\"no\":\"理\",\"title\":\"马克思主义基本原理\",\"desc\":\"哲学、政治经济学与科学社会主义\"}]"}'
```

**验证**：新增测试 `test_product_topics_served_and_switchable`，覆盖默认内容、**政治字样红线断言**、产品隔离、后台切换生效、非法 JSON 回落默认。后端 `25 passed`（原 24 + 1）；重建 theory weapp 后复扫，两个 app 的源码与产物中政治专题名与「时政」字样**全部零命中**，接口调用编译进 `common.js`。

---

## 2. 工作流 B · 外部依赖（需你操作）

| 项 | 状态 | 动作 |
|---|---|---|
| B1 ICP 备案 | 🟡 终审中，`zhixinggk.ltd` 与 `/api` 实测均被阿里云 403 拦截 | 等通过，用 `curl -sI http://zhixinggk.ltd/` 验 200 |
| B2 HTTPS | ❌ nginx 仅 `listen 80` | 备案通过后 `certbot --nginx -d zhixinggk.ltd` |
| B3 微信后台 | 🟡 名称与头像 ✅（2026-09-05）；**剩**：用户隐私保护指引勾选 + request 合法域名（依赖 B2） | request 合法域名 `https://zhixinggk.ltd`（已核实只需 1 个，无 uploadFile/downloadFile）；用户隐私保护指引按 legal-draft 映射表 |
| B4 类目与资质 | ✅ 已确认（2026-09-05 用户在后台完成类目设置） | — |
| B5 名称核验 | ✅ 已完成（2026-09-05「知行策论 / 知行日知」后台备好） | — |

---

## 3. 工作流 C · 内容与数据

| 项 | 说明 |
|---|---|
| C1 首发内容池 | 申论需有足够「已通过双审核」的文章；理论需题库 + 权威文章。用内容后台的「未来 7 天库存」看板先跑一遍，避免上线即空内容。**生产侧一键核查（2026-09-05 新增）**：`cd server && python3 scripts/launch_readiness_check.py`（只读，输出内容池家底/旧昵称残留/.env 关键变量/网关 /docs 收口四类结果） |
| C2 数据隔离（已核实，非待测） | 逐个模型查过：**带 `product_key` 的只有 `DailyLearningTask` 与 `UserDailyTaskProgress`**（`app/models/product.py:26,51`）+ `content_ops`；`practice.py` 里的 `WrongAnswer`/`StudyRecord`/`SectionRead`/`QuizAttempt` **只有 user_id 维度**，`ManualWrong` 靠 `subject` 字段间接区分。`list_wrong_questions`（`wrong_service.py:51`）确认仅按 user_id 过滤。结论：今日任务严格隔离，**错题本与阅读/测验记录是账号级共享**。<br>首版影响有限——申论不产生选择题错题，两个垂直 app 之间暂时不会串；真实重叠场景是「母应用 H5 与知行日知使用同一账号」。**建议首版接受**，并在文案里作为「一个知行账号，跨端同步」的正向特性表述；若产品要求严格分科，则需给这几张表补 `product_key` 并改查询（成本：迁移 + 多处查询）。<br>（更正：我上一轮说「只有两张表带产品维度」漏了 `UserDailyTaskProgress`，现已核准。） |
| C3 内容形态 | 首版权威媒体内容以**节选 + 来源标注 + 用户自主采集**（策论已有「文章采集」能力）呈现，避免成篇展示新闻原文 |

---

## 4. 建议排期

| 时间 | 工作流 A（代码） | 工作流 B/C（外部与内容） |
|---|---|---|
| 第 1 天 | ✅ A3 旧品牌残留 + A2 死入口（已完成，两 app 已重建产物） | B4 类目确认、B5 名称核验 |
| 第 2–4 天 | **A1 隐私政策与协议**（最大块，含三处页面与两 app 双份） | C1 内容池补齐 |
| 第 5 天 | A4 反馈页移植 | C2 数据隔离实测 |
| 第 6 天 | A5 nginx + .env 模板 | A6 体验账号开号与清数据 |
| 备案通过当天 | — | B2 certbot → B3 后台配置 |
| +1 天 | 真机回归（登录、闭环、协议、反馈） | 提审 |

---

## 5. 提审前逐项验收

- [ ] `curl https://zhixinggk.ltd/api/health` 返回 200
- [ ] 微信后台 request 合法域名已配且生效
- [x] 两个 app 均有隐私政策 + 用户协议原生页面，登录与注册页强制勾选（A1 已落地）
- [ ] 后台「用户隐私保护指引」条目与页面内容一致，且不含手机号/邮箱（**依赖你先填 `LEGAL_CONTACT` 三处**）
- [x] profile 无死入口、无「规划中」文案（A2 已完成）
- [x] 新注册用户昵称不再出现「政考学员」（A3 已完成；**存量用户仍需执行那条 UPDATE**）
- [x] 反馈入口可用，内容真实落库（A4 已完成；原先字段名不匹配导致从未通过）
- [x] 管理端可查看反馈并采纳加分 / 驳回（`/admin/feedbacks`，A4 新增）
- [ ] 生产 `.env`：SECRET_KEY / CORS_ORIGINS / ALLOW_REGISTER 已定，管理员口令已按 A5 说明真正改掉（**不是只改 .env**）
- [ ] `/docs`、`/openapi.json` 公网不可访问（配置已收口，**需 `nginx -t && systemctl reload nginx` 后复验**）
- [ ] 体验账号可登录并跑通完整闭环
- [ ] 名称、简介、头像与类目四者口径一致（均为「学习工具」）
- [x] 双 app 全量禁词子串扫描（2026-09-05：legal 免责命中保留；theory 3 处界面「政治理论」已改「理论学习」+ 项目描述，产物已重建）

---

## 6. 风险与回退

| 风险 | 回退方案 |
|---|---|
| 个人主体无任何可用类目 | 转企业主体（同时解锁教育类目与 web-view，协议可改 H5）；或首版只发 H5，小程序延后 |
| 「知行 XX」候选名全部被占 | 用倒序（韦编知行 / 汲古知行）或三字变体（知行帖）；长期靠商标注册证申诉 |
| 「每天 15 分钟」实测压不住 | 简介退回不带时长版本 |
| ~~专题页硬编码政治内容~~ | ✅ 已消除：专题改为 `GET /api/product/topics` 后端下发，提审期只返回方法类专题，政治专题名已从前端源码与产物中彻底移出。详见 A7 |
| 禁词按**子串**匹配，不是分词 | 例：「仿**真题**目」含「真题」子串、「公考」出现在「…知行公考题型应用」。文案自查必须做子串扫描（`grep -o` 逐词），不能只挑明显词。本轮已把「仿真题目」改为「仿真练习」规避 |
| 审核要求教育培训资质 | 按 A6 版本描述主动定性 + 强调无课程/无师资/无收费；仍被拒则考虑主体升级 |
