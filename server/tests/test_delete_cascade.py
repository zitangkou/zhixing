"""删除级联：文章、题目与关联用户数据"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import (
    AppUser,
    Article,
    Question,
    SectionRead,
    StudyRecord,
    WrongAnswer,
)
from app.services.article_service import delete_article_record
from app.services.question_service import delete_question_record


def _session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    from app.database import Base

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_delete_article_clears_study_and_section_reads():
    db = _session()
    user = AppUser(id="u1", nickname="test")
    article = Article(
        id="art1",
        title="t",
        source="s",
        publish_date="2026-01-01",
        summary="s",
        content="c",
    )
    question = Question(
        id="q1",
        article_id="art1",
        type="single",
        stem="?",
        correct_answer="A",
        analysis="a",
    )
    db.add_all([user, article, question])
    db.flush()
    db.add(WrongAnswer(user_id="u1", question_id="q1"))
    db.add(StudyRecord(user_id="u1", article_id="art1", study_date="2026-01-01"))
    db.add(SectionRead(user_id="u1", article_id="art1", section_id="sec1"))
    db.commit()

    delete_article_record(db, article)
    db.commit()

    assert db.get(Article, "art1") is None
    assert db.query(Question).count() == 0
    assert db.query(WrongAnswer).count() == 0
    assert db.query(StudyRecord).count() == 0
    assert db.query(SectionRead).count() == 0
    db.close()


def test_delete_question_clears_wrong_answers():
    db = _session()
    article = Article(
        id="art1",
        title="t",
        source="s",
        publish_date="2026-01-01",
        summary="s",
        content="c",
    )
    user = AppUser(id="u1", nickname="test")
    question = Question(
        id="q1",
        article_id="art1",
        type="single",
        stem="?",
        correct_answer="A",
        analysis="a",
    )
    db.add_all([article, user, question])
    db.flush()
    db.add(WrongAnswer(user_id="u1", question_id="q1"))
    db.commit()

    delete_question_record(db, question)
    db.commit()

    assert db.get(Question, "q1") is None
    assert db.query(WrongAnswer).count() == 0
    db.close()
