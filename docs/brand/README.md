# 知行 · 品牌资产

> 小程序矩阵的 Logo、头像成品与品牌文案定稿。改图先看这里，不要重新生成。

## 目录

```
docs/brand/
├── avatars/            小程序头像成品（品牌红 #D0021B，无水印）
│   ├── rizhi/          知行日知（政治理论）
│   ├── celun/          知行策论（申论）
│   ├── mingbian/       知行明辨（判断推理，预留）
│   │   ├── 144.png       ← 上传微信后台用这一张（144×144，PNG，约 8KB）
│   │   ├── 512.png       应用内/分享图
│   │   ├── 1024.png      高分辨率母档
│   │   └── circle-preview.png  圆形裁切自检图（仅预览，勿上传）
│   └── family-lineup.png  三枚并排的 144px 实拍尺寸
├── scripts/
│   └── seal_pipeline.py   成品流水线（居中 → 圆形安全补底 → 转品牌红 → 多尺寸导出）
├── logo-design-proposal.md  设计方案（印章/书卷风 + 统一品牌红）
├── canva-production-spec.md Canva 制作规格单（画布/配色/版式参数）
├── naming.md              「知行」系列命名候选与低撞车策略
├── product-copy.md        小程序名称/简介/标签文案（个人主体口径）
└── legal-draft.md         用户协议与隐私政策草稿 + 微信后台勾选映射表
```

## 设计要点

- **风格**：中式方章印章，模板底稿为 Canva「灰褐色文艺中国风通用微信公众号Logo」；
- **配色**：统一品牌红 `#D0021B`（真值源 `src/constants/theme.ts`），印面文字反白；
- **圆形安全**：头像按内切圆 90% 安全边距补底，微信圆形裁切不切框、不切字；
- **成对性**：各枚仅印面单字不同（日知→「知」、策论→「策」、明辨→「辨」），版式与尺寸完全一致。

## 重新生成 / 新增一枚

```bash
# 1) 在 Canva 复制模板，改印面字与标题，导出 1000×1000 PNG
# 2) 本地跑流水线（自动居中、补圆形安全区、珊瑚红→品牌红、出三档尺寸）
python3 -m venv .logotool-venv && .logotool-venv/bin/pip install pillow
.logotool-venv/bin/python docs/brand/scripts/seal_pipeline.py \
  <导出的png> <前缀> --out docs/brand/avatars/<产品目录>
```

模板参数（500×500 页面）：印章放大取 `height=260`（300 会顶出画布上沿），印面字 `width=180 / font_size=135`。注意 Canva 插件**无法移动嵌套图片元素、不能改字体族**，所以居中和换色一律交给脚本。

## 待办

- 印面目前是模板自带的现代宋体而非篆书。要换真篆书需在 Canva 手动改字体（Pro 可上传「汉鼎篆体」等免费商用字体）后重新导出。
- `mingbian`（知行明辨）为矩阵预留，尚无对应应用工程。
