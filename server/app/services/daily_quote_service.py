"""每日金句管理与可重入导入；结构化属性均经过白名单校验。"""
import hashlib
import json
import re
from datetime import date
from urllib.parse import urlsplit, urlunsplit
from sqlalchemy import or_
from app.models import DailyQuote, DailyQuoteSelection, DailyQuoteFeedback, DailyQuoteJob
from app.models.base import utcnow

COMPONENTS = {'开头点题', '分论点标题', '论证句', '结尾升华'}
STATUSES = {'pending', 'confirmed', 'archived'}
FEEDBACK_REASONS = {
    'too_abstract': '过于宏观或抽象',
    'too_narrow': '主题过窄或术语过多',
    'context_dependent': '依赖上下文或摘录不完整',
    'ordinary_expression': '表达普通、亮点不足',
    'weak_argument': '论证价值弱、容易成为口号',
    'repetitive': '与已选句主题或来源重复',
    'evidence_concern': '原文证据或出处有疑问',
    'student_perspective': '贴近考生视角',
    'actionable': '具体、可落到行动',
    'memorable': '表达有亮点、易记易用',
    'theme_balance': '与其他句子主题互补',
}


def dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def parse(value, fallback=None):
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return {} if fallback is None else fallback


def string(value, limit=1000):
    if not isinstance(value, str):
        raise ValueError('文本字段必须是字符串')
    if len(value) > limit:
        raise ValueError(f'文本超过{limit}字')
    return value.strip()


def strings(value, limit=20):
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError('标签须为数组且不能过多')
    return list(dict.fromkeys(string(x, 80) for x in value if x))


def normalize(item, collected_date):
    if not isinstance(item, dict):
        raise ValueError('每条金句须为对象')
    text = string(item.get('text', item.get('quote', '')), 500)
    if not text:
        raise ValueError('原句不能为空')
    raw_url = string(item.get('sourceUrl', item.get('url', '')), 1000)
    u = urlsplit(raw_url)
    if u.scheme not in {'http', 'https'} or not u.hostname or u.username or u.password:
        raise ValueError('须填写有效的原文http/https链接')
    url = urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path, '', ''))
    published = item.get('articleDate', item.get('publishedDate', collected_date.isoformat()))
    published = date.fromisoformat(published).isoformat()
    kind = string(item.get('component', item.get('kind', '论证句')), 80)
    # 精选文件可能含“分论点标题 / 论证句”，列表展示首类，保留用途完整文本。
    component = kind.split('/')[0].strip().strip('【】')
    if component not in COMPONENTS:
        raise ValueError('构件须为开头点题、分论点标题、论证句或结尾升华')
    examples = item.get('examples', [])
    if not isinstance(examples, list) or len(examples) > 10:
        raise ValueError('仿写须为数组，最多10条')
    results = []
    for x in examples:
        if isinstance(x, (list, tuple)) and len(x) == 2:
            x = {'topic': x[0], 'text': x[1]}
        if not isinstance(x, dict):
            raise ValueError('仿写示例格式不正确')
        topic, body = string(x.get('topic', ''), 80), string(x.get('text', ''), 2000)
        if not topic or not body:
            raise ValueError('每条仿写须填写主题和正文')
        highlights = strings(x.get('highlights', []))
        if any(w not in body for w in highlights):
            raise ValueError('仿写高亮词须出现在对应正文中')
        results.append({'topic': topic, 'text': body, 'shortText': string(x.get('shortText', ''), 500), 'highlights': highlights})
    evidence = string(item.get('evidence', ''), 1800)
    if evidence and text not in evidence:
        raise ValueError('原句必须逐字出现在证据摘录中')
    highlights = strings(item.get('highlights', item.get('highlight', [])))
    if any(w not in text for w in highlights):
        raise ValueError('原句高亮词须出现在原句中')
    scores = item.get('scores', {})
    if not isinstance(scores, dict):
        scores = {}
    normalized_scores = {}
    for key in ('memory', 'logic', 'transfer', 'spark', 'roleFit'):
        value = scores.get(key)
        if type(value) is int and 0 <= value <= 5:
            normalized_scores[key] = value
    attrs = {'sourceUrl': url, 'articleTitle': string(item.get('articleTitle', item.get('title', '')), 256),
             'articleDate': published, 'source': string(item.get('source', ''), 160), 'author': string(item.get('author', ''), 128),
             'component': component, 'topics': strings(item.get('topics', [item['tag']] if item.get('tag') else [])),
             'use': string(item.get('use', kind), 256), 'formula': string(item.get('formula', ''), 1000),
             'why': string(item.get('why', ''), 1000), 'guidance': string(item.get('guidance', ''), 1000),
             'pitfall': string(item.get('pitfall', ''), 1000), 'roleFitReason': string(item.get('roleFitReason', ''), 120),
             'quoteType': string(item.get('quoteType', item.get('quote_type', item.get('quote_type_label', '完整句'))), 40),
             'evidence': evidence, 'evidenceLocation': string(item.get('evidenceLocation', ''), 128),
             'fetchedAt': string(item.get('fetchedAt', ''), 64), 'highlights': highlights, 'examples': results,
             'scores': normalized_scores}
    # 人民日报同一篇社论可能以不同版面链接重复发布。优先用刊发日期、规范化标题
    # 与原句去重；缺少标题时退回来源URL。页面原文与链接仍完整保留供核对。
    article_title = attrs['articleTitle']
    title_key = re.sub(r'^(?:人民日报)?(?:社论|评论员文章|评论员观察)\s*[:：]?\s*', '', article_title)
    title_key = re.sub(r'[\s\W_]+', '', title_key)
    canonical = (published + '|' + title_key) if title_key else u.netloc.lower() + u.path.rstrip('/')
    fingerprint = hashlib.sha256((canonical + '|' + re.sub(r'[\W_]+', '', text)).encode()).hexdigest()
    return text, attrs, fingerprint


def out(row, selected=False):
    return {'id': row.id, 'text': row.text, **parse(row.attributes_json), 'collectedDate': row.collected_date.isoformat(),
            'reviewStatus': row.review_status, 'auditStatus': row.audit_status or 'pending', 'enabled': bool(row.enabled),
            'reviewedBy': row.reviewed_by, 'reviewedAt': row.reviewed_at,
            'selected': selected, 'updatedAt': row.updated_at}


def _upsert_feedback(db, issue_date, quote_id, decision, reason_codes=None, note='', reviewer=''):
    codes = list(dict.fromkeys(code for code in (reason_codes or []) if code in FEEDBACK_REASONS))
    row = db.query(DailyQuoteFeedback).filter_by(issue_date=issue_date, quote_id=quote_id).first()
    if row is None:
        row = DailyQuoteFeedback(issue_date=issue_date, quote_id=quote_id)
        db.add(row)
    row.decision = decision
    row.reason_codes_json = dump(codes)
    row.note = string(note, 500)
    row.reviewer = string(reviewer, 128)
    row.updated_at = utcnow()
    return row


def record_quote_review(db, row, decision, reason_codes=None, note='', reviewer=''):
    if decision not in {'passed', 'rejected'}:
        raise ValueError('审核结论无效')
    codes = list(reason_codes or [])
    if any(code not in FEEDBACK_REASONS for code in codes):
        raise ValueError('复核原因无效')
    if decision == 'rejected' and not codes and not note.strip():
        raise ValueError('退回金句请至少选择一个原因或填写说明')
    if decision == 'rejected':
        return _upsert_feedback(db, row.collected_date, row.id, 'rejected', codes, note, reviewer)
    existing = db.query(DailyQuoteFeedback).filter_by(issue_date=row.collected_date, quote_id=row.id, decision='rejected').first()
    if existing:
        existing.decision = 'not_selected'
        existing.reason_codes_json = '[]'
        existing.note = ''
        existing.reviewer = string(reviewer, 128)
        existing.updated_at = utcnow()
    return None


def record_daily_selection_feedback(db, issue_date, rows, selected_ids, reason_codes=None,
                                    not_selected_reason_codes=None, reviewer=''):
    codes = list(reason_codes or [])
    not_selected_codes = list(not_selected_reason_codes or [])
    if any(code not in FEEDBACK_REASONS for code in codes + not_selected_codes):
        raise ValueError('精选理由无效')
    selected = set(selected_ids)
    for row in rows:
        _upsert_feedback(db, issue_date, row.id,
                         'selected' if row.id in selected else 'not_selected',
                         codes if row.id in selected else not_selected_codes, '', reviewer)


def feedback_prompt(db, days=90):
    """仅将跨日期反复出现的人工理由作为排序提示，避免单日选择造成过拟合。"""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    cutoff = datetime.now(ZoneInfo('Asia/Shanghai')).date() - timedelta(days=days)
    rows = db.query(DailyQuoteFeedback).filter(DailyQuoteFeedback.issue_date >= cutoff).all()
    meaningful = [row for row in rows if row.decision == 'selected' or
                  (row.decision in {'not_selected', 'rejected'} and parse(row.reason_codes_json, []))]
    active_dates = {row.issue_date for row in meaningful}
    if len(active_dates) < 3 or len(meaningful) < 6:
        return ''
    selected_counts, rejected_counts = {}, {}
    for row in rows:
        target = selected_counts if row.decision == 'selected' else rejected_counts if row.decision in {'not_selected', 'rejected'} else None
        if target is None:
            continue
        for code in parse(row.reason_codes_json, []):
            if code in FEEDBACK_REASONS:
                target[code] = target.get(code, 0) + 1
    preferred = [FEEDBACK_REASONS[k] for k, n in sorted(selected_counts.items(), key=lambda pair: -pair[1]) if n >= 3][:4]
    avoid = [FEEDBACK_REASONS[k] for k, n in sorted(rejected_counts.items(), key=lambda pair: -pair[1]) if n >= 3][:4]
    if not preferred and not avoid:
        return ''
    lines = ['跨日期人工复核反馈（至少3个刊期后才纳入，作为排序提示，不覆盖证据门槛）：']
    if preferred:
        lines.append('反复入选特征：' + '、'.join(preferred) + '。')
    if avoid:
        lines.append('反复未入选/退回原因：' + '、'.join(avoid) + '。')
    return '\n'.join(lines) + '\n'


def listing(db, start=None, end=None, q='', topic='', component='', status='', selected='', selection_date=None, page=1, page_size=20):
    query = db.query(DailyQuote)
    if start: query = query.filter(DailyQuote.collected_date >= start)
    if end: query = query.filter(DailyQuote.collected_date <= end)
    if q: query = query.filter(or_(DailyQuote.text.contains(q), DailyQuote.attributes_json.contains(q)))
    if status: query = query.filter(DailyQuote.review_status == status)
    # JSON属性使用内存精确匹配，避免主题字串匹配错误；全文从未入库。
    rows = query.order_by(DailyQuote.collected_date.desc(), DailyQuote.created_at, DailyQuote.id).all()
    def rank(row):
        values = parse(row.attributes_json).get('scores', {})
        if not isinstance(values, dict): return 0.0
        score = lambda key: values.get(key, 0) if type(values.get(key, 0)) is int and 0 <= values.get(key, 0) <= 5 else 0
        if 'roleFit' in values:
            return (score('transfer') * 0.25 + score('logic') * 0.25 +
                    score('spark') * 0.20 + score('memory') * 0.10 + score('roleFit') * 0.20)
        return (score('transfer') * 0.30 + score('logic') * 0.30 +
                score('spark') * 0.25 + score('memory') * 0.15)
    rows.sort(key=lambda row: (-row.collected_date.toordinal(), -rank(row), row.created_at, row.id))
    sid = selection_date or utcnow().date()
    selected_ids = {x.quote_id for x in db.query(DailyQuoteSelection).filter_by(issue_date=sid)}
    rows = [x for x in rows if (not topic or topic in parse(x.attributes_json).get('topics', []) or any(e['topic'] == topic for e in parse(x.attributes_json).get('examples', []))) and (not component or parse(x.attributes_json).get('component') == component) and (selected != 'yes' or x.id in selected_ids) and (selected != 'no' or x.id not in selected_ids)]
    stats = {'quotes': len(rows), 'sources': len({parse(x.attributes_json).get('sourceUrl') for x in rows}), 'examples': sum(len(parse(x.attributes_json).get('examples', [])) for x in rows), 'selected': sum(x.id in selected_ids for x in rows)}
    page_rows = rows[(page-1)*page_size:page*page_size]
    feedback_rows = db.query(DailyQuoteFeedback).filter(DailyQuoteFeedback.quote_id.in_([x.id for x in page_rows])).all() if page_rows else []
    feedback_by_id = {}
    for feedback in feedback_rows:
        summary = feedback_by_id.setdefault(feedback.quote_id, {'selected': 0, 'notSelected': 0, 'rejected': 0, 'reasons': [], 'selectedReasons': [], 'notSelectedReasons': []})
        if feedback.decision == 'selected':
            summary['selected'] += 1
            summary['selectedReasons'].extend(parse(feedback.reason_codes_json, []))
        elif feedback.decision == 'not_selected':
            summary['notSelected'] += 1
            summary['notSelectedReasons'].extend(parse(feedback.reason_codes_json, []))
        elif feedback.decision == 'rejected':
            summary['rejected'] += 1
            summary['reasons'].extend(parse(feedback.reason_codes_json, []))
    return {'items': [{**out(x, x.id in selected_ids), 'recommendationScore': round(rank(x), 2),
                       'humanFeedback': feedback_by_id.get(x.id, {'selected': 0, 'notSelected': 0, 'rejected': 0, 'reasons': [], 'selectedReasons': [], 'notSelectedReasons': []})}
                      for x in page_rows], 'total': len(rows), 'stats': stats}


def save(db, item, collected_date, row=None, reviewer='', commit=True):
    text, attrs, fingerprint = normalize(item, collected_date)
    status = item.get('reviewStatus', 'pending')
    if status not in STATUSES: raise ValueError('审核状态无效')
    audit = item.get('auditStatus') or (row.audit_status if row else None) or 'pending'
    if audit not in {'pending', 'passed', 'rejected'}:
        raise ValueError('审核结果无效')
    enabled = bool(item.get('enabled', row.enabled if row else False))
    if enabled and audit != 'passed':
        raise ValueError('请先审核通过，再启用')
    if enabled and (not attrs['evidence'] or not attrs['articleTitle']):
        raise ValueError('启用金句须有原文证据摘录及标题')
    if status == 'confirmed' and not enabled:
        status = 'pending'
    if row is None:
        row = DailyQuote(text=text, collected_date=collected_date, fingerprint=fingerprint)
        db.add(row)
    previous = parse(row.attributes_json) if row.id else {}
    history = previous.get('history', [])
    changed = [k for k in attrs if previous.get(k) != attrs[k]]
    if row.id and row.text != text: changed.append('text')
    if row.id and row.review_status != status: changed.append('reviewStatus')
    if changed:
        history = history + [{'at': utcnow().isoformat(), 'actor': reviewer or '导入/任务', 'fields': changed,
                              'previous': {k: previous.get(k) for k in changed if k in previous}}]
    attrs['history'] = history[-30:]
    row.text, row.attributes_json, row.fingerprint = text, dump(attrs), fingerprint
    row.collected_date = collected_date
    row.audit_status = audit
    row.enabled = enabled
    row.review_status = 'confirmed' if enabled else status
    row.reviewed_by = reviewer if audit == 'passed' else ''
    row.reviewed_at = utcnow() if audit == 'passed' else None
    if status == 'archived' and row.id:
        db.query(DailyQuoteSelection).filter_by(quote_id=row.id).delete()
    db.flush()
    if commit: db.commit(); db.refresh(row)
    return row


def preview_import(db, items, collected_date):
    if not isinstance(items, list) or not 1 <= len(items) <= 500:
        raise ValueError('导入须为1—500条的数组')
    seen = set(); output = []
    for i, item in enumerate(items):
        try:
            text, attrs, fp = normalize(item, collected_date)
            duplicate = fp in seen or db.query(DailyQuote.id).filter_by(fingerprint=fp).first() is not None
            seen.add(fp)
            output.append({'index': i, 'text': text, 'status': 'duplicate' if duplicate else 'new', 'evidenceMissing': not bool(attrs['evidence'])})
        except (ValueError, TypeError) as exc:
            output.append({'index': i, 'status': 'invalid', 'error': str(exc)})
    return output


def import_items(db, items, collected_date):
    checks = preview_import(db, items, collected_date)
    if any(x['status'] == 'invalid' for x in checks): raise ValueError('存在无效条目，请修正后导入')
    added = 0
    for check in checks:
        if check['status'] == 'new':
            item = dict(items[check['index']]); item['reviewStatus'] = 'pending'
            save(db, item, collected_date, commit=False); added += 1
    db.commit()
    return {'added': added, 'skipped': len(checks)-added}
