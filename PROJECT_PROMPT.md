# 知行公考（zhixing-gongkao）项目开发规范 Prompt

> 新增任何功能 / 页面 / 组件时，将本文件作为系统上下文注入，确保布局、样式、交互与全局一致。

---

## 1. 项目概况

| 维度 | 说明 |
|---|---|
| 产品 | 公考备考应用「知行公考」，覆盖时政阅读、资料分析、申论·人民日报、真题套卷、错题闭环等公考模块 |
| 技术栈 | Taro 4 + Vue 3 (Composition API `<script setup>`) + NutUI Taro + Pinia + Sass + TypeScript |
| 运行端 | 微信小程序 + H5（双端兼容，`process.env.TARO_ENV` 区分） |
| 单位 | **一律 px**，禁止 rpx |
| 路由 | `src/app.config.ts` 集中注册，页面放 `src/pages/<module>/` |
| 组件 | 共享组件放 `src/components/`，页面私有组件内联 |
| API | `src/api/index.ts` 统一导出 `api` 对象，返回 `{ code, data, message }` |
| 状态 | Pinia store 放 `src/store/`，页面级状态用 `ref` / `reactive` |
| 事件处理器 | 模板内联处理器禁止多语句（如 `@tap="a = 1; load()"`），须抽成方法；prettier 会拆成无分号多行导致 Taro 模板编译失败 |

---

## 2. 设计系统（Design Tokens）

**唯一来源：`src/styles/variables.scss`**

每个 `<style>` 块第一行必须：
```scss
@import '@/styles/variables.scss';
```

### 2.1 颜色 — 禁止硬编码 hex

| 用途 | 变量 | 亮色值 | 暗色值 |
|---|---|---|---|
| 品牌主色 | `$primary-color` | `#d0021b`（默认中国红） | `#e85d6a` |
| 品牌深色 | `$primary-dark` | `#8b0000` | `#8f2f3a` |
| 品牌浅色底 | `$primary-light` | `rgba(208,2,27,.1)` | `rgba(232,93,106,.16)` |
| 正文 | `$text-primary` | `#1a1a1a` | `#e4e4e6` |
| 次要文字 | `$text-secondary` | `#666` | `#a8a8ae` |
| 弱文字 | `$text-muted` | `#999` | `#7c7c84` |
| 页面底 | `$page-bg` | `#f3f4f6` | `#121214` |
| 卡片底 | `$card-bg` | `#fff` | `#1c1c20` |
| 抬升底 | `$elevated` | `#f7f7f8` | `#26262b` |
| 输入框底 | `$input-bg` | `#fff` | `#26262b` |
| 边框 | `$border-color` | `#ebebeb` | `rgba(255,255,255,.08)` |
| 灰标签底 | `$chip-bg` | `rgba(0,0,0,.05)` | `rgba(255,255,255,.07)` |
| 成功 | `$success` | `#07c160` | `#3dba80` |
| 危险 | `$danger` | `#ee0a24` | `#e85d6a` |
| 警示底 | `var(--zk-warn-soft)` | `#fff7e6` | `rgba(224,168,74,.18)` |

**辅助色（编译期 hex，可做 rgba）：**
- `$accent-blue: #2f6fed`
- `$accent-green: #0f9d6c`
- `$accent-amber: #c47d00`

**品牌主题（5 套，运行时切换）：** 中国红（默认）`#d0021b` / 深蓝 `#1e3a5f` / 墨绿 `#0f7d4f` / 靛紫 `#5b3a8e` / 琥珀橙 `#c47d00`。
- JS 真值源：`src/constants/theme.ts`；SCSS 表：`variables.scss` 的 `$brand-themes`（两者必须同步）。
- `$primary-*` 是 `--zk-*` CSS 变量的别名，**色值随主题自动变化**，禁止按某个主题的 hex 硬编码。
- 主题 / 深色切换在学员端「我的」相关页面提供；H5 自定义 TabBar 随主题，小程序原生 tabBar 需额外同步（待优化，见 OPTIMIZATION.md）。

**规则：**
- 文字 / 背景 / 边框 → 用 `$` 变量（运行时 CSS var，暗色自动切换）
- 图标色 → `useBrandColor()` 返回 `brandColor` computed，传给 NutUI icon 的 `:color`
- 品牌渐变 banner → `linear-gradient(168deg, $primary-color 0%, $primary-mid 48%, $primary-dark 100%)`
- 唯一允许硬编码 `#fff` 的场景：品牌色背景上的白字（banner、active tab）

### 2.2 圆角 / 阴影

| Token | 值 |
|---|---|
| `$radius-md` | `12px` |
| `$radius-lg` | `16px` |
| `$shadow-card` | 亮色轻阴影；暗色 `none` |
| `$shadow-float` | 浮层阴影；暗色 `none` |

### 2.3 字号层级

| 场景 | 字号 | 字重 |
|---|---|---|
| 页面大标题 / 分数 | 20–28px | 700 |
| 区块标题 | 16px | 600 |
| 卡片标题 / 正文 | 14px | 500–600 |
| 描述 / 辅助 | 12–13px | 400 |
| 标签 / 角标 | 11px | 600 |
| 行高 | 正文 1.5–1.6，紧凑 1.2–1.4 |

---

## 3. 页面布局模板

### 3.1 通用骨架

```vue
<template>
  <view class="xx-page">
    <!-- 内容 -->
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { usePullDownRefresh } from '@tarojs/taro'
import { api } from '@/api'

definePageConfig({ navigationBarTitleText: '页面标题', enablePullDownRefresh: true })

const loading = ref(true)
const list = ref([])

async function load() { /* ... */ loading.value = false }
onMounted(load)
usePullDownRefresh(async () => {
  try { await load() } finally { Taro.stopPullDownRefresh() }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
.xx-page { @include page-padding; }
</style>
```

### 3.2 页面类型速查

| 类型 | 结构 | 参考 |
|---|---|---|
| **Hub / 入口页** | hero 统计卡 + 功能入口列表/网格 | `ziliao/index.vue` |
| **列表页** | 筛选 chips + 卡片列表 + 空态 | `ziliao/formulas.vue`, `exam/list.vue` |
| **详情页** | 头部卡片 + 分段 section | `ziliao/formula-detail.vue`, `rmrb/article-detail.vue` |
| **表单 / 编辑页** | 字段组 + 底部固定操作栏 | `events/edit.vue` |
| **答题 / 练习页** | 进度条 + 题卡 + 选项 + 底部导航 | `ziliao/drill.vue`, `exam/taking.vue` |
| **结果页** | 分数卡 + 错题解析 + 操作按钮组 | `ziliao/result.vue`, `exam/result.vue` |

### 3.3 间距规范

| 位置 | 值 |
|---|---|
| 页面内边距 | `16px`（`@include page-padding`） |
| 卡片内边距 | `16px`（`@include card`） |
| 卡片间距 | `12px`（card mixin 自带 `margin-bottom`） |
| 区块标题与内容 | `8–12px` |
| 列表行内边距 | `14px 16px` |
| 底部安全区 | `calc(Npx + env(safe-area-inset-bottom))` |
| 有 TabBar 的页面 | 额外 `padding-bottom: 20px` |
| 有固定底栏的页面 | 额外 `padding-bottom: 80–100px` |

---

## 4. 组件使用规范

### 4.1 必须复用的共享组件

| 组件 | 用途 | 禁止 |
|---|---|---|
| `LatexBlock` | 公式渲染（KaTeX） | 禁止页面内自行 `katex.renderToString` |
| `KnowledgeTree` | 知识树递归展示 | 禁止重写树组件 |
| `KnowledgePointPicker` | 知识点选择弹层 | — |
| `AppTabBar` | 自定义 TabBar（3 tab 页必须用） | 禁止用原生 tabBar |
| `ArticleCard` | 文章卡片 | — |
| `PointsBadge` | 积分徽章 | — |
| `VoiceInputBtn` | 语音输入按钮 | — |
| `AppFeedback` | 全局 Toast / Confirm 宿主 | — |

### 4.2 NutUI 组件引入方式

```ts
import { Button as NutButton, Input as NutInput } from '@nutui/nutui-taro'
import { Edit, Star, Category } from '@nutui/icons-vue-taro'
```

- 按钮：`<nut-button type="primary" block>`；次要操作加 `plain`
- 弹层：`<nut-popup v-model:visible position="bottom" round :closeable="true">`
- 骨架屏：`<nut-skeleton rows="3" />`

### 4.3 图标色

```ts
import { useBrandColor } from '@/utils/brandColor'
const { brandColor } = useBrandColor()
// 模板中：<Edit :color="brandColor" size="20" />
```

图标底色容器用 `@include icon-tile` + tone class：
```scss
.xx-icon {
  @include icon-tile;
  &.tone-red   { background: $primary-light; }
  &.tone-amber { background: rgba($accent-amber, 0.12); }
  &.tone-blue  { background: rgba($accent-blue, 0.1); }
  &.tone-green { background: rgba($accent-green, 0.1); }
}
```

---

## 5. 交互模式

### 5.1 数据加载

```
onMounted → load()
usePullDownRefresh → load() + stopPullDownRefresh
useDidShow → 非首次时 refresh（tab 页 / 编辑返回）
useReachBottom → 分页加载（首页推荐流）
```

- 首次加载显示骨架屏或「加载中…」
- 失败显示 `page-state-box`（标题 + 描述 + 重试按钮）
- 空数据显示空态卡片

### 5.2 反馈

| 场景 | 方法 |
|---|---|
| 轻提示 | `showToast(msg, 'none' \| 'success' \| 'error')` |
| 确认操作 | `await showConfirm(title, content)` → boolean |
| 文本输入弹层 | `await promptText(title, { placeholder })` → string \| null |
| 复制 | `await copyText(text)` |

**来源：`@/utils/platform`**，禁止直接调 `Taro.showToast`。

### 5.3 导航

| 场景 | API |
|---|---|
| 普通跳转 | `Taro.navigateTo({ url })` |
| Tab 页切换 | `Taro.switchTab({ url })` |
| 替换当前页（结果→重做） | `Taro.redirectTo({ url })` |
| 返回 | `Taro.navigateBack()` + `.catch(() => redirectTo fallback)` |
| 路由参数 | `useRouter().params?.id`，中文值 `encodeURIComponent` |

### 5.4 选项 / 答题交互

- 选项卡：`border: 1px solid transparent` → 选中 `border-color: $primary-color; background: $primary-light`
- 进度圆点：10px 圆，`$border-color` → 已答 `rgba($primary-color, 0.35)` → 当前 `$primary-color` + `scale(1.3)`
- 材料折叠：`-webkit-line-clamp: 3` + 展开/收起切换
- 底部操作栏：`position: fixed; bottom: 0;` + `env(safe-area-inset-bottom)`

### 5.5 筛选 Chips

```vue
<scroll-view scroll-x class="xx-filter-bar">
  <view class="xx-chip" :class="{ active: ... }" @tap="...">{{ cat }}</view>
</scroll-view>
```
- 默认：`$card-bg` 底 + `$border-color` 边 + `$text-secondary` 字
- 激活：`$primary-light` 底 + `$primary-color` 边和字 + `font-weight: 600`

### 5.6 列表行

```
[名称 14px $text-primary]        [箭头 ›  $text-muted]
[描述 12px $text-muted]
```
行间 `border-bottom: 1px solid $border-color`，末行无边框。

---

## 6. 样式铁律

1. **`<style lang="scss" scoped>`** — 永远 scoped，防止小程序全局泄漏
2. **类名前缀** — 模块缩写（`zl-`、`exam-`、`du-`、`ev-`），禁止裸 `.card` / `.title`
3. **禁止硬编码颜色** — 一切走 `$` 变量 / `var(--zk-*)`
4. **v-html 容器** — 必须 `color: $text-primary`（KaTeX 等库走 currentColor）
5. **暗色兼容** — 不写 `background: #fff`，用 `$card-bg`；不写 `color: #333`，用 `$text-primary`
6. **触控热区** — 可点元素 `@include hit-target`（最小 44×44）
7. **动画** — `transition: all 0.15s ease`；骨架 shimmer 用 `@keyframes`
8. **NutUI 覆写** — 用 `:deep(.nut-xxx)` 限定在页面根 class 内

---

## 7. 暗色主题机制

- CSS 变量切换：`html.theme-dark` / `page.theme-dark` / `.theme-dark` 下覆写 `--zk-*`
- 切换入口：`src/utils/theme.ts` → `applyTheme(dark)` 同步 DOM class + 原生导航栏
- 图标色：`useBrandColor()` 根据 `settingsStore.darkMode` 返回对应 hex
- **检查清单（新增页面必过）：**
  - [ ] 所有文字色用 `$text-*` 变量
  - [ ] 所有背景用 `$card-bg` / `$elevated` / `$page-bg`
  - [ ] 边框用 `$border-color`
  - [ ] 品牌色用 `$primary-*`
  - [ ] v-html 容器设 `color: $text-primary`
  - [ ] 无 `box-shadow` 硬编码（用 `$shadow-card` / `$shadow-float`，暗色自动 none）

---

## 8. 代码约定

### 8.1 文件命名

- 页面：`src/pages/<module>/<name>.vue`（kebab-case）
- 组件：`src/components/PascalCase.vue`
- 工具：`src/utils/camelCase.ts`
- Store：`src/store/camelCase.ts`

### 8.2 Script 结构顺序

```ts
// 1. imports（vue → taro → nutui → icons → 组件 → api → store → utils → types）
// 2. definePageConfig
// 3. router / store 实例
// 4. ref / reactive 状态
// 5. computed
// 6. 业务函数
// 7. 生命周期（onMounted → useDidShow → usePullDownRefresh → useReachBottom → onUnmounted）
```

### 8.3 API 调用模式

```ts
const res = await api.someMethod(params)
if (res.code === 0 && res.data) {
  // 成功
} else {
  showToast(res.message || '操作失败', 'error')
}
```

### 8.4 表单页模式

- `reactive({ ... })` 管理字段
- 保存前校验 → `showToast` 提示缺字段
- `saving` ref 控制按钮 loading
- 删除走 `showConfirm` 二次确认
- 成功后 `setTimeout(() => Taro.navigateBack(), 400)`

---

## 9. 新增功能 Checklist

- [ ] `app.config.ts` 注册页面路径
- [ ] 页面 `<style scoped>` + 模块前缀
- [ ] `@import '@/styles/variables.scss'` 首行
- [ ] 零硬编码颜色
- [ ] 暗色模式视觉检查（切 `.theme-dark` 无不可见元素）
- [ ] 加载态 / 空态 / 错误态 三态齐全
- [ ] 下拉刷新
- [ ] 触控热区 ≥ 44px
- [ ] 底部安全区 `env(safe-area-inset-bottom)`
- [ ] 反馈用 `showToast` / `showConfirm`（不直接调 Taro）
- [ ] 公式渲染用 `LatexBlock`
- [ ] 图标色用 `useBrandColor()`
- [ ] `npm run lint` 无新增 error

---

## 10. 快速参考：Mixin 速查

```scss
@include page-padding;        // 页面容器：16px padding + min-height 100vh + $page-bg
@include card;                // 卡片：$card-bg + 12px radius + 16px padding + shadow + 12px mb
@include page-state-box;      // 空态/加载/错误：居中卡片 + 标题 + 描述 + 按钮
@include brand-chip;          // 品牌标签：$primary-color 字 + $primary-light 底
@include muted-chip;          // 中性标签：$text-secondary 字 + $chip-bg 底
@include soft-chip($hex);     // 彩色标签（编译期 hex）
@include icon-tile;           // 44×44 图标底色容器
@include hit-target;          // 最小 44×44 触控区
@include filter-tab;          // 筛选 tab 最小触控
@include list-act;            // 列表操作文字按钮
@include brand-gradient;      // 品牌渐变背景
```
