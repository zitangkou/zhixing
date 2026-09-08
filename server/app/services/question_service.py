"""题目删除等维护操作"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Question, WrongAnswer


def delete_question_record(db: Session, question: Question) -> None:
    """删除题目及其关联错题记录（避免外键约束失败）"""
    db.query(WrongAnswer).filter(WrongAnswer.question_id == question.id).delete(
        synchronize_session=False
    )
    db.delete(question)


def delete_questions_for_article(db: Session, article_id: str) -> None:
    """删除文章下全部题目及关联错题"""
    question_ids = [
        qid
        for (qid,) in db.query(Question.id).filter(Question.article_id == article_id).all()
    ]
    if question_ids:
        db.query(WrongAnswer).filter(WrongAnswer.question_id.in_(question_ids)).delete(
            synchronize_session=False
        )
        db.query(Question).filter(Question.id.in_(question_ids)).delete(synchronize_session=False)
