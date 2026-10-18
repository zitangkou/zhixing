from copy import deepcopy

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import WechatReplyConfiguration, WechatReplyRelease
from app.schemas.wechat_reply import WechatReplyConfig
from app.services.wechat_official_service import default_reply_config
from app.services.wechat_promotion_service import promotion_config
from app.services.wechat_reply_service import (
    preview_reply, validate_reply_config, save_reply_draft, publish_reply_draft,
    rollback_reply_release, load_active_reply_config,
)


def test_import_preserves_materials_custom_rules_and_existing_instructions():
    old = default_reply_config()
    old['keywordRules'][0]['keywords'].append('每日打卡题')
    old['keywordRules'][2]['keywords'].append('申论！')
    old['keywordRules'].append(dict(id='custom', name='专项', keywords=['专项资料'], responseText='人工资料链接', enabled=True, matchType='exact', priority=100))
    before = deepcopy(old)
    new = promotion_config(old)
    assert old == before
    assert next(r for r in new['keywordRules'] if r['id'] == 'fifteen_five') == next(r for r in old['keywordRules'] if r['id'] == 'fifteen_five')
    assert new['keywordRules'][-1] == old['keywordRules'][-1]
    assert '每日打卡题' in next(r for r in new['keywordRules'] if r['id'] == 'today')['keywords']
    new['promotionEntries'][0]['instruction'] = '运营修改的打开说明'
    assert promotion_config(new)['promotionEntries'][0]['instruction'] == '运营修改的打开说明'
    assert validate_reply_config(new)['valid']
    assert WechatReplyConfig.model_validate(new).model_dump()['promotionEntries']


@pytest.mark.parametrize(('word', 'intent'), [('1', 'today'), ('2', 'theory'), ('3', 'rmrb'), ('0', 'menu'), ('申论！', 'shenlun'), (' 金句 ', 'quotes'), ('十五五', 'fifteen_five'), ('框架', 'knowledge'), ('速算', 'quick_calc')])
def test_no_menu_account_routes_and_old_keywords(word, intent):
    result = preview_reply(promotion_config(default_reply_config()), word, 'text', '', '')
    assert result['intent'] == intent
    assert '下方菜单' not in result['reply']
    assert 'pages/' not in result['reply']


def test_disabled_entry_falls_back_and_bad_bindings_block_publication():
    config = promotion_config(default_reply_config())
    entry = next(e for e in config['promotionEntries'] if e['id'] == 'quotes')
    entry['enabled'] = False
    entry['fallbackText'] = '金句维护中，请先使用每日练习。'
    reply = preview_reply(config, '金句', 'text', '', '')['reply']
    assert entry['fallbackText'] in reply
    assert entry['instruction'] not in reply
    entry['pagePath'] = 'pages/not-real'
    assert not validate_reply_config(config)['valid']
    config['keywordRules'][0]['entryId'] = 'missing'
    assert any('不存在' in e for e in validate_reply_config(config)['errors'])


def test_draft_publish_and_rollback_restore_entry_and_rule_together():
    engine = create_engine('sqlite://')
    WechatReplyConfiguration.__table__.create(engine)
    WechatReplyRelease.__table__.create(engine)
    with Session(engine) as db:
        initial = load_active_reply_config(db)[0]
        new = promotion_config(initial)
        saved = save_reply_draft(db, new, None, '测试')
        old_release = saved['activeReleaseId']
        assert not load_active_reply_config(db)[0].get('promotionEntries')
        publish_reply_draft(db, None, '测试')
        assert load_active_reply_config(db)[0]['promotionEntries'] == new['promotionEntries']
        rollback_reply_release(db, old_release, None, '测试')
        assert not load_active_reply_config(db)[0].get('promotionEntries')
        assert validate_reply_config(load_active_reply_config(db)[0])['valid']
