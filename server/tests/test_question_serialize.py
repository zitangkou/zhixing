"""题目答案序列化：纯数字字符串不应导致 API 500"""

from app.models import Question
from app.services.serializers import (
    encode_correct_answer,
    parse_correct_answer,
    question_to_out,
)


def test_parse_numeric_string_answers():
    assert parse_correct_answer("1.3") == "1.3"
    assert parse_correct_answer("1000") == "1000"
    assert parse_correct_answer("5%") == "5%"
    assert parse_correct_answer('["a", "b"]') == ["a", "b"]


def test_encode_correct_answer():
    assert encode_correct_answer("1.3") == '"1.3"'
    assert encode_correct_answer(["a", "b"]) == '["a", "b"]'


def test_question_to_out_numeric_answer():
    q = Question(
        id="qtest",
        article_id="art1",
        type="single",
        stem="测试",
        options='["1.0", "1.3", "1.5", "2.0"]',
        correct_answer="1.3",
        analysis="解析",
        source_sentence="依据",
        status="approved",
        origin="import",
        is_active=True,
    )
    out = question_to_out(q)
    assert out.correctAnswer == "1.3"
    assert out.options == ["1.0", "1.3", "1.5", "2.0"]
