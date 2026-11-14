import json

from app.classification import Features, grounded_features
from .conftest import ANALYSIS, OTHER, auth


def test_experiences_require_quoted_explicit_evidence_not_mood():
    f = Features(version=1, genres=['fantasy','fantasy'], experiences=[
        {'kind':'lucid', 'quote':'Rüyada olduğumu fark ettim.'},
        {'kind':'recurring', 'quote':'Aynı rüyayı tekrar gördüm.'},
        {'kind':'nightmare', 'quote':'Çok korktum.'},
    ])
    result = grounded_features(f, 'Rüyada olduğumu fark ettim. Aynı rüyayı tekrar gördüm. Çok korktum.')
    assert result.genres == ['fantasy']
    assert [e.kind for e in result.experiences] == ['lucid','recurring']
    assert grounded_features(f, 'Ormanda yürüyordum.').experiences == []
    negative = Features(experiences=[{'type':'lucid','quote':'Rüyada olduğumu fark etmedim.'}])
    assert grounded_features(negative, 'Rüyada olduğumu fark etmedim.').experiences == []
    assert negative.model_dump()['experiences'][0]['kind'] == 'lucid'


def test_analyze_extracts_and_persists_features_and_owner_corrections(api):
    client, s = api
    narrative = 'Rüyada olduğumu fark ettim. Annemle uzay gemisinde uçuyordum.'
    s.llm.reply = json.dumps({**ANALYSIS, 'features': {'version':1, 'genres':['scifi','adventure'], 'perspective':'first-person',
        'people':['annem'], 'places':['uzay gemisi'], 'events':['uçmak'], 'experiences':[{'kind':'lucid','quote':'Rüyada olduğumu fark ettim.'}]}})
    analysis = client.post('/api/v1/analyze', headers=auth(), json={'text':narrative}).json()
    assert analysis['features']['genres'] == ['scifi','adventure']
    saved = client.post('/api/v1/dreams', headers=auth(), json={**analysis,'originalText':narrative}).json()
    assert saved['features']['people'] == ['annem']
    path = f"/api/v1/dreams/{saved['id']}/journal"
    corrected = client.patch(path, headers=auth(), json={'revision':saved['revision'], 'classification':{'genres':[], 'experiences':[], 'tags':['aile']}, 'recall':'fragmentary'}).json()
    assert corrected['journal']['classification']['genres'] == []
    assert corrected['features']['genres'] == ['scifi','adventure']  # retain model provenance
    assert corrected['journal']['recall'] == 'fragmentary'
    assert client.patch(path, headers=auth(OTHER), json={'revision':corrected['revision'],'classification':None}).status_code == 404
    updated = client.patch(path, headers=auth(), json={'revision':corrected['revision'],'refresh':True}).json()
    assert updated['journal']['classification']['tags'] == ['aile']
    for value in ({'genres':['astrology']}, {'perspective':'diagnosis'}, {'tags':['x'*81]}):
        assert client.patch(path, headers=auth(), json={'revision':updated['revision'],'classification':value}).status_code == 400
    reset = client.patch(path, headers=auth(), json={'revision':updated['revision'],'classification':None}).json()
    assert reset['journal']['classification'] is None and reset['journal']['recall'] == 'fragmentary'


def test_old_records_do_not_acquire_invented_classifications(api):
    client, _ = api
    saved = client.post('/api/v1/dreams', headers=auth(), json={**ANALYSIS,'originalText':'Bir ev.'}).json()
    assert saved['features']['version'] == 0 and saved['features']['genres'] == []


def test_english_claims_match_despite_turkish_lower_casing():
    # normalized() lowers I to ı; English markers ('knew i was dreaming') must still be found
    text = 'I knew I was dreaming, so I flew. I had the same dream again.'
    f = Features(experiences=[{'kind': 'lucid', 'quote': 'I knew I was dreaming'}, {'kind': 'recurring', 'quote': 'I had the same dream again'}])
    assert [e.kind for e in grounded_features(f, text).experiences] == ['lucid', 'recurring']
