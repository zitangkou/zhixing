# 拾景纸刊·实景拼贴

```image-style-json
{
  "id": "gathered-scenes-collage",
  "slug": "gathered-scenes-collage",
  "name": "拾景纸刊·实景拼贴",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "以真实照片为锚点，结合照片衍生的抽象插画、结构性色彩和纸边肌理。",
  "status": "draft",
  "version": "1.0.0",
  "sortOrder": 50,
  "promptTemplate": "把输入照片编排成一页独立纸刊式拼贴海报。保留一块清晰可辨的真实照片区域作为场景事实锚点，不把其中的人物、建筑或关键主体重画成另一物体。围绕照片，提取场景里真实存在的方向、轮廓、色彩和空间关系，发展成少量抽象绘画色块或线条，使插画像从现场延伸出来，而非贴上无关装饰。可以使用一处结构性色彩和不规则手撕纸边，边缘有可见纤维与轻微印刷错位；布局保持平面、留白充足、视觉重心明确。先识别核心主体、空间方向、颜色关系和情绪，再只保留让场景仍可辨认的关键信息。场景重点：{{scene_description}}。默认无文字，无地点或时间猜测。",
  "negativePrompt": "不要把原照片全部变成插画，不要用无关纹样或几何形装饰；不要遮挡主体关键部分，不要拼接多个照片，不要添加无来源文字、日期、地点、商标、水印或二维码；避免广告版式、过度撕纸、杂乱剪贴、相框和立体 mockup。",
  "rules": {
    "subjectPreservation": {"priority": "strict-for-photo-anchor", "mustPreserve": ["照片锚点真实性", "核心主体及其空间关系", "场景主色方向"], "allowSimplification": ["非锚点区域细节"], "noInventedObjects": true},
    "rendering": {"photo": "真实照片锚点", "illustration": "从原图关系推导的抽象绘画", "edge": "局部手撕纸纤维", "print": "轻微印刷错位"},
    "layout": {"type": "photo-anchored-editorial-collage", "includeOriginalPhoto": true, "negativeSpace": "generous"},
    "color": {"deriveFromSource": true, "role": "色彩用于构图和视觉重心，不做无规则铺色"}
  },
  "controls": {"photoPreservation": "high", "sceneRelationshipFidelity": "high", "abstraction": "medium", "paperEdge": "selective", "colorAccentCount": 1, "layoutDensity": "low", "aspectRatio": "source-adaptive"},
  "providerParameters": {},
  "maintainerNotes": "按可观察到的实景拼贴理念重新编写，先草稿测试。来源项目公开许可限制非商业用途；本配置未复制原文，正式商用前仍需复核许可并避免复刻其具体成品。"
}
```
