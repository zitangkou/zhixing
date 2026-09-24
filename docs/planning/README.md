# 杜衡阁 · 规划文档索引

> 产品展示名：**杜衡阁**（历史文档仍可能写「知行公考」）。API / 域名：**https://zhixinggk.ltd**（不变）。
>
> 本目录是**在用/规划状态**的活文档入口；模块细节仍以根目录长文为准，避免三处互相打架。

## 文档角色（分工）

| 文档 | 角色 | 何时改 |
|------|------|--------|
| [`FEATURE_INVENTORY.md`](./FEATURE_INVENTORY.md) | **在用 / 隐藏 / 规划状态的操作真相源**（对齐 `featureVisibility` + 各端入口） | 开露、隐藏、下线、换入口时**必改** |
| [`PRODUCT_ROADMAP.md`](./PRODUCT_ROADMAP.md) | **规划清单**（主题状态、近期待办、登录后续） | 拍板优先级、完成里程碑、新增主题时改 |
| 根目录 [`FEATURES.md`](../../FEATURES.md) | 模块明细目录（页面表、组件、API 域说明） | 新增页面/能力时补明细；**状态列以 FEATURE_INVENTORY 为准** |
| 根目录 [`PROGRESS.md`](../../PROGRESS.md) | 历史阶段与质量快照 | 重大里程碑后回填；不替代本目录活状态 |

详细执行稿不在此复制，请链出去：

- 行测数据 / 出题调度 → [`../plans/xingce-data-roadmap-2026.md`](../plans/xingce-data-roadmap-2026.md)
- 工程债 W6 等 → [`../plans/optimization-plan-2026-09.md`](../plans/optimization-plan-2026-09.md)
- 发布 / 轻量部署 → [`../release/`](../release/)

## 文档维护约定

**新增 / 开露 / 隐藏 / 下线功能时，必须同步本目录两份活文档（必要时再改 FEATURES 明细）。**

1. **开露菜单或入口**  
   - 改 `src/constants/featureVisibility.ts`（或 admin `server/admin-web/src/config/featureVisibility.ts`）  
   - 更新 `FEATURE_INVENTORY.md`：状态 → `在用露出`，补入口/路由  
   - 若属规划兑现：在 `PRODUCT_ROADMAP.md` 对应主题标 `已完成` / `进行中`

2. **隐藏已实现能力（路由保留）**  
   - 关 `SHOW_*` / admin `VISIBLE_PATHS`  
   - `FEATURE_INVENTORY` 状态 → `已实现菜单隐藏`  
   - 不要从 FEATURES 长文删模块说明（深链仍可用）

3. **新增未挂菜单的能力**  
   - 先写进 `FEATURE_INVENTORY`（`部分完成` / `规划中`）与 `PRODUCT_ROADMAP`  
   - 有页面后再补 `FEATURES.md` 对应章节

4. **下线 / 后置**  
   - 状态标 `已下线` 或 `后置`，并在 ROADMAP 写清原因；禁止只改代码不改表

5. **冲突时**  
   - **露出与否**以 `featureVisibility` + `FEATURE_INVENTORY` 为准  
   - **怎么做**以 FEATURES / 代码为准  
   - ROADMAP 描述「下一步」，不发明未存在的 API

*约定生效：2026-09-25*
