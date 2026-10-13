# 彩色涂鸦·场景速写

此风格依据用户提供的实际生成结果校准。当前成图呈现彩铅/蜡笔全景场景速写，没有分格，因此名称和规则已调整为场景速写；不复刻或依赖外部 skill 原文。

```image-style-json
{
  "id": "color-doodle-panels",
  "slug": "color-doodle-panels",
  "name": "彩色涂鸦·场景速写",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "将原图转成彩铅与蜡笔质感的鲜活场景手绘，保留主要物体及原始空间关系。",
  "status": "active",
  "version": "0.2.0",
  "sortOrder": 110,
  "promptTemplate": "将参考照片完整转绘成一幅彩色铅笔与蜡笔质感的场景速写。严格沿用原照片的观察视角、画幅比例、地平线、主体数量、位置、大小关系和主要轮廓；先准确保留每个可识别主体，再用清晰略有手绘起伏的深色线条、可见的彩铅排线与蜡笔色块表现。色彩鲜明但取自原图，天空、建筑、道路等大色面有自然笔触，细小窗格和纹理适度概括。画面是单一连续场景，不做分格、拼贴、海报排版或局部重复。场景重点：{{scene_description}}。除非原图中确实存在，不得新增太阳、车辆、人物、文字或标志；不生成标题、水印和装饰符号。",
  "negativePrompt": "不要改变或遗漏原图中的火车/车辆、建筑、桥梁、道路等主要主体及其数量、位置和方向；不要新增原图没有的太阳、云、人物、车辆、树木、路牌或文字；不要分格、漫画格、拼贴、边框、标题、贴纸或装饰涂鸦；避免把画面做成幼儿涂色书、粗黑漫画描边、模糊色块、荧光色泛滥、过密乱线、照片写实、乱码和水印。",
  "rules": {
    "subjectPreservation": {
      "priority": "strict",
      "mustPreserve": [
        "主体身份与数量",
        "主体相对位置和比例",
        "关键轮廓与方向",
        "观察视角和原始画幅"
      ],
      "allowSimplification": [
        "重复窗格",
        "细小背景纹理"
      ],
      "noInventedObjects": true
    },
    "rendering": {
      "medium": "彩色铅笔与蜡笔场景速写",
      "lineQuality": "清楚、略有手绘起伏",
      "texture": "可见但克制的彩铅排线和蜡笔色块",
      "detailLevel": "主体清楚，微小纹理适度概括"
    },
    "color": {
      "sourceAdaptive": true,
      "saturation": "medium-high",
      "fluorescent": false
    },
    "layout": {
      "type": "single-continuous-scene-sketch",
      "preserveSourceAspectRatio": true,
      "panels": false,
      "includeOriginalPhoto": false
    },
    "text": {
      "enabled": false
    }
  },
  "controls": {
    "subjectPreservation": "strict",
    "compositionPreservation": "high",
    "styleIntensity": "medium-high",
    "coloredPencilTexture": "visible-controlled",
    "doodleDensity": "none",
    "palette": "source-inspired-vivid",
    "aspectRatio": "source"
  },
  "providerParameters": {},
  "maintainerNotes": "依据用户提供的 IMG_1276 测试成图复核：实际结果是构图保留度较高的彩铅/蜡笔全景速写，没有分格特征，因此名称调整为“场景速写”。本轮强化原图主体、画幅与禁止新增物体约束；需继续用不同类型原图验证。"
}

```
