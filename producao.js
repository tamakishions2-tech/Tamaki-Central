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
      .map(s => { const m = s.match(/^\(([^)]{2,24})\)\s*(.*)$/); return m ? {emo: m[1].trim(), texto: m[2].trim(), linha: s} : {emo: "", texto: s, linha: s}; })
      .filter(l => l.texto);
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
  async function editor(dados, aviso) {
    try { if (window.parent !== window) window.parent.postMessage({central: "abrir", aba: "editor", fica: true}, location.origin); } catch (e) {}
    const eu = "pr" + Date.now().toString(36), bc = new BroadcastChannel("tamaki-editor");
    try {
      let ed = null; bc.onmessage = e => { const d = e.data || {}; if (d.tipo === "pong" && d.de === eu) ed = d; };
      for (let i = 0; i < 40 && !ed; i++) { bc.postMessage({tipo: "ping", de: eu}); await espera(500); }
      if (!ed) return {erro: "o Editor não abriu. Abra a aba 🎞️ Editor e toque em 🎬 Produzir de novo"};
      if (ed.exportando) return {erro: "o Editor está exportando um vídeo agora"};
      if (aviso) aviso("🎞️ Montando no Editor…");
      const r = await new Promise(ok => { const t = setTimeout(() => ok({erro: "o Editor não respondeu"}), 120000);
        bc.onmessage = e => { const d = e.data || {}; if (d.tipo === "montado" && d.para === eu) { clearTimeout(t); ok(d); } };
        bc.postMessage(Object.assign({tipo: "montar", para: ed.id, de: eu}, dados)); });
      return r;
    } finally { bc.close(); }
  }

  let rodando = false;
  async function produzir(nota, aviso) {
    aviso = aviso || (() => {});
    if (rodando) return aviso("Já estou produzindo um vídeo. Espere terminar.");
    const linhas = linhasDe(nota.html); if (!linhas.length) return aviso("O roteiro está vazio: escreva uma fala por linha.");
    rodando = true;
    try {
      aviso("🔌 Ligando no Estúdio de voz…");
      if (!(await ligar())) return aviso("Estúdio de voz desligado. Ligue o Kaggle e toque em 🎬 Produzir de novo.");
      const st = await est("/status");
      if (!st.motor || st.motor.estado !== "pronto") return aviso("O motor de voz ainda está carregando no Kaggle. Tente de novo em alguns minutos.");
      const lista = (st.emocoes && st.emocoes.lista) || [], conf = st.conf || {}, semEmo = new Set();
      const emoId = x => { if (!x) return ""; const e = lista.find(e => norm(e.id) === norm(x) || norm(e.nome) === norm(x)); if (!e || e.pronta === false) { semEmo.add(x); return ""; } return e.id; };
      const pasta = pastaDoVideo(nota.titulo, nota.id), ids = [];
      for (const [i, l] of linhas.entries()) {
        aviso(`🎙 Fala ${i + 1} de ${linhas.length}: ${l.texto.slice(0, 40)}${l.texto.length > 40 ? "…" : ""}`);
        const r = await est("/falar", {resp: true, body: {texto: l.texto, emocao: emoId(l.emo), exaggeration: conf.exaggeration ?? .5, cfg_weight: conf.cfg_weight ?? .5, temperature: conf.temperature ?? .8}});
        const nome = `${nota.titulo || "Roteiro"} · ${String(i + 1).padStart(2, "0")}${l.emo ? " · " + l.emo.toLowerCase() : ""}`;
        ids.push(await guardar(await r.blob(), {origem: "voz", nome, nomeManual: 1, texto: l.linha, pasta: pasta.id, roteiro: nota.id, ordem: i}));
      }
      // gameplay: o vídeo mais novo da pasta (de preferência do Emulador)
      const todos = await bib("readonly", s => s.getAll()), vids = todos.filter(it => it.pasta === pasta.id && it.tipo === "video" && it.blob).sort((a, b) => (b.origem === "emulador") - (a.origem === "emulador") || b.criado - a.criado);
      const r = await editor({titulo: nota.titulo || "", final: "Até a próxima!", falas: ids, video: vids[0] ? vids[0].id : null}, aviso);
      const extra = semEmo.size ? ` · sem emoção treinada: ${[...semEmo].join(", ")}` : "";
      if (r.erro) return aviso(`As ${ids.length} falas estão na pasta “${pasta.nome}”, mas ${r.erro}.${extra}`);
      try { if (window.parent !== window) window.parent.postMessage({central: "abrir", aba: "editor"}, location.origin); } catch (e) {}
      aviso(`✓ Vídeo montado no Editor: ${ids.length} falas${vids[0] ? " + gameplay" : " (sem gameplay na pasta)"}, título e final.${extra}`);
      gravaJ("tamaki-producao-feito", Object.assign(lerJ("tamaki-producao-feito", {}), {[nota.id]: assinatura(nota)}));
    } catch (e) { aviso("Parei: " + e.message); }
    finally { rodando = false; }
  }
  // para saber se o roteiro mudou desde a última vez que virou vídeo
  const assinatura = n => { const s = (n.titulo || "") + "|" + linhasDe(n.html).map(l => l.linha).join("\n"); let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return h; };
  const jaFeito = n => lerJ("tamaki-producao-feito", {})[n.id] === assinatura(n);

  window.TamakiProducao = {produzir, linhasDe, jaFeito, ocupado: () => rodando};
})();
