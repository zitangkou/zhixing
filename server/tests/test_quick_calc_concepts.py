"""Concept-based training keeps strategy hints private until answering."""
import json
import random

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session



@pytest.fixture
def service():
    from app.services import ziliao_quick_calc_service
    return ziliao_quick_calc_service


@pytest.fixture
def db():
    from app.models import Base
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_comparison_is_one_concept_with_four_valid_scenarios(db, service):
    methods = service.list_methods(db)
    assert {m['code'] for m in methods} == {
        'fraction-compare', 'growth-amount', 'growth-rate', 'base', 'share', 'average',
        'multiple', 'mixed-growth', 'interval-growth', 'period-growth', 'contribution',
    }
    result = service.preview(db, 'fraction-compare', 8)
    assert {'multi-extrema', 'multi-sort'} <= {q['questionForm'] for q in result['questions']}
    assert {q['strategy'] for q in result['questions'] if q.get('strategy')} == service.LEGACY_COMPARE_CODES
    for q in result['questions']:
        assert q['method'] == 'fraction-compare'
        if q['questionForm'] == 'pair':
            assert q['steps'][0]['text'].startswith('最快建议：')
        safe = service._safe_question(q)
        assert not {'strategy', 'steps', 'answer', 'source'} & safe.keys()
    service._validate_questions(result['questions'])


def test_legacy_default_knowledge_links_are_repaired_without_overwriting_custom_links(db, service):
    from app.models import KnowledgeNode, KnowledgeTree, ZiliaoQuickMethod

    methods = service.list_methods(db)
    by_code = {method['code']: db.get(ZiliaoQuickMethod, method['id']) for method in methods}
    node_title = '比重 | 倍数 | 平均数（比值）'
    db.add(KnowledgeTree(
        tree_key='资料分析', title='资料分析', is_visible=True, live_version=1,
        draft_tree_json=json.dumps({'schemaVersion': 2, 'title': '资料分析', 'children': [
            {'title': node_title, 'blocks': [], 'children': []},
        ]}, ensure_ascii=False),
    ))
    db.add(KnowledgeNode(tree_key='资料分析', title=node_title, path=node_title, depth=0))
    for code in ('share', 'average', 'multiple'):
        by_code[code].knowledge_path = '资料分析 / 比重/倍数/平均数'
    # A stale published default must stop serving until the administrator previews and republishes it.
    by_code['share'].status = 'published'
    # Custom paths are intentionally outside the migration allowlist.
    by_code['average'].knowledge_path = '资料分析 / 自定义节点'
    db.commit()

    rows = {method['code']: method for method in service.list_methods(db)}
    expected = '资料分析 / 比重 | 倍数 | 平均数（比值）'
    assert rows['share']['knowledgePath'] == expected
    assert rows['share']['status'] == 'draft'
    assert rows['share']['knowledgeStatus'] == 'ready'
    assert rows['multiple']['knowledgePath'] == expected
    assert rows['multiple']['knowledgeStatus'] == 'ready'
    assert rows['average']['knowledgePath'] == '资料分析 / 自定义节点'


def test_default_preview_includes_long_and_audit_question_forms(db, service):
    compare = service.preview(db, 'fraction-compare', 5)
    assert {'multi-extrema', 'multi-sort'} <= {q['questionForm'] for q in compare['questions']}
    for code in ('growth-amount', 'growth-rate', 'base'):
        preview = service.preview(db, code, 5)
        forms = {q['questionForm'] for q in preview['questions']}
        assert {'calculation-correct', 'calculation-incorrect'} <= forms
        assert all('claims' not in service._safe_question(q) for q in preview['questions'])


def test_extended_concepts_rotate_real_sources_and_fill_twenty_question_sets(db, service):
    from app.models import ZiliaoQuickMethod, ZiliaoQuickSession

    methods = service.list_methods(db)
    for method in methods:
        row = db.get(ZiliaoQuickMethod, method['id'])
        row.status = 'published'
        row.version = 1
    db.commit()

    for code in service.EXTENDED_CODES:
        result = service.create_session(db, f'{code}-user', code, 20)
        stored = json.loads(db.get(ZiliaoQuickSession, result['id']).questions_json)
        assert len(stored) == 20
        identities = {(q['method'], q.get('questionForm'), q['stem'], q['latex']) for q in stored}
        assert len(identities) == 20
        assert all(q['check'] == 'data-concept' for q in stored)
        assert all(q['source']['sourceUrls'] for q in stored)
        service._validate_questions(stored)


def test_extended_concept_question_forms_and_source_families(service):
    assert service.GRAIN_NATIONAL_PRODUCTION == {2022: 68652.8, 2023: 69541.0, 2024: 70649.9}
    assert service.GDP_COMPOSITION_FACTS[2024] == {
        'total': 1348066, 'primary': 91636, 'secondary': 490305, 'tertiary': 766125,
    }
    assert service.GDP_COMPOSITION_SOURCE_URLS[1].endswith('/sj/zxfbhjd/202512/t20251226_1962144.html')
    rng = random.Random(20261018)
    expected_forms = {
        'share': set(service.EXTENDED_FORMS['share']),
        'average': set(service.EXTENDED_FORMS['average']),
        'multiple': set(service.EXTENDED_FORMS['multiple']),
        'mixed-growth': set(service.EXTENDED_FORMS['mixed-growth']),
        'interval-growth': set(service.EXTENDED_FORMS['interval-growth']),
        'period-growth': set(service.EXTENDED_FORMS['period-growth']),
        'contribution': set(service.EXTENDED_FORMS['contribution']),
    }
    for code, forms in expected_forms.items():
        questions = [service._generate(code, {'_questionForm': service.EXTENDED_FORMS[code][i % len(service.EXTENDED_FORMS[code])], '_sourceIndex': i}, rng)
                     for i in range(24)]
        assert {q['questionForm'] for q in questions} == forms
        service._validate_questions(questions)
        assert all(q['source']['sourceType'] == 'official-statistics-adaptation' for q in questions)
        assert all('合成' not in q['source']['sourceLabel'] and q['source']['sourceUrls'] for q in questions)


def test_growth_amount_advice_respects_negative_rate_algebra(service):
    method, advice = service._growth_amount_advice(-12.5)
    assert method == '除乘转化法'
    assert '1/7' in advice and '方向为负' in advice
    assert 'n+1' not in advice


def test_growth_amount_question_advice_matches_decline_direction(service):
    fact = next(item for item in service._official_trade_growth_facts() if item['current'] < item['base'])
    question = service._generate('growth-amount', {'min': 1000, 'max': 9000}, random.Random(14), fact)
    assert '同比下降' in question['stem']
    assert '下降率' in question['steps'][0]['text']
    assert '结果方向为负' in question['steps'][0]['text']


def test_interval_growth_and_annual_growth_are_distinct_concepts_with_their_own_methods(service):
    rng = random.Random(20261018)
    interval = service._generate('interval-growth', {'_questionForm': 'interval-growth', '_sourceIndex': 12}, rng)
    annual_sources = [item for item in service._published_period_sources() if item['periods'] > 1]
    annual = service._generate('period-growth', {'_questionForm': 'annual-growth', '_sourceIndex': 0}, rng)

    assert interval['source']['kind'] == 'interval-growth'
    assert '隔年增长率' in interval['stem']
    assert '两者乘积项微调' in interval['steps'][0]['text']
    assert interval['source']['startYear'] == 2022 and interval['source']['endYear'] == 2024
    assert annual['source']['periods'] > 1
    assert '年均复合增长率' in annual['stem']
    assert '快捷估算' in annual['steps'][0]['text']
    assert '开2次方根' in annual['steps'][0]['text'] or '开3次方根' in annual['steps'][0]['text']
    assert len(annual_sources) > 0
    service._validate_questions([interval, annual])


def test_previous_combined_period_method_migrates_to_annual_only_label(db, service):
    from app.models import ZiliaoQuickMethod

    db.add(ZiliaoQuickMethod(
        id='legacy-period-growth', code='period-growth', name='间隔与年均增长',
        category='计算', scene='旧场景', knowledge_path='资料分析 / 年均增长',
        node_title='年均增长', node_parent='资料分析', config_json='{}', enabled=True,
        status='published', version=1, sort_order=90,
    ))
    db.commit()

    rows = {item['code']: item for item in service.list_methods(db)}
    assert rows['period-growth']['name'] == '年均增长'
    assert rows['period-growth']['status'] == 'draft'
    assert rows['interval-growth']['name'] == '隔年增长率'


def test_extended_sources_never_fill_options_with_arbitrary_nearby_values(service):
    rng = random.Random(20261018)
    checked = 0
    for code, forms in service.EXTENDED_FORMS.items():
        for form in forms:
            for source_index in range(250):
                question = service._generate(
                    code,
                    {'_questionForm': form, '_sourceIndex': source_index},
                    rng,
                )
                service._validate_questions([question])
                precision = question['precision']
                assert precision in (1, 2)
                assert len(question['values']) == len(set(question['values'])) == 4
                assert all(value == round(value, precision) for value in question['values'])
                assert question['values'][question['answer']] == question['target']
                if precision == 2:
                    assert '保留两位小数' in question['stem']
                checked += 1
    assert checked >= 3500


def test_preview_skips_real_rows_that_cannot_form_unique_options(db, service, monkeypatch):
    original_generate = service._generate
    tried = []

    def reject_first_source(code, config, rng, fact=None):
        if code == 'share':
            tried.append(config.get('_sourceIndex'))
            if config.get('_sourceIndex') == 0:
                raise service.UnusableQuickCalcSample('synthetic collision fixture')
        return original_generate(code, config, rng, fact)

    monkeypatch.setattr(service, '_generate', reject_first_source)
    result = service.preview(db, 'share', 1)
    assert len(result['questions']) == 1
    assert tried[:2] == [0, 1]
    service._validate_questions(result['questions'])


def test_comparison_answers_hold_across_difficulties(service):
    rng = random.Random(42)
    for difficulty in range(1, 6):
        questions = [service._generate('fraction-compare', {'difficulty': difficulty}, rng) for _ in range(100)]
        service._validate_questions(questions)
        for form in ('multi-extrema', 'multi-sort'):
            questions = [service._generate('fraction-compare', {'difficulty': difficulty, '_questionForm': form}, rng) for _ in range(40)]
            service._validate_questions(questions)


def test_calculation_audit_forms_have_single_correct_or_incorrect_option(service):
    rng = random.Random(8201)
    for method in ('growth-amount', 'growth-rate', 'base'):
        for form in service.CALCULATION_FORMS:
            for _ in range(80):
                question = service._generate(method, {'difficulty': 2, '_questionForm': form}, rng)
                service._validate_questions([question])
                assert len(question['options']) == 4
                expected_true = 1 if form == 'calculation-correct' else 3
                assert len(question['claims']) == 4 and sum(question['claims']) == expected_true
                assert not any('多计' in option or '少计' in option for option in question['options'])


def test_core_calculation_distractors_come_from_formula_errors(service):
    rng = random.Random(20261018)
    for difficulty in range(1, 6):
        for _ in range(80):
            base_question = service._generate('base', {'difficulty': difficulty}, rng)
            rate = base_question['source']['rate'] / 100
            current = base_question['source']['current']
            precision = base_question['precision']
            base_candidates = [
                current / (1 + rate),
                current * (1 - rate),
                current / (1 - rate) if rate != 1 else -1,
                current,
                current * (1 + rate),
                current / (1 + abs(rate)),
                current / (1 + base_question['source']['rate']),
                current / (1 - base_question['source']['rate']) if base_question['source']['rate'] != 1 else -1,
            ]
            assert set(base_question['values']) <= {
                round(value + 1e-10, precision) for value in base_candidates if value >= 0
            }
            assert base_question['source']['sourceType'] == 'official-statistics-adaptation'
            assert base_question['source']['sourceUrls']
            service._validate_questions([base_question])

        for code, builder in (
            ('growth-amount', service._growth_amount_fact_batch),
            ('growth-rate', service._growth_rate_fact_batch),
        ):
            facts = builder({'difficulty': difficulty}, rng, 40)
            for fact in facts:
                question = service._generate(code, {'difficulty': difficulty}, rng, fact)
                source = question['source']
                if code == 'growth-amount':
                    rate = round(source['rate'], 1) / 100
                    target = source['current'] * rate / (1 + rate)
                    candidates = [target, source['current'] * rate,
                                  source['current'] * rate / (1 - rate) if rate != 1 else source['current'] * rate * 2,
                                  target * 100, target / (1 + rate)]
                else:
                    delta = round(source['current'] - source['base'], 2)
                    target = round(delta / source['base'] * 100, 1)
                    candidates = [target, delta / source['current'] * 100, -target, round(target),
                                  delta / source['base'], source['current'] / source['base'] * 100,
                                  delta / (source['base'] + source['current']) * 100]
                precision = question['precision']
                assert set(question['values']) <= {round(value + 1e-10, precision) for value in candidates}
                service._validate_questions([question])


def test_growth_calculation_audit_uses_distinguishable_real_source_rates(service):
    rng = random.Random(20261018)
    for difficulty in range(1, 6):
        for method, builder, minimum_rate in (
            ('growth-amount', service._growth_amount_fact_batch, 2.5),
            ('growth-rate', service._growth_rate_fact_batch, 0.5),
        ):
            facts = builder({'difficulty': difficulty}, rng, 20)
            assert len(facts) == 20
            for index, fact in enumerate(facts):
                rate = fact.get('rate', (fact['current'] - fact['base']) / fact['base'] * 100)
                assert abs(rate) >= minimum_rate
                form = service.CALCULATION_FORMS[index % len(service.CALCULATION_FORMS)]
                question = service._generate(method, {'difficulty': difficulty, '_questionForm': form}, rng, fact)
                service._validate_questions([question])
                assert not any('多计' in option or '少计' in option for option in question['options'])


def test_growth_training_uses_balanced_official_series_and_multiple_method_advice(service):
    rng = random.Random(20261018)
    rates = service._growth_rate_fact_batch({'difficulty': 1}, rng, 20)
    assert len(rates) == 20
    assert sum(fact['current'] >= fact['base'] for fact in rates) == 10
    assert sum(fact['current'] < fact['base'] for fact in rates) == 10
    assert all(fact['sourceLabel'] and fact['sourceUrls'] for fact in rates)
    assert any(0.5 <= abs(fact['rate']) < 1 for fact in rates)
    assert any(1 <= abs(fact['rate']) <= 5 for fact in rates)
    harder_rates = service._growth_rate_fact_batch({'difficulty': 3}, rng, 20)
    assert any(abs(fact['rate']) > 5 for fact in harder_rates)

    amounts = service._growth_amount_fact_batch({'difficulty': 2}, rng, 20)
    recommended = {
        service._growth_amount_advice(round(fact['rate'], 1))[0]
        for fact in amounts
    }
    assert recommended == {'除乘转化法', '乘数拆分法', '假设估算法', '错位加减法'}

    for rate, method in ((20, '除乘转化法'), (7.5, '乘数拆分法'),
                         (9.62, '假设估算法'), (14.61, '错位加减法')):
        current = 1200
        question = service._generate(
            'growth-amount', {'_questionForm': 'calculation'}, rng,
            {'base': current / (1 + rate / 100), 'current': current, 'rate': rate,
             'context': '测试指标', 'period': '2023—2024年', 'unit': '亿元',
             'sourceLabel': '测试统计来源', 'sourceUrls': ['https://example.invalid/source']},
        )
        assert method in question['steps'][0]['text']
        assert 'n＋1' not in question['steps'][0]['text']
        assert 'n−1' not in question['steps'][0]['text']
        assert '负值说明' not in question['pitfall']
        service._validate_questions([question])

    official = next(fact for fact in service._official_grain_growth_facts() if abs(fact['rate']) >= 2.5)
    official_question = service._generate('growth-amount', {'_questionForm': 'calculation'}, rng, official)
    exam_fact = next(fact for fact in service.GROWTH_AMOUNT_REFERENCE_FACTS if fact['sourceLabel'].startswith('2019'))
    exam_question = service._generate('growth-amount', {'_questionForm': 'calculation'}, rng, exam_fact)
    assert official_question['stem'].startswith('根据国家统计局')
    assert official_question['source']['sourceType'] == 'official-statistics-adaptation'
    assert exam_question['stem'].startswith('真题数据改编（2019 年国考地市级第 121 题）')
    assert exam_question['source']['sourceType'] == 'exam-data-adaptation'
    negative_fact = next(fact for fact in service._official_trade_growth_facts() if fact['current'] < fact['base'])
    negative_question = service._generate('growth-amount', {'_questionForm': 'calculation'}, rng, negative_fact)
    assert '同比下降' in negative_question['stem'] and '同比变化量' in negative_question['stem']
    assert negative_question['target'] < 0


def test_base_period_preview_and_sessions_use_traceable_real_data(db, service):
    from app.models import ZiliaoQuickMethod, ZiliaoQuickSession

    preview = service.preview(db, 'base', 5)
    assert len(preview['questions']) == 5
    assert {q['source']['sourceType'] for q in preview['questions']} == {'official-statistics-adaptation'}
    assert all(q['source']['sourceUrls'] and q['source']['sourceLabel'] for q in preview['questions'])
    assert {q['source']['rate'] >= 0 for q in preview['questions']} == {True, False}
    assert all('基期量' in q['stem'] and q['unit'] for q in preview['questions'])
    assert any('最接近' in q['stem'] for q in preview['questions'])

    method = db.query(ZiliaoQuickMethod).filter_by(code='base').one()
    method.status = 'published'
    method.version = 1
    db.commit()
    for count in (5, 10, 20):
        session = service.create_session(db, f'base-{count}', 'base', count)
        assert len(session['questions']) == count
        snapshot = json.loads(db.get(ZiliaoQuickSession, session['id']).questions_json)
        assert all(q['source']['sourceType'] == 'official-statistics-adaptation' for q in snapshot)
        assert all('source' not in q and 'answer' not in q for q in session['questions'])
        service._validate_questions(snapshot)


def test_growth_session_rotates_official_facts_without_repeating_questions(db, service):
    from app.models import ZiliaoQuickMethod, ZiliaoQuickSession

    for method in service.list_methods(db):
        row = db.get(ZiliaoQuickMethod, method['id'])
        row.status = 'published'
        row.version = 1
    db.commit()

    for code in ('growth-amount', 'growth-rate'):
        result = service.create_session(db, f'{code}-source-user', code, 20)
        stored = json.loads(db.get(ZiliaoQuickSession, result['id']).questions_json)
        identities = {(q['questionForm'], q['stem'], q['latex']) for q in stored}
        assert len(stored) == len(identities) == 20
        assert all(q['source']['sourceLabel'] for q in stored)
        service._validate_questions(stored)
        if code == 'growth-rate':
            signs = [q['source']['current'] >= q['source']['base'] for q in stored]
            assert any(signs) and not all(signs)


def test_material_audit_covers_four_calculation_concepts(service):
    rng = random.Random(117)
    for form, expected_true in (('material-correct', 1), ('material-incorrect', 3)):
        questions = [service._material_audit_question(form, rng) for _ in range(80)]
        service._validate_questions(questions)
        for question in questions:
            assert question['method'] == 'mixed'
            assert question['check'] == 'material-audit'
            assert len(question['material']['rows']) == 4
            changes = [int(row[2].replace(',', '')) - int(row[1].replace(',', '')) for row in question['material']['rows']]
            assert any(change > 0 for change in changes) and any(change < 0 for change in changes)
            assert {item['concept'] for item in question['source']['items']} == set(service.MATERIAL_CONCEPTS)
            assert sum(question['claims']) == expected_true
            safe = service._safe_question(question)
            assert 'material' in safe
            assert not {'answer', 'check', 'source', 'claims', 'claimValues'} & safe.keys()


def test_mixed_session_adds_material_question_and_feedback_only_when_answered(db, service):
    from app.models import ZiliaoQuickMethod, ZiliaoQuickSession

    methods = service.list_methods(db)
    for method in methods:
        row = db.get(ZiliaoQuickMethod, method['id'])
        row.status = 'published'
        row.version = 1
    db.commit()

    result = service.create_session(db, 'material-user', 'mixed', 10)
    stored_session = db.get(ZiliaoQuickSession, result['id'])
    stored = json.loads(stored_session.questions_json)
    material = next(question for question in stored if question['check'] == 'material-audit')
    safe_material = next(question for question in result['questions'] if question['id'] == material['id'])
    assert material['questionForm'] == 'material-correct'
    assert safe_material['material']['rows'] == material['material']['rows']
    assert not {'answer', 'check', 'source', 'claims'} & safe_material.keys()
    assert json.loads(stored_session.method_versions_json)['material-audit'] == 1

    response = service.answer_question(db, 'material-user', result['id'], material['id'], material['answer'], 8)
    assert response['correct'] is True
    assert response['optionFeedback'].count('该计算成立') == 1
    assert response['optionFeedback'].count('该计算不成立') == 3

    longer = service.create_session(db, 'material-user', 'mixed', 20)
    longer_stored = json.loads(db.get(ZiliaoQuickSession, longer['id']).questions_json)
    assert {q['questionForm'] for q in longer_stored if q['check'] == 'material-audit'} == {
        'material-correct', 'material-incorrect',
    }

    service.complete_session(db, 'material-user', result['id'], 8)
    mixed_row = next(row for row in service.analytics(db)['methods'] if row['method'] == 'mixed')
    assert mixed_row['name'] == '综合材料辨析'
    assert mixed_row['formCounts']['综合材料·选正确项'] == 1


def test_session_balances_scenarios_and_reveals_advice_after_answer(db, service):
    from app.models import ZiliaoQuickMethod, ZiliaoQuickSession

    method = next(m for m in service.list_methods(db) if m['code'] == 'fraction-compare')
    rule = db.get(ZiliaoQuickMethod, method['id'])
    rule.status = 'published'
    rule.version = 1
    db.commit()
    result = service.create_session(db, 'session-user', 'fraction-compare', 8)
    assert all(q['method'] == 'fraction-compare' for q in result['questions'])
    assert all(not {'strategy', 'steps', 'answer'} & q.keys() for q in result['questions'])
    stored = json.loads(db.get(ZiliaoQuickSession, result['id']).questions_json)
    assert {'multi-extrema', 'multi-sort'} <= {q['questionForm'] for q in stored}
    question = stored[0]
    answer = service.answer_question(db, 'session-user', result['id'], question['id'], question['answer'], 4)
    assert answer['correct'] is True
    if question['questionForm'] == 'pair':
        assert answer['steps'][0]['text'].startswith('最快建议：')


def test_legacy_comparison_statistics_aggregate_under_concept(db, service):
    from app.models import ZiliaoQuickSession
    answers = [dict(method=code, correct=True, seconds=3, selected=0) for code in service.LEGACY_COMPARE_CODES]
    answers.append(dict(method='fraction-compare', strategy='difference', correct=False, seconds=6, selected=1))
    db.add(ZiliaoQuickSession(user_id='history-user', status='completed', answers_json=json.dumps(answers)))
    db.commit()
    result = service.analytics(db)
    assert len(result['methods']) == 1
    row = result['methods'][0]
    assert row['method'] == 'fraction-compare'
    assert row['attempts'] == 5 and row['accuracy'] == 80
    assert row['strategyCounts']['差分比较'] == 2
    assert row['formPerformance']['直接计算'] == {'attempts': 5, 'accuracy': 80, 'averageSeconds': 3.6}
