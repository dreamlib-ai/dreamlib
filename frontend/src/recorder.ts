/** Owns one microphone session. Cancelling also invalidates pending permission requests. */
export type RecorderEvents = {
  onState: (state: 'idle' | 'requesting' | 'recording', stream: MediaStream | null) => void;
  onAudio: (audio: Blob) => void;
  onError: (error: 'unsupported' | 'permission' | 'empty' | 'limit') => void;
};
export class DreamRecorder {
  private generation = 0;
  private recorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private requesting = false;
  private events: RecorderEvents;
  constructor(events: RecorderEvents) { this.events = events; }

  async start() {
    if (this.recorder || this.requesting) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      this.events.onError('unsupported'); return;
    }
    const generation = ++this.generation;
    this.requesting = true;
    this.events.onState('requesting', null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (generation !== this.generation) { stream.getTracks().forEach(track => track.stop()); return; }
      this.stream = stream;
      this.requesting = false;
      const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm', 'audio/ogg;codecs=opus']
        .find(type => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      this.recorder = recorder;
      const chunks: Blob[] = [];
      let bytes = 0;
      recorder.ondataavailable = event => {
        if (generation !== this.generation || !event.data.size) return;
        chunks.push(event.data); bytes += event.data.size;
        if (bytes >= 7 * 1024 * 1024) this.finish();
      };
      recorder.onerror = () => { if (generation === this.generation) { this.cancel(); this.events.onError('permission'); } };
      recorder.onstop = () => {
        if (generation !== this.generation) return;
        const audio = new Blob(chunks, { type: recorder.mimeType || mimeType || 'audio/webm' });
        this.release();
        if (audio.size > 8 * 1024 * 1024) { this.events.onError('limit'); return; }
        if (!audio.size) { this.events.onError('empty'); return; }
        this.events.onAudio(audio);
      };
      stream.getAudioTracks().forEach(track => { track.onended = () => {
        if (generation === this.generation) { this.cancel(); this.events.onError('permission'); }
      }; });
      recorder.start(500);
      this.timer = setTimeout(() => this.finish(), 120_000);
      this.events.onState('recording', stream);
    } catch {
      if (generation === this.generation) { this.cancel(); this.events.onError('permission'); }
    }
  }

  finish() {
    clearTimeout(this.timer);
    if (this.recorder?.state === 'recording') this.recorder.stop();
  }

  cancel() {
    ++this.generation;
    const recorder = this.recorder;
    if (recorder) {
      recorder.onstop = null; recorder.ondataavailable = null; recorder.onerror = null;
      if (recorder.state !== 'inactive') recorder.stop();
    }
    this.release();
  }

  private release() {
    clearTimeout(this.timer);
    this.stream?.getTracks().forEach(track => { track.onended = null; track.stop(); });
    this.stream = null; this.recorder = null;
    this.requesting = false;
    this.events.onState('idle', null);
  }
}
