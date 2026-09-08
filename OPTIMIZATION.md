# 知行公考 · 待优化清单与后续路线

> 更新：2026-08-22（基于代码与本地命令实测，非仅凭文档）
> 用途：集中记录质量基线、待优化项与后续功能路线；每次修复 / 重构 / 新增功能后同步更新本文件。

## 1. 现状基线（2026-08-22 复核）

| 项 | 现状 |
|---|---|
| 后端测试 | `server/tests/` 现有 8 个测试文件；实测 **21 passed、37 warnings**。公开 / 管理 HTTP 路由分别为 107 / 109 个 |
| 前端 lint | `npm run lint` 实测 **0 errors、85 warnings**，门禁通过；warning 主要为 Vue 模板格式规则，应清理并防止继续增长 |
| 管理后台构建 | `vue-tsc -b && vite build` 通过；P2 已分包：主入口 59KB，vue / element / katex 独立 vendor chunk（element 1.07MB 仍偏大） |
| H5 构建 | 2026-08-22 本机触发 `system-configuration` Rust worker 的 macOS `NULL object` panic 后挂起并中止；需用 CI / 干净 Node 环境区分环境问题与项目问题 |
| 文件规模 | P2 已按域拆分：public/admin 路由各拆 11-13 个域文件；schemas 拆 16 个域模块；models 拆 12 个域模块；`src/api` 拆 9 个域模块 + `_shared`；`mock` 拆 8 个域模块 + `_core` |
| 行为事件埋点 | `activity_service.record_event()` 共 7 处调用（文章阅读、答题、套卷交卷、资料练习、申论开采、签到），仅写入、无统计页 |
| 文档漂移 | 品牌色默认值、管理端入口、`deploy-ali.md` 引用等 6+ 处与代码不一致（本文件生成时已同步修正） |

## 2. P0 质量基线（建议立即处理）

### 2.1 让 `npm run lint` 通过 ✅

已完成（2026-08-14）：`eslint --fix` + `prettier` 曾全量统一。2026-08-22 复核为 0 errors、85 warnings，说明后续提交重新引入了格式 warning；当前不阻断 lint，但“0 problems”基线已失效。

- `src/utils/bootstrap.ts:2` — `api` 导入未使用
- `src/utils/memoryCurve.ts:58` — `baseDate` 赋值未使用
- `src/utils/speechInput.ts:98` — `_hotwords` 赋值未使用
- 其余 3014 个 warning 主要是 vue 模板格式规则（`max-attributes-per-line`、`singleline-html-element-content-newline` 等），2743 个可自动修复；建议先 `eslint --fix` + `prettier` 统一格式，再评估是否放宽个别规则
- 处理中发现的坑：prettier 会把 `@tap="a = 1; load()"` 拆成无分号多行表达式，导致 Taro 模板编译失败——已把 4 处（exam/list、rmrb/drill、rmrb/terms）抽成方法，并写入 PROJECT_PROMPT §1 禁止此类写法
- 顺带修复：mock 服务中重复的 `getStudyRecords` 方法（同步版覆盖异步版，破坏 Mock 类型契约）
- 顺带修复：`article_to_out` 对 `mind_map="{}"` 无兜底，会导致管理端文章列表 500——已加归一化兜底

### 2.2 补后端核心闭环测试 ✅

已完成：新增 `server/tests/test_core_loops.py`，覆盖答题 → 错题 → SRS 复习推进 → 掌握移除、套卷开考/作答/交卷判分、签到积分、管理端 RBAC（只读角色写接口 403）、资料分析提交与统计；2026-08-22 实测 `pytest` 21 passed。

现有 15 个用例集中在 smoke / 导入 / 序列化，建议优先补：

- 答题 → 错题 → 复习 SRS 阶段推进闭环
- 套卷 start / submit / finish 交卷闭环
- 签到 + 积分流水
- 管理端 RBAC 权限矩阵
- 资料分析练习提交与统计

### 2.3 引入 CI ✅

已完成：`.github/workflows/ci.yml` 三条门禁（前端 lint / 后端 pytest / 管理后台 build）。

仓库无 CI。建议 GitHub Actions 三条门禁：前端 `lint`、后端 `pytest`、`admin-web build`（vue-tsc）。

## 3. P1 残留与死代码清理

| 项 | 位置 | 说明 | 状态 |
|---|---|---|---|
| 英语 / 读书 / 健康 / 音标 / 美剧口语空壳 | `models`、`api/public`、`api/admin`、`schemas`、`core/permissions.py`、`src/types/index.ts` | 裁剪时只删了功能，注释段与空壳 schema（`HealthFocusBody`）残留 | ✅ 已全部清除 |
| 理财域残留 | `schemas` 中的 `LEDGER_*` / `WEALTH_*` 常量 | 拆分 schemas 时发现，无任何引用 | ✅ 已删除 |
| 计划模板含英语 / 健身任务 | `services/plan_service.py`（7 天默认模板）、`admin-web/src/views/plan/Templates.vue`、`src/mock` 计划数据 | 公考版计划不应出现英语 / 健身 | ✅ 已替换为时政 / 申论 / 行测任务 |
| 爬虫代码 | `services/crawler.py`、`services/rss_crawler.py`、admin 爬虫注释、`CrawlLog` / `CrawlLogOut`、crawler 权限、`CRAWL_*` 配置 | 功能长期关闭，决定彻底删除 | ✅ 已删除（如需自动抓取需重建，见 §5） |
| Obsidian 本机路径 | `services/knowledge_service.py:42`（iCloud 目录硬编码） | 开发专用路径，生产无意义 | ✅ 已改为配置项 `KNOWLEDGE_KB_DIR` |
| 部署文档旧信息 | `DEPLOY.md` | 标题 / 仓库地址 / 端口 / 镜像名 | ✅ 已由「政考通」更新为「知行公考」 |

## 4. P2 结构性重构（规模变大后值得做）

全部已完成（2026-08-14）：

1. **路由拆分 ✅**：`api/public/` 与 `api/admin/` 均按域拆分并由 `routes.py` 聚合；前缀与路由顺序保持不变。2026-08-22 从 FastAPI 路由表实测为 public 107 个、admin 109 个 HTTP 路由。
2. **schema 拆分 ✅**：`schemas/` 按域拆 16 个模块，`__init__.py` 统一 re-export，`from app.schemas import X` 全部兼容。
3. **前端 API 层拆分 ✅**：`src/api/` 拆为 `_shared.ts`（request / isMock / 类型 / 上传）+ `domains/` 9 个域模块，`index.ts` 聚合导出 `api` 对象，调用方零改动。
4. **Mock 拆分 ✅**：`src/mock/` 拆为 `_core.ts`（状态 + 辅助函数 + 数据）+ 8 个域模块，`service.ts` 聚合导出 `mockService`；域内 `this` 调用全部在同域内，组合后运行时行为不变。
5. **管理后台分包 ✅**：`manualChunks` 拆 vue / element-plus / katex；主入口 1.24MB → 59KB。element 单独 chunk 1.07MB 仍偏大，后续可上按需引入（unplugin-vue-components）。
6. **数据库迁移 ✅**：`main.py` 中 12+ 个 `_ensure_*` 收拢到 `server/app/db_compat.py`，`run_compat_migrations()` 启动时幂等执行。
7. **模型收拢 ✅**：`models/` 拆为 base + 11 个域模块，`__init__.py` 统一 re-export，保持 `from app.models import X` 兼容。

> 遗留：`src/mock/shiwuwu-plan.ts` 与 mock 个别数据的类型报错为拆分前既有问题（`tsc --noEmit` 可复现），不影响构建；element-plus 大 chunk 属后续优化。

## 5. 后续需要优化的功能（功能补全）

| 优先级 | 功能 | 现状与目标 |
|---|---|---|
| 高 | 行为事件统计页 | `activity_events` 已埋 7 处；补齐 M4：上岸卡片 / 能力雷达 / 里程碑可视化 |
| 高 | 文档与质量基线回稳 | 清理 85 条 lint warning；修正 `server/app/main.py` 中“政考通”旧品牌及过时 API 描述；处理或约束 `python-jose` 弃用 warning |
| 高 | 主题切换小程序端一致性 | 原生 `tabBar` 的 `selectedColor` 硬编码 `#D0021B`，H5 自定义 TabBar 随主题、小程序不随；需同步 |
| 中 | 足迹 Admin 入口 | 目前仅有学员端 growth 数据，管理端无入口 |
| 中 | AI 出题 | `LLM_ENABLED` 默认关闭；管理端 AI 出题按需开启（DeepSeek 配置已在 env） |
| 中 | 语音输入云端识别 | `ASR_PROVIDER=none`，当前仅本地语音；可接云端 ASR |
| 低 | 支付 / 会员 | 无真实微信 / 支付宝对接（原充值页已移除）；如需课程 / 会员再接入 |
| 低 | 爬虫重建 | P1 已彻底删除爬虫代码；如需自动抓取时政文章，需按现状重建并加配置开关 |

## 6. 维护协议

- 每次修复 / 重构 / 新增功能后：更新本文件对应条目，并同步 FEATURES.md §8（已知缺口）。
- 新发现的问题先登记到 P0 / P1 / P2 对应小节，避免丢失。
