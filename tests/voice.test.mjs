import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import assert from 'node:assert/strict';
const code = await readFile(new URL('../web/voice.js', import.meta.url), 'utf8');
const { WakeGate, PCMResampler, DeviceSpeech } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
test('wake phrase preserves the complete following sentence', () => {
  const gate = new WakeGate('Clifford', () => 1000);
  assert.equal(gate.accept('clifford tell me the time'), 'tell me the time');
  assert.equal(gate.accept('Clifford, explain quantum physics.'), 'explain quantum physics.');
  assert.equal(gate.accept('a conversation without the wake phrase'), null);
  assert.equal(gate.accept('cliffordish is not a wake phrase'), null);
});
test('wake alone arms the next sentence, with expiry', () => {
  let now = 1000; const gate = new WakeGate('Clifford', () => now);
  assert.equal(gate.accept('Clifford'), null);
  assert.equal(gate.accept('what time is it'), 'what time is it');
  gate.accept('Clifford'); now += 16000;
  assert.equal(gate.accept('unrelated speech'), null);
});
test('spoken interruption accepts a replacement without another wake phrase', () => {
  const gate = new WakeGate('Clifford', () => 1000);
  gate.interrupt(); assert.equal(gate.accept('stop, explain it more simply'), 'stop, explain it more simply');
  assert.equal(gate.accept('unrelated speech'), null);
});
test('PCM resampling preserves a continuous 16kHz clock across chunks', () => {
  const resampler = new PCMResampler(48000); let count = 0;
  for (let i=0;i<100;i++) count += resampler.convert(new Float32Array(480).fill(.5)).byteLength / 2;
  assert.equal(count,16000);
  const view = new DataView(new PCMResampler(16000).convert(new Float32Array([-1,1])));
  assert.equal(view.getInt16(0,true),-32768); assert.equal(view.getInt16(2,true),32767);
});
test('automatic sentence output and interruption cancel pending playback', () => {
  const spoken=[]; let cancelled=0;
  const engine={getVoices:()=>[{localService:true,lang:'en-US'}],speak:u=>spoken.push(u.text),cancel:()=>cancelled++};
  const speech=new DeviceSpeech(engine,text=>({text}));
  speech.push('Hello. Next'); assert.deepEqual(spoken,['Hello. ']);
  speech.cancel(); speech.push('Replacement.',true);
  assert.deepEqual(spoken,['Hello. ','Replacement.']); assert.equal(cancelled,1);
});
