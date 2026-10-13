# 纸上留影·记忆版画

```image-style-json
{
  "id": "photo-relic-editorial",
  "slug": "photo-relic-editorial",
  "name": "纸上留影·记忆版画",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "真实照片搭配由原图结构、光线和色彩提炼出的克制纸上版画。",
  "status": "draft",
  "version": "1.0.0",
  "sortOrder": 80,
  "promptTemplate": "制作一页安静的照片记忆版画。上方或主区域保留真实照片作为事实记录，不重新绘制照片；下方温白纸面呈现从照片提炼的一枚可识别图形。先观察主体轮廓、光线逻辑、负空间、颜色关系和视觉重心，再用少量平面墨色块、断续边缘、留白切口和轻微印刷不均来概括它。图形需保留足以辨认主体的结构，不退化成无关色块；建筑要保留屋顶/主体块面与基座关系，水岸和道路要有稳定的水平或路径线索。主色从照片取样，以冷灰、墨蓝、石色或低饱和绿为基底，只有原图支持时才加入一处暖色。留白充足，标题可不出现。场景重点：{{scene_description}}。禁止虚构地点、编号和说明文字。",
  "negativePrompt": "不要重绘照片区域，不要让版画遮盖照片主体；不要把版画简化到无法识别，不要添加无关几何装饰；避免强渐变、广告式标题、厚重水彩、仿旧污渍、贴纸拼贴、UI元素、文字乱码、商标和水印。",
  "rules": {
    "subjectPreservation": {"priority": "strict-for-photo-semantic-for-print", "mustPreserve": ["真实照片内容", "版画主形身份", "照片中主体关系与光线方向"], "noInventedObjects": true},
    "rendering": {"photo": "真实、未经改绘", "print": "平面油墨形、破边、留白切口", "paper": "干净温白", "marks": "一个主形加少数辅助线"},
    "color": {"deriveFromSource": true, "inkCount": "limited", "warmAccent": "only-if-source-supports"},
    "layout": {"type": "photo-over-memory-print", "includeOriginalPhoto": true, "negativeSpace": "generous"}
  },
  "controls": {"photoPreservation": "strict", "printAbstraction": "medium-high", "recognizability": "high", "inkCoverage": "low", "imperfection": "subtle", "negativeSpace": "high", "aspectRatio": "portrait-editorial"},
  "providerParameters": {},
  "maintainerNotes": "参考开源项目的纸面记忆版画方向，概念上重新组织；项目许可证为 MIT。此风格与抽象面板区别在于保留主体识别轮廓而非纯抽象关系。"
}
```
