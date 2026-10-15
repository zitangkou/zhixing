from datetime import date
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import RmrbVocabulary, RmrbVocabularyJob, ShenlunMaterial
from app.services import rmrb_vocabulary_service as joint
from app.services.shenlun_materials import save_joint_ai_candidates


ISSUE_DATE = date(2026, 10, 15)
TEXT = '基层治理要从群众急难愁盼处着手，才能把服务做到群众心坎上。'
BODY = f'报道指出，{TEXT} 这也是提升基层服务效能的重要抓手。'
SAMPLE = '围绕群众急难愁盼，应完善诉求收集、分级办理和跟踪反馈机制，推动服务资源下沉到一线。' * 2
BREAKDOWN = {'独立成义': 2, '主题咬合': 2, '场景匹配': 2, '可改写': 1, '规范': 1, '可追溯': 1, '不重复': 1}


def material_candidate(**overrides):
    item = {
        'type': 'golden', 'text': TEXT, 'source_evidence': f'报道指出，{TEXT}', 'source_anchor': TEXT,
        'theme_code': 'zl', 'theme_element': ['做法', '成效'], 'scene_code': 'essay_subpoint',
        'usage_note': '用于基层治理分论点', 'example_topic': '基层治理', 'example_body': SAMPLE,
        'quality_breakdown': BREAKDOWN, 'veto': False,
    }
    item.update(overrides)
    return item


def db_factory():
    engine = create_engine('sqlite:///:memory:')
    for model in (RmrbVocabulary, RmrbVocabularyJob, ShenlunMaterial):
        model.__table__.create(engine)
    return engine, sessionmaker(bind=engine, autoflush=False)


def test_ai_materials_are_hard_checked_deduplicated_and_pending():
    engine, factory = db_factory()
    article = {'url': 'https://paper.people.com.cn/a.html', 'title': '基层治理的实践',
               'pageNo': '02', 'pageName': '评论', 'body': BODY}
    candidates = [
        material_candidate(),
        material_candidate(),
        material_candidate(source_evidence='模型编造的来源摘录。'),
    ]
    with factory() as db:
        result = save_joint_ai_candidates(db, candidates, article, ISSUE_DATE)
        row = db.query(ShenlunMaterial).one()
        payload = json.loads(row.payload_json)
        rejected = save_joint_ai_candidates(db, [material_candidate(quality_breakdown={**BREAKDOWN, '独立成义': 0, '主题咬合': 0, '场景匹配': 0})], article, ISSUE_DATE)
        assert result == {'added': 1, 'duplicates': 1, 'invalid': 1, 'qualityRejected': 0}
        assert rejected['qualityRejected'] == 1 and rejected['added'] == 0
        assert row.review_status == 'pending'
        assert row.source_url == article['url']
        assert payload['source_evidence'] == f'报道指出，{TEXT}'
    engine.dispose()


def test_joint_job_reuses_analysis_cache_and_saves_shenlun_material(monkeypatch):
    engine, factory = db_factory()
    article = {'url': 'https://paper.people.com.cn/a.html', 'title': '基层治理的实践', 'pageNo': '02',
               'pageName': '评论', 'body': BODY, 'bodySha256': 'body-sha'}
    cached = {'ruleVersion': joint.ANALYSIS_RULE_VERSION, 'category': 'core', 'quotes': [],
              'vocabulary': [], 'shenlunMaterials': [material_candidate()]}
    monkeypatch.setattr(joint, 'SessionLocal', factory)
    monkeypatch.setattr(joint, 'get_full_articles', lambda _: ([article], [], 1))
    monkeypatch.setattr(joint, 'get_analysis', lambda *_: cached)
    monkeypatch.setattr(joint, 'save_analyses', lambda *args: 1)
    monkeypatch.setattr(joint, 'chat_json', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('cache miss caused a model call')))
    with factory() as db:
        job = RmrbVocabularyJob(issue_date=ISSUE_DATE, status='pending', attempts=0, progress_json='{}', error='')
        db.add(job); db.commit(); job_id = job.id

    joint.run_job(job_id)

    with factory() as db:
        job = db.get(RmrbVocabularyJob, job_id)
        progress = json.loads(job.progress_json)
        assert job.status == 'completed'
        assert progress['analysisCacheHits'] == 1
        assert progress['shenlunAdded'] == 1
        assert db.query(ShenlunMaterial).one().review_status == 'pending'
    engine.dispose()
