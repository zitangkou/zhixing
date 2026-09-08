"""文章删除等维护操作"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Article, SectionRead, StudyRecord, TheoryLearningEntry
from app.services.question_service import delete_questions_for_article


def delete_article_record(db: Session, article: Article) -> None:
    """删除文章及其关联数据（题目、错题、学习记录、小节已读）"""
    db.query(TheoryLearningEntry).filter(TheoryLearningEntry.article_id == article.id).delete(
        synchronize_session=False
    )
    delete_questions_for_article(db, article.id)
    db.query(StudyRecord).filter(StudyRecord.article_id == article.id).delete(
        synchronize_session=False
    )
    db.query(SectionRead).filter(SectionRead.article_id == article.id).delete(
        synchronize_session=False
    )
    db.delete(article)
