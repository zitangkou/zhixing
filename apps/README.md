# 知行公考独立题型应用

本目录承载可独立开发、构建和发布的题型产品。每个目录都是完整的 Taro 项目，不通过环境变量切换产品。

| 应用 | 目录 | H5 开发端口 | 产品定位 |
| --- | --- | --- | --- |
| 申论 | `shenlun-app/` | `10088` | 人民日报精读、三刀法拆解、申论专项训练 |
| 政治理论 | `theory-app/` | `10089` | 时政与理论学习、真题化生成、刷题复习 |

后续资料分析、数量关系、言语理解、判断推理等项目，从同一题型应用模板创建，但必须拥有独立的 `package.json`、`config/`、`src/`、路由和构建产物。

统一体验规范见 [`../docs/architecture/vertical-app-design-system.md`](../docs/architecture/vertical-app-design-system.md)。

## 启动

依赖暂时复用仓库根目录已安装的 Taro 工具链，应用源码与构建配置彼此独立。

```bash
cd apps/shenlun-app && npm run dev:h5
cd apps/theory-app && npm run dev:h5
```

微信小程序分别执行 `npm run build:weapp`，并用微信开发者工具打开对应应用目录；正式发布前为每个产品配置独立 AppID。

## 生产发布

主 Docker 镜像会同时编译三套 H5，统一复用一个 FastAPI 后端：

- 综合应用：`/`
- 申论：`/shenlun/`
- 政治理论：`/theory/`

垂直 H5 构建时必须设置对应 `TARO_APP_PUBLIC_PATH`；独立域名部署时可保持 `/`。`TARO_APP_API_URL` 留空表示请求当前域名的 `/api`，跨域部署时填写完整 HTTPS API 域名。

```bash
TARO_APP_API_URL=https://zhixinggk.ltd TARO_APP_PUBLIC_PATH=/ npm run build:h5
TARO_APP_API_URL=https://zhixinggk.ltd npm run build:weapp
```

小程序正式包不能使用仓库中的 `touristappid`。发布人员需在两个项目各自的 `project.config.json` 中填写独立 AppID，并在微信公众平台配置 HTTPS request 合法域名；该 AppID 配置属于发布环境信息，不共用、不互相切换。
