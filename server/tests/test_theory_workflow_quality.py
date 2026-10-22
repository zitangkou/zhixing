from app.services.theory_workflow_service import _difficulty, _paper_quality_errors


def _valid_mock_questions():
    questions = []
    tricks = ["time", "subject", "direction", "collocation", "degree"]
    for index in range(20):
        subtype = "direct" if index < 16 else "combo" if index < 18 else "count"
        answer = "ABCD"[index % 4]
        if subtype == "combo":
            stem = f"第{index}题，请判断①②③④，有几项正确？"
            options = ["①②", "①③", "②④", "③④"]
        elif subtype == "count":
            stem = f"第{index}题，以下说法正确的有几项？①甲②乙③丙④丁"
            options = ["1项", "2项", "3项", "4项"]
        else:
            stem = f"第{index}题，下列表述正确的是？"
            options = [f"选项{letter}-{index}" for letter in "ABCD"]
        focus_type = ("general" if index < 4 else "core" if index < 14 else
                      "metric" if index < 16 else "deployment" if index < 19 else "background")
        distractors = {
            letter: {"type": tricks[(index + offset) % len(tricks)], "note": "将原文主体作可控替换"}
            for offset, letter in enumerate("ABCD") if letter != answer
        }
        questions.append({
            "subtype": subtype,
            "focusType": focus_type,
            "numericRecall": False,
            "stem": stem,
            "options": options,
            "answer": answer,
            "analysis": "原文指出该项符合文件提出的核心要求，并说明其他选项的偷换点。",
            "sourceSentence": "坚持以人民为中心的发展思想，完整准确全面贯彻新发展理念。",
            "sourceRef": "文件第一部分·总体要求段",
            "topic": f"主题{index}",
            "tag": f"考点{index}",
            "distractors": distractors,
            "difficulty": 2 if subtype == "direct" else 3,
        })
    return questions


def test_latest_mock_paper_gates_accept_valid_paper():
    questions = _valid_mock_questions()
    body = "材料：坚持以人民为中心的发展思想，完整准确全面贯彻新发展理念。"
    assert _paper_quality_errors(questions, body) == []


def test_latest_mock_paper_gates_reject_unbalanced_answers_and_unmarked_distractors():
    questions = _valid_mock_questions()
    for question in questions:
        question["answer"] = "A"
    questions[0]["distractors"].pop("B")
    errors = _paper_quality_errors(questions, "坚持以人民为中心的发展思想，完整准确全面贯彻新发展理念。")
    assert any("答案分布" in error for error in errors)
    assert any("干扰项B" in error for error in errors)


def test_difficulty_matches_local_assessment_rules():
    question = _valid_mock_questions()[0]
    question["stem"] += "2035年"
    question["distractors"]["B"]["type"] = "time"
    question["analysis"] += "跨文档辨析。"
    assert _difficulty(question) == 4
