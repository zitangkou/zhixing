# 微信小程序打包与预览（知行公考）

> 给在 Mac 上构建、再导入微信开发者工具做预览 / 真机 / 上传的人。  
> 命令以仓库为准：`package.json`、`scripts/build-release-artifacts.sh`、`scripts/release-preflight.py`、`config/index.ts`、`project.config.json`。  
> 与 [DEPLOY.md](../../DEPLOY.md) §10 配套。仓库没有小程序上传脚本，预览、真机调试、上传代码都在微信开发者工具里手工完成。

## 1. 什么时候打包

1. **先有正式 HTTPS API。** 生产指向的小程序包会把 `TARO_APP_API_URL` 写进产物。后端和域名（例如 `https://zhixinggk.ltd`）应已可访问，再打这个包做真机验收。本地联调不要用这份正式包。
2. **修 bug 时不要顺手打包。** 问题一个一个修。只有明确要出一版预览 / 上传包时才构建。
3. **H5 和微信小程序共用 `dist/`。** `config/index.ts` 的 `outputRoot` 是 `dist`。两种目标不能并行构建，也不能连续构建后只留下最后一次的 `dist`。用下面的归档脚本：它先构建 H5 并立刻拷走，再构建小程序并立刻拷走。

## 2. 推荐的正式构建

在仓库根目录（需已 `npm install`）：

```bash
bash scripts/build-release-artifacts.sh --api-url https://zhixinggk.ltd
# 可选：--output 必须是尚不存在的绝对路径
# bash scripts/build-release-artifacts.sh --api-url https://zhixinggk.ltd --output /绝对/路径
python3 scripts/release-preflight.py --artifact-dir '<OUTPUT_DIR>'
```

`--api-url` 必填，且必须是 `https://` 开头（脚本拒绝 `http://`）。不传 `--output` 时，产物在 `${TMPDIR:-/tmp}/zhixing-release-日期时间`。目录已存在会拒绝覆盖。

脚本实际做的事：

| 步骤 | 环境变量 | 命令 | 归档 |
|------|----------|------|------|
| H5 | `TARO_APP_API_URL=`（空字符串） | `npm run build:h5` | 拷到 `<OUTPUT>/h5/` |
| 小程序 | `TARO_APP_API_URL` = 上面的 HTTPS 地址 | `npm run build:weapp` | 拷到 `<OUTPUT>/weapp/dist/`，并复制根目录 `project.config.json` |

空字符串和「未设置」不一样。`config/index.ts` 里 `API_BASE_URL` 取 `process.env.TARO_APP_API_URL ?? 'http://127.0.0.1:8001'`：未设置时是本地 `http://127.0.0.1:8001`；空字符串是同域 `/api`（Docker H5）。小程序没有同域页面，正式包必须带 HTTPS 域名，不能留空、也不能落回 `127.0.0.1`。

产物布局：

```text
<OUTPUT_DIR>/
  RELEASE.txt                 # created_at、api_url、git_commit
  h5/                         # 含 index.html；同域 /api
  weapp/
    project.config.json       # 从仓库复制，miniprogramRoot 为 dist/
    dist/                     # 含 app.json；请求打到 --api-url
```

脚本结束后，仓库里的 `dist/` 是**后一次的小程序产物**，不是 H5。要发布的是归档目录，不要把仓库 `dist/` 当正式包。

`release-preflight.py` 只读、不打印密钥值。`--artifact-dir` 检查：

- `RELEASE.txt` 存在
- `h5/index.html` 存在
- `weapp/dist/app.json` 与 `weapp/project.config.json` 都在（打印「微信小程序产物可导入」）

同时它会看**仓库根**的 `project.config.json`（不是只看归档副本）：`compileType` 须为 `miniprogram`、`miniprogramRoot` 须为 `dist/`；`urlCheck: false` 和 `appid` 仍为 `touristappid` 时只告警、不阻断。服务器环境和公网路由另见 [DEPLOY.md](../../DEPLOY.md) §10 的 `--env-file` / `--base-url`。

### 只打小程序、本地反复迭代

```bash
TARO_APP_API_URL=https://zhixinggk.ltd npm run build:weapp
```

对应脚本是 `taro build --type weapp`。监听模式是 `npm run dev:weapp`（同一条构建加 `--watch`），适合改代码，不代替上面的正式归档。

导入方式：

- 导入**仓库根目录**。根目录已有 `project.config.json`，`miniprogramRoot` 指向 `dist/`。
- 不要把 `project.config.json` 原样放进 `dist/` 再导入：`miniprogramRoot: dist/` 会去找 `dist/dist/`。若只想打开 `dist/`，直接把该目录当小程序根（里面已有 `app.json`），不要再套这一层配置。

之后再跑 `npm run build:h5` 会覆盖同一个 `dist/`。迭代中途要留小程序包，先自己拷走 `dist/`，或改用第 2 节的归档脚本。

## 3. 导入微信开发者工具

手工步骤（仓库无上传 CLI）：

1. 微信开发者工具 → 导入项目。正式包导入归档的 **`weapp/`**（该目录有 `project.config.json`，代码在 `weapp/dist/`）。本地迭代导入仓库根目录，见上一节。
2. 游客预览可以暂时用 `touristappid`。游客模式之外，把导入工程的 `appid` 改成小程序真实 AppID（开发者工具「项目详情」，或改归档里的 `weapp/project.config.json`）。AppID 不是密钥。仓库里的 `project.config.json` 目前是 `touristappid`；不要为了一次预览把 AppSecret 写进该文件。
3. 微信公众平台 → 开发管理 → 开发设置 → 服务器域名：把 **request 合法域名** 配成生产 API 主机（HTTPS，无路径），与构建时的 `--api-url` 主机一致，例如 `https://zhixinggk.ltd`。
4. 仓库 `project.config.json` 的 `setting.urlCheck` 是 `false`，只方便本地不校验域名。正式真机必须在合法域名已配置的前提下再验一遍请求是否打到生产 HTTPS，不要靠关掉校验蒙混过关。`release-preflight.py` 对此有同样的告警。

## 4. 环境变量与密钥

| 位置 | 变量 | 用途 |
|------|------|------|
| 本次前端构建 | `TARO_APP_API_URL` | 唯一需要传入的前端地址；写入 `API_BASE_URL` |
| 服务器 / 本机 `.env`（已 gitignore） | `MINIPROGRAM_APP_ID` | 小程序 AppID |
| 同上 | `MINIPROGRAM_NAME` | 名称占位 |
| 同上 | `MINIPROGRAM_BASE_URL` | 小程序侧基地址占位 |
| 同上 | `MINIPROGRAM_APP_SECRET` | AppSecret，只放 `.env` |

占位说明见 `.env.docker.example`。`.env`、`server/.env`、`dist/` 都在 `.gitignore`。文档和提交里只写变量名，不写、不粘贴任何密钥值。打包时不要设 `USE_MOCK=true`（生产走真实 API）。

## 5. 已在仓库里的小程序构建补丁

下面两处只在 `TARO_ENV=weapp` 时生效，H5 构建会直接跳过。改小程序时不要让 H5 行为跟着变。

- **分包循环**：`config/weappChunkCycle.ts` 的 `weappBreakVueChunkCycle`。Taro 4.0.9 把 Vue 打进 `taro.js`、把 `@babel/runtime` 打进 `vendors.js`，循环依赖下 `defineComponent` 还是空的。插件把 `@babel` 拆到 `babelHelpers` chunk。
- **scoped CSS**：`config/weappScopedCss.ts` 的 `weappScopedCss`。小程序节点上没有 `data-v-*`，插件把选择器改成同类名，并补页面 `page-meta`、组件 `addGlobalClass`，以及图标用的 `comp.wxss`。运行时配合 `src/utils/weappScopeClass.ts`。

### 排查（补丁已在 main，不要重复打一遍）

按钮没反应时，先看 `src/utils/weappScopeClass.ts` 的标签映射是否还在，而不是再贴一套补丁。

- **登录 / 注册按钮点了没反应。** NutUI Button 渲染原生 `button`。不传 `disabled` 时模板仍是空绑定，基础库把它当成 disabled，不派发 tap，也没有报错。现有逻辑在小程序里把 `button`（以及图标用的 `i`）映射成 `view`。映射被拿掉或没打进本次产物时，登录按钮会再次失灵。
- **登录 / 注册后报 `page "" is not found`。** 空跳转不能 `redirectTo`。`src/utils/postAuthRoute.ts` 的 `resolveAfterAuthTarget`：空目标或非页面路径走首页 `switchTab`；tab 页（学习 / 我的）只能 `switchTab`；普通页才 `redirectTo`。`src/utils/auth.ts` 的 `enterAfterAuth` 走这条路径。
- **登录成功，回到「我的」仍是游客。** 「我的」判定是 token 和 `userInfo.id` 都在（`src/pages/user/index.vue`）。token 存在 `zhixing_token`（`Taro` storage，`setToken`）。Pinia 只持久化 `userInfo`。页面 `useDidShow` 会 `bumpAuthView`，并在有 token 但没有用户 id 时调用 `userStore.bootstrap()`（请求 `/api/user/me`）。仍显示游客时，查 token 是否写入、`/api/user/me` 是否成功，而不是只看登录接口返回。
- **预览报 `defineComponent is not a function`。** 循环依赖的修复已在 `weappChunkCycle`。这个报错更多是产物不完整，或导入了错误目录（例如 H5 的 `dist`、或 `dist` 被下一次构建盖掉）。清掉旧 `dist` 后按第 2 节重编，导入归档的 `weapp/`（其下有 `dist/app.json`）。
- **行测入口不见或打开空白页。** `src/app.config.ts` 须保留 `pages/question/xingce-hub`、`pages/question/xingce-modules`、`pages/question/xingce`。学习页「行测真题」进入 `/pages/question/xingce-hub`（`src/pages/index/index.vue`）。
- **控制台噪声。** `comp.wxss` 是图标字体抽取（`weappScopedCss`），选择器告警按既有联调记录通常不挡预览。`reportRealtimeAction` 在仓库代码里没有对应处理，同样按非阻断噪声看待，除非它伴随着白屏或请求失败。

## 6. 导入后冒烟（按顺序）

1. **API 根是生产 HTTPS。** 在开发者工具网络面板确认请求主机是构建时的 `--api-url`（如 `https://zhixinggk.ltd`），不是 `127.0.0.1:8001`，也不是空主机。详情里的「不校验合法域名」只能用于本地；真机按第 3 节核对合法域名。
2. **登录 / 注册 / 「我的」。** 登录或注册成功后用 `switchTab` 回到 tab，没有 `page "" is not found`。「我的」显示昵称和用户名，而不是「游客浏览」。
3. **行测入口和目录。** 学习页能进「行测真题」。目录接口是 `GET /api/xingce/catalog`。生产库还没导入行测 JSON 时，页面是「还没有可练真题」（`xingce-hub` 空态），这是数据未导入，不是打包失败。有数据时应出现年度套卷，而不是请求失败。
4. **反馈。** 登录后「我的」→「反馈建议」，提交走 `POST /api/feedback`（需登录 token）。未登录会得到「未登录」，不要当成接口挂了。
5. **H5 不被小程序补丁带偏。** 同一轮归档里的 `h5/` 仍按同域 `/api` 打开；登录按钮、样式、行测入口与改小程序之前一致。第 5 节的插件不应作用到 H5。

## 7. 不要做

- 不要提交 `.env`、`server/.env`、`dist/`，不要把 AppSecret 或其它密钥写进文档、PR、聊天记录。
- 不要对同一个 `dist/` 并行或连续跑 `build:h5` 和 `build:weapp` 而不立刻归档。用 `scripts/build-release-artifacts.sh`。
- 不要在文档或示例里写假的 AppSecret。变量名以 `.env.docker.example` 为准，值留空。
- 不要在 bug 还没修完时打正式预览包，除非明确要求出包。
