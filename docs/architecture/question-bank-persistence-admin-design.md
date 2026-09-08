# 统一题库持久化与管理后台设计方案

> 版本：1.0  
> 日期：2026-09-02  
> 状态：P0–P2 已于 2026-09-03 落地（导入对账 / 题目资产页+发布门禁 / 生成工作台+教研审核，见 §13/§14 执行日志）；P3/P4 待实施  
> 适用范围：国考真题、题型专项题、文章生成题、人工模拟题及后续各垂直应用  
> 关联文档：[真题 schema v2](../../xingce-structured-data/_schema/conventions.md)、[各题型模拟题设计参考](../products/question-type-simulation-design-reference.md)、[政治理论模拟题方案](../products/theory-question-generation-plan.md)

## 0. 结论

项目应采用三层持久化结构：

```text
结构化 JSON / 原始媒体
  = 可追溯、可重建的数据归档层

统一关系数据库
  = 管理、审核、发布和应用查询的业务真值层

对象存储 / 文件存储
  = PDF、题图、图表、文章快照等媒体层
```

核心改造是把“题目本身”和“题目在某份试卷里的位置”分开。一道三卷共享真题只保存一个题目实体，再通过三个题位分别关联到三份试卷；生成题也进入同一题目资产库，但通过来源类型、生成批次和审核状态与真题严格区分。

不建议继续扩展当前彼此独立的 `questions` 和 `exam_questions` 两套模型。它们可以在迁移期保留兼容，最终应统一到中心题库。

---

## 1. 当前数据是如何保存的

### 1.1 真题归档层

当前解析出的行测真题保存在：

```text
xingce-structured-data/
├── catalog.json
├── _schema/
│   ├── conventions.md
│   └── topic-vocabulary.json
└── {year}/xingce/
    ├── meta.json
    ├── _extract/                  # 分模块提取和答案映射中间结果
    ├── papers/
    │   ├── shengji.json           # 省级完整卷
    │   ├── shidi.json             # 市地级完整卷
    │   ├── xingzhengzhifa.json    # 行政执法类完整卷
    │   └── all_merged.json        # 跨卷去重分析池
    ├── media/
    │   ├── pages/
    │   ├── figures/
    │   └── media_index.json
    └── source/EXTRACT_STATUS.json
```

每份试卷 JSON 的结构是：

```text
试卷元信息
  → modules 题号范围
  → sections 模块
      → materials 共享材料
      → questions 题目
```

题目包含题号、模块、题干、组合条目、选项、题型、考点、答案、解析、媒体、材料引用、来源和质量标记。

该层的价值：

- 可在没有数据库时独立校验和重建；
- 保留解析来源和历史加工过程；
- 适合 Git 审查、数据分析和跨年比较；
- 不受应用数据库迁移影响。

它不适合作为 H5 或小程序运行时直接数据源，因为缺少高效筛选、权限、审核、版本、发布和用户行为关联。

### 1.2 当前数据库

开发环境默认使用：

```text
server/data/zhixing.db
```

技术是 SQLite + SQLAlchemy。当前存在两套题目模型。

#### 文章题 `questions`

主要字段：

- `article_id`
- `type`
- `stem`
- `options`（JSON 字符串）
- `correct_answer`
- `analysis`
- `source_sentence`
- `status`
- `origin`
- `is_active`

它主要服务文章自动出题、政治理论练习和文章管理页面。

#### 试卷题 `exam_questions`

主要字段：

- `paper_id`
- `section`
- `section_index`
- `sort_order`
- `type`
- `material`
- `stem`
- `options`（JSON 字符串）
- `correct_answer`
- `analysis`
- `difficulty`
- `knowledge_tags`
- 知识树引用

它依附于 `exam_papers`，主要服务整卷作答和资料分析专项练习。

当前开发库实测只有：

- 1 份资料分析系统样例卷；
- 3 道 `exam_questions` 样例题；
- 1 篇文章；
- 10 道文章 `questions`。

也就是说，`xingce-structured-data` 中的正式国考真题尚未整体持久化到业务数据库。

### 1.3 当前管理后台

已有两个局部入口：

- “试卷题库”：能新建试卷、设置真题/自定义/模拟类型，并从 Markdown、JSON、CSV 导入。
- “文章管理 → 题目管理”：能新增、编辑、删除和审核文章关联题。

当前“试卷题库”页面只展示试卷列表和导入预览，没有统一题目列表、题目详情、题源追溯、版本、媒体、质量标记和生成审核工作台。

---

## 2. 当前结构的主要问题

### 2.1 同一种资产被拆成两套模型

真题存在 `exam_questions`，文章生成题存在 `questions`。两套表字段、接口、审核方式和用户作答关系不同，后续会导致：

- 错题本需要判断题目来自哪张表；
- 知识点统计需要合并两套查询；
- 同一道题无法同时用于文章练习、专题练习和阶段检测；
- 审核、版本、证据和质量指标重复建设；
- 新题型接入时继续增加第三、第四套题目表。

### 2.2 题目和试卷题位绑定过紧

`ExamQuestion.paper_id` 规定一道题只能属于一份试卷。国考三卷共享题因此必须复制三份，修改解析时也要同步三次。

正确关系应是：

```text
一个题目实体
  ← 多个试卷题位引用
```

题号、卷种、模块内序号和共享关系属于“题位”，不属于题目正文。

### 2.3 材料被重复保存在题目中

当前 `ExamQuestion.material` 是一段文本。同一篇资料分析材料对应 5 道题时，会重复保存 5 份，无法独立编辑、绑定图表或检查材料完整性。

材料应成为独立实体，题目通过关联表引用。

### 2.4 JSON 字符串字段缺少约束

选项、标签等以 Text 形式存 JSON 字符串，数据库无法有效检查结构，也不利于按干扰项类型、知识标签和答案位置筛选。

开发期 SQLite 可以继续存 JSON 文本，但应用层必须使用固定 schema；生产 PostgreSQL 应使用 JSONB 或规范化子表。

### 2.5 缺少来源、版本和审核谱系

现有模型不能完整表达：

- 真题来自哪份原始 PDF、哪一页；
- 当前题面是第几个修订版本；
- 哪次导入创建或更新了题目；
- AI 使用哪个模型、模板和提示词生成；
- 每个错误选项为何错误；
- 谁审核了什么字段；
- 来源更新后哪些题需要复核。

### 2.6 当前文章出题模型过于简单

现有规则生成主要采用关键词挖空和“根本/基本、核心/关键”替换，只适合演示，不能作为正式政治理论题生产能力。新的生成题需要原子事实、证据区间、干扰项策略、质量检查和人工审核记录。

---

## 3. 目标架构

### 3.1 三层真值定义

#### 归档真值

结构化 JSON 保存“当时从原始资料解析出了什么”。原则上不由管理后台直接反向覆盖。

#### 编辑真值

数据库保存“当前审核、发布和应用使用的版本”。管理员的修订以新版本形式保存在数据库。

#### 原始证据

PDF、图片、网页快照和文章原文保存为不可变来源资产，用于追溯。

不能让 JSON 和数据库双向自动覆盖。推荐单向流程：

```text
JSON 导入包
  → 暂存与校验
  → 数据库创建或更新版本
  → 管理审核与发布
  → 必要时导出数据库快照
```

### 3.2 存储技术

#### 开发环境

- SQLite 保持轻量启动。
- 题图继续存本地文件。
- 使用统一 repository/service 接口，避免业务层依赖 SQLite 特性。

#### 生产环境

- PostgreSQL：题库、审核、用户作答和统计。
- S3、Cloudflare R2 或兼容对象存储：PDF、图片、图表、文章快照。
- CDN：面向 H5 和小程序分发题图。
- 数据库只保存对象键、哈希、尺寸、类型和访问策略，不保存大文件二进制。

正式上线并开始多人管理、AI 生成和定时发布前，建议从 SQLite 切换到 PostgreSQL。

---

## 4. 核心领域模型

### 4.1 `question_items`：逻辑题目实体

表示“一道独立题目”，不包含某份试卷中的题号。

建议字段：

| 字段 | 说明 |
|---|---|
| `id` | 稳定题目 ID |
| `origin_type` | `real` / `generated` / `manual` |
| `subject` | 行测 / 申论 / 公基 |
| `module` | 政治理论、言语、数量、判断、资料等 |
| `subtype` | 选词填空、定义判断、增长率等 |
| `response_type` | single / multiple / judge / subjective |
| `current_version_id` | 当前编辑版本 |
| `canonical_hash` | 去重哈希 |
| `difficulty` | 1～5，后续可扩展能力参数 |
| `lifecycle_status` | active / retired / disputed |
| `created_at/updated_at` | 时间 |

`origin_type=real` 代表官方真题；`generated` 代表 AI 或程序生成；`manual` 代表教研原创。来源类型不可因编入模拟练习包而改变。

### 4.2 `question_versions`：题目内容版本

题干和答案的修改必须创建版本，不直接覆盖历史。

建议字段：

- `question_id`
- `version_no`
- `stem`
- `items_json`
- `options_json`
- `correct_answer_json`
- `explanation`
- `analysis_payload_json`
- `language`
- `content_hash`
- `change_summary`
- `created_by`
- `created_at`

`analysis_payload_json` 保存题型专属结构：数学计算树、逻辑表达式、选项错因、申论采分点等，并通过 `payload_schema_version` 管理格式版本。

### 4.3 `question_options`：可选的规范化选项表

若后续要按干扰项分析用户行为，建议将选项从 JSON 拆出：

- `question_version_id`
- `label`
- `content`
- `asset_id`
- `is_correct`
- `distractor_type`
- `distractor_rationale`
- `sort_order`

首期可以继续在版本表使用 JSON，等正式建设干扰项统计时迁移到子表。不要同时长期维护两份可编辑选项数据。

### 4.4 `exam_papers`：试卷

保留试卷元信息，但扩展：

- `exam_kind`：国考、省考、事业单位等；
- `paper_type`：省级、市地级、行政执法类；
- `source_document_id`；
- `schema_version`；
- `import_batch_id`；
- `review_status`；
- `publish_status`。

### 4.5 `paper_sections`：试卷模块

- `paper_id`
- `name`
- `sort_order`
- `number_start/number_end`
- `question_count`
- `instructions`

### 4.6 `paper_question_positions`：试卷题位

解决题目复用和题号问题：

| 字段 | 说明 |
|---|---|
| `paper_id` | 所属试卷 |
| `section_id` | 所属模块 |
| `question_id` | 逻辑题目 |
| `number` | 整卷题号 |
| `section_index` | 模块内序号 |
| `sort_order` | 展示顺序 |
| `provenance_json` | shared、差异卷映射等 |
| `quality_flags_json` | 数据质量标记 |

唯一约束建议：

- `(paper_id, number)` 唯一；
- `(paper_id, section_id, section_index)` 唯一。

### 4.7 `materials` 与 `question_material_links`

材料独立保存：

- `materials`：标题、正文、结构化数据、材料类型和版本；
- `question_material_links`：题目、材料、引用角色和顺序；
- `material_assets`：表格、图表和整页图片。

一篇资料分析材料关联 5 道题，只存一份正文和图表。

### 4.8 `content_sources` 与 `source_documents`

`content_sources` 表示逻辑来源，例如人民日报、二十届三中全会决定、2025 国考解析册。

`source_documents` 表示不可变版本：

- 来源类型；
- 标题、URL、发布日期和抓取日期；
- 本地或对象存储键；
- SHA-256；
- 文档版本；
- 版权与可用范围；
- 是否有效。

### 4.9 `evidence_spans` 与 `question_evidence`

保存题目答案依据：

- 文档 ID；
- 页码、段落、句子或字符区间；
- 证据原文；
- 证据角色：正确项、错误项反证、解析补充；
- 关联题目版本和选项；
- 置信度和审核状态。

政治理论发布题要求证据覆盖率 100%。

### 4.10 知识体系关联

使用多对多表 `question_knowledge_links`：

- `question_id`
- `knowledge_node_id`
- `role`：primary / secondary / prerequisite
- `weight`

不再只依赖一个 `knowledge_node_id` 或无法约束的标签字符串。

### 4.11 生成与审核

#### `generation_batches`

- 输入来源和文章；
- 目标题型与数量；
- 模型、提示词、模板和求解器版本；
- 原始输出；
- 校验摘要；
- 批次状态。

#### `question_generation_records`

- 生成批次；
- 题目 ID；
- 使用的事实、数据集或模型；
- 干扰项策略；
- 自动评分；
- 失败和重试记录。

#### `review_tasks` / `review_records`

- 审核对象及版本；
- 审核类型：数据、答案、教研、运营；
- 审核人；
- 结论和意见；
- 字段级修改；
- 时间。

### 4.12 练习编排

生成题不必先放进“模拟卷”。统一使用：

- `collections`：专题练习、每日包、阶段检测、真题卷等集合；
- `collection_items`：集合内题目和顺序；
- `collection_type`：daily / topic / stage / paper / review。

政治理论每日 8 题、资料分析一组 5 题和完整真题卷都可以用相同集合框架，但展示方式由类型决定。

---

## 5. 去重与稳定标识

### 5.1 为什么不能只用题干去重

同一道题可能存在：

- 标点和空格差异；
- 简繁体或 OCR 差异；
- 题号不同；
- 选项顺序不同；
- 题干引用同一材料但文本省略。

### 5.2 推荐标识

- `source_key`：如 `guokao:2025:shengji:1`，标识某卷题位。
- `canonical_hash`：标准化题干、条目、选项和材料引用后的哈希，辅助发现逻辑重复题。
- `question_id`：数据库稳定主键，人工确认合并后不变。
- `version_id`：某次题面内容修订。

导入时先按 `source_key` 幂等更新题位，再用哈希给出“疑似共享题”建议。哈希不能自动合并所有题，最终应由规则或人工确认。

---

## 6. JSON 到数据库的导入流程

### 6.1 不直接写正式表

```text
选择年度和卷文件
  → 创建 import_batch
  → schema 校验
  → 写入暂存区
  → 解析试卷、模块、材料、题目、媒体和来源
  → 去重匹配
  → 展示差异预览
  → 人工确认
  → 单事务写入正式表
  → 回读并与源 JSON 对账
```

### 6.2 导入批次必须保存

- 文件路径和哈希；
- schema 版本；
- 解析时间和程序版本；
- 新增、更新、复用、跳过和冲突数量；
- 全部错误与警告；
- 操作人；
- 是否已回滚。

### 6.3 对账指标

以 2025 三卷为首批导入时至少核对：

- 省级 135 个题位；
- 市地级 130 个题位；
- 行政执法类 130 个题位；
- 合计 395 个题位；
- 政治理论三卷共用 20 个逻辑题实体；
- 每个题位题号连续；
- 答案与解析覆盖率和源 JSON 一致；
- `flags`、材料和媒体引用无丢失；
- 导入两次不会重复新增数据。

### 6.4 修改策略

- 原始导入错误：创建新题目版本并记录修订原因。
- 卷中映射错误：修正题位，不复制或删除题目正文。
- 多题被错误合并：拆分逻辑题实体并迁移题位。
- 同题重复：合并逻辑题实体，保留所有来源题位。
- 不直接回写 `_extract` 中间文件。

---

## 7. 管理后台信息架构

### 7.1 一级菜单建议

将当前“试卷题库”升级为“题库中心”，包含：

```text
题库中心
├── 题目资产
├── 真题试卷
├── 练习集合
├── 材料与媒体
├── 生成工作台
├── 审核中心
├── 模板与规则
├── 导入批次
└── 质量看板
```

首期不用一次上线全部页面，但数据模型要允许逐步增加。

### 7.2 题目资产列表

筛选条件：

- 真题 / AI 生成 / 教研原创；
- 科目、模块、子题型；
- 年份、地区和卷种；
- 单选、多选、判断、主观；
- 草稿、待审核、已通过、已发布、已下线、有争议；
- 知识点和难度；
- 是否有答案、解析、材料、媒体和证据；
- 质量 flag；
- 生成批次和模板版本；
- 正确率、区分度和争议反馈。

列表主要列：来源标识、题干摘要、题型、来源类型、知识点、审核状态、发布状态、质量问题和更新时间。

### 7.3 题目详情

建议使用分页签：

#### 题面

题干、条目、选项、答案、解析、难度和题型专属结构。

#### 出处

原始文档、卷种、题号、页码、共享题位和媒体。

#### 证据与知识点

证据原文高亮、专题树、主次知识点和前置知识。

#### 生成信息

仅生成题展示模型、提示词、模板、原子事实、错误路径和自动校验。

#### 审核与版本

版本对比、审核意见、修改人、发布时间和下线原因。

#### 学习数据

作答量、正确率、平均用时、选项分布、区分度和用户反馈。

### 7.4 真题试卷页面

应补充：

- 试卷详情路由；
- 按模块显示题位；
- 题号拖动和批量调整；
- 缺题、重复、断号和答案缺失检查；
- 题目复用提示；
- 原始 JSON 与数据库对账；
- 整卷预览；
- 发布前完整性门禁。

### 7.5 生成工作台

政治理论示例流程：

```text
选择人民日报文章
  → 查看原子事实
  → 选择练习目标和题型结构
  → 生成候选题
  → 查看每个选项的证据和变换策略
  → 自动校验
  → 批量送审
```

数量、资料和逻辑题则展示参数、求解过程和双重验算结果。

### 7.6 审核中心

支持：

- 按题型和风险分配任务；
- 原文/题目并排审核；
- 逐选项审核；
- 批准、退回、驳回和标记争议；
- 批量处理低风险项；
- 记录字段级修改；
- 未通过硬门禁时禁止批准。

### 7.7 导入批次页面

展示：

- 导入文件和哈希；
- 解析、复用、冲突和失败数量；
- schema 错误；
- 去重建议；
- 源数据与正式数据差异；
- 确认导入和安全回滚。

### 7.8 质量看板

至少包含：

- 各模块题量与覆盖率；
- 答案、解析、证据、媒体覆盖率；
- 待审核和高风险题；
- 生成题一次通过率；
- 模板争议率；
- 选项无人选择率；
- 双答案反馈；
- 来源失效影响范围。

---

## 8. API 设计建议

### 8.1 管理端

建议按领域拆分：

```text
/admin/question-bank/questions
/admin/question-bank/questions/{id}
/admin/question-bank/questions/{id}/versions
/admin/question-bank/papers
/admin/question-bank/papers/{id}/positions
/admin/question-bank/materials
/admin/question-bank/import-batches
/admin/question-bank/generation-batches
/admin/question-bank/reviews
/admin/question-bank/collections
/admin/question-bank/quality
```

### 8.2 学员端

学员端不直接读取管理模型，只读取已发布投影：

```text
/api/practice/daily
/api/practice/topics/{id}
/api/practice/collections/{id}
/api/questions/{id}
/api/questions/{id}/submit
/api/reviews/due
```

答案和完整解析不应在未提交前随题面一起下发，避免前端包或网络请求直接暴露答案。

### 8.3 产品隔离

题目资产可以共享，但发布关系按产品隔离：

- `general`
- `theory`
- `shenlun`
- 后续 `data_analysis`、`quantity`、`verbal`、`reasoning`

不要在题目本身只保存一个 `product_key`。一题可能同时用于综合版和某个垂直应用，应使用 `question_product_links` 或集合发布关系。

---

## 9. 与现有数据的兼容迁移

### 9.1 迁移原则

- 新表并行建立，不直接删除旧表。
- 先迁正式真题，再迁文章生成题和样例题。
- 旧 API 暂时通过适配器读取新题库。
- 作答、错题和学习记录完成外键迁移后再停用旧表。
- 全部迁移必须可重复执行并有对账报告。

### 9.2 旧 `exam_questions`

迁移为：

- `question_items`
- `question_versions`
- `paper_question_positions`
- `materials`
- `question_knowledge_links`

### 9.3 旧 `questions`

迁移为：

- `origin_type=generated/manual`
- 原 `article_id` 转成 `question_evidence` 或来源关联；
- `source_sentence` 转成文章证据区间；
- `origin=ai` 转成生成记录；
- `status` 转成统一审核状态。

现有 10 道演示文章题应标为样例或低质量草稿，不能默认成为正式发布题。

### 9.4 作答数据

不建议继续让作答表分别外键到不同题目表。统一使用 `question_id + question_version_id`，保证用户作答时看到的题目版本可以永久还原。

---

## 10. 分阶段实施

### P0：统一 schema 与导入链路

任务：

1. 确定统一题目、版本、试卷题位、材料、来源和媒体模型。
2. 定义数据库约束和题型专属 payload schema。
3. 建立 import batch 和暂存校验。
4. 编写 `xingce-structured-data` 原生导入适配器。
5. 导入 2025 三卷并完成 395 题位对账。

验收：

- 重复执行导入不产生重复数据；
- 政治理论三卷共享 20 个逻辑题；
- JSON 字段无丢失；
- flags、材料、媒体和答案解析完整保留；
- 可从数据库重建等价的试卷结构。

### P1：题目资产与真题试卷管理

任务：

1. 统一题目列表和详情页。
2. 真题试卷详情和模块题位管理。
3. 来源、证据、媒体、知识点和版本展示。
4. 导入预览、冲突处理和对账页面。
5. 发布完整性门禁。

验收：

- 管理员可以按年份、模块、题型和来源检索；
- 一处修改新版本后，所有引用题位读取同一结果；
- 能查看真题原始出处和质量 flag；
- 无法发布缺答案、缺材料或高风险未审核题。

### P2：生成题与审核工作台

任务：

1. 生成批次和模板版本。
2. 文章事实、题目证据和干扰项记录。
3. 自动校验结果展示。
4. 教研审核和版本对比。
5. 真题/生成题/原创题明确标识。

验收：

- AI 不能直接发布；
- 每道政治理论生成题证据覆盖率 100%；
- 可以追溯到生成输入、模型和模板；
- 审核修改不丢失原始生成版本。

### P3：练习集合与学习反馈

任务：

1. 每日包、专题练习和阶段检测编排。
2. 跨产品发布关系。
3. 统一作答、错题和复习引用。
4. 题目正确率、选项分布和争议反馈。
5. 低质量模板自动预警。

### P4：迁移完成与生产数据库切换

任务：

- 迁移旧题目和作答外键；
- 旧接口改为新服务适配；
- PostgreSQL 和对象存储上线；
- 完成备份、恢复和审计演练；
- 停止写入旧表，观察稳定后再决定是否移除。

---

## 11. 备份与安全

### 11.1 备份

- PostgreSQL 每日自动备份，保留多个时间点。
- 对象存储开启版本和生命周期策略。
- 每次大批量导入前创建数据库快照。
- JSON 归档层继续保留 Git 版本。
- 定期执行恢复演练，不能只确认“备份任务成功”。

### 11.2 权限

权限至少拆分：

- 题目读取；
- 真题导入；
- 题目编辑；
- 答案和解析审核；
- 生成任务；
- 发布与下线；
- 删除和回滚；
- 用户作答统计。

删除真题和已有作答的题目属于高风险操作。默认采用下线或归档，不做物理删除。

### 11.3 审计

记录：操作人、时间、对象、旧值、新值、来源 IP 或会话、批次和原因。尤其要审计答案、解析、发布状态和来源证据的修改。

---

## 12. 最终推荐

近期最合理的落地顺序是：

1. 保留当前 JSON 数据，不把它当运行时接口。
2. 新建统一题库模型，不继续扩展两套旧题目表。
3. 先打通 2025 三卷的幂等导入和对账。
4. 再做“题目资产＋真题试卷详情”管理页面。
5. 政治理论文章生成题接入统一题库和审核工作台。
6. 最后统一作答、错题、复习和多产品发布。

这样既保留了真题数据的可追溯性，也能让真题、模拟生成题和人工原创题在一个管理系统中统一检索、审核、发布和统计，同时不会把“题目”和“试卷”重新绑死。

---

## 13. P1 执行日志

### 13.1 实施范围

- 后端：新增 `/admin/question-bank/` 域路由（`server/app/api/admin/question_bank.py`），在 `routes.py` 聚合
- 前端：新增 API 层（`src/api/questionBank.ts`）和 4 个页面（题目列表/题目详情/试卷列表/试卷详情）
- 发布门禁：缺答案/高风险 flag/争议状态 → 400 拒绝；缺解析 → 警告但可发布

### 13.2 新增 API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/question-bank/questions` | 题目分页列表（支持 origin_type/module/subtype/exam_year/paper_type/has_answer/review_status/quality_flag 筛选） |
| GET | `/admin/question-bank/questions/{id}` | 题目详情（当前版本完整内容+版本列表+关联题位+材料+quality flags+provenance） |
| GET | `/admin/question-bank/papers` | 试卷列表（年份/卷种/题量/答案覆盖率/导入状态） |
| GET | `/admin/question-bank/papers/{id}` | 试卷详情（元信息+模块列表） |
| GET | `/admin/question-bank/papers/{id}/positions` | 题位列表（按模块分组） |
| GET | `/admin/question-bank/papers/{id}/reconcile` | 对账报告（题位数/答案覆盖率/断号/共享题数/flags统计） |
| POST | `/admin/question-bank/questions/{id}/publish` | 发布题目（带门禁检查） |
| POST | `/admin/question-bank/questions/{id}/unpublish` | 下线题目 |

### 13.3 新增前端页面

| 路由 | 页面 | 说明 |
|---|---|---|
| `/manage/question-bank/questions` | 题目资产列表 | 多维度筛选+表格+分页+发布/下线操作 |
| `/manage/question-bank/questions/:id` | 题目详情 | Tab：题面/出处/版本/质量 + 发布/下线按钮 |
| `/manage/question-bank/papers` | 真题试卷列表 | 年份/卷种筛选+答案覆盖率进度条+对账入口 |
| `/manage/question-bank/papers/:id` | 试卷详情 | 元信息+对账摘要卡片+按模块折叠题位+对账报告 Tab |

### 13.4 发布门禁规则

1. **缺答案** → 400 拒绝（`correct_answer_json` 为空）
2. **高风险 flag** → 400 拒绝（关联题位的 `quality_flags_json` 含 content_mismatch/answer_conflict/missing_answer 等 8 种高风险标记）
3. **未审核/争议** → 400 拒绝（`lifecycle_status=disputed`）
4. **缺解析** → 警告但可发布（`explanation` 为空时返回 warnings）
5. 通过后 `lifecycle_status → active`；下线 → `retired`

### 13.5 验证结果

- 前端 build：通过（vue-tsc 类型检查 + vite build，2.52s）
- 后端测试：68 passed（含 P0 导入测试，未修改模型结构）
- 发布门禁单元验证：5/5 通过（缺答案拒绝、争议拒绝、有效通过、发布状态变更、下线状态变更）
- API 路由注册：8/8 端点正确挂载到 `/admin/question-bank/`

### 13.6 约束遵守

- 未修改 P0 模型结构（`question_bank.py` 表定义无变更）
- 未修改已有题目数据（仅读取，发布/下线只改 `lifecycle_status`）
- 前端使用 CSS 变量（`--admin-*`），无硬编码颜色
- 后端按域拆分路由文件，在 `routes.py` 聚合
- 所有 API 复用现有 `require_permission("exam:read"/"exam:write")` JWT 认证机制

---

## 14. P2 执行日志（生成工作台）

### 14.1 实施范围

- 后端：新增 `generation` 域模型（`server/app/models/generation.py`：`GenerationBatch`、`ReviewRecord`），新增 `/admin/generation/` 域路由（`server/app/api/admin/generation.py`），新增生成题数据读取服务（`server/app/services/generation_service.py`）
- 前端：新增 API 层（`src/api/generation.ts`）和 3 个页面（生成工作台首页/批次详情/教研审核）+ 1 个题目详情展开面板组件
- 生成题源数据为只读 JSON（`xingce-structured-data/generated/`），不修改 Q2/Q4 引擎和产出文件
- 审核结论持久化到 `review_records` 表，若题已导入 `question_items` 则同步更新 `lifecycle_status`

### 14.2 新增 API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/generation/stats` | 工作台统计（总题数/通过率/待审核/已通过/已驳回/已发布/按引擎分组） |
| GET | `/admin/generation/batches` | 生成批次列表（分页，支持 engine_type 筛选） |
| GET | `/admin/generation/batches/{batch_id}` | 批次详情（元信息+题目列表+每题审核状态） |
| POST | `/admin/generation/batches/run` | 触发生成（创建 pending 批次记录，参数 engine_type/skill/count/seed） |
| GET | `/admin/generation/templates` | 模板列表（template_id/engine_type/version/param_schema） |
| GET | `/admin/generation/templates/{id}/history` | 模板版本历史 |
| GET | `/admin/generation/batches/{batch_id}/validation` | 自动校验报告（每题 5 项校验+通过率+失败原因分布） |
| GET | `/admin/generation/review-tasks` | 审核任务列表（支持 status/engine_type/module/subtype/difficulty 筛选+统计） |
| GET | `/admin/generation/questions/{id}` | 生成题详情（题干/选项/计算树/干扰项错误路径/双求解结果/生成元信息/校验/审核记录） |
| POST | `/admin/generation/questions/{id}/review` | 提交审核结果（approve/reject + comment + reviewer） |
| POST | `/admin/generation/questions/batch-review` | 批量审核（多选题目批量通过/驳回） |

### 14.3 自动校验规则（5 项）

1. **dual_solve_match**：双求解器结果一致（`dual_solve.match == true`）
2. **options_distinct**：选项文本互不相同且 ≥2 个
3. **answer_unique**：答案唯一且在选项键中
4. **data_consistent**：答案与计算树/双求解结果一致（宽松校验）
5. **distractors_traced**：每个非正确选项都有 `distractors` 记录（错误类型+错误公式+计算值）

### 14.4 新增前端页面

| 路由 | 页面 | 说明 |
|---|---|---|
| `/manage/generation` | 生成工作台首页 | 4 统计卡片+批次列表表格+触发生成弹窗+审核入口 |
| `/manage/generation/batches/:id` | 批次详情 | 元信息卡片+校验汇总+校验报告折叠+题目列表（展开查看计算树/干扰项/双求解） |
| `/manage/generation/review` | 教研审核 | 审核统计+多维度筛选+题目列表（多选）+逐题审核弹窗（题面+生成元信息+通过/驳回+评论）+批量审核 |

### 14.5 审核流程状态机

```
pending（待审核）
  ├─ approve → review_records.action=approve
  │            └─ 若题已导入 question_items → lifecycle_status=active
  └─ reject  → review_records.action=reject
               └─ 若题已导入 question_items → lifecycle_status=disputed
```

- 审核通过的题才能进入 P1 发布流程（与发布门禁衔接：`lifecycle_status=disputed` 禁止发布）
- 生成题 `origin_type=generated`，与真题 `origin_type=real` 明确区分

### 14.6 验证结果

- 前端 build：通过（vue-tsc 类型检查 + vite build，2.66s）
- 后端测试：108 passed（含新增 25 个 generation API 测试，未破坏已有 83 个测试）
- 批次展示验证：Q2 资料分析 32 题 + Q4 数量关系 10 题，批次元信息/校验/题目列表正确返回
- 审核流程验证：通过/驳回正确写入 `review_records`，审核状态在列表/详情中正确回显
- API 路由注册：11/11 端点正确挂载到 `/admin/generation/`

### 14.7 约束遵守

- 未修改 Q2/Q4 生成引擎（`scripts/xingce/gen_*.py`）和题目产出文件（只读 JSON）
- 未修改 P0/P1 已有模型结构（`question_bank.py` 无变更），仅新增 `generation.py`
- 前端使用 CSS 变量（`--admin-*` / `--el-color-*`），无硬编码颜色
- 生成题 `origin_type=generated`，与真题明确区分
- 审核通过的题才能进入发布流程（与 P1 发布门禁衔接）
- 后端按域拆分路由文件，在 `routes.py` 聚合
- 所有 API 复用现有 `require_permission("exam:read")` JWT 认证机制
