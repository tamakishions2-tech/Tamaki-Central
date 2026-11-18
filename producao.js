/* Linha de produção · Tamaki Central
   Roteiro (aba Escrita › Roteiros da Tamaki) → falas no Estúdio de voz (Kaggle) → Biblioteca (pasta do vídeo) → Editor montado.
   O roteiro: uma fala por linha, com a emoção na frente: "(brava) Chamei ele na chincha!".
   Linhas que começam com # são ignoradas (servem de anotação). */
(function () {
  "use strict";
  const norm = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
  const espera = ms => new Promise(r => setTimeout(r, ms));
  const lerJ = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } };
  const gravaJ = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };

  // o texto da nota, uma fala por linha
  function linhasDe(html) {
    const d = document.createElement("div"); d.innerHTML = html || "";
    d.querySelectorAll("br").forEach(b => b.replaceWith("\n"));
    d.querySelectorAll("p,div,li,h1,h2,h3,h4").forEach(e => e.append("\n"));
    return d.textContent.split("\n").map(s => s.replace(/\s+/g, " ").trim()).filter(s => s && !s.startsWith("#"))
      .map(s => { // [6:24] no começo: a partir de que momento do gameplay esta fala aparece
        let cena = null, close = false; const c = s.match(/^\[\s*(?:(\d+):)?(\d{1,2}):(\d{2})\s*\]\s*/);
        if (c) { cena = (+c[1] || 0) * 3600 + +c[2] * 60 + +c[3]; s = s.slice(c[0].length); }
        const cl = s.match(/^\[\s*(close|intro|fim|perto)\s*\]\s*/i); if (cl) { close = true; s = s.slice(cl[0].length); } // close na Tamaki (abertura e final)
        const m = s.match(/^\(([^)]{2,80})\)\s*(.*)$/); return Object.assign(m ? tomDe(m[1]) : {emo: "", tom: {}}, {texto: (m ? m[2] : s).trim(), linha: s, cena, close}); })
      .filter(l => l.texto);
  }
  /* Tom de cada fala, dentro dos parênteses, separado por vírgula: (brava, forte, rápida, pausa)
     intensidade: suave · normal · forte · exagerada        → exaggeration
     ritmo:       lenta · rápida                             → cfg_weight
     jeito:       firme (sempre igual) · solta (mais variada) → temperature
     pausa / pausa longa: silêncio depois da fala
     Ou números exatos: (brava, exag=1.1, cfg=.4, temp=.9, pausa=1.2) */
  const TONS = {
    suave: {exaggeration: .35}, leve: {exaggeration: .35}, normal: {exaggeration: .6}, forte: {exaggeration: .85}, intensa: {exaggeration: .85}, exagerada: {exaggeration: 1.2}, "muito forte": {exaggeration: 1.2},
    lenta: {cfg_weight: .3}, devagar: {cfg_weight: .3}, calma: {cfg_weight: .35}, "rapida": {cfg_weight: .7}, acelerada: {cfg_weight: .7},
    firme: {temperature: .6}, estavel: {temperature: .6}, solta: {temperature: 1}, variada: {temperature: 1},
    pausa: {pausa: .9}, "pausa longa": {pausa: 1.6}, "sem pausa": {pausa: .1}
  };
  const CHAVES = {exag: "exaggeration", emocao: "exaggeration", intensidade: "exaggeration", cfg: "cfg_weight", ritmo: "cfg_weight", temp: "temperature", variacao: "temperature", pausa: "pausa"};
  const LIM = {exaggeration: [.25, 1.5], cfg_weight: [0, 1], temperature: [.4, 1.2], pausa: [0, 4]};
  function tomDe(dentro) {
    const tom = {}; let emo = "";
    for (const p0 of dentro.split(/[,;|]/)) { const p = norm(p0); if (!p) continue;
      const kv = p.match(/^([a-z]+)\s*[=:]\s*([\d.,]+)$/);
      if (kv && CHAVES[kv[1]]) { tom[CHAVES[kv[1]]] = parseFloat(kv[2].replace(",", ".")); continue; }
      if (TONS[p]) { Object.assign(tom, TONS[p]); continue; }
      if (!emo) emo = p0.trim(); }
    for (const k in tom) { const [a, b] = LIM[k]; if (!isFinite(tom[k])) delete tom[k]; else tom[k] = Math.min(b, Math.max(a, tom[k])); }
    return {emo, tom};
  }

  /* ---------- Estúdio de voz (mesmo código de ligação e mesmo Kaggle das outras abas) ---------- */
  const EST = {url: null};
  const codigo = () => { try { return localStorage.getItem("tvz_codigo") || ""; } catch (e) { return ""; } };
  async function responde(u) { const c = new AbortController(), t = setTimeout(() => c.abort(), 7000); try { return (await fetch(u + "/", {signal: c.signal})).ok; } catch (e) { return false; } finally { clearTimeout(t); } }
  async function ligar() {
    if (EST.url && await responde(EST.url)) return true;
    let c = codigo();
    if (!c) { c = (prompt("Para gerar as falas, cole o código de ligação do Estúdio de voz (começa com tamaki-). Ele fica guardado neste aparelho.") || "").trim(); if (!c) return false; try { localStorage.setItem("tvz_codigo", c); } catch (e) {} }
    const r = await fetch(`https://ntfy.sh/${encodeURIComponent(c)}/json?poll=1&since=12h`);
    const ms = (await r.text()).trim().split("\n").filter(Boolean).map(l => { try { const m = JSON.parse(l); return m.event === "message" ? JSON.parse(m.message) : null; } catch (e) { return null; } }).filter(Boolean);
    const fechados = new Set(ms.filter(m => m.estado === "encerrado").map(m => m.url));
    for (const u of [...new Set(ms.filter(m => m.estado === "ligado" && m.url && !fechados.has(m.url)).map(m => m.url).reverse())]) if (await responde(u)) { EST.url = u; return true; }
    return false;
  }
  async function est(rota, o = {}) {
    const cab = {"x-codigo": codigo()}; let corpo = o.body; if (corpo) { corpo = JSON.stringify(corpo); cab["Content-Type"] = "application/json"; }
    const r = await fetch(EST.url + rota, {method: corpo ? "POST" : "GET", headers: cab, body: corpo});
    if (!r.ok) { let m = r.statusText; try { m = (await r.json()).erro || m; } catch (e) {} if (r.status == 401) m = "código de ligação errado (confira na aba Kaggle do Estúdio)"; throw new Error(m); }
    return o.resp ? r : r.json();
  }

  /* ---------- Biblioteca ---------- */
  const abrirBib = () => new Promise((ok, no) => { const r = indexedDB.open("tamaki-biblioteca", 1);
    r.onupgradeneeded = () => { if (!r.result.objectStoreNames.contains("itens")) r.result.createObjectStore("itens", {keyPath: "id"}); };
    r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });
  async function bib(modo, fn) { const db = await abrirBib(); try { return await new Promise((ok, no) => { const t = db.transaction("itens", modo); const q = fn(t.objectStore("itens")); t.oncomplete = () => ok(q && q.result); t.onerror = () => no(t.error); }); } finally { db.close(); } }
  async function guardar(blob, o) {
    const it = Object.assign({id: "b" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7), tipo: "audio", mime: (blob.type || "audio/wav").split(";")[0], tamanho: blob.size, criado: Date.now(), blob}, o);
    await bib("readwrite", s => s.put(it));
    try { const c = new BroadcastChannel("tamaki-biblioteca"); c.postMessage({novo: it.id}); c.close(); } catch (e) {}
    return it.id;
  }
  // a pasta do vídeo em andamento; sem ela, cria uma com o nome do roteiro
  function pastaDoVideo(titulo, notaId) {
    const A = lerJ("tamaki-bib-auto", {}), P = lerJ("tamaki-bib-pastas", []);
    let p = A.ligado !== false && A.pasta ? P.find(x => x.id === A.pasta) : null;
    if (!p) { p = {id: "p" + Date.now().toString(36), nome: titulo || "Vídeo novo", rot: []}; P.push(p);
      if (window.TamakiOrganizador) TamakiOrganizador.usarPasta(p.id); else gravaJ("tamaki-bib-auto", Object.assign({ligado: true, renomear: true, emocoes: true, repetidos: true}, A, {pasta: p.id, desde: Date.now()})); }
    if (notaId && !(p.rot || []).includes(notaId)) p.rot = (p.rot || []).concat(notaId);
    gravaJ("tamaki-bib-pastas", P);
    return p;
  }

  /* ---------- Editor (aba da Central) ---------- */
  const abrirAba = (aba, fica) => { try { (window.parent !== window ? window.parent : window).postMessage({central: "abrir", aba, fica}, location.origin); } catch (e) {} };
  async function editor(dados, aviso) {
    abrirAba("editor", true);
    const eu = "pr" + Date.now().toString(36), bc = new BroadcastChannel("tamaki-editor");
    try {
      // pode haver mais de um Editor aberto (o da Central e o da Sala de edição): monta em todos
      const eds = new Map(); bc.onmessage = e => { const d = e.data || {}; if (d.tipo === "pong" && d.de === eu) eds.set(d.id, d); };
      for (let i = 0; i < 40 && !eds.size; i++) { bc.postMessage({tipo: "ping", de: eu}); await espera(500); }
      await espera(1200); // dá tempo do segundo Editor responder
      const livres = [...eds.values()].filter(x => !x.exportando);
      if (!eds.size) return {erro: "o Editor não abriu. Abra a aba 🎞️ Editor e toque em 🎬 Produzir de novo"};
      if (!livres.length) return {erro: "o Editor está exportando um vídeo agora"};
      if (aviso) aviso(`🎞️ Montando no Editor${livres.length > 1 ? ` (${livres.length} editores abertos)` : ""}…`);
      return await new Promise(ok => { const t = setTimeout(() => ok({erro: "o Editor não respondeu"}), 120000); let falta = livres.length, bom = null;
        bc.onmessage = e => { const d = e.data || {}; if (d.tipo === "montado" && d.para === eu) { if (!d.erro) bom = d; if (--falta <= 0) { clearTimeout(t); ok(bom || d); } } };
        for (const x of livres) bc.postMessage(Object.assign({tipo: "montar", para: x.id, de: eu}, dados)); });
    } finally { bc.close(); }
  }

  // sinais para a Central mostrar o andamento (barra 🎬 no topo)
  function sinal(etapa, texto, extra) { try { const c = new BroadcastChannel("tamaki-producao"); c.postMessage(Object.assign({etapa, texto, quando: Date.now()}, extra || {})); c.close(); } catch (e) {} }
  /* ---------- Palco (aba da Central): toca as falas e grava a cena de cima ---------- */
  async function palco(dados, aviso) {
    if (window.TamakiPalcoGravar) { aviso("🎭 Palco gravando a cena da Tamaki…"); return await window.TamakiPalcoGravar(dados); }
    abrirAba("palco", false); // o Palco precisa estar na tela para desenhar
    const eu = "pr" + Date.now().toString(36), bc = new BroadcastChannel("tamaki-palco");
    try {
      let pa = null; bc.onmessage = e => { const d = e.data || {}; if (d.tipo === "pong" && d.de === eu) pa = d; };
      for (let i = 0; i < 40 && !pa; i++) { bc.postMessage({tipo: "ping", de: eu}); await espera(500); }
      if (!pa) return {erro: "o Palco não abriu"};
      if (pa.ocupado) return {erro: "o Palco já está gravando"};
      await espera(1200); // a cena termina de carregar os PNGs
      aviso("🎭 Palco gravando a cena da Tamaki…");
      const total = (dados.duracao || 60) * 1000 + 90000;
      return await new Promise(ok => { const t = setTimeout(() => ok({erro: "o Palco não terminou a gravação"}), total);
        bc.onmessage = e => { const d = e.data || {}; if (d.tipo === "gravado" && d.para === eu) { clearTimeout(t); ok(d); } };
        bc.postMessage(Object.assign({tipo: "gravar", para: pa.id, de: eu}, dados)); });
    } finally { bc.close(); }
  }
  let rodando = false, rodandoDesde = 0;
  async function produzir(nota, aviso0) {
    const ETAPA = {"🔌": "voz", "🎙": "falas", "🎭": "palco", "🎞": "editor", "✓": "pronto"};
    const aviso = t => { (aviso0 || (() => {}))(t); const e = Object.keys(ETAPA).find(k => t.startsWith(k));
      sinal(e ? ETAPA[e] : /^(Parei|Estúdio de voz desligado|O motor|O roteiro está vazio|As \d+ falas|Já estou)/.test(t) ? "erro" : "info", t); };
    sinal("recebido", `📥 Roteiro “${nota.titulo || "Roteiro"}” recebido na Escrita`);
    if (rodando && Date.now() - rodandoDesde < 600000) return aviso("Já estou produzindo um vídeo. Espere terminar (ou toque no ⟳ do navegador para recomeçar).");
    const linhas = linhasDe(nota.html); if (!linhas.length) return aviso("O roteiro está vazio: escreva uma fala por linha.");
    rodando = true; rodandoDesde = Date.now();
    try {
      aviso("🔌 Ligando no Estúdio de voz…");
      if (!(await ligar())) return aviso("Estúdio de voz desligado. Ligue o Kaggle e toque em 🎬 Produzir de novo.");
      const st = await est("/status");
      if (!st.motor || st.motor.estado !== "pronto") return aviso("O motor de voz ainda está carregando no Kaggle. Tente de novo em alguns minutos.");
      const lista = (st.emocoes && st.emocoes.lista) || [], conf = st.conf || {}, semEmo = new Set();
      const emoId = x => { if (!x) return ""; const e = lista.find(e => norm(e.id) === norm(x) || norm(e.nome) === norm(x)); if (!e || e.pronta === false) { semEmo.add(x); return ""; } return e.id; };
      const pasta = pastaDoVideo(nota.titulo, nota.id), ids = [];
      for (const [i, l] of linhas.entries()) {
        sinal("falas", "", {n: i, total: linhas.length});
        aviso(`🎙 Fala ${i + 1} de ${linhas.length}: ${l.texto.slice(0, 40)}${l.texto.length > 40 ? "…" : ""}`);
        // padrão "vivo" (menos robótico): mais emoção e variação, ritmo menos preso; o tom de cada fala manda quando existe
        const t = l.tom || {}, VIVO = {exaggeration: Math.max(conf.exaggeration ?? .5, .65), cfg_weight: Math.min(conf.cfg_weight ?? .5, .42), temperature: Math.max(conf.temperature ?? .8, .9)};
        const r = await est("/falar", {resp: true, body: {texto: l.texto, emocao: emoId(l.emo), exaggeration: t.exaggeration ?? VIVO.exaggeration, cfg_weight: t.cfg_weight ?? VIVO.cfg_weight, temperature: t.temperature ?? VIVO.temperature}});
        const nome = `${nota.titulo || "Roteiro"} · ${String(i + 1).padStart(2, "0")}${l.emo ? " · " + l.emo.toLowerCase() : ""}`;
        let blobFala = await r.blob(); if (window.TamakiPolir) blobFala = await window.TamakiPolir(blobFala);   // som macio (sem o metálico)
        ids.push(await guardar(blobFala, {origem: "voz", nome, nomeManual: 1, texto: l.linha, pasta: pasta.id, roteiro: nota.id, ordem: i}));
      }
      // gameplay: o vídeo mais novo da pasta (de preferência do Emulador)
      const todos = await bib("readonly", s => s.getAll()), vids = todos.filter(it => it.pasta === pasta.id && it.tipo === "video" && it.blob).sort((a, b) => (b.origem === "emulador") - (a.origem === "emulador") || b.criado - a.criado);
      // Palco: a Tamaki falando em cima (o texto vai na caixa do Editor, então o balão do Palco fica desligado)
      const pausas = linhas.map(l => (l.tom || {}).pausa ?? .3);
      let durTot = 0; for (const id of ids) { const it = await bib("readonly", s => s.get(id)); try { const c = new (window.OfflineAudioContext || window.webkitOfflineAudioContext)(1, 1, 44100); durTot += (await c.decodeAudioData(await it.blob.arrayBuffer())).duration; } catch (e) { durTot += 4; } }
      sinal("palco", "🎭 Abrindo o Palco…");
      const pr = await palco({ids, textos: linhas.map(l => l.texto), emos: linhas.map(l => l.emo || ""), pausas, ini: .2, semBalao: true, titulo: nota.titulo, pasta: pasta.id, duracao: durTot + pausas.reduce((a, b) => a + b, 0)}, aviso);
      if (pr.erro) aviso(`⚠ Sem a cena do Palco (${pr.erro}). Monto só com o jogo.`);
      const r = await editor({palco: pr.id || null, palcoDur: pr.dur || null, layout: "palco", pausasFinais: pausas, titulo: nota.titulo || "", final: nota.final || "", legendas: linhas.map(l => l.texto), emos: linhas.map(l => l.emo), tons: linhas.map(l => l.tom || {}), falas: ids, pausas: linhas.map(l => (l.tom || {}).pausa ?? null), cenas: linhas.map(l => l.cena), closes: linhas.map(l => !!l.close), redes: nota.redes || "", video: nota.video && todos.some(it => it.id === nota.video) ? nota.video : vids[0] ? vids[0].id : null}, aviso);
      const extra = semEmo.size ? ` · sem emoção treinada: ${[...semEmo].join(", ")}` : "";
      if (r.erro) return aviso(`As ${ids.length} falas estão na pasta “${pasta.nome}”, mas ${r.erro}.${extra}`);
      abrirAba("editor", false);
      aviso(`✓ Vídeo montado no Editor: ${ids.length} falas${vids[0] || nota.video ? " + gameplay" : " (sem gameplay na pasta)"}, título e final.${extra}`);
      gravaJ("tamaki-producao-feito", Object.assign(lerJ("tamaki-producao-feito", {}), {[nota.id]: assinatura(nota)}));
    } catch (e) { aviso("Parei: " + e.message); }
    finally { rodando = false; }
  }
  // para saber se o roteiro mudou desde a última vez que virou vídeo
  const assinatura = n => { const s = (n.titulo || "") + "|" + linhasDe(n.html).map(l => l.linha).join("\n"); let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return h; };
  const jaFeito = n => lerJ("tamaki-producao-feito", {})[n.id] === assinatura(n);

  window.TamakiProducao = {produzir, linhasDe, tomDe, jaFeito, ocupado: () => rodando};
})();
