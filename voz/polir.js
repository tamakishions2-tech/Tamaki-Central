/* Som macio: tira o chiado metálico e o estridente das falas geradas (roda no aparelho, sem mexer no Kaggle).
   Corta graves inúteis, aquece um pouco o corpo, abaixa a faixa "de lata" (3 kHz), o chiado do "s" (6–7 kHz) e o brilho falso de cima,
   e passa um compressor leve para o volume ficar parelho. Devolve um WAV. */
(function () {
  "use strict";
  function wav(buf) {
    const n = buf.length, ch = buf.numberOfChannels, sr = buf.sampleRate, d = new DataView(new ArrayBuffer(44 + n * 2));
    const s = (o, t) => { for (let i = 0; i < t.length; i++) d.setUint8(o + i, t.charCodeAt(i)); };
    s(0, "RIFF"); d.setUint32(4, 36 + n * 2, true); s(8, "WAVE"); s(12, "fmt "); d.setUint32(16, 16, true); d.setUint16(20, 1, true); d.setUint16(22, 1, true);
    d.setUint32(24, sr, true); d.setUint32(28, sr * 2, true); d.setUint16(32, 2, true); d.setUint16(34, 16, true); s(36, "data"); d.setUint32(40, n * 2, true);
    const cs = []; for (let c = 0; c < ch; c++) cs.push(buf.getChannelData(c));
    let pico = 1e-6; for (let i = 0; i < n; i++) { let v = 0; for (const x of cs) v += x[i]; pico = Math.max(pico, Math.abs(v / ch)); }
    const g = 0.92 / pico;
    for (let i = 0; i < n; i++) { let v = 0; for (const x of cs) v += x[i]; v = Math.max(-1, Math.min(1, v / ch * g)); d.setInt16(44 + i * 2, v < 0 ? v * 0x8000 : v * 0x7fff, true); }
    return new Blob([d], {type: "audio/wav"});
  }
  async function polir(blob, forca = 1) {
    try {
      const AC = window.AudioContext || window.webkitAudioContext, OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
      const tmp = new AC(); const src = await tmp.decodeAudioData(await blob.arrayBuffer()); try { tmp.close(); } catch (e) {}
      const c = new OAC(1, src.length, src.sampleRate), b = c.createBufferSource(); b.buffer = src;
      const f = (tipo, freq, ganho, q) => { const x = c.createBiquadFilter(); x.type = tipo; x.frequency.value = freq; if (ganho != null) x.gain.value = ganho * forca; if (q) x.Q.value = q; return x; };
      const cadeia = [f("highpass", 75, null, .7), f("lowshelf", 220, 2), f("peaking", 3100, -3, 1.1), f("peaking", 6600, -4.5, 2),
        f("highshelf", 9000, -6), f("lowpass", Math.min(11500, src.sampleRate / 2 - 200), null, .7)];
      const comp = c.createDynamicsCompressor(); comp.threshold.value = -20; comp.ratio.value = 2.5; comp.knee.value = 8; comp.attack.value = .008; comp.release.value = .2;
      let no = b; for (const x of cadeia) { no.connect(x); no = x; } no.connect(comp); comp.connect(c.destination);
      b.start(); return wav(await c.startRendering());
    } catch (e) { return blob; }   // se o aparelho não conseguir, fica o áudio original
  }
  window.TamakiPolir = polir;
})();
