from pathlib import Path

from app.services.article_import import parse_article_markdown

LEGACY_SAMPLE = Path(__file__).resolve().parent / "fixtures" / "shiwuwu-structure-sample.md"
CHAPTER_SAMPLE = Path(__file__).resolve().parent / "fixtures" / "shiwuwu-chapter-sample.md"


def test_parse_chapter_section_format():
    text = CHAPTER_SAMPLE.read_text(encoding="utf-8")
    result, _warnings = parse_article_markdown(text)
    assert "十五五" in result["title"]
    assert result["stats"]["chapters"] >= 2
    assert result["stats"]["sections"] >= 5
    assert result["stats"]["paragraphs"] >= 1

    chapter = result["sections"][0]
    assert chapter["level"] == 1
    assert "第一章" in chapter["title"]
    assert chapter.get("children")

    section = chapter["children"][0]
    assert section["level"] == 2
    assert "第一节" in section["title"]
    assert section.get("content")

    # 第六节：多条加粗原则 → level-3 段
    sec6 = next(s for s in chapter["children"] if "第六节" in s["title"])
    assert sec6.get("children")
    assert sec6["children"][0]["level"] == 3
    assert "坚持党的全面领导" in sec6["children"][0]["title"]


def test_parse_legacy_part_format_remapped():
    text = LEGACY_SAMPLE.read_text(encoding="utf-8")
    result, warnings = parse_article_markdown(text)
    assert any("编-章-节" in w for w in warnings)
    assert result["stats"]["chapters"] >= 1
    assert result["sections"][0]["level"] == 1
    assert result["sections"][0]["children"][0]["level"] == 2


def test_chapter_title_from_heading():
    md = """# 测试文

## 第二章 分论：重大战略任务部署

### 第八节 现代化产业体系是中国式现代化的物质技术基础

> 现代化产业体系是中国式现代化的物质技术基础。坚持把发展经济的着力点放在实体经济上。
>
> **优化提升传统产业。** 推动重点产业提质升级。
"""
    result, _ = parse_article_markdown(md)
    chapter = result["sections"][0]
    assert chapter["level"] == 1
    assert "第二章" in chapter["title"]

    section = chapter["children"][0]
    assert section["level"] == 2
    assert "第八节" in section["title"]
    assert section.get("content")
    assert section.get("children")
    assert section["children"][0]["level"] == 3
