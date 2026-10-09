# AI 图片处理风格配置

AI 百宝箱的图片风格配置由共享后端管理，当前保存到 `system_settings` 的 `image_style_presets` JSON 设置项。模型无关的风格规则与特定图像服务参数分开保存，后续新增风格或模型适配参数时不需要新增数据库列。

## 首个预设

- 名称：旅行手账·清透淡彩
- 标识：`travel-journal-watercolor`
- 适用产品：`general`
- 定位：旅行和日常风景照片的轻盈低饱和水彩手账风格
- 维护依据：四张测试原图的多轮转换观察

预设包括风格说明、提示词模板、负面提示词、主体保留与画面规则、模型无关的语义控制、服务商参数、状态和版本信息。模板支持 `{{scene_description}}` 场景描述占位符。当前尚未接入图片生成模型，`providerParameters` 初始化为空对象；不要将未验证的采样数值当成已测参数。

## 后台管理

访问管理后台“工具配置 → 图片配置”。拥有 `setting:read` 权限的管理员可查看，拥有 `setting:write` 权限的管理员可新增、编辑、删除配置。

模型在“工具配置 → 模型配置”中单独维护。每个风格的 `modelId` 可指定已启用模型；留空则继承默认模型。模型密钥只保存在服务器 `.env`，管理界面只显示对应变量是否已配置。当前适配器配置支持 DashScope 与 OpenAI 兼容图像编辑接口；服务端凭据未配置时模型不能启用。

小程序登录用户可调用 `POST /api/image-generations`（multipart 字段 `file`、`style_id`）进行图像编辑。后端根据风格的 `modelId` 或模型注册表默认项选择适配器，再合并后台提示词和模型参数；原图只在内存中转发模型。生成结果保存在非公开目录，使用 `GET /api/image-generations/{result_id}/result` 且同一登录用户授权读取，24 小时后清理。当前模型密钥为空时，须先在服务器设置 `DASHSCOPE_API_KEY` 或 `OPENAI_IMAGE_API_KEY` 并重启后端，再到后台启用对应模型。

### Markdown 本地迭代与导入

先在本地用代表性原图迭代提示词和规则，完成后按 [Markdown 导入模板](/Users/dnn/Projects/zhixing/server/admin-web/public/templates/image-style-preset.md) 记录测试说明，并将完整配置放入唯一的 `image-style-json` fenced code block。后台图片配置页提供“导入 Markdown”：选取文件后会预览名称、ID、slug、状态、产品键和提示词，并检查字段格式及 ID/slug 冲突；管理员确认后才写入配置。导入只新增，不覆盖已有风格。

模板文件部署后可从管理后台页面直接下载。文案配置已作为“工具配置”的独立入口预留；当前小程序工具目录仍是项目内置数据，后续可接入名称、简介、分类和使用说明的集中维护。

- `draft`：草稿，不出现在公开目录
- `active`：启用，可被适用产品公开查询
- `archived`：归档，不出现在公开目录
- `version`：人工维护的风格版本，例如 `1.0.0`
- `rules`、`controls`、`providerParameters`：可扩展 JSON 对象

## 接口

- `GET /admin/image-styles`：读取完整配置，需要 `setting:read`
- `POST /admin/image-styles`：新增配置，需要 `setting:write`
- `PUT /admin/image-styles/{id}`：整体更新配置，需要 `setting:write`
- `DELETE /admin/image-styles/{id}`：删除配置，需要 `setting:write`
- `POST /admin/image-styles/import/preview`：解析 Markdown 并预览校验，需要 `setting:write`
- `POST /admin/image-styles/import`：新增导入的风格；拒绝重复 ID 或 slug，需要 `setting:write`
- `GET /api/image-styles`：按当前产品返回已启用风格的展示元数据；不返回提示词、规则和维护备注

实际图片处理接入后，后端应按风格 ID 读取完整预设，合并场景描述，再交给所选模型适配器。模型密钥和内部提示词不应放入小程序客户端。
