import { useEffect, useState } from 'react';
import { ApiError, createAvatar, getJob, getSelfProfile, updateSelfProfile, type AvatarProfile } from './api';
import { appearanceOptions, clearAvatarDraft, defaultAvatar, presetIds, readAvatarDraft, writeAvatarDraft, type AvatarSpec, type PresetId } from './avatar';
import { tr } from './strings';
import './avatar.css';

const text=tr.avatar;
export default function AvatarPage({owner,onUpdated}:{owner:string;onUpdated:(profile:AvatarProfile)=>void}) {
  const [profile,setProfile]=useState<AvatarProfile|null>(null);
  const [form,setForm]=useState<AvatarSpec>(defaultAvatar);
  const [name,setName]=useState('');
  const [pending,setPending]=useState(()=>readAvatarDraft(owner));
  const [preview,setPreview]=useState('');
  const [working,setWorking]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [retry,setRetry]=useState(0);
  const [load,setLoad]=useState(0);
  useEffect(()=>{
    let alive=true;
    getSelfProfile().then(value=>{ if(alive){ setProfile(value);setName(value.displayName);setForm(readAvatarDraft(owner)?.spec ?? value.avatar ?? defaultAvatar);onUpdated(value); } })
      .catch(cause=>{if(alive)setError(cause instanceof Error?cause.message:tr.genericError);});
    return()=>{alive=false;};
  },[owner,load]);
  useEffect(()=>{
    if(!pending)return;
    let alive=true;const controller=new AbortController();
    setWorking(true);setError('');setPreview('');
    async function follow(){
      try{
        await createAvatar(pending!.id,pending!.spec,pending!.baseRevision);
        while(alive){
          const job=await getJob(pending!.id,controller.signal);
          if(!alive)return;
          if(job.status==='failed'){clearAvatarDraft(owner);setPending(null);throw new Error(job.error||tr.genericError);}
          if(job.status==='done'){if(!job.panels[0]?.url)throw new Error(tr.genericError);setPreview(job.panels[0].url);return;}
          await new Promise(resolve=>setTimeout(resolve,2000));
        }
      }catch(cause){if(alive){if(cause instanceof ApiError && [400,404,409].includes(cause.status)){clearAvatarDraft(owner);setPending(null);}setError(cause instanceof Error?cause.message:tr.genericError);}}
      finally{if(alive)setWorking(false);}
    }
    void follow();return()=>{alive=false;controller.abort();};
  },[pending?.id,retry,owner]);
  async function choose(changes:{displayName?:string;presetId?:PresetId;avatarJobId?:string;clearAvatar?:boolean}) {
    if(!profile)return;
    setBusy(true);setError('');
    try{
      const updated=await updateSelfProfile(profile.revision,changes);
      setProfile(updated);onUpdated(updated);setName(updated.displayName);
      if(changes.presetId||changes.avatarJobId||changes.clearAvatar)setForm(updated.avatar??defaultAvatar);
      if(changes.presetId||changes.avatarJobId||changes.clearAvatar){clearAvatarDraft(owner);setPending(null);setPreview('');}
    }catch(cause){setError(cause instanceof Error?cause.message:tr.genericError);}
    finally{setBusy(false);}
  }
  const disabled=busy||working||!profile;
  const matches=!!pending&&JSON.stringify(pending.spec)===JSON.stringify(form);
  const label=(group:keyof AvatarSpec,key:string)=>(text.options[group] as Record<string,string>)[key];
  return <section className="avatar-page view-transition"><header className="page-heading"><h1>{text.heading}</h1></header>
    <div className="avatar-layout"><div className="avatar-stage" aria-busy={working}>
      {(preview||profile?.avatarUrl)?<img src={preview||profile!.avatarUrl} alt={preview?text.preview:text.active} />:<div className="avatar-empty">{text.pick}</div>}
      {working&&<p role="status">{text.generating}</p>}
      {preview&&<div className="avatar-preview-actions"><span>{matches?text.preview:text.oldPreview}</span><button className="go" disabled={disabled||!matches} onClick={()=>void choose({avatarJobId:pending!.id})}>{text.use}</button></div>}
    </div><div className="avatar-controls">
      <div className="avatar-presets" role="group" aria-label={text.presets}>{presetIds.map((id,i)=><button key={id} disabled={disabled} aria-pressed={profile?.presetId===id} aria-label={text.variant(i+1)} onClick={()=>void choose({presetId:id})}><img src={`/avatars/${id}.webp`} alt="" loading="lazy" /></button>)}</div>
      <form className="avatar-name" onSubmit={event=>{event.preventDefault();void choose({displayName:name});}}><label>{text.name}<input maxLength={40} value={name} disabled={disabled} onChange={e=>setName(e.target.value)} /></label><button className="text-action" disabled={disabled||name===profile?.displayName}>{text.saveName}</button></form>
      <details className="avatar-customize"><summary>{text.design}</summary><form className="avatar-form" onSubmit={event=>{
        event.preventDefault();if(!profile)return;const value={id:crypto.randomUUID(),spec:form,baseRevision:profile.revision};
        if(!writeAvatarDraft(owner,value)){setError(tr.recovery.storage);return;}setWorking(true);setPending(value);
      }}>
        {(Object.keys(appearanceOptions) as (keyof AvatarSpec)[]).map(key=><label key={key}>{text.fields[key]}<select value={form[key]} disabled={disabled} onChange={e=>setForm({...form,[key]:e.target.value})}>{appearanceOptions[key].map(value=><option key={value} value={value}>{label(key,value)}</option>)}</select></label>)}
        <button className="go" disabled={disabled}>{text.generate}</button>
      </form></details>
      {pending&&!working&&!preview&&<button className="text-action" disabled={busy} onClick={()=>setRetry(value=>value+1)}>{tr.recovery.resume}</button>}
      {profile?.avatar&&<button className="text-action" disabled={disabled} onClick={()=>void choose({clearAvatar:true})}>{text.remove}</button>}
      <a className="avatar-about" href="/?onboarding">{tr.intro.replay}</a>
      {error&&<p className="error" role="alert">{error}<button className="text-action" disabled={busy||working} onClick={()=>{setError('');setLoad(value=>value+1);}}>{tr.app.retry}</button></p>}
    </div></div>
  </section>;
}
