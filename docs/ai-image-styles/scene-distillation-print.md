# 场景蒸馏·纸刊插画

```image-style-json
{
  "id": "scene-distillation-print",
  "slug": "scene-distillation-print",
  "name": "场景蒸馏·纸刊插画",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "不保留原照片，提炼场景事实、关系与情绪，重新创作纸刊插画。",
  "status": "draft",
  "version": "1.0.0",
  "sortOrder": 60,
  "promptTemplate": "把输入照片当作观察资料，而不是需要描摹的底图。先识别真实主体、动作、空间距离、光线方向和一条最有意义的关系，然后把这些事实压缩为一张全新纸刊插画；成品中不出现原照片，也不做照片拼贴。构图只使用少数清晰的大形、留白、纸片边界和一种有目的的强调色。插画必须保留场景的语义核心和至少两个可辨认的身份线索，但可以省略偶然细节，用形状、颜色和简单动作表达照片的情绪。纸面质感自然，边界略有手作纤维感，避免模板化海报。场景观察：{{scene_description}}。不猜地名、人物身份和拍摄时间，不生成文字。",
  "negativePrompt": "不要把原照片直接放进成品，不要按像素复刻照片，不要改变场景核心事实或替换主体；不要罗列多个隐喻，不要添加无关人物、物件、文字、水印、品牌、二维码；避免过多颜色、繁杂拼贴、照片写实和通用图库式插画。",
  "rules": {
    "subjectPreservation": {"priority": "semantic", "mustPreserve": ["核心主体身份线索", "关键动作或空间关系", "场景主要情绪依据"], "allowSimplification": ["照片表面细节", "次要背景物件"], "noInventedObjects": true},
    "rendering": {"medium": "纸面编辑插画", "forms": "少数来源明确的大形", "paperEdge": "轻微手作纤维", "negativeSpace": "high"},
    "layout": {"type": "full-canvas-scene-distillation", "includeOriginalPhoto": false, "focus": "single visual metaphor"},
    "text": {"enabled": false}
  },
  "controls": {"photoPreservation": "none", "semanticFidelity": "high", "abstraction": "high", "identityAnchors": "2-4", "metaphorCount": 1, "negativeSpace": "high", "aspectRatio": "source-adaptive"},
  "providerParameters": {},
  "maintainerNotes": "与实景拼贴分开建档，强调独立重绘。来源项目公开许可限制非商业用途；此配置为独立摘要，不复用其提示词或作品。"
}
```
