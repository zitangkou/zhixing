# 单双色印刷·编辑海报

```image-style-json
{
  "id": "mono-color-editorial-print",
  "slug": "mono-color-editorial-print",
  "name": "单双色印刷·编辑海报",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "把照片转成受控单色或双色油墨印刷风的编辑画页。",
  "status": "draft",
  "version": "1.0.0",
  "sortOrder": 100,
  "promptTemplate": "将输入照片转译为一张现代编辑印刷风海报。先选择一个主体和一处视觉事件，再从原图关系中提取两到四个辨识锚点；保留主体可辨认性，但用版画色块、清晰网点或干净套色重新组织，不做简单模糊滤镜。全画面最多使用两种油墨色和一种纸张底色：一色承担主体结构与节奏，另一色只强调一处重点。留出大块未印纸白，构图非对称、重心明确；照片可被局部裁切或简化，但不可替换主体。可用细网点、轻微套印偏差或纸纤维表达印刷材料，现代清洁效果优先。场景重点：{{scene_description}}。不要生成未经提供的事实、日期、地名或品牌文字；默认不加字。",
  "negativePrompt": "不要超出两色油墨限制，不要无目的地叠色；不要把抽象误做成模糊或低清照片；不要丢失全部主体识别线索；避免强烈做旧、脏污纸张、过量噪点、满版填色、亮面渐变、广告常规模板、错误文字、商标和水印。",
  "rules": {
    "subjectPreservation": {"priority": "high", "mustPreserve": ["主体身份线索", "关键结构和方向", "主要空间关系"], "allowSimplification": ["照片材质细节", "次要背景"], "noInventedObjects": true},
    "rendering": {"medium": "单色或双色平版/网点印刷", "inkLimit": 2, "substrate": "根据原图与色彩选择白、冷灰或浅米纸", "imperfections": "现代风格轻微或不使用"},
    "color": {"dominantInkRole": "主体结构和节奏", "accentInkRole": "单一强调", "paperAsNegativeSpace": true},
    "layout": {"type": "asymmetric-editorial-print", "negativeSpace": "35%-55%", "includeOriginalPhoto": false}
  },
  "controls": {"inkCount": 2, "dominantInkShare": "70%-85%", "accentInkShare": "15%-30%", "halftone": "subject-adaptive", "paperSpace": "35%-55%", "printImperfection": "0-2 subtle", "text": "off-by-default", "aspectRatio": "3:4"},
  "providerParameters": {},
  "maintainerNotes": "借鉴单双色印刷的通用工艺控制理念，使用本项目自己的描述与色彩策略。源项目 MIT；不要直接复制其色彩目录、版式目录或完整 recipe。"
}
```
