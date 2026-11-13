"""Explicit live smoke using disposable synthetic accounts, never existing user records."""
import argparse
import os
import secrets
import sys
from pathlib import Path
from uuid import uuid4

parser = argparse.ArgumentParser()
parser.add_argument('--run', action='store_true', help='Create temporary accounts, test, then remove only those accounts')
parser.add_argument('--settings-root', type=Path, required=True, help='Backend folder containing the normal app configuration')
parser.add_argument('--classification-eval', action='store_true', help='Also evaluate synthetic classification cases with the real model')
args = parser.parse_args()
if not args.run:
    raise SystemExit('Pass --run to execute the live smoke.')
sys.path.insert(0, str(args.settings_root.resolve()))
from app.config import load_settings
import httpx

settings = load_settings()
expected = os.environ.get('DREAMLIB_LIVE_SUPABASE_URL', '')
assert expected and settings.supabase_url == expected, 'set DREAMLIB_LIVE_SUPABASE_URL to the live project URL'
assert settings.supabase_service_key
api = os.environ.get('DREAMLIB_LIVE_API', 'https://dreamlib.cenker.dev')
admin = {'apikey': settings.supabase_service_key, 'Authorization': 'Bearer ' + settings.supabase_service_key}
created = []
# Use the same direct public endpoints as the browser, not a workstation HTTP proxy.
with httpx.Client(timeout=65, trust_env=False, transport=httpx.HTTPTransport(local_address='0.0.0.0')) as client:
    try:
        tokens = []
        for _ in range(2):
            email, password = f'journal-smoke-{uuid4().hex}@example.invalid', secrets.token_urlsafe(32)
            response = client.post(settings.supabase_url + '/auth/v1/admin/users', headers=admin, json={'email': email, 'password': password, 'email_confirm': True})
            response.raise_for_status()
            created.append(response.json()['id'])
            response = client.post(settings.supabase_url + '/auth/v1/token?grant_type=password', headers={'apikey': settings.supabase_service_key}, json={'email': email, 'password': password})
            response.raise_for_status()
            tokens.append(response.json()['access_token'])
        owner, other = ({'Authorization': 'Bearer ' + token} for token in tokens)
        did = str(uuid4())
        route = api + '/api/dreams/' + did
        response = client.put(route, headers=owner, json={'title': 'Synthetic sea dream', 'originalText': 'I walked beside a calm sea.'})
        response.raise_for_status()
        dream = response.json()
        changes = {'revision': dream['revision'], 'favorite': True, 'dreamedOn': '2026-10-29', 'reflection': 'Synthetic private thought', 'originalText': 'I walked beside a calm sea and saw a forest.'}
        response = client.patch(route + '/journal', headers=owner, json=changes)
        response.raise_for_status()
        dream = response.json()
        assert dream['journal']['favorite'] and dream['journal']['firstText'] == 'I walked beside a calm sea.'
        assert dream['journal']['dreamedOn'] == '2026-10-29' and dream['journal']['analysisStale']
        assert client.patch(route + '/journal', headers=owner, json=changes).status_code == 409
        assert client.patch(route + '/journal', headers=other, json={'revision': dream['revision'], 'favorite': False}).status_code == 404
        assert client.get(route, headers=other).status_code == 404
        response = client.patch(route + '/journal', headers=owner, json={'revision': dream['revision'], 'addition': {'id': str(uuid4()), 'text': 'A friend was waiting at the shore.'}})
        response.raise_for_status()
        dream = response.json()
        assert len(dream['journal']['entries']) == 1
        response = client.patch(route + '/journal', headers=owner, json={'revision': dream['revision'], 'refresh': True})
        response.raise_for_status()
        dream = response.json()
        assert dream['interpretation'] and not dream['journal']['analysisStale']
        if args.classification_eval:
            cases = [
                ('Rüyada olduğumu fark ettim. Annemle uzay gemisinde Mars\u2019a uçuyordum.', 'scifi', {'lucid'}),
                ('Otobüsü kaçırdım. İşe geç kaldığım için çok korktum.', 'daily', set()),
                ('Aynı rüyayı tekrar gördüm. Bu bir kâbustu. Eski evimde bir gölge beni kovalıyordu.', None, {'recurring','nightmare'}),
                ('I did not realize I was dreaming. I was afraid, but it was not a nightmare. I was waiting for a bus.', None, set()),
            ]
            for index, (narrative, genre, expected) in enumerate(cases, 1):
                response = client.post(api + '/api/analyze', headers=owner, json={'text':narrative})
                if response.status_code != 200:
                    print('Classification case', index, 'failed:', response.status_code, response.json().get('error','request failed'))
                response.raise_for_status()
                features = response.json()['features']
                assert features['version'] == 1
                assert not genre or genre in features['genres'], (genre,features['genres'])
                assert {e['kind'] for e in features['experiences']} == expected, (expected,features['experiences'])
                print('Classification case', index, 'PASS')
            response = client.patch(route + '/journal', headers=owner, json={'revision':dream['revision'], 'classification': {'genres':['daily'], 'experiences':[], 'tags':['family']}, 'recall':'fragmentary'})
            response.raise_for_status()
            dream = response.json()
            assert dream['journal']['classification']['genres'] == ['daily']
            assert dream['journal']['recall'] == 'fragmentary'
            assert dream['features']['version'] == 1
            print('PASS: four real-model classification cases and persisted user corrections')
        listed = client.get(api + '/api/dreams', headers=owner)
        listed.raise_for_status()
        assert [d['id'] for d in listed.json()['dreams']] == [did]
        print('PASS: live create/edit/date/favorite/addition/refresh/revision/owner isolation; one record')
    finally:
        failures = []
        for uid in created:
            result = client.delete(settings.supabase_url + '/auth/v1/admin/users/' + uid, headers=admin)
            if result.status_code // 100 != 2:
                failures.append(uid)
        if failures:
            raise RuntimeError('Temporary account cleanup failed: ' + ', '.join(failures))
        print(f'Cleanup: {len(created)} temporary accounts removed')
