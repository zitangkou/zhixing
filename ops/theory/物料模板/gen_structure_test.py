#!/usr/bin/env python3
"""按「文章转MD结构化文档经验总结」将《十五五规划建议》原文转为两份测试产物：
  1) 结构化 MD（三章结构 + 原文引用块 + 每节【关键词】）
  2) 结构化 HTML（参考 zhixing 三刀解剖 displayHtml 排版样式，红白卡片风）
输入：物料模板/结构化文章/十五五规划建议-框架结构版.md（原文已逐字保留）
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent  # 物料模板
SRC = BASE / "结构化文章/十五五规划建议-框架结构版.md"
OUT_MD = BASE / "结构化文章/十五五规划建议-结构化MD.md"
OUT_HTML = BASE / "结构化文章/十五五规划建议-结构化HTML.html"

# 每节关键词（记忆锚点，3-8 个，/ 分隔）
KEYWORDS = {
    "一": "极不寻常、极不平凡 / 经济运行稳中有进 / 高质量发展扎实推进 / 根本在于…领航掌舵、科学指引 / 中国式现代化迈出新的坚实步伐",
    "二": "承前启后 / 阶梯式递进 / 夯实基础、全面发力 / 战略主动 / 重大突破",
    "三": "战略机遇和风险挑战并存 / 世界百年变局 / 制度、市场、产业、人才四大优势 / 发展不平衡不充分 / 长期向好",
    "四": "两个确立 / 四个意识 / 四个自信 / 两个维护 / 战略定力 / 历史主动精神 / 两大奇迹",
    "五": "五位一体 / 四个全面 / 新发展理念 / 新发展格局 / 稳中求进 / 以经济建设为中心 / 高质量发展为主题 / 全面从严治党为根本保障",
    "六": "坚持党的全面领导 / 坚持人民至上 / 坚持高质量发展 / 坚持全面深化改革 / 有效市场和有为政府相结合 / 统筹发展和安全",
    "七": "高质量发展取得显著成效 / 科技自立自强 / 人民生活品质不断提高 / 美丽中国 / 国家安全屏障 / 2035年基本实现社会主义现代化",
    "八": "现代化产业体系 / 制造强国、质量强国、航天强国、交通强国、网络强国 / 优化提升传统产业 / 培育壮大新兴产业和未来产业 / 量子科技、生物制造、氢能和核聚变能、脑机接口、具身智能、第六代移动通信",
    "九": "新型举国体制 / 集成电路、工业母机、高端仪器 / 原始创新 / 企业科技创新主体 / 教育科技人才一体推进 / 数字中国 / 人工智能+",
    "十": "扩大内需战略基点 / 大力提振消费 / 扩大有效投资 / 全国统一大市场 / 内卷式竞争",
    "十一": "两个毫不动摇 / 民营经济促进法 / 要素市场化配置 / 宏观经济治理 / 零基预算改革 / 金融强国",
    "十二": "制度型开放 / 自由贸易试验区 / 海南自由贸易港 / 贸易强国 / 人民币国际化 / 一带一路",
    "十三": "三农 / 千亿斤粮食产能提升行动 / 耕地红线 / 千万工程 / 宜居宜业和美乡村 / 常态化防止返贫致贫",
    "十四": "四大区域战略 / 京津冀、长三角、粤港澳大湾区 / 长江经济带、黄河流域 / 雄安新区 / 以人为本的新型城镇化 / 海洋强国",
    "十五": "文化强国 / 社会主义核心价值观 / 文化事业 / 文化产业 / 中华优秀传统文化传承发展工程 / 体育强国",
    "十六": "就业优先 / 收入分配 / 办好人民满意的教育 / 社会保障体系 / 房地产发展新模式 / 健康中国 / 人口高质量发展 / 基本公共服务均等化",
    "十七": "绿水青山就是金山银山 / 碳达峰碳中和 / 蓝天碧水净土保卫战 / 新型能源体系 / 三北工程 / 绿色生产生活方式",
    "十八": "总体国家安全观 / 平安中国 / 新兴领域安全 / 公共安全治理 / 枫桥经验 / 社会治理体系",
    "十九": "习近平强军思想 / 新三步走 / 政治建军、改革强军、科技强军、人才强军、依法治军 / 新域新质作战力量 / 一体化国家战略体系和能力",
    "二十": "党的自我革命 / 全面从严治党 / 民主集中制 / 中央八项规定精神 / 不敢腐、不能腐、不想腐 / 全过程人民民主 / 全面依法治国",
    "二十一": "一国两制 / 爱国者治港、爱国者治澳 / 两岸关系和平发展 / 台独 / 人类命运共同体 / 全球发展、安全、文明、治理倡议",
    "二十二": "国家规划体系 / 监测评估 / 尊重劳动、尊重知识、尊重人才、尊重创造 / 基本实现社会主义现代化 / 强国建设、民族复兴",
}

CN = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
      "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十", "二十一", "二十二"]


def parse_src():
    """解析框架结构版 md → [(章标题, [(节标题, [引用行], 节序数字符串), ...]), ...]"""
    chapters = []
    cur_ch = None
    cur_sec = None
    for raw in SRC.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("## "):
            if cur_sec:
                cur_ch[1].append(cur_sec)
                cur_sec = None
            if cur_ch:
                chapters.append(cur_ch)
            cur_ch = [line[3:].strip(), []]
        elif line.startswith("### "):
            if cur_sec:
                cur_ch[1].append(cur_sec)
            m = re.match(r"### 第([\u4e00-\u9fff]+)节\s*(.*)", line)
            cur_sec = [m.group(2) if m else line[4:].strip(), [], m.group(1) if m else ""]
        elif line.startswith(">") and cur_sec:
            cur_sec[1].append(line[1:].strip())
    if cur_sec:
        cur_ch[1].append(cur_sec)
    if cur_ch:
        chapters.append(cur_ch)
    return chapters


def to_md(chapters):
    lines = ["# 《十五五规划建议》全文（三章结构·关键词版）", "",
             "> 来源：《中共中央关于制定国民经济和社会发展第十五个五年规划的建议》",
             "> 日期：2025年10月23日中国共产党第二十届中央委员会第四次全体会议通过", ""]
    for ch_title, secs in chapters:
        lines += ["## 第一章" if False else f"## {ch_title}", ""]
        for sec_title, quotes, num in secs:
            lines.append(f"### 第{num}节 {sec_title}")
            lines.append("")
            for q in quotes:
                lines.append(f"> {q}" if not q.startswith(">") else q)
            lines.append("")
            lines.append(f"**【关键词】** {KEYWORDS.get(num, '')}")
            lines.append("")
    return "\n".join(lines)


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def q_to_html(q: str) -> str:
    """引用块内 **小节名** → 红色加粗 span"""
    parts = re.split(r"(\*\*.+?\*\*)", q)
    out = []
    for p in parts:
        if p.startswith("**") and p.endswith("**") and len(p) > 4:
            out.append(f'<b style="color:#D0021B;">{esc(p[2:-2])}</b>')
        else:
            out.append(esc(p))
    return "".join(out)


def to_html(chapters):
    h = []
    h.append('<div style="max-width:680px;margin:0 auto;padding:20px;background:#FFFFFF;font-family:-apple-system,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;color:#333;box-sizing:border-box;">')

    # 报头（对齐三刀解剖样本）
    h.append('<div style="text-align:center;border-bottom:3px solid #D0021B;padding-bottom:12px;margin-bottom:20px;">')
    h.append('<div style="font-size:12px;color:#D0021B;letter-spacing:6px;margin-bottom:4px;">人民时评 · 精读系列</div>')
    h.append('<div style="font-size:28px;font-weight:bold;color:#D0021B;letter-spacing:2px;">政策理论精读</div>')
    h.append('<div style="font-size:12px;color:#999;margin-top:6px;">中共中央文件 · 三章结构精读</div>')
    h.append('</div>')

    # 开篇引导卡（对齐三刀解剖样本：浅红底 + 左侧红条）
    h.append('<div style="background:#FFF5F6;padding:15px;border-radius:8px;border-left:4px solid #D0021B;margin-bottom:20px;">')
    h.append('<p style="margin:0;font-size:14px;color:#4A4A4A;line-height:1.7;">')
    h.append('<b>【文件精读】《十五五规划建议》</b><br />')
    h.append('通过：2025年10月23日二十届四中全会<br />')
    h.append('结构：三章（总论 / 分论 / 保障）· 22 节 · 原文逐字保留<br />')
    h.append('<a style="color:#D0021B;text-decoration:none;">📄 来源：新华社受权发布（人民日报 2025年10月24日头版）</a>')
    h.append('</p></div>')

    for ch_title, secs in chapters:
        # 章标题（对齐三刀 h2：红字 + 下划线）
        h.append(f'<h2 style="color:#D0021B;font-size:18px;border-bottom:2px solid #D0021B;padding-bottom:8px;margin:20px 0 10px;">{esc(ch_title)}</h2>')
        for sec_title, quotes, num in secs:
            # 节标题：红徽章 + 标题
            h.append('<div style="display:flex;align-items:center;gap:8px;margin:14px 0 8px;">')
            h.append(f'<span style="display:inline-block;background:#D0021B;color:#fff;font-size:12px;border-radius:10px;padding:2px 10px;flex-shrink:0;">第{esc(num)}节</span>')
            h.append(f'<span style="font-size:15px;font-weight:600;color:#1A1B1C;line-height:1.5;">{esc(sec_title)}</span>')
            h.append('</div>')
            # 原文引用：整节合并为一张连续灰卡，段间紧凑（消除多小节节"每段一张卡"造成的空行感）
            h.append('<div style="background:#F8F8F8;border-radius:8px;padding:12px 14px;margin-bottom:6px;font-size:14px;line-height:1.9;color:#333;">')
            for qi, q in enumerate(quotes):
                mb = "10px" if qi < len(quotes) - 1 else "0"
                h.append(f'<p style="margin:0 0 {mb};">{q_to_html(q)}</p>')
            h.append('</div>')
            # 关键词：浅红底紧凑卡 + 文本流（统一协调，避免长短标签参差）
            kw = KEYWORDS.get(num, "")
            if kw:
                items = [k.strip() for k in kw.split("/") if k.strip()]
                h.append('<div style="background:#FFF5F6;border-radius:8px;padding:8px 12px;margin:8px 0 14px;line-height:1.9;">')
                h.append('<b style="color:#D0021B;font-size:12px;">关键词</b>')
                h.append(f'<span style="font-size:13px;color:#4A4A4A;margin-left:8px;">{" · ".join(esc(k) for k in items)}</span>')
                h.append('</div>')

    h.append('</div>')
    return "\n".join(h)


def main():
    chapters = parse_src()
    total_secs = sum(len(s) for _, s in chapters)
    assert total_secs == 22, f"节数异常: {total_secs}"

    md = to_md(chapters)
    OUT_MD.write_text(md, encoding="utf-8")

    html = to_html(chapters)
    OUT_HTML.write_text(html, encoding="utf-8")

    print(f"✅ 章数: {len(chapters)} | 节数: {total_secs} | 关键词块: {sum(1 for _,s in chapters for _ in s)}")
    print(f"   MD  : {OUT_MD} ({len(md)} 字符)")
    print(f"   HTML: {OUT_HTML} ({len(html)} 字符)")


if __name__ == "__main__":
    main()
