# 影像抽象·编辑画页

```image-style-json
{
  "id": "photo-abstract-editorial",
  "slug": "photo-abstract-editorial",
  "name": "影像抽象·编辑画页",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "保持照片原样，并从照片自身的形状、色调和颜色关系生成极简抽象面板。",
  "status": "draft",
  "version": "1.0.0",
  "sortOrder": 70,
  "promptTemplate": "生成一张竖版编辑艺术页：原照片作为主要区域，保持照片内容真实、清晰且不经滤镜重绘；另一块为浅象牙白抽象面板。先从照片中观察地平线高度、主体大小关系、主要轴线、重叠、留白、明暗和实际颜色，只从这些关系中提取少量抽象形状、色带和线条。抽象面板不是缩略图、描摹图或图标，而是照片结构的简洁回应；颜色必须来自照片，最多保留一组主色与少量辅助色，不添加无关装饰。照片与面板依画幅自然上下或左右排列，版式简洁，留白充足。场景重点：{{scene_description}}。不生成标题、日期、标识或水印。",
  "negativePrompt": "不要修改、滤镜化、补绘、裁切主体或扩展照片内容；不要把抽象面板做成照片缩略图或具象插画；不要引入原图不存在的颜色、图标、符号、文字或对称装饰；避免厚重纹理、海报广告感、阴影相框和水印。",
  "rules": {
    "subjectPreservation": {"priority": "strict-for-photo", "mustPreserve": ["照片像素内容的视觉真实性", "主体与构图", "原始方向"], "noInventedObjects": true},
    "rendering": {"photo": "未经风格化的原始照片", "abstractPanel": "少量来源于照片结构的抽象形", "palette": "仅取自照片", "background": "均匀浅象牙白"},
    "layout": {"type": "photo-plus-derived-abstract-panel", "includeOriginalPhoto": true, "frame": false, "decoration": "none"},
    "text": {"enabled": false}
  },
  "controls": {"photoPreservation": "strict", "panelAbstraction": "high", "sourceRelationshipFidelity": "high", "shapeFamilies": "1-3", "paletteSource": "photo-only", "negativeSpace": "high", "aspectRatio": "portrait-editorial"},
  "providerParameters": {},
  "maintainerNotes": "公开来源的自定义许可限制商业使用；这里只记录通用抽象方法并独立撰写。商用前复核授权；照片区域保真需重点测试。"
}
```
