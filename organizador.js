/* Organizador da Biblioteca · Tamaki Central
   Arruma sozinho cada coisa que entra na Biblioteca (IndexedDB "tamaki-biblioteca"):
   - põe na pasta do vídeo em andamento
   - troca nomes genéricos ("Gravação", "VID_2026…") por "Voz · 13/11 21:20 · brava"
   - etiqueta as emoções das falas e marca o que veio repetido
   Roda na Central e na Biblioteca; arrumar o mesmo item duas vezes não muda nada. */
(function () {
  "use strict";
  const CHAVE = "tamaki-bib-auto", ORIG = {palco: "Palco", atriz: "Atriz", voz: "Voz", editor: "Editor", efeitos: "Efeitos", escrita: "Escrita", emulador: "Emulador", outro: "Outros"};
  const PADRAO = {ligado: true, pasta: null, renomear: true, emocoes: true, repetidos: true};
  const cfg = () => { try { return Object.assign({}, PADRAO, JSON.parse(localStorage.getItem(CHAVE)) || {}); } catch (e) { return Object.assign({}, PADRAO); } };
  const salvaCfg = c => { try { localStorage.setItem(CHAVE, JSON.stringify(c)); } catch (e) {} };
  const pastas = () => { try { return JSON.parse(localStorage.getItem("tamaki-bib-pastas")) || []; } catch (e) { return []; } };
  const abrir = () => new Promise((ok, no) => { const r = indexedDB.open("tamaki-biblioteca", 1);
    r.onupgradeneeded = () => { if (!r.result.objectStoreNames.contains("itens")) r.result.createObjectStore("itens", {keyPath: "id"}); };
    r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });

  const generico = n => !n || /^(grava[cç][aã]o|recording|audio|áudio|video|vídeo|imagem|image|sem nome|clip|captura)\s*\d*$/i.test(n.trim())
    || /^(vid|img|aud|rec|pxl|screenrecorder|screen_recording|xrecorder|whatsapp)[\s_-]/i.test(n.trim()) || /^\d[\d_\-\s.]{6,}$/.test(n.trim());
  const emocoesDe = t => [...new Set([...(t || "").matchAll(/(?:^|\n)\s*\(([a-zà-ú ]{3,18})\)/gi)].map(m => m[1].trim().toLowerCase()))].slice(0, 4);
  const hora = d => d.toLocaleDateString("pt-BR", {day: "2-digit", month: "2-digit"}) + " " + d.toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit"});

  // adivinha a origem de algo que entrou sem dizer de onde veio
  function origemDe(it) {
    if (it.origem && it.origem !== "outro") return it.origem;
    const n = (it.nome || "").toLowerCase();
    if (/xrecorder|screen|emul|gba|mega|gameplay/.test(n)) return "emulador";
    if (/tamaki|voz|fala|narra/.test(n) && it.tipo === "audio") return "voz";
    return it.origem || "outro";
  }

  // devolve o item arrumado (ou null se não mudou nada)
  function arrumar(it, todos, c, forcar) {
    if (!it || (it.auto && !forcar)) return null;
    const antes = JSON.stringify([it.origem, it.nome, it.pasta, it.tags]);
    it.origem = origemDe(it);
    const em = emocoesDe(it.texto);
    if (c.renomear && generico(it.nome) && !it.nomeManual) it.nome = [ORIG[it.origem] || "Outros", hora(new Date(it.criado || Date.now())), em[0]].filter(Boolean).join(" · ");
    const tags = new Set(it.tags || []);
    if (c.emocoes) em.forEach(e => tags.add(e));
    if (c.repetidos && todos.some(o => o.id !== it.id && o.tamanho === it.tamanho && o.mime === it.mime && (it.tipo !== "audio" || (o.texto || "") === (it.texto || "")) && (o.criado || 0) < (it.criado || 0))) tags.add("repetido");
    it.tags = [...tags];
    // pasta do vídeo em andamento: só para o que chegou depois dela ser escolhida
    if (!it.pasta && c.pasta && pastas().some(p => p.id === c.pasta) && (forcar === "tudo" ? false : (it.criado || 0) >= (c.desde || 0))) it.pasta = c.pasta;
    it.auto = 1;
    return JSON.stringify([it.origem, it.nome, it.pasta, it.tags]) !== antes ? it : null;
  }

  async function processar(ids, forcar) {
    const c = cfg(); if (!c.ligado && !forcar) return 0;
    const db = await abrir(); let n = 0, ultimo = null;
    await new Promise((ok, no) => { const tx = db.transaction("itens", "readwrite"), st = tx.objectStore("itens");
      const q = st.getAll(); q.onsuccess = () => { const todos = q.result || [];
        for (const it of todos) { if (ids && !ids.includes(it.id)) continue; if (it.auto && !forcar) continue;
          const a = JSON.stringify([it.origem, it.nome, it.pasta, it.tags]); arrumar(it, todos, c, forcar);
          if (JSON.stringify([it.origem, it.nome, it.pasta, it.tags]) !== a) { n++; ultimo = it; } st.put(it); } };
      tx.oncomplete = ok; tx.onerror = () => no(tx.error); });
    db.close();
    if (n) { try { const b = new BroadcastChannel("tamaki-biblioteca"); b.postMessage({mudou: 1, organizador: 1}); b.close(); } catch (e) {} }
    return {n, ultimo};
  }

  let fila = [], timer = 0, aviso = null;
  function ouvir() {
    try { new BroadcastChannel("tamaki-biblioteca").onmessage = e => { const d = e.data || {}; if (!d.novo) return;
      fila.push(d.novo); clearTimeout(timer);
      timer = setTimeout(async () => { const ids = fila.splice(0); try { const r = await processar(ids);
        if (r && r.ultimo && aviso) { const p = pastas().find(x => x.id === r.ultimo.pasta); aviso(`📚 “${r.ultimo.nome}” guardado${p ? " em " + p.nome : ""}`); } } catch (e) {} }, 400); }; } catch (e) {}
  }

  window.TamakiOrganizador = {
    cfg, salvaCfg, processar, emocoesDe, generico,
    // pasta do vídeo em andamento: tudo que entrar daqui pra frente vai pra ela
    usarPasta(id) { const c = cfg(); c.pasta = id || null; c.desde = Date.now(); salvaCfg(c); },
    arrumarTudo: () => processar(null, "tudo"),
    iniciar(opcoes) { aviso = (opcoes && opcoes.aviso) || null; ouvir(); processar(null).catch(() => {}); }
  };
})();
