import hold from './assets/koala/hold.webp';
import listen from './assets/koala/listen.webp';
import curious from './assets/koala/curious.webp';
import wave from './assets/koala/wave.webp';
import think from './assets/koala/think.webp';
import sleep from './assets/koala/sleep.webp';
import joy from './assets/koala/joy.webp';

/** One pastel koala, drawn in seven poses from the same reference (kaynak/referans/koala-pastel-2026-11-15). */
const poses = { hold, listen, curious, wave, think, sleep, joy };
export type Pose = keyof typeof poses;

export default function Mascot({ pose = 'curious', className = '' }: { pose?: Pose; className?: string }) {
  return <span className={`koala koala-${pose} ${className}`} aria-hidden="true">
    {(Object.keys(poses) as Pose[]).map(key => <img key={key} src={poses[key]} alt="" draggable={false} className={key === pose ? 'on' : ''} loading={key === pose ? 'eager' : 'lazy'} />)}
  </span>;
}
