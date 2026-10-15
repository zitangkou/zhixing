"""申论素材的闭集配置、筛选门槛与入库校验。"""
import hashlib
import json
import re
from pathlib import Path
from datetime import date
from app.models import ShenlunMaterial

RULES = {
    'version': '1.0.0', 'source': '人民日报当天已刊发稿件',
    'exclude': ['人事任免', '公告', '广告', '天气预报', '纯转载通稿'],
    'no_external_fill': True, 'quote_must_appear_in_source': True,
    'themes': {'zl':'基层治理','kj':'科技创新','st':'生态文明','wh':'文化自信','ms':'民生保障','xc':'乡村振兴','fz':'法治建设','qn':'青年担当','gf':'共同富裕','aq':'安全发展'},
    'theme_elements': ['理念','制度','主体','做法','问题','成效'],
    'scenes': {'essay_title':'作文标题','essay_open':'作文开头','essay_subpoint':'分论点','essay_reason':'理证','essay_example':'例证','essay_bridge':'过渡','essay_close':'结尾','summary_lead':'归纳概括','analysis_judge':'综合分析','solution_line':'提出对策','doc_purpose':'应用文目的','doc_close':'应用文收束'},
    'types': {'golden':'金句','template':'模板句','rhetoric':'优美词句','quote':'名人语录','case':'事实素材','policy_phrase':'规范表述','problem_line':'问题句'},
    'quality_gate': {'pass_score': 8, 'max_score': 10, 'dimensions': {'独立成义':2,'主题咬合':2,'场景匹配':2,'可改写':1,'规范':1,'可追溯':1,'不重复':1}, 'veto': ['跑题','语录无法核对','事实无法压缩','示例空话']},
    'case_required': ['fact','result','proves','do_not_use_for'],
    'daily_quota': {'golden':{'target':10,'min':6},'template':{'target':10,'min':6},'rhetoric':{'target':10,'min':0},'quote':{'target':10,'min':0},'case':{'target':10,'min':6},'policy_phrase':{'target':6,'min':0},'problem_line':{'target':4,'min':0}},
}

def normalize(item: dict, collected_date: date, actor: str = '') -> dict:
    data = dict(item)
    required = ['type','text','theme_code','theme_element','scene_code','usage_note','example_topic','example_body','source_date','source_title','source_section','veto']
    missing = [key for key in required if data.get(key) in (None, '', [])]
    if missing: raise ValueError('缺少必填字段：' + '、'.join(missing))
    if data['type'] not in RULES['types']: raise ValueError('物料类型不在闭集内')
    if data['theme_code'] not in RULES['themes']: raise ValueError('主题编码不在闭集内')
    if data['scene_code'] not in RULES['scenes']: raise ValueError('使用场景不在闭集内')
    elements = data['theme_element'] if isinstance(data['theme_element'], list) else [data['theme_element']]
    if not set(elements).issubset(set(RULES['theme_elements'])): raise ValueError('主题要素不在闭集内')
    score = int(data['quality_score']) if data.get('quality_score') not in (None, '') else None
    if score is not None and not 0 <= score <= 10: raise ValueError('质量分必须为 0–10')
    breakdown = data.get('quality_breakdown') or {}
    if breakdown:
        weights = RULES['quality_gate']['dimensions']
        if set(breakdown) != set(weights): raise ValueError('质量评分需覆盖全部七个评分维度')
        try: breakdown = {key:int(value) for key,value in breakdown.items()}
        except (TypeError,ValueError): raise ValueError('评分维度必须为整数')
        if any(value < 0 or value > weights[key] for key,value in breakdown.items()): raise ValueError('评分维度超出对应分值上限')
        if score is not None and sum(breakdown.values()) != score: raise ValueError('质量总分必须等于各维度得分之和')
        if score is None: score = sum(breakdown.values()); data['quality_score'] = score
    if data.get('review_status') == 'confirmed' and (data['veto'] or score is None or score < RULES['quality_gate']['pass_score'] or set(breakdown) != set(RULES['quality_gate']['dimensions'])):
        raise ValueError('确认入库需完成质量评分且不低于8分、无否决项')
    if data['veto'] or (score is not None and score < RULES['quality_gate']['pass_score']):
        data['review_status'] = 'rejected'
    elif data.get('review_status') not in ('pending','confirmed','rejected'):
        data['review_status'] = 'pending'
    if data['type'] == 'case':
        missing_case = [key for key in RULES['case_required'] if not str(data.get(key,'')).strip()]
        if missing_case: raise ValueError('事实素材缺少字段：' + '、'.join(missing_case))
        if data['scene_code'] != 'essay_example': raise ValueError('事实素材主场景必须为 essay_example')
        if not 60 <= len(str(data['text'])) <= 90: raise ValueError('事实素材正文需压缩至60–90字')
    if data['type'] == 'quote' and not data.get('verified'):
        raise ValueError('语录必须标记已核验并提供文中核对上下文')
    if data['type'] == 'quote' and not data.get('context_15'):
        raise ValueError('语录缺少原文前后文核对字段')
    if not data.get('source_url'):
        data['source_url'] = ''
    if len(str(data['usage_note'])) > 30: raise ValueError('usage_note 不超过 30 字')
    if data.get('example_body') and len(str(data['example_body'])) > 500: raise ValueError('示例正文不超过 500 字')
    if data.get('example_body') and not 80 <= len(str(data['example_body'])) <= 120:
        raise ValueError('原创示例正文需控制在80–120字')
    source_date = date.fromisoformat(str(data['source_date'])[:10])
    fingerprint_source = '|'.join([source_date.isoformat(), str(data['type']), str(data['source_title']), str(data['text']).strip()])
    fingerprint = hashlib.sha256(re.sub(r'\s+', '', fingerprint_source).encode()).hexdigest()
    return {'id': str(data.get('id') or f"sm{fingerprint[:24]}"), 'fingerprint': fingerprint,
            'source_date': source_date, 'collected_date': collected_date,
            'source_title': str(data['source_title'])[:300], 'source_section': str(data['source_section'])[:100],
            'source_url': str(data.get('source_url',''))[:1000], 'item_type': data['type'],
            'theme_code': data['theme_code'], 'scene_code': data['scene_code'], 'quality_score': score,
            'veto': bool(data['veto']), 'review_status': data.get('review_status','pending'), 'text': str(data['text']),
            'payload_json': json.dumps(data, ensure_ascii=False), 'created_by': actor, 'updated_by': actor}

def out(row: ShenlunMaterial) -> dict:
    item = json.loads(row.payload_json or '{}')
    item.update({'id':row.id, 'type':row.item_type, 'source_date':row.source_date.isoformat(), 'collected_date':row.collected_date.isoformat(),
                 'source_title':row.source_title, 'source_section':row.source_section, 'source_url':row.source_url,
                 'theme_code':row.theme_code, 'scene_code':row.scene_code, 'quality_score':row.quality_score,
                 'veto':row.veto, 'review_status':row.review_status, 'created_at':row.created_at.isoformat() if row.created_at else None})
    return item

def preview(db, items: list[dict], collected_date: date):
    results=[]; seen=set()
    for i,item in enumerate(items,1):
        try:
            row=normalize(item,collected_date)
            duplicate = row['fingerprint'] in seen or db.query(ShenlunMaterial.id).filter_by(fingerprint=row['fingerprint']).first() is not None
            seen.add(row['fingerprint'])
            results.append({'index':i,'status':'duplicate' if duplicate else 'ready','id':row['id'],'title':row['source_title'],'type':row['item_type'],'score':row['quality_score']})
        except (ValueError, TypeError) as exc: results.append({'index':i,'status':'invalid','error':str(exc)})
    return results

def save(db, item: dict, collected_date: date, actor: str, row=None):
    values=normalize(item,collected_date,actor)
    duplicate=db.query(ShenlunMaterial).filter_by(fingerprint=values['fingerprint']).first()
    if duplicate and (row is None or duplicate.id != row.id): raise ValueError('同来源同内容已存在')
    if row is None: row=ShenlunMaterial(**values); db.add(row)
    else:
        for key,value in values.items():
            if key not in ('id','created_by'): setattr(row,key,value)
    db.commit(); db.refresh(row); return row

def save_joint_ai_candidates(db, candidates: list[dict], article: dict, collected_date: date):
    """保存共用全文分析得到的申论候选；任何 AI 结果都只进入待审核状态。"""
    from sqlalchemy.exc import IntegrityError

    added = duplicates = invalid = quality_rejected = 0
    if len(candidates) > 3:
        invalid += len(candidates) - 3
        candidates = candidates[:3]
    body = str(article.get('body') or '')
    if not body:
        return {'added': 0, 'duplicates': 0, 'invalid': len(candidates), 'qualityRejected': 0}

    exact_types = {'golden', 'rhetoric', 'quote', 'policy_phrase', 'problem_line'}
    weights = RULES['quality_gate']['dimensions']
    for candidate in candidates:
        try:
            if not isinstance(candidate, dict):
                raise ValueError('候选格式错误')
            item = dict(candidate)
            item_type = item.get('type')
            theme_code = str(item.get('theme_code') or '')
            if theme_code not in RULES['themes'] and theme_code[:2] in RULES['themes']:
                item['theme_code'] = theme_code[:2]
            evidence = str(item.get('source_evidence') or '').strip()
            anchor = str(item.get('source_anchor') or '').strip()
            if not evidence or len(evidence) > 800 or evidence not in body:
                raise ValueError('原文证据无法逐字核验')
            if item_type in exact_types and (not item.get('text') or item['text'] not in evidence):
                raise ValueError('原句必须逐字出现在原文证据中')
            if item_type == 'template' and (not anchor or anchor not in evidence or anchor not in body):
                raise ValueError('模板句缺少可回查的原文句式锚点')
            if type(item.get('veto')) is not bool:
                raise ValueError('候选必须明确填写一票否决判断')

            item.update({
                'source_date': collected_date.isoformat(),
                'source_title': str(article.get('title') or '')[:300],
                'source_section': f"第{article.get('pageNo') or ''}版 {article.get('pageName') or ''}".strip(),
                'source_url': str(article.get('url') or ''),
                'source_evidence': evidence,
                'source_anchor': anchor,
                'review_status': 'pending',
                'veto': item['veto'],
                'collection_method': 'rmrb_joint_analysis',
            })
            breakdown = item.get('quality_breakdown')
            if not isinstance(breakdown, dict) or set(breakdown) != set(weights):
                # 提示词允许附带 total 展示字段，入库评分仍以七项权重之和为准。
                if isinstance(breakdown, dict) and set(breakdown) == set(weights) | {'total'}:
                    breakdown = {key: value for key, value in breakdown.items() if key in weights}
                    item['quality_breakdown'] = breakdown
                else:
                    raise ValueError('质量评分未覆盖全部维度')
            if any(type(v) is not int or v < 0 or v > weights[k] for k, v in breakdown.items()):
                raise ValueError('质量维度评分超出范围')
            score = sum(breakdown.values())
            item['quality_score'] = score
            if item['veto'] or score < RULES['quality_gate']['pass_score']:
                quality_rejected += 1
                continue

            if item_type == 'quote':
                speaker = str(item.get('speaker') or '').strip()
                context = str(item.get('context_15') or '').strip()
                if not speaker or speaker not in evidence or not context or len(context) > 500 or item['text'] not in context or context not in body:
                    raise ValueError('语录说话人或前后文无法核验')
                item['verified'] = True

            values = normalize(item, collected_date, actor='ai:rmrb_joint_analysis')
            existing = db.query(ShenlunMaterial.id).filter_by(fingerprint=values['fingerprint']).first()
            if existing:
                duplicates += 1
                continue
            with db.begin_nested():
                db.add(ShenlunMaterial(**values))
                db.flush()
            added += 1
        except (ValueError, TypeError, KeyError, IntegrityError):
            invalid += 1
    db.commit()
    return {'added': added, 'duplicates': duplicates, 'invalid': invalid, 'qualityRejected': quality_rejected}

def seed_curated_materials(db):
    """将仓库内的首批已筛选样本以待审核状态幂等导入。"""
    seed_path = Path(__file__).resolve().parents[1] / 'seed_data' / 'shenlun_materials_2026-10-15.json'
    if not seed_path.exists(): return 0
    seed = json.loads(seed_path.read_text(encoding='utf-8'))
    collected_date = date.fromisoformat(seed['collected_date'])
    added = 0
    for item in seed.get('items', []):
        values = normalize(item, collected_date, 'seed:2026-10-15')
        if db.query(ShenlunMaterial.id).filter_by(fingerprint=values['fingerprint']).first(): continue
        db.add(ShenlunMaterial(**values)); added += 1
    if added: db.commit()
    return added
