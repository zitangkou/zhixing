# 知行公考 · 项目进度

> 更新：2026-09-09
> 定位：纯公考备考应用矩阵（综合母应用 + 申论/政治理论垂直应用 + 内容运营 + 真题库），Taro 4 + Vue 3 + FastAPI + SQLite

## 1. 阶段进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 0 | 品牌改名（知行公考）+ 端口统一（10087 / 8001） | ✅ |
| Phase 1 | 后端裁剪（删非公考域 + 充值） | ✅ |
| Phase 2 | 前端裁剪 + 品牌换色 | ✅ |
| Phase 3 | 4-Tab 布局 + 今日驾驶舱 + 考试倒计时 | ✅ |
| Phase 4 | `activity_events` 埋点（7 处） | ✅ |
| Phase 5/6 | admin-web 裁剪重建 + 仓库清理 | ✅ |
| P0 | 质量基线：lint 0 errors、核心闭环测试 21 passed、CI 三条门禁 | ✅ |
| P1 | 残留清理：空壳注释 / 爬虫删除 / Obsidian 配置化 / 计划模板公考化 | ✅ |
| P2 | 按域拆分：路由 / schema / model / api / mock + 后台分包 + 迁移收拢 | ✅ |
| 部署 | 一键部署 `deploy.sh` + 宿主机 Nginx 网关 + 整包备份 | ✅ 2026-08-16 |
| 真题资产 | 2025 三卷 135/130/130 + 媒体（31 页/32 图）已入库；2024 三卷 135/**125**/**125**（差异槽位待精修，**media 为 0**，源 PDF 缺主卷 `20240124.pdf`）；2023/2022 仅初始化、2021/2020 未建目录但源 PDF 已备。**780 题答案与解析未入库**（v2 已预留字段，待解析册扫描接入）。2026-09-02 完成①文档治理（两份 WORKFLOW 合并、路径漂移与 2024 进度矛盾修正、新增跨年结构差异表）②**schema v2 数据格式统一**：首次沉淀 `scripts/xingce/{normalize_papers,validate_papers}.py`，`type` 归一 13 个中文枚举、`source_note`→结构化 `provenance`、媒体路径基准统一、材料引用改 `material_ids` 数组、新增 `modules[].number_range` 与 `flags`；迁移暴露 5 项此前未察觉的缺陷（判断推理各缺 5 题、执法卷内重复、材料 `m106_110` 漏提取、省级资料全借市地、2024 媒体引用悬空），校验 **0 错误 / 57 警告**。见 `xingce-structured-data/DATA_STATUS.md` | 🟡 2026-09-02 |
| 双产品 Sprint 0 | 申论/政治理论 PRD、共享底座设计、`product_key` 后端上下文、公开配置、前端请求/上传注入和产品 Store | 🟡 2026-08-23 第一批完成 |
| 双产品 Sprint 0 | 通用今日任务、五态学习状态机、服务端草稿与跨端断点恢复、产品隔离、前端任务 Store | ✅ 2026-08-23 第二批完成 |
| 申论 Sprint 1 | 垂直今日首页、审核文章自动编排、单主任务入口、阅读/三刀进度回写、Mock 演示数据 | ✅ 2026-08-23 第一批完成 |
| 申论 Sprint 1 | 小题短作答、三项规则自检、自动草稿、表达沉淀入规范词库、今日任务完成页 | ✅ 2026-08-23 第二批完成 |
| 政治理论 Sprint 1 | 垂直今日首页、3题/证据质量门、权威文章自动编排、独立蓝色主题与三产品动态导航 | ✅ 2026-08-23 第一批完成 |
| 政治理论 Sprint 1 | 无答案读前定向、原文精读门、证据题过滤、测验结果回写、逐题错因归类与完成页 | ✅ 2026-08-23 第二批完成 |
| 内容运营 Sprint 1 | 10个固定栏目模板、四渠道变体、母资产/深链/排期、教研与运营双审核状态机、Admin API | ✅ 2026-08-23 第一批完成 |
| 内容运营 Sprint 1 | 管理后台模板浏览、发布包新建/编辑、渠道文案维护、审核推进与驳回、审核中编辑锁定 | ✅ 2026-08-23 第二批完成 |
| 内容运营 Sprint 1 | 月历式内容排期、待发布素材包 JSON 导出、人工发布清单与导出状态门 | ✅ 2026-08-23 第三批完成 |
| 内容运营 Sprint 1 | 发布包结构化栏目槽位、模板字段校验、缺项阻断送审、旧库自动补列 | ✅ 2026-08-23 第四批完成 |
| 内容运营 Sprint 1 | 已发布文章一键生成结构化母稿与四平台草稿、渠道深链归因、缺项人工补齐与重复生成保护 | ✅ 2026-08-23 第五批完成 |
| 内容运营 Sprint 1 | 未来7天内容库存、双科配比、审核积压、待发布与未排期提醒，状态变更实时刷新 | ✅ 2026-08-23 第六批完成 |
| 垂类应用独立化 | 申论/政治理论拆为 `apps/` 独立 Taro 工程（端口 10088/10089），独立认证与账号、红色 Tab 导航、每日训练/学习闭环、反馈与训练历史 | ✅ 2026-08-23~24 |
| 部署升级 | 单 Docker 镜像编译三套 H5（综合 `/` + 申论 `/shenlun/` + 理论 `/theory/`），共用一个 FastAPI；compose 绑定可配（默认 127.0.0.1）+ healthcheck | ✅ 2026-08-24 |
| 内容运营·日常 | 每日多渠道运营启动（`content/daily/`）；发布包按 campaign 隔离去重修复 | ✅ 2026-08-24~25 |
| 原应用流程回填 | 定义迁移基线（`docs/architecture/original-app-feature-inventory.md`）；申论三刀法/资产复盘/文章采集、理论读前定向与复习/结构化精读/证据测验已回填；错题闭环回填中 | 🟡 2026-08-24~26 |
| 内容运营·双审核留痕 | `ContentReviewRecord` 审核留痕表 + 流转 checklist + review-config/reference-library API + 后台 UI | ✅ 2026-08-28（`04e6f46`） |
| 理论错题复习 | theory-app `StudyRecord`/`ReviewTask` 复习模型 + 新页 `question/review.vue` | ✅ 2026-08-28（`a1047d3`） |
| 小程序发布 | 双 AppID + 定稿名 + weapp 生产构建（产物含 `https://zhixinggk.ltd`）+ 印章头像产出 | 🟡 2026-08-30 阻断在 ICP 备案，详见 `docs/release/wechat-miniapp-launch-checklist.md` |
| 数据 schema v2 + 解析工作流治理 | 全库归一 schema v2（13 题型枚举 / 结构化 provenance / flags 门禁），校验 0 错误；两份 WORKFLOW 合一 | ✅ 2026-09-02 |
| 行测答案接入（D 线） | 2024 三卷 100%（385/385）、2023 三卷 95.2%（376/395，19 题锚点待复核）；2020-2022 共 650 题待解析册扫描接入 | ✅ 2026-09-03~04 |
| S1 真题规律报告 | 16 卷 2100 题三层统计 → `docs/research/xingce-patterns-2026.md`，作为出题引擎“5 维度真题一致性”校准基准 | ✅ 2026-09-03 |
| 出题引擎 Q2-Q6 | 言语 v2（40 题）/ 判断推理（35 题）/ 常识+政治理论 / 数量 / 资料分析引擎 + 真题一致性校准；137 题生成题入库（全部 pending_review） | ✅ 2026-09-03 |
| 题库持久化 P0-P2 | 导入对账、题目资产页+发布门禁、生成工作台+教研审核（approve→publish 门禁拦截 pending_review） | ✅ 2026-09-03 |
| 每日政治理论出题线 | cron 每日 06:30：人民日报头版→20 题→iCloud 云盘；自动产出公众号长图（含 4 张分段）+ 小红书 22 卡（双封面）+ 知乎 HTML；已产出 09-02/04/05 三天 | ✅ 2026-09-05 |
| 项目优化计划 + 文档治理 | 全仓扫描沉淀 `docs/plans/optimization-plan-2026-09.md`；CLAUDE.md 同步、战略文档历史标注、.bak 归档清理、导出重导 | ✅ 2026-09-05 |
| 时政/时评 HTML + 词表 inbox | 文章与时评原文 HTML 入库展示；后台菜单拆成时政考点 / 时评精拆；`vocab_inbox` 待收录后人工晋升词表 | ✅ 2026-09-09 |

## 2. 当前质量基线（2026-08-23 实测）

- 后端 `server/.venv/bin/python -m pytest -q`：**24 passed，70 warnings**（warning 来自 `python-jose` 使用即将弃用的 `datetime.utcnow()`）
- 前端 `npm run lint`：**0 errors，85 warnings**；门禁通过，但格式类 warning 已重新积累，不能再表述为“0 problems”
- 管理后台构建：2026-08-23 实测通过（主入口 59.57KB，Element Plus chunk 1.07MB）
- H5 构建：本机运行时卡在 `system-configuration` Rust worker 的 macOS `NULL object` panic，已中止；更像本机构建环境问题，但本次不能记为通过
- CI：GitHub Actions（lint + pytest + admin build）
- 类型检查：`src/api`、`src/mock` 拆分后新增代码零错误
- 规模快照：学员端 **60 个页面路由**（16 模块）、**20+ 共享组件**；FastAPI **107 个 `/api` 路由**、**109 个 `/admin` 路由**（08-22 实测；09 月新增题库/生成/审核域后待复核）

## 3. 已知遗留

| 项 | 说明 |
|---|---|
| `src/mock/shiwuwu-plan.ts` 类型报错 | 拆分前既有（`tsc --noEmit` 可复现），不影响构建 |
| 前端 lint warning | 当前 85 条，集中在 Vue 属性顺序、标签换行与缩进；无 error，但应避免继续增长 |
| FastAPI 元信息仍为旧品牌 | `server/app/main.py` 的 title/description 仍写“政考通 / 政治理论学习”，影响 `/docs` 展示 |
| 依赖弃用告警 | 后端测试产生 37 条 `python-jose` 的 `datetime.utcnow()` 弃用 warning |
| H5 本机构建异常 | `npm run build:h5` 触发 `system-configuration` Rust worker 的 macOS `NULL object` panic 后挂起；需在 CI 或干净 Node 环境复核 |
| element-plus chunk 1.07MB | 已拆独立 vendor；后续可按需引入（unplugin-vue-components） |
| 行为事件统计页 | `activity_events` 已埋点，无统计/可视化（M4：上岸卡片 / 能力雷达 / 里程碑） |
| 足迹 Admin 入口 | 仅学员端有 growth 数据 |
| LLM 出题 / 云端 ASR | `LLM_ENABLED=false`、`ASR_PROVIDER=none`，按需开启 |
| 支付 / 会员 | 无真实微信/支付宝对接（原充值页已移除） |

## 4. 后续路线（按优先级）

产品路线已调整为垂直题型矩阵：优先孵化申论，其次政治理论、资料分析、数量关系、言语理解、判断推理；详细需求与共享边界见 [`PRODUCT_SPLIT_PLAN.md`](./PRODUCT_SPLIT_PLAN.md)（历史战略文档）。现有综合应用继续作为能力母体和验证场，不立即复制成六套代码。

2026-08-23 首期范围进一步收敛：只实现**申论、政治理论**两个垂直产品，其余四科暂停独立产品开发。共同底座按题型插件设计，为资料、数量、言语、判断保留接入契约但不提前开发；账号运营从审核后的教学母资产派生内容，以首训完成和留存衡量转化。执行方案见 [`TWO_PRODUCT_MVP_PLAN.md`](./TWO_PRODUCT_MVP_PLAN.md)（Sprint 1 已于 08-23~24 执行完毕）。

| 优先级 | 事项 |
|---|---|
| 高 | **小程序发布**（知行策论/知行日知）：✅ 双 AppID 已填、产品名定稿、weapp 生产构建产物已确认含 `https://zhixinggk.ltd`、印章头像已产出、profile 死入口与「规划中」文案已清、隐私政策与用户协议原生页面已落地；**阻断**：ICP 备案未通过（域名与 `/api` 实测被阿里云 403 拦截）→ certbot 上 HTTPS → 微信后台 request 合法域名 + 用户隐私保护指引；**代码级待补**：生产 `.env` 密钥与 `ALLOW_REGISTER`。完整清单见 `docs/release/wechat-miniapp-launch-checklist.md` |
| 高 | 发布前代码级合规：✅ A2 profile 死入口与「规划中」文案、✅ A3 旧品牌昵称/API 元信息/token 键名、✅ A1 隐私政策与用户协议原生页面 + 登录注册勾选 + 我的页入口、✅ 应用内文案去禁词（真题化→仿真练习、去「公考」；禁词按**子串**匹配，「仿真题目」也含「真题」）、✅ A7 专题页政治内容改为后端下发（`GET /api/product/topics` + `system_settings` 不发版切换）、✅ A4 反馈链路修复（`FeedbackBody` 字段名不匹配致反馈从未提交成功、内容被丢弃、随机判采纳送分 → 新增 `Feedback` 表 + 管理端查看/处理接口 + 两 app 反馈页）、✅ A5 nginx 收口 `/docs` 与 `.env.example` 重写、✅ 管理员自助改密 `PUT /admin/auth/password`（强度校验 + 旧密码验证，补上「改 .env 对已部署环境无效」的缺口）（2026-08-30，后端 27 passed，两 app 已重建 weapp 产物）；**剩余**：`constants/legal.ts` 三处待填（署名/邮箱/生效日期）、服务器侧生产 `.env` 与管理员口令、体验账号与提审材料。排期见 `docs/release/wechat-miniapp-launch-plan.md` |
| 高 | 行为事件统计页（M4：上岸卡片 / 能力雷达 / 里程碑） |
| 中 | 清理/约束前端 lint warning（85 条）与后端 `python-jose` 的 `utcnow` 弃用告警；~~FastAPI `/docs` 旧品牌元信息~~ 已随 A3 修正 |
| 中 | 足迹 Admin 入口 |
| 中 | AI 出题、云端语音识别按需开启 |
| 中 | element-plus 按需引入 |
| 低 | 支付 / 会员、爬虫重建（如需自动抓取时政） |

## 5. 最近提交

```text
708b1eb docs: 沉淀政治理论每日出题+运营物料自动化会话内容
799ea24 feat(xingce): 公众号长图新增分段拆分（4张5题一组），同时保留超长图
5bc7dc9 refactor(xingce): 卡片/长图脚本参数化(--date/--title)，纳入每日定时任务
b7cf07e refine(xingce): 小红书上题解析扩展为正确项+双干扰项；长图/知乎答案滞后3题
4e25995 feat(xingce): 新增公众号长图+知乎HTML生成器
28a9b64 feat(xingce): 新增封面B分色对撞风格，每日自动生成双封面备选
9e7d8ef feat(xingce): 小红书/公众号文案合规优化：政治理论→时政考点
ad46da5 [xingce] 2024三卷答案+解析入库，覆盖率100%（385/385）
89497d2 [xingce] 2023 三卷答案+解析入库（覆盖率 95.2%）
9ee810a [xingce] 生成题入库脚本：137题幂等导入 + dry-run + 25项测试
35a5c81 [xingce] 生成工作台：注册5引擎 + 校验引擎感知
8ccb17a [xingce] 审核→发布闭环：approve→approved + publish门禁拦截pending_review
```

## 6. 相关文档

- 全量功能清单 → [`FEATURES.md`](./FEATURES.md)
- 架构与模块边界 → [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- 待优化清单 → [`OPTIMIZATION.md`](./OPTIMIZATION.md)
- 部署手册 → [`DEPLOY.md`](./DEPLOY.md)
- 模板化账号内容运营 → [`CONTENT_OPERATIONS_PLAN.md`](./CONTENT_OPERATIONS_PLAN.md)
- 行测数据与出题调度中枢 → [`docs/plans/xingce-data-roadmap-2026.md`](./docs/plans/xingce-data-roadmap-2026.md)
- 项目级优化总盘 → [`docs/plans/optimization-plan-2026-09.md`](./docs/plans/optimization-plan-2026-09.md)
