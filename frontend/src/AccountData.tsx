import { useState } from 'react';
import { deleteAccount, exportAccount } from './api';
import { clearAvatarDesign, clearAvatarDraft } from './avatar';
import { clearDraft } from './draft';
import { signOut } from './session';
import { tr } from './strings';

const text = tr.account;

/** R2: take everything along, or delete the account; deleting asks once more and then signs out. */
export default function AccountData({ owner }: { owner: string }) {
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState('');

  async function download() {
    setBusy(true); setError('');
    try {
      const url = URL.createObjectURL(await exportAccount());
      const link = Object.assign(document.createElement('a'), { href: url, download: `dreamlib-${new Date().toISOString().slice(0, 10)}.json` });
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(e instanceof Error ? e.message : tr.genericError); }
    finally { setBusy(false); }
  }

  async function remove() {
    setBusy(true); setError('');
    try {
      await deleteAccount();
      clearDraft(owner); clearAvatarDraft(owner); clearAvatarDesign(owner);
      await signOut().catch(() => {});
      window.location.assign('/');
    } catch (e) { setError(e instanceof Error ? e.message : tr.genericError); setBusy(false); }
  }

  return <section className="account-data" aria-label={text.heading}>
    <h2>{text.heading}</h2>
    <button className="text-action" disabled={busy} onClick={() => void download()}>{text.download}</button>
    {confirming ? <div className="account-delete" role="group" aria-label={text.delete}>
      <p>{text.deleteSure}</p>
      <button className="go tiny danger" disabled={busy} onClick={() => void remove()}>{text.deleteYes}</button>
      <button className="go tiny quiet" disabled={busy} onClick={() => setConfirming(false)}>{tr.library.cancel}</button>
    </div> : <button className="text-action" disabled={busy} onClick={() => setConfirming(true)}>{text.delete}</button>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}
