# 图片处理风格配置模板

填写说明：

- 每个 Markdown 文件只能包含一个 `image-style-json` 配置块；其余内容可记录测试过程、参考图特征、迭代结论等说明。
- `id` 使用唯一英文标识（字母、数字、下划线或连字符）；`slug` 使用唯一的小写英文和连字符。
- 先在本地测试迭代，完成后再把最终规则和提示词写入下方 JSON。后台导入会先预览并校验，确认后新增为一条风格配置。
- 新风格建议先设为 `draft`，经代表性图片复核后，再在后台编辑为 `active`。
- `rules`、`controls`、`providerParameters` 可按所选模型能力灵活扩展。服务商参数暂不确定时保留 `{}`。

## 本地测试与迭代记录

- 测试原图：填写文件名或样本编号
- 目标风格：填写风格方向
- 主体保留要求：描述主体、数量、位置、构图和比例
- 已知问题与迭代结论：记录每轮变化及效果
- 发布前复核：列出需重点检查的代表性样图

## 可导入配置

```image-style-json
{
  "id": "example-ink-wash",
  "slug": "example-ink-wash",
  "name": "示例·水墨风格",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "",
  "description": "将输入图片转换为克制的水墨画风，同时保留原图主要主体与构图。",
  "status": "draft",
  "version": "1.0.0",
  "sortOrder": 100,
  "promptTemplate": "将输入图片转绘为克制、清晰的水墨画风。以原图作为构图蓝图，保留主要主体的身份、数量、轮廓、相对位置、比例、视角与画幅，不新增、删除、替换或移动主体。场景重点：{{scene_description}}。",
  "negativePrompt": "不要改变主要主体和构图；不要新增或删除主体；不要添加文字、水印、边框或无关装饰。",
  "rules": {
    "subjectPreservation": {
      "priority": "strict",
      "mustPreserve": ["主体身份与数量", "主体轮廓", "相对位置与比例", "视角", "原图画幅"],
      "noInventedObjects": true
    },
    "rendering": {
      "medium": "水墨画",
      "detailLevel": "主体清晰，次要细节适度概括"
    },
    "prohibitedAdditions": ["新主体", "文字与水印", "边框与贴纸"]
  },
  "controls": {
    "subjectPreservation": "strict",
    "compositionPreservation": "high",
    "styleIntensity": "medium",
    "aspectRatio": "source"
  },
  "providerParameters": {},
  "maintainerNotes": "示例模板，请使用本地样图验证并替换提示词、规则和参数后再启用。"
}
```
