"""每日金句管理与可重入导入；结构化属性均经过白名单校验。"""
import hashlib
import json
import re
from datetime import date
from urllib.parse import urlsplit, urlunsplit
from sqlalchemy import or_
from app.models import DailyQuote, DailyQuoteSelection, DailyQuoteJob
from app.models.base import utcnow

COMPONENTS = {'开头点题', '分论点标题', '论证句', '结尾升华'}
STATUSES = {'pending', 'confirmed', 'archived'}


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
    attrs = {'sourceUrl': url, 'articleTitle': string(item.get('articleTitle', item.get('title', '')), 256),
             'articleDate': published, 'source': string(item.get('source', ''), 160), 'author': string(item.get('author', ''), 128),
             'component': component, 'topics': strings(item.get('topics', [item['tag']] if item.get('tag') else [])),
             'use': string(item.get('use', kind), 256), 'formula': string(item.get('formula', ''), 1000),
             'why': string(item.get('why', ''), 1000), 'guidance': string(item.get('guidance', ''), 1000),
             'pitfall': string(item.get('pitfall', ''), 1000), 'quoteType': string(item.get('quoteType', item.get('quote_type', item.get('quote_type_label', '完整句'))), 40),
             'evidence': evidence, 'evidenceLocation': string(item.get('evidenceLocation', ''), 128),
             'fetchedAt': string(item.get('fetchedAt', ''), 64), 'highlights': highlights, 'examples': results}
    # 协议与标点规范化仅用于去重，保留text和出处原样。
    canonical = u.netloc.lower() + u.path.rstrip('/')
    fingerprint = hashlib.sha256((canonical + '|' + re.sub(r'[\W_]+', '', text)).encode()).hexdigest()
    return text, attrs, fingerprint


def out(row, selected=False):
    return {'id': row.id, 'text': row.text, **parse(row.attributes_json), 'collectedDate': row.collected_date.isoformat(),
            'reviewStatus': row.review_status, 'reviewedBy': row.reviewed_by, 'reviewedAt': row.reviewed_at,
            'selected': selected, 'updatedAt': row.updated_at}


def listing(db, start=None, end=None, q='', topic='', component='', status='', selected='', selection_date=None, page=1, page_size=20):
    query = db.query(DailyQuote)
    if start: query = query.filter(DailyQuote.collected_date >= start)
    if end: query = query.filter(DailyQuote.collected_date <= end)
    if q: query = query.filter(or_(DailyQuote.text.contains(q), DailyQuote.attributes_json.contains(q)))
    if status: query = query.filter(DailyQuote.review_status == status)
    # JSON属性使用内存精确匹配，避免主题字串匹配错误；全文从未入库。
    rows = query.order_by(DailyQuote.collected_date.desc(), DailyQuote.created_at, DailyQuote.id).all()
    sid = selection_date or utcnow().date()
    selected_ids = {x.quote_id for x in db.query(DailyQuoteSelection).filter_by(issue_date=sid)}
    rows = [x for x in rows if (not topic or topic in parse(x.attributes_json).get('topics', []) or any(e['topic'] == topic for e in parse(x.attributes_json).get('examples', []))) and (not component or parse(x.attributes_json).get('component') == component) and (selected != 'yes' or x.id in selected_ids) and (selected != 'no' or x.id not in selected_ids)]
    stats = {'quotes': len(rows), 'sources': len({parse(x.attributes_json).get('sourceUrl') for x in rows}), 'examples': sum(len(parse(x.attributes_json).get('examples', [])) for x in rows), 'selected': sum(x.id in selected_ids for x in rows)}
    return {'items': [out(x, x.id in selected_ids) for x in rows[(page-1)*page_size:page*page_size]], 'total': len(rows), 'stats': stats}


def save(db, item, collected_date, row=None, reviewer='', commit=True):
    text, attrs, fingerprint = normalize(item, collected_date)
    status = item.get('reviewStatus', 'pending')
    if status not in STATUSES: raise ValueError('审核状态无效')
    if status == 'confirmed' and (not attrs['evidence'] or not attrs['articleTitle']):
        raise ValueError('确认金句须有原文证据摘录及标题')
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
    row.collected_date, row.review_status = collected_date, status
    row.reviewed_by = reviewer if status == 'confirmed' else ''
    row.reviewed_at = utcnow() if status == 'confirmed' else None
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
