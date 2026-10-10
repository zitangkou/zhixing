# 言遇英语

知行仓库内的独立 Taro 4 + Vue 3 微信小程序项目。英语内容服务和管理菜单复用仓库 `server/` 与 `server/admin-web/`，学员端代码、微信配置和构建产物独立在本目录。

## 开发

```bash
npm install
npm run dev:weapp
```

微信开发者工具导入本目录下生成的 `dist/`。H5 调试可运行 `npm run dev:h5`。小程序 AppID 从服务端本地 `server/.env` 的 `YANYU_ENGLISH_MINIPROGRAM_APP_ID` 同步到 `project.config.json`；AppSecret 只保存在服务端本地环境变量 `YANYU_ENGLISH_MINIPROGRAM_APP_SECRET`。

API 地址在 `src/config.ts`，当前指向 `https://zhixinggk.ltd/api`。在微信公众平台「开发管理 → 开发设置 → 服务器域名」中，将 `https://zhixinggk.ltd` 配置为 request 合法域名。微信登录由小程序 `wx.login` 获取临时 code，再由后端使用服务端 AppID/AppSecret 换取会话；登录 token 缓存在本机，学习完成记录绑定微信登录用户。未能连接 API 时，学员端会回退到内置样例内容。

## 当前功能

- 今日推荐、场景浏览和课程练习。
- 对话中英对照、核心句块、情境替换任务；后台可在课程 JSON 中关联已获授权的 `dialogueAudioUrl`，示范音频尚未配齐的课程会明确显示待配置状态。
- 微信录音、当前设备回放与删除；录音不上传服务器。
- 本地完成进度、学习统计和次日复习提示基础。
- 公开 API 获取已发布内容、写入单元完成记录。
- 管理后台“英语学习”菜单：场景、课程单元、发布状态和基础数据概览。

小程序名称定为“言遇英语”。项目内图标使用 `src/assets/logo.svg`；微信公众平台头像上传物料单独提供在 `/Users/dnn/Projects/内容运营/英语学习/言遇英语头像.png`（144×144 PNG）。上线前仍需在微信公众平台完成名称、主体、类目和 AppID 核验。
