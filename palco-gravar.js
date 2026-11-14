/* Injetado pela Central dentro da aba Palco (funciona com qualquer versão do Palco, até código guardado no aparelho).
   Toca as falas do roteiro (a boca anima com o áudio), grava a cena e guarda na Biblioteca.
   Usa as variáveis do próprio Palco: cv, cfg, audio(), tocarBuffer(), parar(), rec, hold, cap. */
window.__tamakiGravar = async function (d, sinal) {
  sinal = sinal || (() => {});
  const espera = ms => new Promise(r => setTimeout(r, ms));
  const abrir = () => new Promise((ok, no) => { const r = indexedDB.open("tamaki-biblioteca", 1); r.onupgradeneeded = () => { if (!r.result.objectStoreNames.contains("itens")) r.result.createObjectStore("itens", {keyPath: "id"}); }; r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });
  const tx = async (modo, fn) => { const db = await abrir(); try { return await new Promise((ok, no) => { const t = db.transaction("itens", modo), q = fn(t.objectStore("itens")); t.oncomplete = () => ok(q && q.result); t.onerror = () => no(t.error); }); } finally { db.close(); } };
  if (typeof cv === "undefined" || typeof tocarBuffer !== "function" || typeof audio !== "function") throw new Error("esta versão do Palco não tem a cena ou o tocador de áudio");
  if (rec) throw new Error("o Palco já está gravando (toque em ■ Parar gravação)");
  const c = audio(); try { await c.resume(); } catch (e) {}
  if (c.state != "running") throw new Error("o som do Palco está bloqueado: toque uma vez na cena do Palco e produza de novo");
  sinal("Palco: carregando as falas…");
  const bufs = []; for (const id of d.ids) { const it = await tx("readonly", s => s.get(id)); if (!it || !it.blob) throw new Error("uma fala não chegou na Biblioteca"); bufs.push(await c.decodeAudioData(await it.blob.arrayBuffer())); }
  const antes = {bal: cfg.bal.on, guias: cfg.guides};
  try { parar(); } catch (e) {}
  if (d.semBalao) cfg.bal.on = 0; cfg.guides = 0; hold = false;
  rec = {stop() {}, state: "recording", roteiro: true}; // o Palco esconde guias e marcações enquanto "grava"
  try {
    const st = cv.captureStream(30), tipo = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"].find(m => MediaRecorder.isTypeSupported(m));
    const r = new MediaRecorder(st, tipo ? {mimeType: tipo, videoBitsPerSecond: 4e6} : {}), pts = [], fim = new Promise(ok => r.onstop = ok);
    r.ondataavailable = e => { if (e.data.size) pts.push(e.data); };
    r.start(250); const t0 = performance.now();
    await espera((d.ini ?? .2) * 1000);
    for (const [i, ab] of bufs.entries()) {
      sinal(`Palco: fala ${i + 1} de ${bufs.length}`);
      await tocarBuffer(ab, (d.textos || [])[i] || "");
      await espera(((d.pausas || [])[i] ?? .3) * 1000);
    }
    await espera(400); r.stop(); await fim; cap = "";
    const dur = (performance.now() - t0) / 1000, blob = new Blob(pts, {type: "video/webm"});
    if (blob.size < 2000) throw new Error("a gravação da cena saiu vazia");
    const it = {id: "b" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7), origem: "palco", tipo: "video", nome: "Palco · " + (d.titulo || "Roteiro"), nomeManual: 1, pasta: d.pasta || null, texto: "", mime: "video/webm", tamanho: blob.size, criado: Date.now(), dur, blob};
    await tx("readwrite", s => s.put(it));
    try { const b = new BroadcastChannel("tamaki-biblioteca"); b.postMessage({novo: it.id}); b.close(); } catch (e) {}
    return {id: it.id, dur, w: cv.width, h: cv.height};
  } finally { rec = null; cfg.bal.on = antes.bal; cfg.guides = antes.guias; }
};
