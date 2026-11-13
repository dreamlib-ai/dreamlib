from uuid import uuid4

from .conftest import ANALYSIS, OTHER, auth


def create(client):
    return client.post('/api/dreams', headers=auth(), json={**ANALYSIS, 'originalText': 'Ormanda yürüyordum.'}).json()


def patch(client, dream, **body):
    return client.patch(f"/api/dreams/{dream['id']}/journal", headers=auth(), json={'revision': dream['revision'], **body})


def test_edit_preserves_first_recollection_date_and_does_not_duplicate(api):
    client, _ = api
    original = create(client)
    edited = patch(client, original, title='Eski orman', originalText='Ormanda bir arkadaşım vardı.', dreamedOn='2026-10-20', favorite=True, reflection='Bana bir gezimizi hatırlattı.').json()
    assert edited['id'] == original['id'] and edited['createdAt'] == original['createdAt']
    assert edited['journal']['firstText'] == original['originalText']
    assert edited['journal']['analysisStale'] and edited['journal']['favorite']
    assert edited['journal']['dreamedOn'] == '2026-10-20'
    assert patch(client, original, title='Stale edit').status_code == 409
    assert len(client.get('/api/dreams', headers=auth()).json()['dreams']) == 1
    assert client.patch(f"/api/dreams/{original['id']}/journal", headers=auth(OTHER), json={'revision': 0, 'favorite': True}).status_code == 404
    assert client.patch(f"/api/dreams/{original['id']}/journal", json={'revision': 0}).status_code == 401


def test_addition_is_timestamped_and_refresh_excludes_reflection(api):
    client, s = api
    d = create(client)
    addition = {'id': str(uuid4()), 'text': 'Sonra bir deniz gördüm.'}
    d = patch(client, d, addition=addition, reflection='PRIVATE THOUGHT').json()
    assert d['journal']['entries'][0]['createdAt']
    assert d['journal']['analysisStale'] and len(d['journal']['entries']) == 1
    d = patch(client, d, addition=addition).json()
    assert len(d['journal']['entries']) == 1
    messages = []
    original_reply = s.llm.reply
    s.llm.reply = lambda batch: (messages.extend(batch), original_reply)[1]
    d = patch(client, d, refresh=True).json()
    assert not d['journal']['analysisStale']
    assert 'Sonra bir deniz' in str(messages) and 'PRIVATE THOUGHT' not in str(messages)
    assert d['originalText'] == 'Ormanda yürüyordum.'


def test_journal_validation_and_booklet_save_preserve_preferences(api):
    client, _ = api
    d = create(client)
    for fields in ({'dreamedOn': '2999-01-01'}, {'title': '  '}, {'reflection': 'x' * 4001}, {'originalText': ' '}, {'user_id': OTHER}):
        assert patch(client, d, **fields).status_code == 400
    d = patch(client, d, favorite=True, reflection='Notum').json()
    # A capture retry using the same identity must preserve journal fields.
    saved = client.put(f"/api/dreams/{uuid4()}", headers=auth(), json={**ANALYSIS, 'originalText': 'Rüya'}).json()
    saved = patch(client, saved, favorite=True).json()
    res = client.put(f"/api/dreams/{saved['id']}?existing=true", headers=auth(), json={**ANALYSIS, 'originalText': 'Rüya'}).json()
    assert res['journal']['favorite'] and res['revision'] > saved['revision']
    current = patch(client, res, originalText='A newly remembered version.').json()
    stale_capture = client.put(f"/api/dreams/{saved['id']}?existing=true", headers=auth(), json={**ANALYSIS, 'originalText': 'Rüya'})
    assert stale_capture.status_code == 409
    assert client.get(f"/api/dreams/{saved['id']}", headers=auth()).json()['originalText'] == current['originalText']
