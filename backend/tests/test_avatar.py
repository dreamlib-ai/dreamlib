from uuid import uuid4
from .conftest import OTHER, TOKEN, auth, storyboard, wait_job


def test_private_profile_selection_revision_and_validation(api):
    client,_ = api
    p=client.get('/api/v1/profile',headers=auth()).json()
    assert p['avatar'] is None and 'avatarPath' not in p
    p=client.patch('/api/v1/profile',headers=auth(),json={'revision':0,'presetId':'ink','displayName':'Düşçü'}).json()
    assert p['presetId']=='ink' and p['avatar']['accessory']=='glasses' and p['avatarUrl'].endswith('/ink.webp')
    assert client.get('/api/v1/profile',headers=auth(OTHER)).json()['avatar'] is None
    assert client.patch('/api/v1/profile',headers=auth(),json={'revision':0,'presetId':'dawn'}).status_code==409
    assert client.patch('/api/v1/profile',headers=auth(),json={'revision':p['revision'],'avatarPath':'https://attacker.example'}).status_code==400
    assert client.get('/api/v1/profile').status_code==401


def test_custom_avatar_job_uses_owned_reference_and_activation(api):
    client,s=api
    p=client.patch('/api/v1/profile',headers=auth(),json={'revision':0,'presetId':'dawn'}).json()
    spec={**p['avatar'],'hair':'long','accessory':'glasses'}
    body={'requestId':str(uuid4()),'baseRevision':p['revision'],'spec':spec}
    response=client.post('/api/v1/avatar',headers=auth(),json=body)
    assert response.status_code==202
    job=wait_job(client,response.json()['id'])
    assert job['status']=='done' and len(s.editor.calls)==1
    assert s.editor.calls[0][2]==[p['avatarUrl']]
    assert client.post('/api/v1/avatar',headers=auth(),json=body).json()['id']==job['id']
    assert client.patch('/api/v1/profile',headers=auth(OTHER),json={'revision':0,'avatarJobId':job['id']}).status_code==404
    selected=client.patch('/api/v1/profile',headers=auth(),json={'revision':p['revision'],'avatarJobId':job['id']}).json()
    assert selected['avatar']['hair']=='long' and selected['presetId'] is None
    assert s.queue.jobs[job['id']].state['saved']
    assert client.post('/api/v1/avatar',headers=auth(),json={**body,'spec':{**spec,'hair':'none'}}).status_code==409


def test_manga_freezes_avatar_and_viewpoint_through_profile_changes(api):
    client,s=api
    p=client.patch('/api/v1/profile',headers=auth(),json={'revision':0,'presetId':'ink'}).json()
    s.llm.reply=storyboard(4)
    body={'requestId':str(uuid4()),'text':'Gökyüzünde uçtum.','useAvatar':True,'avatarRevision':p['revision'],'perspective':'first-person'}
    job=wait_job(client,client.post('/api/v1/manga',headers=auth(),json=body).json()['id'])
    assert job['status']=='done' and not s.images.calls and len(s.editor.calls)==4
    assert s.editor.calls[0][2]==[p['avatarUrl']]
    assert 'POV' in s.editor.calls[0][1]
    meta=s.queue.jobs[job['id']].state['meta']
    assert meta['AvatarPath']==p['avatarUrl'] and meta['Perspective']=='first-person'
    client.patch('/api/v1/profile',headers=auth(),json={'revision':p['revision'],'presetId':'moss'})
    assert client.post('/api/v1/manga',headers=auth(),json=body).json()['id']==job['id']
    new_request={**body,'requestId':str(uuid4())}
    assert client.post('/api/v1/manga',headers=auth(),json=new_request).status_code==409
