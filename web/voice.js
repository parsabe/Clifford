// Pure wake/turn state machine, shared by browser code and deterministic Node tests.
export class WakeGate {
  constructor(wake = 'Clifford', clock = () => Date.now()) {
    this.wake = wake.toLowerCase(); this.clock = clock; this.armedUntil = 0;
  }
  interrupt() { this.armedUntil = this.clock() + 15000; }
  reset() { this.armedUntil = 0; }
  accept(text) {
    text = text.trim(); if (!text) return null;
    const words = text.match(/^[\p{L}\p{N}]+/u);
    if (words && words[0].toLowerCase() === this.wake) {
      this.armedUntil = this.clock() + 15000;
      const remainder = text.slice(words[0].length).replace(/^[\s,.:;!?-]+/, '').trim();
      if (!remainder) return null;
      this.armedUntil = 0; return remainder;
    }
    if (this.clock() <= this.armedUntil) { this.armedUntil = 0; return text; }
    return null;
  }
}

export class PCMResampler {
  constructor(sourceRate, targetRate = 16000) {
    if (sourceRate < targetRate) throw new Error('Unsupported microphone sample rate');
    this.ratio = sourceRate / targetRate; this.next = this.ratio; this.count = 0;
    this.sum = 0; this.samples = 0;
  }
  convert(input) {
    const result = [];
    for (const sample of input) {
      this.sum += sample; this.samples++; this.count++;
      if (this.count >= this.next) {
        const x = Math.max(-1, Math.min(1, this.sum / this.samples));
        result.push(Math.round(x < 0 ? x * 32768 : x * 32767));
        this.sum = 0; this.samples = 0; this.next += this.ratio;
      }
    }
    const buffer = new ArrayBuffer(result.length * 2), view = new DataView(buffer);
    result.forEach((sample, i) => view.setInt16(i * 2, sample, true));
    return buffer;
  }
}

export class DeviceSpeech {
  constructor(engine = globalThis.speechSynthesis, utterance = text => new SpeechSynthesisUtterance(text)) {
    this.engine = engine; this.utterance = utterance; this.buffer = ''; this.active = false;
  }
  supported() { return !!this.engine?.getVoices().some(v => v.localService); }
  push(text, flush = false) {
    this.buffer += text;
    while (this.buffer) {
      const sentence = this.buffer.match(/^([\s\S]*?[.!?](?:\s|$))/);
      let size = sentence?.[0].length || (this.buffer.length > 240 ? 240 : flush ? this.buffer.length : 0);
      if (!size) break;
      const text = this.buffer.slice(0, size); this.buffer = this.buffer.slice(size);
      const voice = this.engine?.getVoices().find(v => v.localService && /^en/i.test(v.lang)) ||
        this.engine?.getVoices().find(v => v.localService);
      if (!voice) throw new Error('Install a local device speech voice, then enable voice again.');
      const utterance = this.utterance(text); utterance.voice = voice;
      this.active = true; this.engine.speak(utterance);
    }
  }
  speaking() { return !!(this.engine?.speaking || this.engine?.pending); }
  cancel() { this.buffer = ''; this.active = false; this.engine?.cancel(); }
}

export class HandsFree {
  constructor({token, wake, submit, interrupt, speaking, status, failure}) {
    this.token = token; this.gate = new WakeGate(wake); this.submit = submit;
    this.interrupt = interrupt; this.speaking = speaking; this.status = status;
    this.failure = failure; this.enabled = false; this.resources = [];
  }
  async start() {
    if (!navigator.mediaDevices?.getUserMedia || !globalThis.AudioWorkletNode) {
      throw new Error('Microphone requires HTTPS (or localhost) and an AudioWorklet-capable browser.');
    }
    this.enabled = true;
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({audio: {
        echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1}});
      if (!this.enabled) { this.stream.getTracks().forEach(t => t.stop()); return; }
      this.context = new AudioContext(); await this.context.resume();
      await this.context.audioWorklet.addModule('/console/pcm-worklet.js');
      if (!this.enabled) { this.stop(); return; }
      this.source = this.context.createMediaStreamSource(this.stream);
      this.worklet = new AudioWorkletNode(this.context, 'pcm-capture');
      this.muted = this.context.createGain(); this.muted.gain.value = 0;
      const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
      this.socket = new WebSocket(`${scheme}//${location.host}/v1/voice/listen`);
      const ready = new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Speech recognition did not become ready.')), 30000);
        this.socket.onopen = () => this.socket.send(JSON.stringify({token: this.token()}));
        this.socket.onmessage = e => {
          const event = JSON.parse(e.data);
          if (event.type === 'audio.ready') { clearTimeout(timer); resolve(); }
          if (event.type === 'error') { clearTimeout(timer); reject(new Error(event.payload.code)); this.failure(event.payload.code); this.stop(); }
          if (event.type === 'audio.transcript' && event.payload.final && this.enabled) {
            // While playing through speakers, reject non-wake echo unless local VAD
            // already established a user interruption. Headphones give best isolation.
            const command = this.gate.accept(event.payload.text);
            if (command) { this.interrupt(); Promise.resolve(this.submit(command)).catch(this.failure); }
          }
        };
        this.socket.onerror = () => { clearTimeout(timer); reject(new Error('Speech connection failed.')); };
        this.socket.onclose = () => {
          clearTimeout(timer); reject(new Error('Speech connection closed.'));
          if (this.enabled) { this.failure('Speech connection closed. Enable voice to reconnect.'); this.stop(); }
        };
      });
      await ready;
      if (!this.enabled) return;
      const resampler = new PCMResampler(this.context.sampleRate); let loudSince = 0, interrupted = false;
      this.worklet.port.onmessage = event => {
        if (!this.enabled || this.socket?.readyState !== WebSocket.OPEN) return;
        const samples = event.data; let sum = 0;
        for (const sample of samples) sum += sample * sample;
        const loud = Math.sqrt(sum / samples.length) > .035;
        const now = performance.now();
        if (loud) {
          if (!loudSince) loudSince = now;
          if (this.speaking() && now - loudSince > 120 && !interrupted) {
            interrupted = true; this.gate.interrupt(); this.interrupt(); this.status('Listening to your interruption');
          }
        } else { loudSince = 0; interrupted = false; }
        const pcm = resampler.convert(samples);
        if (this.socket.bufferedAmount > 64000) { this.failure('Voice connection is too slow.'); this.stop(); return; }
        if (pcm.byteLength) this.socket.send(pcm);
      };
      this.source.connect(this.worklet); this.worklet.connect(this.muted); this.muted.connect(this.context.destination);
      this.status(`Listening for “${this.gate.wake}”`);
    } catch (e) { this.stop(); throw e; }
  }
  stop() {
    this.enabled = false; this.gate.reset();
    this.stream?.getTracks().forEach(t => t.stop());
    this.worklet?.disconnect(); this.source?.disconnect(); this.muted?.disconnect();
    if (this.context && this.context.state !== 'closed') this.context.close();
    this.socket?.close(); this.status('Microphone off');
  }
}
