# 知库 · 独立微信小程序

知库使用独立的 Taro 工程和微信小程序 AppID，技术栈为 Taro 4 + Vue 3 + TypeScript。它与知行主应用分开构建、分开发布，通过 `X-Product-Key: zhiku` 调用同一 FastAPI 服务，并复用主应用管理后台。

## 页面与能力

- 首页：精选目录、关键词搜索、分类筛选。
- 我的：微信快捷登录、个人文档上传和删除、退出登录。
- 阅读页：读取发布目录或个人文档的解析文本，展示身份水印和只读提示。
- 登录页提供隐私政策和用户服务协议入口；我的页面可再次查看。
- 支持 MD、TXT、PDF、DOCX 上传；扫描版 PDF 标记为待 OCR。
- 原始视觉稿保存在 `prototype/`。

## 本地构建

```bash
cd zhishiku
npm install
cp .env.example .env.development
# 编辑 .env.development，将 TARO_APP_API_BASE_URL 指向可访问的后端 HTTPS 根地址
npm run dev:weapp
```

微信开发者工具选择本目录（`project.config.json`），或先运行 `npm run build:weapp`，再选择生成的 `dist/` 小程序代码。

## 发布前配置

1. `project.config.json` 已配置知库独立小程序 AppID（取自本地 `.env` 的 `APP_ID`）；不要复用主应用 AppID。`APP_SECRET` 只保留在服务端环境变量中，不得写入小程序包。
2. 生产后端配置 `ZHIKU_MINIPROGRAM_APP_ID` 和 `ZHIKU_MINIPROGRAM_APP_SECRET`，并确认 `ENABLED_PRODUCT_KEYS=general,zhiku`；部署微信登录与知库文档接口。
3. 在本地隐私政策和用户服务协议页面补齐运营主体法定名称、联系渠道，并由运营方确认文本后再发布。
4. 在微信公众平台配置后端 HTTPS `request`、`uploadFile` 域名和隐私保护指引，确保备案、证书及平台信息符合要求。
5. 在微信开发者工具真机检查登录、目录搜索、文件上传、文档阅读和水印，再上传代码并提交审核。

管理人员在现有管理后台「备考教学 → 知库文档」上传、编辑并发布资料；发布状态控制小程序目录的可见性。管理权限复用 `knowledge:read` / `knowledge:write`。

## 微信登录与开放范围

知库通过 `wx.login` 获取临时 code，由共用后端的 `/api/auth/wechat/login` 换取会话并创建登录态。知库是独立小程序，后端必须配置独立的 `ZHIKU_MINIPROGRAM_APP_ID` 和 `ZHIKU_MINIPROGRAM_APP_SECRET`；AppSecret 只允许放在服务端环境变量中，不能写入 Taro `.env` 或小程序代码包。首版所有已登录用户可浏览管理员发布的目录，不做文档级授权或付费限制；个人上传的文档仍仅本人可见。

小程序中的文本选择限制和身份水印只能增加普通复制成本，无法阻止截图或客户端绕过。定向分享、付费权益和访问审计留待后续迭代。

后端当前私有文档上限为 20 MB，提取文本最多保存 100 万字符。PDF 解析使用 pypdf；无文本层的扫描件需后续接入 OCR。
