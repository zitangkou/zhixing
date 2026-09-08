from app.services.question_import import parse_questions_markdown

SAMPLE = """
## 第一部分：单选题（共50题）

**1. 《建议》指出，"十四五"时期我国发展历程的特征是：**
A. 平稳有序、持续向好
B. 极不寻常、极不平凡
C. 攻坚克难、砥砺奋进
D. 开拓创新、成就卓著

> **答案：B**
> **原文依据：** 首句定性

**2. 《建议》将"十五五"时期定位为基本实现社会主义现代化（ ）的关键时期。**
A. 决战决胜、全力冲刺
B. 夯基垒台、立柱架梁
C. 夯实基础、全面发力
D. 承前启后、继往开来

> **答案：C**
> **原文依据：** "十五五时期……夯实基础、全面发力的关键时期"

## 第二部分：多选题（共50题）

**51. 《建议》指出，"十四五"时期我国发展取得重大成就，包括：**
A. 新质生产力稳步发展
B. 脱贫攻坚成果巩固拓展
C. 绿色低碳转型步伐加快
D. 国家完全统一大业完成

> **答案：ABC**
> **解析：** D项为陷阱，国家完全统一尚未完成
> **原文依据：** 四项均为原文成就表述
"""


def test_parse_sample():
    qs, errs = parse_questions_markdown(SAMPLE)
    assert len(errs) == 0
    assert len(qs) == 3
    assert qs[0]["type"] == "single"
    assert qs[0]["correct_answer"] == "极不寻常、极不平凡"
    assert qs[0]["source_sentence"] == "首句定性"
    assert qs[0]["analysis"] == "首句定性"
    assert qs[1]["correct_answer"] == "夯实基础、全面发力"
    assert qs[1]["source_sentence"].startswith("十五五时期")
    assert qs[2]["type"] == "multiple"
    assert len(qs[2]["correct_answer"]) == 3
    assert qs[2]["analysis"] == "D项为陷阱，国家完全统一尚未完成"
    assert qs[2]["source_sentence"] == "四项均为原文成就表述"


def test_parse_gov_report_format():
    """2026 政府工作报告题库：冒号在加粗外的 **原文依据**："…" """
    text = """
**1. 测试题**
A. 甲
B. 乙
C. 丙
D. 丁

> **答案：C**
> **原文依据**："我们隆重纪念中国人民抗日战争暨世界反法西斯战争胜利80周年，设立台湾光复纪念日。"
> **技巧点拨：** A、B、D均为已有纪念日。
"""
    qs, errs = parse_questions_markdown(text)
    assert len(errs) == 0
    assert qs[0]["source_sentence"].startswith("我们隆重纪念")
    assert qs[0]["analysis"] == "A、B、D均为已有纪念日。"


def test_parse_with_trailing_stars():
    text = """
**1. 测试题**
A. 甲
B. 乙
C. 丙
D. 丁

> **答案：A**
> **原文依据：** 原文摘录**
> **解析：** 解析内容**
"""
    qs, errs = parse_questions_markdown(text)
    assert len(errs) == 0
    assert qs[0]["source_sentence"] == "原文摘录"
    assert qs[0]["analysis"] == "解析内容"
