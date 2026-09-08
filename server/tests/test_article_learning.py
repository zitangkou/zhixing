"""Isolated API tests: no application startup, disk DB or account side effects."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.public.article_learning import router
from app.database import get_db
from app.models import Article, Question, TheoryLearningEntry
from app.models.base import Base

THEORY_HEADERS = {"X-Product-Key": "theory"}


@pytest.fixture
def fixture():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Article(id='a', title='测试文章', source='测试', publish_date='2026-09-07',
                       summary='摘要', content='正文', status='published', is_published=True, allow_quiz=True))
        for i in range(12):
            db.add(Question(id=f'q{i:02}', article_id='a', type='single', stem=f'题目{i}',
                            options=json.dumps(['甲', '乙']), correct_answer='甲',
                            analysis='解析', source_sentence='原文依据', status='approved', is_active=True))
        db.add(TheoryLearningEntry(
            id='entry-a', article_id='a', is_daily=True, status='published',
            collection_enabled=True,
            parts_json=json.dumps([
                {'number': 1, 'title': '第 1 辑', 'questionIds': [f'q{i:02}' for i in range(5)]},
                {'number': 2, 'title': '第 2 辑', 'questionIds': [f'q{i:02}' for i in range(5, 10)]},
                {'number': 3, 'title': '第 3 辑', 'questionIds': [f'q{i:02}' for i in range(10, 12)]},
            ]),
        ))
        db.commit()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            yield client, db
    engine.dispose()


def bundle(client):
    response = client.get('/learning/articles/a', headers=THEORY_HEADERS)
    assert response.status_code == 200
    return response.json()['data']


def check(client, data, **overrides):
    payload = {'revision': data['revision'], 'questionId': 'q00', 'answer': '甲', **overrides}
    return client.post('/learning/articles/a/check', json=payload, headers=THEORY_HEADERS)


def test_anonymous_parts_and_hidden_answers(fixture):
    client, db = fixture
    data = bundle(client)
    assert [len(p['questionIds']) for p in data['parts']] == [5, 5, 2]
    assert data['collectionComplete'] is True
    assert sum((p['questionIds'] for p in data['parts']), []) == [q['id'] for q in data['questions']]
    assert not {'correctAnswer', 'analysis', 'sourceSentence'} & data['questions'][0].keys()
    assert check(client, data).json()['data']['correct'] is True
    assert check(client, data, answer='乙').json()['data']['correct'] is False
    assert check(client, data).json()['data']['pointsEarned'] == 0
    assert not db.new and not db.dirty


@pytest.mark.parametrize('field,value', [('is_published', False), ('status', 'draft'), ('allow_quiz', False)])
def test_closed_article_rejects_read_and_check(fixture, field, value):
    client, db = fixture
    data = bundle(client)
    setattr(db.get(Article, 'a'), field, value)
    db.commit()
    assert client.get('/learning/articles/a', headers=THEORY_HEADERS).status_code == 404
    assert check(client, data).status_code == 404


def test_revision_guards_changed_answers_but_not_read_counts(fixture):
    client, db = fixture
    data = bundle(client)
    db.get(Article, 'a').read_count += 1
    db.commit()
    assert bundle(client)['revision'] == data['revision']
    db.get(Question, 'q00').correct_answer = '乙'
    db.commit()
    assert check(client, data).status_code == 409


def test_incomplete_and_unapproved_questions(fixture):
    client, db = fixture
    db.get(Question, 'q00').source_sentence = ' '
    db.get(Question, 'q01').status = 'pending'
    db.get(Question, 'q02').is_active = False
    db.commit()
    assert client.get('/learning/articles/a', headers=THEORY_HEADERS).status_code == 404


@pytest.mark.parametrize('answer', ['', '丙', [], ['甲', '甲'], ['甲', '乙']])
def test_invalid_answers(fixture, answer):
    client, _ = fixture
    assert check(client, bundle(client), answer=answer).status_code == 422


def test_multiple_and_foreign_question(fixture):
    client, db = fixture
    q = db.get(Question, 'q00')
    q.type = 'multiple'
    q.correct_answer = json.dumps(['甲', '乙'])
    db.commit()
    data = bundle(client)
    assert check(client, data, answer=['乙', '甲']).json()['data']['correct'] is True
    assert check(client, data, answer=['甲']).status_code == 422
    assert check(client, data, questionId='other').status_code == 404


def test_other_products_cannot_access_theory_bundle(fixture):
    client, _ = fixture
    for product in ('general', 'shenlun'):
        assert client.get('/learning/articles/a', headers={'X-Product-Key': product}).status_code == 404
