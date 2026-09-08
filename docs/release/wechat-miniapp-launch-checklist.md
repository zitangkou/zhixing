# 知行策论 / 知行日知 · 小程序发布前待办清单

> 核查时间：2026-08-30 · 核查方式：代码 + 构建产物 + 线上域名实测
> 结论：**当前不可提审**。第一道硬阻断是 ICP 备案未通过（域名正被阿里云拦截）。

---

## 0. 实测证据（先看这个）

```text
$ curl -sI http://zhixinggk.ltd/
HTTP/1.1 403 Forbidden        ← 响应体标题 "Non-compliance ICP Filing"（阿里云备案拦截页）
$ curl -s -o /dev/null -w "%{http_code}" https://zhixinggk.ltd/
000                            ← 无证书，HTTPS 不可达
$ curl -s -o /dev/null -w "%{http_code}" http://zhixinggk.ltd/api/health
403                            ← 连 API 也被备案拦截
```

构建产物这一项是**好的**：两个 app 的 `dist/common.js` 里 API 基址已确认为 `https://zhixinggk.ltd`（无 127.0.0.1 残留），说明上次 weapp 生产构建参数正确，备案+证书完成后**无需重新构建**（域名不变）。

---

## 1. 阻断提审（必须全部完成才能提交审核）

| # | 事项 | 现状 | 要做的事 |
|---|---|---|---|
| B1 | **ICP 备案通过** | 🟡 终审中，域名被拦截 | 等备案通过，确认 `http://zhixinggk.ltd/` 返回 200 而不是 403 |
| B2 | **HTTPS 证书** | ❌ nginx 仅 `listen 80`（`deploy/nginx.conf:15`） | `certbot --nginx -d zhixinggk.ltd`，验证 `curl https://zhixinggk.ltd/api/health` 返回 200 |
| B3 | **微信后台合法域名** | ❌ 未配（依赖 B1/B2） | request 合法域名填 `https://zhixinggk.ltd`。已核实两个 app **只调用 `/api/*`，无 `Taro.uploadFile`/`downloadFile`/`chooseImage`**，所以一个 request 域名就够 |
| B4 | **用户隐私保护指引** | ❌ 完全缺失 | 微信后台「设置-服务内容声明-用户隐私保护指引」必须声明收集：微信昵称/账号、手机号（如收集）、学习记录。同时**小程序内要有隐私政策与用户协议页面 + 登录页勾选同意**（`apps/*/src/pages/auth/login.vue` 目前无任何协议入口，全仓库搜「隐私/协议/agreement」零命中） |
| B5 | **服务端生产密钥** | ❌ 全是开发默认值 | `server/.env`：`SECRET_KEY` 仍是 `dev-secret-key-change-in-production`；`ADMIN_PASSWORD` 仍是 `admin123`；`CORS_ORIGINS` 不含线上域名；`ALLOW_REGISTER` 未显式设置（默认 `True`） |
| B6 | **注册与账号体系** | 🟡 纯账号密码，无找回 | 二选一：① 关闭自助注册（`ALLOW_REGISTER=false`），提审时用管理员开通的体验账号；② 保持开放但补「忘记密码/重置」路径。纯账密且无找回是常见拒审点 |
| B7 | **死入口与「规划中」文案** | ❌ 会被判「功能不可用」 | `apps/theory-app/src/pages/profile/index.vue`：4 行「学习资产」都渲染「查看」标签但**整行没有绑定 `@tap`**，点击完全无响应。`apps/shenlun-app/src/pages/profile/index.vue`：「学习计划与设置」显示「规划中」标签 + `showToast('该功能正在规划中')`。要么隐藏未实现项，要么实现 |
| B8 | **小程序基本信息** | 🟡 头像已产出 | 名称（知行策论/知行日知）、简介、图标（用刚做的 144px 品牌红印章头像）、服务类目 |

## 2. 强烈建议（与提审并行，成本低）

| # | 事项 | 说明 |
|---|---|---|
| S1 | **关闭公网 API 文档** | `deploy/nginx.conf:70` 把 `/docs`、`/openapi.json`、`/health` 全部代理到公网，等于把整套后台接口清单公开。生产建议只留 `/health`，或给 `/docs` 加 IP 白名单/Basic Auth |
| S2 | **确认服务类目与主体资质** | 考公/教育培训类目在微信侧通常需要主体资质（企业营业执照含相应经营范围，部分情况需办学许可或 ICP 证）。个人主体基本无法选教育类——这决定两个小程序能否过审，需优先在微信后台确认可选类目 |
| S3 | **提审时提供体验账号** | 在「版本描述」里给出测试账号密码，否则审核员无法登录会直接驳回 |
| S4 | **首发内容池检查** | 申论需有足够「已通过双审核」的文章池，政治理论需有题库+权威文章。内容运营后台的库存看板（未来 7 天）应先跑一遍，避免上线即空内容 |
| S5 | **修正 FastAPI 品牌元信息** | `server/app/main.py` 的 title/description 仍是旧品牌「政考通」，会出现在 `/docs` 与部分对外响应里 |
| S6 | **加「关于我们/反馈」入口** | 教育类常要求可联系的反馈渠道，可用「关于我们」页 + 公众号引导（正好是 CONTENT_OPERATIONS_PLAN 里公众号作为私域入口的设计） |

## 3. 可延后（不影响首版发布）

行为事件统计页（M4 上岸卡片/能力雷达/里程碑）、足迹 Admin 入口、AI 出题与云端 ASR、element-plus 按需引入、支付会员、时政爬虫重建、lint 85 条 warning 与 pytest 70 条 warning 清理、H5 本机构建 panic 复核。

行测真题数据（`xingce-structured-data/`，2025 三卷 ready、答案/解析待补）**不属于这两个首发垂直产品**，可以后置到资料/数量/言语/判断产品。

## 4. 文档需要修正的地方

| 位置 | 问题 | 状态 |
|---|---|---|
| `PROGRESS.md` 阶段表 | 「内容运营·双审核留痕」与「理论错题复习」标注为**未提交**，实际已提交（`04e6f46`、`a1047d3`） | ✅ 本次已修正 |
| `PROGRESS.md` 后续路线 | 未记录备案拦截导致 `/api` 全线 403 这一实际阻断 | ✅ 本次已补充 |
| 全局 | 缺少一份「小程序提审检查单」 | ✅ 即本文档，已固化在 `docs/release/` |
| `DEPLOY.md:131` | 把 HTTPS 写成「可选」，对小程序提审是**必需**项 |  待改 |
| `apps/README.md:33` | 「`TARO_APP_API_URL` 留空表示请求当前域名的 `/api`」只对 H5 成立；weapp 必须填完整 HTTPS 域名，建议补一句警示 | ⬜ 待改 |

## 5. 建议执行顺序

1. **等备案**（不可控，期间做代码层的事）
2. 补隐私政策 + 用户协议页面与登录页勾选（B4）
3. 清理死入口与「规划中」文案（B7）
4. 生产 `.env` 换密钥、定 `ALLOW_REGISTER`（B5/B6）
5. nginx 收口 `/docs`（S1）
6. 微信后台确认类目资质（S2）+ 填基本信息与隐私指引（B4/B8）
7. 备案通过 → `certbot` 上 HTTPS（B2）→ 配合法域名（B3）
8. 真机预览验证登录/主流程 → 上传提审（带体验账号，S3）

其中 2、3、4、5 是纯代码/配置工作，现在就能做完，备案一下来即可提审。
