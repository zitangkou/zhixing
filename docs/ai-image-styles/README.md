# AI 百宝箱图片风格初始配置

这组配置参考公开的图片风格工作流说明，重新编写为本项目可维护的风格提示词和规则；没有安装或调用外部 skill，也没有复制其完整提示词。Markdown 文件与后台配置一一对应，可在“工具配置 → 图片配置”中导入。

## 当前本地配置

后台目前保留原有“旅行手账·清透淡彩”、四种已复核风格，以及一条新建的草稿“钢笔淡彩·漫游手账”。新草稿不会下发到小程序，可在管理后台直接上传原图测试。其余探索风格已从后台配置清理；相应 Markdown 文件只作为未启用的研究记录。

| 配置文件 | 当前风格名称 | 本轮观察与优化方向 |
|---|---|---|
| `color-doodle-panels.md` | 彩色涂鸦·场景速写 | 成图是彩铅/蜡笔全景速写，没有分格；强化主体、构图和禁止新增对象。 |
| `photo-zine-postcard.md` | 拾色明信片·照片与手绘 | 照片+明信片版式辨识度高；下方仅保留一个局部手绘母题，避免重复缩绘全景。 |
| `impasto-miniature-landscape.md` | 立体厚涂·微缩风景 | 油彩厚涂成立，微缩立体感偏弱；强化颜料隆起、分层、侧边与柔和投影。 |
| `watercolor-travel-card.md` | 旅行档案·穿孔水彩卡 | 穿孔侧栏辨识度良好；强化空白档案栏与细节概括，和原有淡彩风格拉开距离。 |
| `penwash-travel-journal.md` | 钢笔淡彩·漫游手账 | 新增草稿：原比例、细黑钢笔、水彩自然融边、适配明暗的外围底色、四枚取自原图的纯色色卡和底部英文手写标题/短句。与原淡彩同属水彩媒介，区别聚焦在钢笔线、无分隔融边、色卡和文字版式。 |

新增测试风格使用 `seedream-50-flash`。`providerParameters` 只填写经过模型实测的服务参数；风格提示词和 `controls` 是语义规则，不等于服务商 API 参数。文档更新后，需在本地后台重新导入对应 Markdown 才会更新数据库；生产环境需单独部署/配置。

## 来源与使用边界

- `photo-to-poster-skills`：https://github.com/GZ-L/photo-to-poster-skills
- `photo-to-zine-postcard`：https://github.com/Whiplashzeb/photo-to-zine-postcard
- `gathered-scenes-zine-skill`：https://github.com/Zeejay0/gathered-scenes-zine-skill
- `photo-abstract-editorial`：https://github.com/ZzzLc0405/photo-abstract-editorial
- `photo-relic-editorial`：https://github.com/wnby/photo-relic-editorial
- `heytea-style`：https://github.com/Hchen1218/heytea-style
- `mono-color-skill`：https://github.com/yanliudesign/mono-color-skill

这些配置借鉴的是可观察到的视觉方向与工作流，不将原作者的完整 skill 文本、专有名称或样例作品作为产品资产。已公开说明限制个人非商业用途的来源（例如 Gathered Scenes Zine 与 Photo Abstract Editorial）仅作概念研究；商业上线前需再次核对原项目许可证，并避免复用受限制的表达和素材。

`xxd-panel-115` 暂未找到可核验的公开定义；当前“彩色涂鸦·场景速写”基于实际测试成图重新归纳规则，不再使用“分格画页”的命名。
