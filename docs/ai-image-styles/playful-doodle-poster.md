# 趣味涂鸦·物件海报

```image-style-json
{
  "id": "playful-doodle-poster",
  "slug": "playful-doodle-poster",
  "name": "趣味涂鸦·物件海报",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "让照片中的真实物件成为主角，辅以轻松的黑线小人涂鸦叙事。",
  "status": "draft",
  "version": "1.0.0",
  "sortOrder": 90,
  "promptTemplate": "把生活或产品照片设计成一张轻松、有手作感的竖版涂鸦海报。真实照片中的核心物件保持原样、清晰且比例可信，作为画面主角；只在周围留白处加入少量黑色手绘线条和极简小人物，让小人通过攀爬、搬运、观察或互动讲出一个简单动作故事。线条稚拙但干净，角色尺寸远小于主体，动作关系一眼可读。背景尽量留白，最多使用一两种从主体提取的轻快点缀色。可选短标题区域默认留空，避免生成乱码；不使用任何真实品牌名或商标。场景重点：{{scene_description}}。",
  "negativePrompt": "不要改变照片主体的外观、包装、标签、颜色和比例；不要遮住商品关键区域，不要生成品牌标志或仿冒商标；避免复杂人物、写实人脸、过多小人、厚重插画覆盖、满版彩色背景、促销价签、乱码文字、水印和二维码。",
  "rules": {
    "subjectPreservation": {"priority": "strict-for-photo-object", "mustPreserve": ["主物件外观与比例", "标签和可读原始标记", "主体摆放位置"], "noInventedObjects": true},
    "rendering": {"photo": "保留真实物件", "doodle": "黑色简笔线条与小比例人物", "story": "单一易读互动", "accentColorCount": 2},
    "layout": {"type": "object-anchored-doodle-poster", "includeOriginalPhoto": true, "negativeSpace": "high"},
    "text": {"enabled": false, "brandNames": false}
  },
  "controls": {"photoObjectPreservation": "strict", "doodleDensity": "low", "characterScale": "tiny", "narrativeActionCount": 1, "lineStyle": "rough-clean-black-pen", "accentColors": "1-2 source-derived", "aspectRatio": "3:4"},
  "providerParameters": {},
  "maintainerNotes": "将特定品牌联想抽象成通用物件涂鸦风格，不复用品牌素材或官方标识；开源来源标注 MIT，但品牌商标仍应避免。"
}
```
