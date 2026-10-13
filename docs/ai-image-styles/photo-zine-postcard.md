# 拾色明信片·照片与手绘

```image-style-json
{
  "id": "photo-zine-postcard",
  "slug": "photo-zine-postcard",
  "name": "拾色明信片·照片与手绘",
  "category": "image-to-image",
  "productKey": "general",
  "modelId": "seedream-50-flash",
  "description": "保留原照片主体，在纸面下方配一枚取材于原图的手绘图案与色卡。",
  "status": "active",
  "version": "1.1.0",
  "sortOrder": 40,
  "promptTemplate": "制作一张竖版旅行明信片正面。输入照片作为成品上方的真实影像区域，尽量完整保留原片内容与比例，不重绘、不替换照片中的主体。下方使用温和的暖白纸面，只安排一枚来自原照片的局部手绘母题：选择一个最具辨识度的局部主体或局部关系（例如火车车厢的一段轮廓，或桥梁与夕阳的一小段关系），以水彩、粉彩或细墨线简洁表现；不得把整张原场景再次缩画成第二幅完整风景。附近放置恰好三枚小色块，颜色取自原照片。画面像可印刷的小型独立刊物，轻手作、克制、整洁，照片区和手绘区边界清楚。场景重点：{{scene_description}}。不要猜测地点、日期和拍摄者；不生成文字，保留简洁空白标签区域。",
  "negativePrompt": "不要把照片裁掉、拉伸、重绘或替换，不要改变照片主体；下方只能有一个局部母题，禁止重复完整场景、全景缩略图、多个小插画或图标集合；不要凭空补地点、日期、作者、标题或说明文字；避免乱码、水印、二维码、真实邮票图案、厚重边框、繁杂贴纸和低分辨率照片。",
  "rules": {
    "subjectPreservation": {
      "priority": "strict-for-photo-region",
      "mustPreserve": [
        "照片内容真实性",
        "原始比例",
        "主体数量和位置"
      ],
      "noInventedObjects": true
    },
    "rendering": {
      "photoRegion": "保留真实照片",
      "motif": "单一局部、来源明确的手绘母题，不重复完整场景",
      "paper": "暖白细纸纹",
      "swatches": 3
    },
    "layout": {
      "type": "portrait-postcard-front",
      "photoPosition": "upper",
      "motifPosition": "lower",
      "motifScale": "localized-detail",
      "metadata": "minimal",
      "includeOriginalPhoto": true
    },
    "text": {
      "enabled": false,
      "reserveBlankLabelArea": true
    }
  },
  "controls": {
    "photoPreservation": "strict",
    "motifSourceFidelity": "high",
    "motifScope": "single-local-detail",
    "styleIntensity": "medium",
    "paperTexture": "subtle",
    "layoutDensity": "low",
    "swatchCount": 3,
    "aspectRatio": "2:3"
  },
  "providerParameters": {},
  "maintainerNotes": "依据 IMG_1276 测试结果：明信片版式和照片+手绘组合区分度高；优化重点是下方手绘仅保留一个局部母题，禁止重复缩绘整张场景。照片原样保留仍需用多种照片复核模型稳定性。"
}

```
