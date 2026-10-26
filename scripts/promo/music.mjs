// Synthesises the intro video's music bed (44.1 kHz stereo WAV): node music.mjs out.wav [speed]
// Section times follow video.html at 1x: the window enters (BRAND), the walkthrough (TOUR to PLATFORM), the closing card
// (FINALE). `speed` is video.html's SPEED: the sections move with the picture, the tempo stays.
import fs from 'node:fs';

const SPEED = Number(process.argv[3] || 1);
const SR = 44100, DUR = Math.ceil(128 / SPEED), N = SR * DUR;
const [BRAND, TOUR, PLATFORM, FINALE] = [4.6, 5.4, 118.4, 118.8].map(t => t / SPEED);
const L = new Float32Array(N), R = new Float32Array(N);
const BPM = 96, BEAT = 60 / BPM, BAR = BEAT * 4;
const midi = m => 440 * Math.pow(2, (m - 69) / 12);

// D major: Gmaj9 – D/F# – Em7 – Cmaj7(#11-ish colour) – Bm7 – A
const prog = [
  { root: 43, tones: [55, 59, 62, 66, 69] },
  { root: 42, tones: [54, 57, 62, 66, 69] },
  { root: 40, tones: [55, 59, 62, 64, 67] },
  { root: 36, tones: [52, 55, 59, 64, 67] },
];
const finale = { root: 38, tones: [54, 57, 62, 66, 69, 73] };

const chordAt = t => {
  if (t >= FINALE) return finale;
  return prog[Math.floor(t / BAR) % prog.length];
};

function add(buf, i, v) { if (i >= 0 && i < N) buf[i] += v; }

// Pad: detuned soft tones per bar, slow attack/release.
function pad(t0, len, notes, gain) {
  const n0 = Math.floor(t0 * SR), n = Math.floor(len * SR);
  for (const m of notes) {
    const f = midi(m);
    for (const det of [-0.12, 0.12]) {
      const fd = f * Math.pow(2, det / 12);
      const pan = det < 0 ? 0.35 : 0.65;
      for (let k = 0; k < n + SR * 3; k++) {
        const tt = k / SR;
        const env = Math.min(1, tt / (t0 < 1 ? 1.2 : 0.3)) * (tt > len ? Math.exp(-(tt - len) / 0.9) : 1);
        const ph = 2 * Math.PI * fd * tt;
        const v = (Math.sin(ph) + 0.18 * Math.sin(2 * ph) + 0.06 * Math.sin(3 * ph)) * env * gain;
        add(L, n0 + k, v * (1 - pan)); add(R, n0 + k, v * pan);
      }
    }
  }
}

// Pluck/bell for arpeggios.
function pluck(t0, m, gain, pan = 0.5, decay = 0.55) {
  const f = midi(m), n0 = Math.floor(t0 * SR), n = Math.floor(SR * decay * 5);
  for (let k = 0; k < n; k++) {
    const tt = k / SR;
    const env = Math.min(1, tt / 0.004) * Math.exp(-tt / decay);
    const ph = 2 * Math.PI * f * tt;
    const v = (Math.sin(ph) + 0.35 * Math.sin(2 * ph) * Math.exp(-tt / 0.15) + 0.12 * Math.sin(3.01 * ph) * Math.exp(-tt / 0.08)) * env * gain;
    add(L, n0 + k, v * (1 - pan)); add(R, n0 + k, v * pan);
  }
}

function bass(t0, m, len, gain) {
  const f = midi(m), n0 = Math.floor(t0 * SR), n = Math.floor(len * SR);
  for (let k = 0; k < n; k++) {
    const tt = k / SR;
    const env = Math.min(1, tt / 0.02) * Math.min(1, (len - tt) / 0.15);
    const ph = 2 * Math.PI * f * tt;
    const v = (Math.sin(ph) + 0.25 * Math.sin(2 * ph)) * env * gain;
    add(L, n0 + k, v); add(R, n0 + k, v);
  }
}

function kick(t0, gain) {
  const n0 = Math.floor(t0 * SR), n = Math.floor(0.4 * SR);
  let ph = 0;
  for (let k = 0; k < n; k++) {
    const tt = k / SR;
    const f = 45 + 75 * Math.exp(-tt / 0.04);
    ph += 2 * Math.PI * f / SR;
    const v = Math.sin(ph) * Math.exp(-tt / 0.13) * gain;
    add(L, n0 + k, v); add(R, n0 + k, v);
  }
}

let seed = 7;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) * 2 - 1;
function shaker(t0, gain, pan) {
  const n0 = Math.floor(t0 * SR), n = Math.floor(0.09 * SR);
  let prev = 0;
  for (let k = 0; k < n; k++) {
    const tt = k / SR, x = rnd(), hp = x - prev; prev = x;
    const v = hp * Math.exp(-tt / 0.025) * gain;
    add(L, n0 + k, v * (1 - pan)); add(R, n0 + k, v * pan);
  }
}

// --- arrangement -----------------------------------------------------------
const bars = Math.ceil(FINALE / BAR);
for (let b = 0; b < bars; b++) {
  const t = b * BAR, c = chordAt(t);
  if (t >= FINALE) break;
  pad(t, Math.min(BAR, FINALE - t), c.tones.slice(0, 4), t < 5.6 ? 0.020 : 0.016);

  if (t >= BRAND) {                          // bass enters on the brand reveal
    bass(t, c.root, BEAT * 2.9, 0.09);
    bass(t + BEAT * 3, c.root + 7, BEAT * 0.9, 0.07);
  }
  // arpeggio: sparse in the intro, 8ths through the feature tour, sparse again for the platform scenes
  const dense = t >= TOUR - 0.5 && t < PLATFORM;
  const step = dense ? BEAT / 2 : BEAT;
  if (t >= 2.0) {
    const pattern = [0, 2, 4, 3, 1, 3, 4, 2];
    for (let s = 0; s * step < BAR - 1e-6; s++) {
      const m = c.tones[pattern[s % pattern.length]] + 12;
      pluck(t + s * step, m, dense ? 0.05 : 0.06, s % 2 ? 0.7 : 0.3);
    }
  }
  if (t >= TOUR && t < PLATFORM) {
    for (let q = 0; q < 4; q++) kick(t + q * BEAT, q % 2 ? 0.16 : 0.22);
    for (let e = 0; e < 8; e++) shaker(t + e * BEAT / 2 + BEAT / 4, e % 2 ? 0.05 : 0.035, e % 2 ? 0.65 : 0.4);
  }
}
// finale: resolve on D with a slow bell roll
pad(FINALE, 7.5, finale.tones, 0.016);
bass(FINALE, finale.root, 7, 0.08);
finale.tones.forEach((m, i) => pluck(FINALE + i * 0.16, m + 12, 0.06, 0.25 + i * 0.1, 1.4));
pluck(FINALE + 4.5, 81, 0.04, 0.6, 1.6);
// soft riser into the brand reveal
for (let k = 0; k < SR * 1.6; k++) {
  const tt = k / SR, i = Math.floor((4.4 + tt) * SR);
  const v = rnd() * Math.pow(tt / 1.6, 2) * 0.03;
  add(L, i, v); add(R, i, v);
}

// --- simple stereo reverb: a few feedback combs + ping-pong delay ------------
function comb(src, dst, delay, fb, mix) {
  const d = Math.floor(delay * SR), buf = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const y = src[i] + (i >= d ? buf[i - d] * fb : 0);
    buf[i] = y; dst[i] += (i >= d ? buf[i - d] : 0) * mix;
  }
}
const wetL = new Float32Array(N), wetR = new Float32Array(N);
for (const [dl, dr] of [[0.0297, 0.0311], [0.0371, 0.0353], [0.0411, 0.0437], [0.0437, 0.0459]]) {
  comb(L, wetL, dl, 0.82, 0.06); comb(R, wetR, dr, 0.82, 0.06);
}
comb(L, wetR, BEAT * 0.75, 0.3, 0.12); comb(R, wetL, BEAT * 0.75, 0.3, 0.12);
for (let i = 0; i < N; i++) { L[i] += wetL[i]; R[i] += wetR[i]; }

// fades + normalise
let peak = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR, g = Math.min(1, t / 1.2) * Math.min(1, Math.max(0, (DUR - t) / 3.5));
  L[i] *= g; R[i] *= g; peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
}
const norm = 0.85 / peak;
const out = Buffer.alloc(44 + N * 4);
out.write('RIFF', 0); out.writeUInt32LE(36 + N * 4, 4); out.write('WAVE', 8);
out.write('fmt ', 12); out.writeUInt32LE(16, 16); out.writeUInt16LE(1, 20); out.writeUInt16LE(2, 22);
out.writeUInt32LE(SR, 24); out.writeUInt32LE(SR * 4, 28); out.writeUInt16LE(4, 32); out.writeUInt16LE(16, 34);
out.write('data', 36); out.writeUInt32LE(N * 4, 40);
for (let i = 0; i < N; i++) {
  out.writeInt16LE(Math.round(Math.tanh(L[i] * norm) * 32000), 44 + i * 4);
  out.writeInt16LE(Math.round(Math.tanh(R[i] * norm) * 32000), 46 + i * 4);
}
fs.writeFileSync(process.argv[2] || 'music.wav', out);
console.log('peak', peak.toFixed(3));
