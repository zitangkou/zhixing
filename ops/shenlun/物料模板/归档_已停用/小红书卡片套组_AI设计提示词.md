---
type: content_operation_template
template_code: xhs_card_ai_prompt
channel: xiaohongshu
version: v1.2
review_status: draft
---

# 小红书卡片套组 · AI 设计提示词（v1.2 · 安全版）

> 用途：贴到 Canva「魔法设计 / Magic Design」生成 5 页套组。
> v1.2 起因：v1.1 细化版含「人民日报/申论/时评/考公」等词，被 Canva AI 审核拦截 → 全部改为中性占位词；文字框可编辑，生成后手动替换成真实内容。
> 配套《小红书卡片文字结构规范.md》《小红书卡片模板搭建规范.md》。

## 安全版中文提示词（推荐，直接复制）

```
请生成一套小红书图文笔记模板，共 5 页，竖版 3:4（1242×1660），多页套组，5 页风格统一。

整体风格：复古油墨报纸风——做旧泛黄纸底 #F5F0E6，主文字墨黑 #1A1A1A，点缀朱砂红 #C03028。标题用宋体，正文用思源黑体。每页四边留白，深字浅底，文字清晰，不要英文。所有文字用可编辑文本框，占位示例即可。

第1页 封面：顶部居中一行小字（朱砂红约40号）；中央大标题（墨黑约90号，占2行）；下方胶囊标签（红底白字约40号）；底部一行小字（深灰约32号）。

第2页 结构：顶部标题（朱砂红约56号）；一行出处小字（深灰约36号）；一句核心观点（墨黑约48号）；三个竖排圆角方框用箭头连接（墨黑约40号）；底部一句总结（深灰约36号）。

第3页 金句：上半区居中大字金句（墨黑约76号，占2行）；下方两行小字（深灰约32号）；一条朱砂红分隔线；下半区4-6个竖排浅色圆角色块（词墨黑加粗约42号+解释深灰约32号）。

第4页 方法：上半区红色小标签；论点（墨黑约44号）、论据（深灰约36号）、方法标签（朱砂红约32号）、模板（墨黑约36号）；一条朱砂红分隔线；下半区红色小标签；类型/原文/模板/仿写（约40号）。

第5页 总结：顶部标题（朱砂红约56号）；一句核心句（墨黑约44号）；三行要点（深灰约36号）；一行示例（墨黑约40号）；底部3-4个红色圆角色块（白字约36号）。

保持5页配色、字体完全一致，文字框可编辑。
```

## 英文版提示词（中文被拦时兜底）

```
Create a 5-page Xiaohongshu post template set, vertical 3:4 (1242×1660), unified vintage newspaper ink style: aged cream paper background #F5F0E6, ink black text #1A1A1A, vermilion red accent #C03028. Serif title, sans-serif body, generous margins, dark text on light background, all text as editable placeholder (no real content).

Page 1 Cover: small red label top-center; large black title center (2 lines); red pill badge; small gray line at bottom.
Page 2 Structure: red heading; a source line; one core statement; three rounded boxes linked by arrows; a summary line.
Page 3 Quote + Words: large quote upper-half; two small lines; red divider; 4-6 light rounded blocks lower-half.
Page 4 Method + Sentence: red label; statement; evidence; method tag; template; red divider; sentence type/original/template/example.
Page 5 Summary: red heading; one key sentence; three bullet lines; one example; 3-4 red blocks at bottom.

Keep all 5 pages consistent, editable text.
```

## 生成后：替换成真实内容（手动，10 秒）

| 占位 | 真实内容（模板字段） |
|------|---------------------|
| 封面中央大标题 | 《文章标题》（≤20 字） |
| 封面胶囊标签 | 适用申论 · XX主题 |
| 封面顶部小字 | 时评精拆 |
| 第2页出处行 | 人民日报 YYYY-MM-DD 第X版 |
| 第2页核心观点 | 总论点 |
| 第3页大字金句 | 原文金句 |
| 第4页各段 | 论证四段 + 万能句式 |
| 第5页要点/清单 | 案例速记 + 行动清单 |

## 使用入口

Canva 网页版 → 首页左侧「Magic Studio / 魔法设计」→ 粘贴 → 生成。

## 生成后自检（发我链接前）

- [ ] 5 页套组、尺寸 1242×1660
- [ ] 每页文字可双击编辑（可编辑文本框）
- [ ] 风格统一、深字浅底、无英文装饰
