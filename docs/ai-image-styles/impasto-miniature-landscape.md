# 立体厚涂·微缩风景

```image-style-json
{
  "id": "impasto-miniature-landscape",
  "slug": "impasto-miniature-landscape",
  "name": "立体厚涂·微缩风景",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "把原图场景转成明亮、有雕塑体积感的厚涂油彩微缩画。",
  "status": "active",
  "version": "1.1.0",
  "sortOrder": 30,
  "promptTemplate": "参考输入照片，制作一幅具有真实手工堆塑体积感的微缩场景厚涂作品。严格保留原图主体身份、数量、关键轮廓、空间顺序、观察视角和主要构图；不删减或挪动火车、建筑、桥梁、道路、车辆等可识别主体。画面呈现为放在暖白纸面上的小型立体绘画/浅浮雕：主体与前景分层隆起，边缘可见不规则颜料堆叠，侧向柔光投下真实短阴影，局部可见刮刀纹与厚颜料脊；体积效果来自颜料和层次，不是塑料模型或3D渲染。仅在主体和少量光影处使用厚涂，背景笔触概括，保留清晰留白边缘。颜色从原图提取并适度增强，不改变原场景冷暖关系。场景重点：{{scene_description}}。不添加文字、标签或新物体。",
  "negativePrompt": "不要改变主体身份、数量、空间顺序或主要构图，不要删掉小型主体或替换场景；不要变成普通平面油画、全幅密集颜料覆盖、塑料玩具、树脂微缩模型、游戏CG或照片拼贴；不要新增道具、装饰、文字、标题、标牌、边框、水印；避免强行弯曲地面、改变道路/桥梁形状、糖果色、霓虹和浑浊暗色滤镜。",
  "rules": {
    "subjectPreservation": {
      "priority": "high",
      "mustPreserve": [
        "主体身份和数量",
        "主体标志性轮廓",
        "空间顺序与主要构图",
        "原始观察视角"
      ],
      "allowSimplification": [
        "微小表面纹理",
        "无关背景细节"
      ],
      "noInventedObjects": true
    },
    "rendering": {
      "medium": "有真实堆叠颜料的厚涂浅浮雕",
      "surface": [
        "刮刀纹",
        "堆叠颜料脊",
        "可见侧边与短投影"
      ],
      "volume": "颜料层和柔和投影形成微缩体积感，不做塑料CG",
      "paintDistribution": "主体局部隆起，背景克制，边缘留白"
    },
    "color": {
      "sourceAdaptive": true,
      "brightness": "medium-high",
      "clarity": "high",
      "avoidForcedColors": true
    },
    "layout": {
      "type": "sculptural-miniature-scene-on-paper",
      "preserveSourceComposition": true,
      "includeOriginalPhoto": false
    },
    "text": {
      "enabled": false
    }
  },
  "controls": {
    "subjectPreservation": "high",
    "compositionPreservation": "high",
    "styleIntensity": "high",
    "impastoRelief": "strong-visible",
    "layerDepth": "visible",
    "castShadow": "soft-short",
    "paintCoverage": "selective",
    "colorVividness": "source-adaptive",
    "negativeSpace": "visible-paper-margin",
    "aspectRatio": "source"
  },
  "providerParameters": {},
  "maintainerNotes": "依据 IMG_1276 测试结果：厚涂油画质感和主体构图已成立，但微缩立体感偏弱。本轮强调颜料隆起、可见侧边、分层和投影，同时明确不改主体与空间结构；注意不同模型对“浅浮雕”执行度仍可能有限。"
}

```
