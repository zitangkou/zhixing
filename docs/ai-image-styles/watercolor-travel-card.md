# 旅行档案·穿孔水彩卡

基于“照片转旅行档案卡”的视觉方向独立编写。全画布重新绘制，不把原照片拼进成品。

```image-style-json
{
  "id": "watercolor-travel-card",
  "slug": "watercolor-travel-card",
  "name": "旅行档案·穿孔水彩卡",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "将照片重绘为带穿孔档案栏的清透水彩旅行记忆卡。",
  "status": "active",
  "version": "1.1.0",
  "sortOrder": 20,
  "promptTemplate": "把参考照片重新创作为一张竖版旅行档案记忆卡，整张成品都使用绘画表现，不嵌入原始照片。保留原图的观察视角、主体数量、主要轮廓和空间关系，但将窗格、栏杆等重复细节明显概括，呈现轻盈、透明、松弛的水彩写生。主体场景仅占左侧约68%区域；右侧约32%为贯穿全高的独立温润象牙白档案栏，与画面之间用一列均匀小圆孔清楚分隔。右栏只保留空白标题线和空白记录区域，不生成任何文字、地名、日期、编号或坐标。纸张纹理极轻，保留明显纸白和柔和水彩边缘；颜色只从原图提取，不统一泛黄。场景观察：{{scene_description}}。成品必须首先读作一张带穿孔侧栏的档案卡，而非普通整幅水彩风景画。",
  "negativePrompt": "不要嵌入原始照片，不要拼贴或前后对照；不要改变、增删、替换主要主体；禁止在档案栏生成标题、地名、日期、编号、坐标、签名、条码、二维码或乱码，档案栏保持空白；不要省略右侧独立栏或穿孔分隔；避免整幅无版式水彩、过密建筑线条、卡通、儿童绘本、厚重水粉、油画堆叠、塑料三维、数码矢量感、强黄滤镜、贴纸边框和水印。",
  "rules": {
    "subjectPreservation": {
      "priority": "high",
      "mustPreserve": [
        "主体身份和数量",
        "主要轮廓和方向",
        "关键空间关系和观察视角"
      ],
      "allowSimplification": [
        "微小纹理",
        "重复窗格",
        "细小栏杆",
        "远景杂物"
      ],
      "noInventedObjects": true
    },
    "rendering": {
      "medium": "透明、低对比水彩与少量细线",
      "paper": "象牙白纸面，纸纹极轻",
      "edge": "主体水彩柔和收边，档案栏保持干净",
      "detail": "重复细节大幅概括，主体可辨"
    },
    "layout": {
      "type": "vertical-archive-card-with-perforated-sidebar",
      "sceneArea": "68% left",
      "archiveColumn": "32% full-height right",
      "separator": "visible uniform perforation row",
      "includeOriginalPhoto": false
    },
    "text": {
      "enabled": false,
      "archiveFields": "blank"
    }
  },
  "controls": {
    "subjectPreservation": "high",
    "compositionPreservation": "high",
    "styleIntensity": "medium",
    "detailSimplification": "high",
    "watercolorTransparency": "high",
    "paperTexture": "very-subtle",
    "archiveLayout": "strong-visible-right-sidebar",
    "archiveText": "blank",
    "palette": "source-sampled-limited",
    "aspectRatio": "3:4"
  },
  "providerParameters": {},
  "maintainerNotes": "依据 IMG_1276 测试结果：穿孔侧栏、纵向档案卡版式执行良好，但水彩媒介与原有“旅行手账·清透淡彩”重叠。本轮不改原风格，而是强化本款的全高穿孔侧栏、空白档案字段和明显细节概括，使区分点落在版式与信息组织，而非仅靠水彩质感。"
}

```
