from app.services.shenlun_exercise_generation import _apply_semantic_review, quality_check


def _payload():
    excerpt = "完善基层服务体系，提升公共服务能力。" * 30
    answer = "完善基层服务体系，提升公共服务能力，并推动服务事项落实。"
    points = [{"point": "完善基层公共服务", "evidence": "完善基层服务体系，提升公共服务能力。"}]
    return {
        "question_type": "summary",
        "title": "概括完善基层公共服务的主要做法",
        "source_title": "基层公共服务实践",
        "source_url": "https://paper.people.com.cn/example.html",
        "source_excerpt": excerpt,
        "prompt": "请概括材料中完善基层公共服务的主要做法。",
        "requirements": "分条作答，概括准确，答案不超过200字。",
        "max_chars": 200,
        "key_points": points,
        "rubric": [
            {"name": "要点完整", "description": "完整覆盖主要要点"},
            {"name": "归纳准确", "description": "依据材料归纳"},
            {"name": "表达有条理", "description": "分条清晰"},
        ],
        "sample_answer": answer,
        "analysis": "先定位材料中的服务举措，再归并为完善基层公共服务。答题时应紧扣材料中的具体动作，避免扩展材料未提及的措施。接着检查题干要求的概括对象，筛选与对象直接相关的信息，合并重复内容并用简洁主旨句表达。复盘时可先在材料旁标注动作词，再将相近动作合并，并检查每个主旨句是否能回到对应原文。易错点是只摘录口号、照抄全文或补写材料没有提供的实施效果，导致答案偏离给定资料。",
    }


def _report():
    return {"pass": True, "score": 10, "errors": []}


def _review(**overrides):
    review = {
        "pass": True,
        "score": 9,
        "task_fits": True,
        "answer_faithful": True,
        "answer_within_limit": True,
        "analysis_faithful": True,
        "analysis_teaches": True,
        "key_points_granularity_ok": True,
        "point_checks": [{"point_index": 0, "supported": True, "quote": "完善基层服务体系，提升公共服务能力。", "reason": "原文明确说明了基层服务体系和公共服务能力之间的直接关系。"}],
        "answer_point_checks": [{"point_index": 0, "covered": True, "quote": "完善基层服务体系，提升公共服务能力", "reason": "答案保留了原文的服务对象和具体动作，没有扩大适用范围。"}],
        "findings": [],
        "suggestions": [],
    }
    review.update(overrides)
    return review


def test_material_outside_named_entities_block_even_when_marked_minor():
    payload = _payload()
    payload["analysis"] += " 易错点：把成都或深圳做法混入。"
    result = _apply_semantic_review(payload, _report(), _review(findings=[{
        "severity": "minor",
        "issue_type": "unsupported_named_entity",
        "dimension": "analysis_faithful",
        "target": "解析中的地名",
        "reason": "提到摘录之外的成都、深圳做法。",
        "quote": "成都或深圳做法混入",
    }]))
    assert result["pass"] is False
    assert result["semantic_review"]["blocking_findings"]


def test_answer_point_must_have_verifiable_coverage_quote():
    payload = _payload()
    result = _apply_semantic_review(payload, _report(), _review(answer_point_checks=[{
        "point_index": 0, "covered": True, "quote": "答案里不存在的句子",
    }]))
    assert result["pass"] is False
    assert any("答案覆盖引文无法逐字回查" in error for error in result["errors"])


def test_style_only_finding_can_pass_and_remains_visible():
    payload = _payload()
    payload["analysis"] += "表达可以更凝练。"
    findings = [{
        "severity": "minor",
        "issue_type": "style_only",
        "dimension": "expression",
        "target": "解析措辞",
        "reason": "可将表达再压缩一些，不影响事实和教学结论。",
        "quote": "表达可以更凝练",
    }]
    result = _apply_semantic_review(payload, _report(), _review(findings=findings))
    assert result["pass"] is True
    assert result["semantic_review"]["findings"] == findings


def test_quality_gate_rejects_overfragmented_point_count():
    payload = _payload()
    payload["key_points"] = payload["key_points"] * 9
    report = quality_check(payload, payload["source_excerpt"])
    assert report["pass"] is False
    assert any("参考要点数量" in error for error in report["errors"])
