import { DeviceSpeech, HandsFree } from '/console/voice.js';
const $ = id => document.getElementById(id);
let session = null, abort = null, busy = false, lastReply = '', activeRun = Promise.resolve();
let submitVersion = 0;
let assistantName = 'Clifford', wakePhrase = 'Clifford', voiceEnabled = false;
const speech = new DeviceSpeech();
const headers = () => ({'Content-Type': 'application/json', 'Accept':'application/json',
  'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content});
function error(text) { $('error').textContent = String(text); }
function message(role, text) {
  const row = document.createElement('div'); row.className = 'message ' + role;
  const label = document.createElement('span'); label.className = 'label'; label.textContent = role === 'user' ? 'You' : assistantName;
  const content = document.createElement('span'); content.textContent = text;
  row.append(label, content); $('messages').append(row); row.scrollIntoView({block: 'nearest'}); return content;
}
function state(running) { busy = running; $('send').disabled = running; $('stop').disabled = !running && !speech.speaking(); $('new').disabled = running; $('state').textContent = running ? 'Thinking with you' : voiceEnabled ? `Listening for “${wakePhrase}”` : 'Ready when you are'; }
function interrupt() { speech.cancel(); abort?.abort(); }
const handsFree = new HandsFree({ticket: async () => {
    const response = await fetch('/api/voice/ticket', {method:'POST',headers:headers()});
    if (!response.ok) throw new Error('Voice connection is unavailable. Check the kernel and aaPanel voice proxy.');
    return response.json();
  }, wake: wakePhrase,
  submit: text => submit(text), interrupt, speaking: () => speech.speaking() || busy,
  status: text => { $('voiceStatus').textContent = text; $('voice').textContent = handsFree.enabled ? 'Disable voice' : 'Enable voice'; if (!handsFree.enabled) voiceEnabled = false; },
  failure: text => error(text)});
$('voice').onclick = async () => {
  if (handsFree.enabled) { interrupt(); handsFree.stop(); voiceEnabled = false; return; }
  if (!speech.supported()) { error('No local speech voice is available on this device. Install an OS speech voice first.'); return; }
  try {
    // This explicit one-time gesture grants microphone consent and initializes local audio.
    speech.engine.resume(); handsFree.gate.wake = wakePhrase.toLowerCase(); voiceEnabled = true;
    await handsFree.start();
  } catch (e) { voiceEnabled = false; error(e.message); }
};
async function connect() {
  try {
    const response = await fetch('/api/providers', {headers: headers()});
    if (response.status === 401) throw new Error('Site authentication is required. Reopen the protected site.');
    if (!response.ok) throw new Error('Kernel unavailable. Check the server connection settings.');
    const config = await response.json(); assistantName = config.assistant_name; wakePhrase = config.wake_phrase;
    $('connection').textContent = 'Connected';
  } catch (e) { $('connection').textContent = 'Kernel unavailable'; error(e.message); }
}
connect();
$('new').onclick = () => { interrupt(); session = null; lastReply = ''; $('messages').replaceChildren(); error(''); };
$('stop').onclick = interrupt;
$('prompt').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (!busy) $('chat').requestSubmit(); } };
$('chat').onsubmit = e => { e.preventDefault(); const text = $('prompt').value.trim(); if (!text || busy) return; $('prompt').value = ''; submit(text); };
async function submit(text) {
  const version = ++submitVersion; interrupt(); await activeRun;
  if (version !== submitVersion) return;
  activeRun = run(text); await activeRun;
}
async function run(text) {
  message('user', text); const output = message('assistant', ''); lastReply = ''; error(''); state(true); abort = new AbortController();
  try {
    const response = await fetch('/api/chat/stream', {method: 'POST', headers: headers(), signal: abort.signal, body: JSON.stringify({text, session_id: session})});
    if (!response.ok) throw new Error(`Request failed (${response.status}).`);
    const reader = response.body.getReader(), decoder = new TextDecoder(); let buffer = '', completed = false;
    while (true) {
      const {value, done} = await reader.read(); if (done) break;
      buffer += decoder.decode(value, {stream: true}); let boundary;
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
        const data = frame.split('\n').filter(line => line.startsWith('data: ')).map(line => line.slice(6)).join('\n');
        if (!data) continue; const event = JSON.parse(data);
        if (event.session_id) session = event.session_id;
        if (event.type === 'assistant.delta') {
          output.textContent += event.payload.text; output.scrollIntoView({block: 'nearest'});
          if (voiceEnabled) speech.push(event.payload.text);
        }
        if (event.type === 'assistant.completed') { completed = true; lastReply = event.payload.text; if (voiceEnabled) speech.push('', true); }
        if (event.type === 'error') throw new Error(`${assistantName}: ${event.payload.code.replaceAll('_', ' ')}. Check Ollama and the installed Gemma model on your server.`);
      }
    }
    if (!completed) throw new Error('Stream ended before completion. Check session history before retrying.');
  } catch (e) { speech.cancel(); if (e.name !== 'AbortError') error(e.message); }
  finally { state(false); abort = null; }
}
addEventListener('pagehide', () => { interrupt(); handsFree.stop(); });
// Procedural layered cyan ribbons inspired by the supplied image. This is an ambient
// visualization, not an audio analyser or evidence that a microphone is active.
const canvas = $('wave'), ctx = canvas.getContext('2d'), reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
let t = 0;
function draw() {
  const box = canvas.getBoundingClientRect(), ratio = Math.min(devicePixelRatio || 1, 2);
  if (canvas.width !== box.width * ratio || canvas.height !== box.height * ratio) { canvas.width = box.width * ratio; canvas.height = box.height * ratio; }
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0); ctx.clearRect(0, 0, box.width, box.height);
  const w = box.width, h = box.height; const amp = busy ? 1.3 : 1;
  ctx.globalCompositeOperation = 'lighter';
  for (let strand = 0; strand < 90; strand++) {
    const k = strand / 89; ctx.beginPath();
    for (let i = 0; i <= 250; i++) {
      const x = i / 250, envelope = Math.sin(Math.PI * x) ** .8;
      const y = h * .48 + envelope * amp * (Math.sin(x * 15 + t + k * 2.7) * 55 + Math.sin(x * 24 - t * .6 + k * 4) * 32 + Math.cos(x * 8 + t * .4) * 15);
      if (i === 0) ctx.moveTo(x * w, y); else ctx.lineTo(x * w, y);
    }
    ctx.strokeStyle = `rgba(${35 + k * 100},${175 + k * 70},255,${.045 + Math.sin(k * Math.PI) * .18})`; ctx.lineWidth = 1.1;
    ctx.shadowColor = '#1acfff'; ctx.shadowBlur = 16; ctx.stroke();
  }
  ctx.shadowBlur = 0; ctx.globalCompositeOperation = 'source-over';
  t += busy ? .025 : .008;
  if (!reduced) requestAnimationFrame(draw);
}
draw(); if (reduced) addEventListener('resize', draw);
