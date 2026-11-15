# ============ Gerador de Imagem da Tamaki · versão 2 (baixada do GitHub pela célula) ============
# A célula do Kaggle define CODIGO (e, se quiser, HORAS, SATURACAO…). Este arquivo é público: nunca ponha o CODIGO aqui.
try:
    CODIGO
except NameError:
    raise SystemExit("Falta a linha CODIGO = \"tamaki-img-…\" na célula. Use a célula de kaggle/celula-imagem.py.")
HORAS = globals().get("HORAS", 3)
SEGREDO_HF = globals().get("SEGREDO_HF", "HF_TOKEN")
SATURACAO = globals().get("SATURACAO", 1.12)
CONTRASTE = globals().get("CONTRASTE", 1.04)
COR_TREINO = globals().get("COR_TREINO", 1.18)
# IA de texto que entende o seu pedido em português e escreve as etiquetas (roda no Kaggle, grátis)
MODELO_TEXTO = globals().get("MODELO_TEXTO", "")   # vazio = escolhe sozinho (7B com 2 GPUs, 3B com 1)
VERSAO = 4
import os, sys, glob, json, time, subprocess, threading, re, io, base64, uuid, random, queue, shutil, gc

def rodar(cmd, cwd=None, cada_linha=None):
    p = subprocess.Popen(cmd, cwd=cwd, shell=isinstance(cmd, str), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for linha in p.stdout:
        print(linha, end="")
        if cada_linha: cada_linha(linha)
    if p.wait(): raise RuntimeError("o comando falhou (veja as linhas acima)")

def instalar(pacotes, atualizar=""):
    rodar(f"{sys.executable} -m pip -q install {pacotes}" + (f" && {sys.executable} -m pip -q install -U {atualizar}" if atualizar else ""))

W, LORA_DIR = "/kaggle/working", "/kaggle/working/lora"
print("Instalando o que falta…")
instalar("huggingface_hub requests transformers accelerate safetensors compel bitsandbytes", "diffusers peft")
# o Kaggle vem com um torchao velho que faz o LoRA recusar carregar; sem ele, funciona
subprocess.run(f"{sys.executable} -m pip uninstall -y -q torchao", shell=True)
from kaggle_secrets import UserSecretsClient
from huggingface_hub import HfApi, hf_hub_download, list_repo_files, snapshot_download
import requests, torch
from PIL import Image, ImageEnhance, ImageStat
if not torch.cuda.is_available(): raise RuntimeError("Sem GPU: vá em Settings › Accelerator e escolha GPU T4 x2")
from compel import Compel, ReturnedEmbeddingsType
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline, EulerAncestralDiscreteScheduler, AutoencoderKL
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
TOK = UserSecretsClient().get_secret(SEGREDO_HF)
api = HfApi(token=TOK)
REPO = api.whoami()["name"] + "/tamaki-lora"
api.create_repo(REPO, private=True, exist_ok=True)
ORIGINAIS = (glob.glob("/kaggle/input/**/10_tmkshion", recursive=True) or [None])[0]
EXTRA = W + "/treino_extra"

def ordem(c):
    m = re.search(r"-(\d+)\.safetensors$", c)
    return (re.sub(r"-\d+\.safetensors$|\.safetensors$", "", os.path.basename(c)), int(m.group(1)) if m else 10**6)

def realce(img):
    # devolve a cor que o desenho perde; não muda o traço nem a composição
    if SATURACAO != 1: img = ImageEnhance.Color(img).enhance(SATURACAO)
    if CONTRASTE != 1: img = ImageEnhance.Contrast(img).enhance(CONTRASTE)
    return img

# ---------- modelo de gerar ----------
pipe, LORAS, TRAVA, ERROS_LORA, compel = None, {}, threading.Lock(), {}, None
def carregar():
    global pipe, LORAS, compel
    print("Carregando o modelo…")
    vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
    pipe = StableDiffusionXLPipeline.from_pretrained("cagliostrolab/animagine-xl-4.0", vae=vae,
        torch_dtype=torch.float16, use_safetensors=True, add_watermarker=False)
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.to("cuda:0"); pipe.vae.enable_slicing(); pipe.vae.enable_tiling()
    try: snapshot_download(REPO, local_dir=LORA_DIR, token=TOK, allow_patterns="*.safetensors")
    except Exception as e: print("Não baixei LoRAs do Hugging Face:", e)
    LORAS = {}; ERROS_LORA.clear()
    for i, arq in enumerate(sorted(glob.glob(LORA_DIR + "/*.safetensors"), key=ordem)):
        nome = os.path.basename(arq)[:-12]
        try: pipe.load_lora_weights(arq, adapter_name=f"l{i}"); LORAS[nome] = f"l{i}"
        except Exception as e: ERROS_LORA[nome] = f"{type(e).__name__}: {e}"[:400]
    if LORAS: pipe.disable_lora()
    # prompt comprido: o normal corta tudo depois de 77 pedaços; o compel junta em blocos
    compel = Compel(tokenizer=[pipe.tokenizer, pipe.tokenizer_2], text_encoder=[pipe.text_encoder, pipe.text_encoder_2],
        returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
        requires_pooled=[False, True], truncate_long_prompts=False)
    resumo_lora()
def resumo_lora():
    print("\n🎨 Versões da Tamaki (LoRA):", ", ".join(LORAS) or "nenhuma")
    for n, e in ERROS_LORA.items(): print(f"⚠️ Não consegui carregar {n}: {e}")
def descarregar():
    global pipe
    pipe = None; gc.collect(); torch.cuda.empty_cache()

# ---------- caprichar: aumenta 1,5x e repassa de leve (o "hires fix"): mais detalhe no rosto e no cenário ----------
def caprichar(img, p, s):
    try:
        i2i = StableDiffusionXLImg2ImgPipeline.from_pipe(pipe)
        W2, H2 = int(img.width * 1.5) // 8 * 8, int(img.height * 1.5) // 8 * 8
        grande = img.resize((W2, H2), Image.LANCZOS)
        c, cp = compel(p["prompt"]); nc, ncp = compel(p.get("negativo", "") or "")
        c, nc = compel.pad_conditioning_tensors_to_same_length([c, nc])
        return i2i(prompt_embeds=c, pooled_prompt_embeds=cp, negative_prompt_embeds=nc, negative_pooled_prompt_embeds=ncp,
                   image=grande, strength=0.35, num_inference_steps=20, guidance_scale=float(p.get("cfg", 5)),
                   generator=torch.Generator("cuda").manual_seed(s)).images[0]
    except Exception as e:
        print("Não consegui caprichar (fica a imagem normal):", e); torch.cuda.empty_cache(); return img

# ---------- IA de texto: o seu pedido em português vira etiquetas que o Animagine entende ----------
TX = {"m": None, "tok": None, "estado": "desligada", "erro": ""}
TRAVA_TX = threading.Lock()
DEV_TX = "cuda:1" if torch.cuda.device_count() > 1 else "cuda:0"
if not MODELO_TEXTO: MODELO_TEXTO = "Qwen/Qwen2.5-7B-Instruct" if DEV_TX == "cuda:1" else "Qwen/Qwen2.5-3B-Instruct"
def carregar_texto():
    with TRAVA_TX:
        if TX["m"] is not None or TX["estado"] == "carregando": return
        TX["estado"] = "carregando"
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        print(f"Carregando a IA de texto ({MODELO_TEXTO}) na {DEV_TX}…")
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4") if ("7B" in MODELO_TEXTO or DEV_TX == "cuda:0") else None
        TX["tok"] = AutoTokenizer.from_pretrained(MODELO_TEXTO, token=TOK)
        TX["m"] = AutoModelForCausalLM.from_pretrained(MODELO_TEXTO, token=TOK, torch_dtype=torch.float16, quantization_config=q, device_map={"": DEV_TX})
        TX["estado"] = "pronta"; print("🗣️ IA de texto pronta: já dá para pedir em português.")
    except Exception as e:
        TX.update(estado="erro", erro=f"{type(e).__name__}: {e}"[:300]); print("IA de texto não carregou:", TX["erro"])
def soltar_texto():
    TX.update(m=None, tok=None, estado="desligada"); gc.collect(); torch.cuda.empty_cache()

INSTRUCAO = """You are the art director of an anime illustration generator (Animagine XL 4.0, an SDXL model that ONLY understands Danbooru tags).
The user is Tama, the creator of the character Tamaki Shion (an elf woman). He writes in Brazilian Portuguese, casually, like talking to a friend.
Turn his request into Danbooru tags for the SCENE. The app already adds the character, her face, hair, skin, ears, art style and quality tags: never describe those.
Rules:
- Only real Danbooru tags, lowercase, English, separated by ", ", spaces instead of underscores. No sentences.
- Order: pose/action, expression, outfit, props, framing (portrait, upper body, cowboy shot, full body), camera angle, lighting, time of day, then place details (only if no place id fits).
- Be concrete: "sitting on couch, reading book, holding book", not "relaxing".
- 8 to 25 tags. Keep everything he asked for; do not invent big things he did not ask for.
- If PREVIOUS TAGS are given and the request is a change ("agora…", "muda…", "tira…", "põe…", "mais…"), edit the previous tags: keep the rest, change only what he asked.
- "lugar": choose the id of one of the PLACES when it fits, otherwise "".
- "formato": "story" for stories/vertical full body, "paisagem" for wide scenery, "quadrado" for square, otherwise "".
- "evitar": extra negative tags only if he asked to avoid something (e.g. "crosses"), otherwise "".
- If another character appears with Tamaki, start the tags with the count tags counting Tamaki too (1girl, 1boy / 2girls / 2girls, 1boy…) and use that character's tags from KNOWN CHARACTERS when given (keep their trigger word first). Use real Danbooru character tags like "bulbasaur", "pikachu", "character name (series)".
- "resposta": one short sentence in Brazilian Portuguese telling him what you will draw.
Answer ONLY with JSON: {"tags": "...", "lugar": "...", "formato": "...", "evitar": "...", "resposta": "..."}"""
EXEMPLOS = [
    ("faz ela sentada no sofá lendo um livro de noite com a galinha de pelúcia do lado", "",
     {"tags": "sitting, on couch, reading, holding book, open book, smile, hoodie, stuffed chicken, stuffed toy, cowboy shot, from side, lamp, night, warm lighting", "lugar": "sala", "formato": "", "evitar": "", "resposta": "Ela no sofá lendo à noite, com a galinha do lado."}),
    ("agora ela rindo e de pijama", "sitting, on couch, reading, holding book, open book, smile, hoodie, stuffed chicken, stuffed toy, cowboy shot, from side, lamp, night, warm lighting",
     {"tags": "sitting, on couch, reading, holding book, open book, laughing, open mouth, pajamas, stuffed chicken, stuffed toy, cowboy shot, from side, lamp, night, warm lighting", "lugar": "sala", "formato": "", "evitar": "", "resposta": "Mesma cena, agora rindo e de pijama."}),
    ("ela jogando videogame toda concentrada, de fone, story", "",
     {"tags": "sitting, playing video games, holding controller, concentrating, serious, headphones, oversized shirt, upper body, from side, screen light, night, dark room", "lugar": "mesa", "formato": "story", "evitar": "", "resposta": "Ela concentrada no game, de fone, no formato story."}),
]
# ---------- conferência no Danbooru: o modelo aprendeu com as etiquetas de lá ----------
DB = {}
def danbooru(tag):
    """(nome certo, nº de imagens) ou (None, 0). Usa apelidos e o autocompletar do Danbooru. Guarda o resultado."""
    t = tag.strip().lower().replace(" ", "_")
    if not t: return (None, 0)
    if t in DB: return DB[t]
    r = (None, 0)
    try:
        H = {"User-Agent": "TamakiCentral/1.0 (gerador pessoal)"}
        j = requests.get("https://danbooru.donmai.us/tags.json", params={"search[name]": t, "search[hide_empty]": "true"}, headers=H, timeout=8).json()
        if j: r = (j[0]["name"], int(j[0]["post_count"]))
        else:
            a = requests.get("https://danbooru.donmai.us/tag_aliases.json", params={"search[antecedent_name]": t, "search[status]": "active"}, headers=H, timeout=8).json()
            if a:
                return danbooru(a[0]["consequent_name"].replace("_", " ")) if a[0]["consequent_name"] != t else r
            c = requests.get("https://danbooru.donmai.us/autocomplete.json", params={"search[query]": t, "search[type]": "tag_query", "limit": 1}, headers=H, timeout=8).json()
            if c and c[0].get("value"):
                v = c[0]["value"]; n = int(c[0].get("post_count") or 0)
                r = (v, n)
    except Exception as e:
        print("Danbooru não respondeu:", e); return (tag, -1)   # -1 = não deu para conferir
    DB[t] = r
    return r

COMUNS = set("1girl 1boy 2girls 2boys 3girls solo indoors outdoors night day smile".split())
def conferir(tags, protegidas=()):
    """Troca etiquetas por nomes do Danbooru e avisa as que o modelo provavelmente não conhece."""
    saida, avisos = [], []
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(6) as ex:   # confere várias de uma vez (fica guardado para a próxima)
        list(ex.map(danbooru, [t for t in tags if t.lower() not in COMUNS and t not in protegidas]))
    for tg in tags:
        if tg.lower() in COMUNS or tg in protegidas or tg.lower() in protegidas:
            saida.append(tg); continue
        nome, n = danbooru(tg)
        if n < 0: saida.append(tg); continue
        if not nome:
            avisos.append(f"“{tg}” não existe no Danbooru: tirei (ensine em 🧠 Saber)"); continue
        nome = nome.replace("_", " ")
        if nome.lower() != tg.lower(): avisos.append(f"“{tg}” → “{nome}”")
        if n < 30: avisos.append(f"“{nome}” tem só {n} imagens: o modelo mal conhece")
        saida.append(nome)
    return saida, avisos

def entender(texto, anterior="", lugares=None, gosto="", exemplos=None, conhecidos=None, conferir_db=True):
    if TX["m"] is None:
        carregar_texto()
        if TX["m"] is None: raise RuntimeError("a IA de texto não carregou: " + TX["erro"])
    lug = "\n".join(f"- {l.get('id')}: {l.get('n')} ({l.get('t')})" for l in (lugares or [])) or "(none)"
    con = "\n".join(f"- {c.get('nome')} ({c.get('universo', '')}): {', '.join(x for x in [c.get('gatilho', ''), c.get('tags', '')] if x)}" for c in (conhecidos or [])[:12])
    sis = INSTRUCAO + f"\nPLACES:\n{lug}" + (f"\nKNOWN CHARACTERS (use exactly these tags when they appear):\n{con}" if con else "") + (f"\nTAMA'S TASTE (always respect): {gosto}" if gosto else "")
    msgs = [{"role": "system", "content": sis}]
    for pt, ant, js in EXEMPLOS + [(e.get("pedido", ""), e.get("anterior", ""), {"tags": e.get("tags", ""), "lugar": e.get("lugar", ""), "formato": "", "evitar": "", "resposta": "Do jeito que você gostou."}) for e in (exemplos or [])[-6:] if e.get("pedido") and e.get("tags")]:
        msgs += [{"role": "user", "content": (f"PREVIOUS TAGS: {ant}\n" if ant else "") + f"REQUEST: {pt}"}, {"role": "assistant", "content": json.dumps(js, ensure_ascii=False)}]
    msgs.append({"role": "user", "content": (f"PREVIOUS TAGS: {anterior}\n" if anterior else "") + f"REQUEST: {texto}"})
    tok, m = TX["tok"], TX["m"]
    with TRAVA_TX:
        txt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        ids = tok(txt, return_tensors="pt").input_ids.to(DEV_TX)
        out = m.generate(input_ids=ids, max_new_tokens=300, do_sample=False, pad_token_id=tok.eos_token_id)
    t = tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
    a, b = t.find("{"), t.rfind("}")
    try: d = json.loads(t[a:b + 1])
    except Exception: d = {"tags": re.sub(r"[\n\"{}]", " ", t).strip(), "resposta": "Entendi assim."}
    tags = [x.strip().replace("_", " ") for x in str(d.get("tags", "")).split(",") if x.strip()]
    vistos, limpas = set(), []
    for x in tags:
        if x.lower() not in vistos: vistos.add(x.lower()); limpas.append(x)
    avisos = []
    if conferir_db:
        prot = set()
        for c in conhecidos or []:
            for x in [c.get("gatilho", "")] + str(c.get("tags", "")).split(","):
                if x.strip(): prot.add(x.strip()); prot.add(x.strip().lower())
        limpas, avisos = conferir(limpas[:30], prot)
    return {"avisos": avisos[:8], "tags": ", ".join(limpas[:30]), "lugar": str(d.get("lugar") or ""), "formato": str(d.get("formato") or ""),
            "evitar": str(d.get("evitar") or ""), "resposta": str(d.get("resposta") or "")}

# ---------- aprender: um link ou um texto vira fichas para o "Saber" da Tamaki ----------
def texto_do_link(url):
    H = {"User-Agent": "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"}
    r = requests.get(url, headers=H, timeout=20); r.raise_for_status()
    h = r.text
    h = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|aside)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?is)<br\s*/?>|</p>|</li>|</h\d>|</tr>", "\n", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    import html as H2
    h = H2.unescape(h)
    h = "\n".join(" ".join(l.split()) for l in h.split("\n"))
    h = re.sub(r"\n{2,}", "\n", h).strip()
    if len(h) < 200: raise RuntimeError("a página veio quase vazia (pode ser protegida). Copie o texto e cole aqui.")
    return h
APRENDER = """You read a text (often a fan wiki page, in Portuguese or English) and extract knowledge cards for an AI character named Tamaki, so she can talk about it and draw it.
Return ONLY JSON: {"universo": "name of the franchise/universe or topic", "resumo": "3 to 5 sentences in Brazilian Portuguese about the universe/topic",
 "fichas": [{"nome": "character/place/thing name", "tipo": "personagem|lugar|criatura|coisa", "apelidos": ["other names"], "resumo": "2 to 3 sentences in Brazilian Portuguese: who/what it is",
 "tags": "Danbooru tags in English for HOW IT LOOKS (count tag like 1boy/1girl/no humans, hair, eyes, clothes, accessories, colors). Empty if the text does not say"}]}
Up to 10 cards, the most important ones. Never invent appearance that is not in the text."""
def aprender(url="", texto=""):
    fonte = texto.strip()
    if url: fonte = texto_do_link(url) + ("\n\n" + fonte if fonte else "")
    if not fonte: raise RuntimeError("mande um link ou cole um texto")
    if TX["m"] is None:
        carregar_texto()
        if TX["m"] is None: raise RuntimeError("a IA de texto não carregou: " + TX["erro"])
    tok, m = TX["tok"], TX["m"]
    msgs = [{"role": "system", "content": APRENDER}, {"role": "user", "content": fonte[:9000]}]
    with TRAVA_TX:
        txt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        ids = tok(txt, return_tensors="pt").input_ids.to(DEV_TX)
        out = m.generate(input_ids=ids, max_new_tokens=1400, do_sample=False, pad_token_id=tok.eos_token_id)
    t = tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
    a, b = t.find("{"), t.rfind("}")
    d = json.loads(t[a:b + 1])
    for f in d.get("fichas", []):
        # o Danbooru conhece este personagem? se conhece, o modelo também desenha
        nome, n = danbooru(f.get("nome", ""))
        if (not nome or n <= 0) and d.get("universo"):
            nome, n = danbooru(f"{f.get('nome', '')} ({d['universo']})")
        f["danbooru"] = {"tag": (nome or "").replace("_", " "), "imagens": n} if nome and n > 0 else {"tag": "", "imagens": max(n, 0)}
        if f["danbooru"]["imagens"] >= 30:
            f["tags"] = ", ".join(x for x in [f["danbooru"]["tag"], f.get("tags", "")] if x)
    return d

# ---------- fila de imagens ----------
TAREFAS, FILA = {}, queue.Queue()
def trabalhador():
    while True:
        tid, p = FILA.get(); t = TAREFAS[tid]
        with TRAVA:
            t["estado"] = "gerando"
            try:
                if pipe is None: raise RuntimeError("o modelo está desligado por causa do treino")
                lora = p.get("lora") or ""
                usar = ([(LORAS[lora], float(p.get("forca", .9)))] if lora in LORAS else []) + \
                       [(LORAS[x.get("lora")], float(x.get("forca", .8))) for x in (p.get("extras") or []) if x.get("lora") in LORAS and x.get("lora") != lora]
                if usar: pipe.enable_lora(); pipe.set_adapters([u[0] for u in usar], [u[1] for u in usar])
                elif LORAS: pipe.disable_lora()
                n = max(1, min(4, int(p.get("quantidade", 1)))); t["total"] = n
                passos = max(10, min(60, int(p.get("passos", 28))))
                w = max(512, min(1536, int(p.get("largura", 896)))) // 8 * 8
                h = max(512, min(1536, int(p.get("altura", 1152)))) // 8 * 8
                s0 = int(p.get("semente", -1))
                for i in range(n):
                    s = random.randint(0, 2**31 - 1) if s0 < 0 else s0 + i
                    def passo(pp, k, ts, kw, i=i):
                        t["progresso"] = (i + (k + 1) / passos) / n; return kw
                    extra = dict(width=w, height=h, guidance_scale=float(p.get("cfg", 5)), num_inference_steps=passos,
                        generator=torch.Generator("cuda").manual_seed(s), callback_on_step_end=passo)
                    try:
                        c, cp = compel(p["prompt"]); nc, ncp = compel(p.get("negativo", "") or "")
                        c, nc = compel.pad_conditioning_tensors_to_same_length([c, nc])
                        img = pipe(prompt_embeds=c, pooled_prompt_embeds=cp, negative_prompt_embeds=nc,
                                   negative_pooled_prompt_embeds=ncp, **extra).images[0]
                    except Exception as e:
                        print("compel falhou, usando o prompt cortado:", e)
                        img = pipe(p["prompt"], negative_prompt=p.get("negativo", ""), **extra).images[0]
                    if p.get("caprichar"):
                        t["msg"] = "caprichando nos detalhes…"
                        img = caprichar(img, p, s)
                    img = realce(img)
                    b = io.BytesIO(); img.save(b, "PNG")
                    t["imagens"].append({"png": base64.b64encode(b.getvalue()).decode(), "semente": s}); t["feitas"] = i + 1
                t["estado"], t["progresso"] = "pronto", 1
            except Exception as e:
                t["estado"], t["erro"] = "erro", str(e)
            torch.cuda.empty_cache()
threading.Thread(target=trabalhador, daemon=True).start()

# ---------- treino ----------
TREINO = {"estado": "parado", "passo": 0, "total": 0, "perda": None, "resta": None, "msg": "", "nome": "", "log": []}
def tempo_seg(t):
    p = [int(x) for x in t.split(":")]; s = 0
    for x in p: s = s * 60 + x
    return s
def fundo_liso(img):
    # olha a borda da imagem: se quase não muda de cor, é fundo liso
    g = img.convert("RGB").resize((64, 64)); px = g.load()
    borda = [px[x, y] for x in range(64) for y in (0, 1, 62, 63)] + [px[x, y] for y in range(64) for x in (0, 1, 62, 63)]
    faixa = Image.new("RGB", (len(borda), 1)); faixa.putdata(borda)
    return sum(ImageStat.Stat(faixa).stddev) / 3 < 12
# ---------- legendas automáticas (WD Tagger) ----------
# O segredo de um LoRA que obedece: a legenda descreve tudo o que MUDA (roupa, pose, fundo, enquadramento)
# e deixa de fora o que é SEMPRE dela (cabelo, olhos, pele, orelhas). Assim a palavra-gatilho guarda só o rosto
# e o jeito dela, e a roupa e o cenário continuam obedecendo ao pedido.
TAGGER = {"s": None, "tags": None}
IDENTIDADE = {"dark skin", "dark-skinned female", "brown skin", "tan", "blue hair", "purple hair", "dark blue hair", "black hair", "aqua hair",
    "curly hair", "wavy hair", "long hair", "very long hair", "medium hair", "big hair", "orange hair", "multicolored hair", "streaked hair",
    "two-tone hair", "colored inner hair", "hair over one eye", "aqua eyes", "green eyes", "blue eyes", "teal eyes", "pointy ears", "elf",
    "mole", "mole under eye", "mole under mouth", "fang", "fangs", "skin fang", "eyeliner", "makeup", "lips"}
def legendar(img):
    if TAGGER["s"] is None:
        instalar("onnxruntime")
        import onnxruntime as ort, csv
        rep = "SmilingWolf/wd-vit-tagger-v3"
        m = hf_hub_download(rep, "model.onnx"); c = hf_hub_download(rep, "selected_tags.csv")
        TAGGER["s"] = ort.InferenceSession(m, providers=["CPUExecutionProvider"])
        TAGGER["tags"] = [(r["name"].replace("_", " "), int(r["category"])) for r in csv.DictReader(open(c))]
    import numpy as np
    sz = TAGGER["s"].get_inputs()[0].shape[1]
    im = img.convert("RGBA"); fundo = Image.new("RGBA", im.size, (255, 255, 255, 255)); fundo.alpha_composite(im); im = fundo.convert("RGB")
    lado = max(im.size); q = Image.new("RGB", (lado, lado), (255, 255, 255)); q.paste(im, ((lado - im.width) // 2, (lado - im.height) // 2))
    x = np.asarray(q.resize((sz, sz), Image.BICUBIC), dtype=np.float32)[:, :, ::-1][None]
    pr = TAGGER["s"].run(None, {TAGGER["s"].get_inputs()[0].name: x})[0][0]
    out = [(t, float(v)) for (t, cat), v in zip(TAGGER["tags"], pr) if cat == 0 and v >= 0.35]
    out.sort(key=lambda z: -z[1])
    return [t for t, _ in out]

def preparar_treino(pasta, gatilho="tmkshion"):
    # realça a cor e escreve a legenda de cada imagem com o WD Tagger (sem os traços fixos dela)
    feitas = 0
    for arq in sorted(glob.glob(pasta + "/*")):
        if arq.endswith(".txt"): continue
        try:
            img = Image.open(arq).convert("RGB")
            if COR_TREINO != 1: img = ImageEnhance.Color(img).enhance(COR_TREINO)
            base = os.path.splitext(arq)[0]; img.save(base + ".png")
            if not arq.endswith(".png"): os.remove(arq)
            txt = base + ".txt"
            antiga = open(txt).read().strip() if os.path.exists(txt) else ""
            conta = next((t for t in ["1girl", "1boy", "no humans"] if t in antiga), "1boy" if gatilho != "tmkshion" and "1girl" not in antiga else "1girl")
            try:
                tags = [t for t in legendar(img) if t not in IDENTIDADE and t not in ("1girl", "1boy", "solo", "no humans")] if gatilho == "tmkshion" else \
                       [t for t in legendar(img) if t not in ("1girl", "1boy", "solo", "no humans")]
            except Exception as e:
                print("Sem legenda automática:", e); tags = [t.strip() for t in antiga.split(",") if t.strip() and t.strip() not in (gatilho, conta, "solo")]
            leg = ", ".join([conta, gatilho, "solo"] + tags[:40])
            open(txt, "w").write(leg); feitas += 1
            if feitas <= 3: print("Legenda:", os.path.basename(base), "→", leg)
        except Exception as e:
            print("Não preparei", os.path.basename(arq), e)
    return feitas

def treinar(epocas, usar_originais, gatilho="tmkshion"):
    gatilho = re.sub(r"[^a-z0-9]", "", gatilho.lower()) or "tmkshion"
    T = TREINO
    T.update(estado="preparando", passo=0, total=0, perda=None, resta=None, nome="", log=[], msg="Instalando as ferramentas de treino (só demora na primeira vez)…")
    try:
        instalar("bitsandbytes toml einops voluptuous imagesize opencv-python-headless sentencepiece ftfy rich "
                 "lion-pytorch schedulefree pytorch-optimizer prodigyopt prodigy-plus-schedule-free tensorboard")
        SD = W + "/sd-scripts"
        if not os.path.exists(SD): rodar(f"git clone -q https://github.com/kohya-ss/sd-scripts {SD}")
        T["msg"] = "Baixando o modelo base do treino…"
        base_repo = "cagliostrolab/animagine-xl-4.0-zero"
        arq = [f for f in list_repo_files(base_repo) if f.endswith(".safetensors") and "/" not in f][0]
        BASE = hf_hub_download(base_repo, arq, local_dir=W + "/base")
        VAE = hf_hub_download("madebyollin/sdxl-vae-fp16-fix", "sdxl_vae.safetensors", local_dir=W + "/base")
        DADOS = W + "/treino_dados"; PASTA = DADOS + f"/1_{gatilho}"
        shutil.rmtree(DADOS, ignore_errors=True); os.makedirs(PASTA)
        if usar_originais and ORIGINAIS and gatilho == "tmkshion":
            for f in glob.glob(ORIGINAIS + "/*"): shutil.copy(f, PASTA)
        for f in glob.glob(EXTRA + "/*"): shutil.copy(f, PASTA)
        T["msg"] = "Escrevendo a legenda de cada imagem (o que muda: roupa, pose, fundo)…"
        preparar_treino(PASTA, gatilho)
        n = len([f for f in os.listdir(PASTA) if not f.endswith(".txt")])
        # repetições pelo tamanho do conjunto: ~150 passos por volta (antes eram 10 repetições fixas, e passava do ponto)
        rep_n = max(2, min(10, round(150 / max(n, 1))))
        NOVA = DADOS + f"/{rep_n}_{gatilho}"; os.rename(PASTA, NOVA); PASTA = NOVA
        if n < 5: raise RuntimeError(f"só {n} imagens; precisa de pelo menos 5")
        nome = gatilho + "_" + time.strftime("%m%d_%H%M")
        T.update(estado="treinando", msg=f"Treinando a versão {nome} com {n} imagens…")
        with TRAVA:
            descarregar()
            if DEV_TX == "cuda:0": soltar_texto()
            def le(linha):
                T["log"] = (T["log"] + [linha.rstrip()])[-25:]
                m = re.search(r"(\d+)/(\d+) \[[\d:]+<([\d:]+)", linha)
                if m: T["passo"], T["total"], T["resta"] = int(m.group(1)), int(m.group(2)), tempo_seg(m.group(3))
                m = re.search(r"avr_loss=([\d.]+)", linha)
                if m: T["perda"] = float(m.group(1))
            try:
                rodar(["accelerate", "launch", "--num_processes", "1", "--num_machines", "1", "--dynamo_backend", "no",
                    "--mixed_precision", "fp16", "sdxl_train_network.py",
                    f"--pretrained_model_name_or_path={BASE}", f"--vae={VAE}", "--no_half_vae",
                    f"--train_data_dir={DADOS}", "--caption_extension=.txt", "--resolution=1024,1024",
                    "--enable_bucket", "--min_bucket_reso=512", "--max_bucket_reso=1536",
                    f"--output_dir={LORA_DIR}", f"--output_name={nome}", "--save_model_as=safetensors",
                    "--network_module=networks.lora", "--network_dim=16", "--network_alpha=8", "--network_train_unet_only",
                    "--learning_rate=8e-5", "--optimizer_type=AdamW8bit", "--lr_scheduler=cosine", "--lr_warmup_steps=50",
                    "--train_batch_size=1", f"--max_train_epochs={epocas}", "--save_every_n_epochs=1",
                    "--mixed_precision=fp16", "--save_precision=fp16", "--gradient_checkpointing", "--sdpa",
                    "--cache_latents", "--cache_text_encoder_outputs", "--seed=42",
                    # mais contraste e cor no que o LoRA aprende, e treino mais estável
                    "--noise_offset=0.0357", "--min_snr_gamma=5"], cwd=SD, cada_linha=le)
            finally:
                T["msg"] = "Religando o gerador…"
                carregar()
        T.update(estado="salvando", resta=None, msg="Guardando a versão nova no seu Hugging Face…")
        api.upload_folder(folder_path=LORA_DIR, repo_id=REPO, allow_patterns=f"{nome}*.safetensors")
        T.update(estado="pronto", nome=nome, msg=f"A versão {nome} está pronta e guardada no Hugging Face.")
    except Exception as e:
        T.update(estado="erro", msg=str(e))
        if pipe is None:
            try: carregar()
            except Exception: pass

# ---------- porta para a Central ----------
class Porta(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def cab(self, c=200, tipo="application/json"):
        self.send_response(c)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type, x-codigo")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Type", tipo); self.end_headers()
    def js(self, o, c=200): self.cab(c); self.wfile.write(json.dumps(o).encode())
    def do_OPTIONS(self): self.cab(204)
    def treinando(self): return TREINO["estado"] in ("preparando", "treinando", "salvando")
    def do_GET(self):
        if self.path == "/": self.cab(200, "text/plain"); self.wfile.write(b"ok"); return
        if self.headers.get("x-codigo") != CODIGO: return self.js({"erro": "código de ligação errado"}, 403)
        if self.path == "/estado":
            return self.js({"versao": VERSAO, "texto": TX["estado"], "texto_erro": TX["erro"], "gpu": torch.cuda.get_device_name(0).replace("Tesla ", "") + (f" x{torch.cuda.device_count()}" if torch.cuda.device_count() > 1 else ""), "loras": list(LORAS), "erros_lora": ERROS_LORA, "fila": FILA.qsize(),
                "originais": len(glob.glob(ORIGINAIS + "/*.png")) if ORIGINAIS else 0,
                "treino": {k: v for k, v in TREINO.items() if k != "log"}})
        if self.path == "/treino": return self.js(TREINO)
        m = re.match(r"^/tarefa/(\w+)$", self.path)
        if m and m.group(1) in TAREFAS: return self.js(TAREFAS[m.group(1)])
        self.js({"erro": "não achei"}, 404)
    def do_POST(self):
        if self.headers.get("x-codigo") != CODIGO: return self.js({"erro": "código de ligação errado"}, 403)
        p = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/gerar":
            if self.treinando(): return self.js({"erro": "estou treinando agora; tente quando o treino terminar"}, 409)
            if not p.get("prompt"): return self.js({"erro": "faltou o prompt"}, 400)
            tid = uuid.uuid4().hex[:10]
            TAREFAS[tid] = {"estado": "fila", "progresso": 0, "feitas": 0, "total": int(p.get("quantidade", 1)), "imagens": []}
            while len(TAREFAS) > 30: TAREFAS.pop(next(iter(TAREFAS)))
            FILA.put((tid, p)); return self.js({"id": tid})
        if self.path == "/pedido":
            if not str(p.get("texto", "")).strip(): return self.js({"erro": "escreva o que quer na imagem"}, 400)
            try: return self.js(entender(p["texto"], p.get("anterior", ""), p.get("lugares"), p.get("gosto", ""), p.get("exemplos"), p.get("conhecidos"), p.get("conferir", True)))
            except Exception as e: return self.js({"erro": str(e)[:300]}, 500)
        if self.path == "/aprender":
            try: return self.js(aprender(str(p.get("url", "")).strip(), str(p.get("texto", ""))))
            except Exception as e: return self.js({"erro": str(e)[:300]}, 500)
        if self.path == "/danbooru":
            nome, n = danbooru(str(p.get("tag", "")))
            return self.js({"tag": (nome or "").replace("_", " "), "imagens": n})
        if self.path == "/treino/imagens":
            if self.treinando(): return self.js({"erro": "já tem um treino rodando"}, 409)
            if p.get("limpar"): shutil.rmtree(EXTRA, ignore_errors=True)
            os.makedirs(EXTRA, exist_ok=True)
            for im in p.get("imagens", []):
                nome = re.sub(r"[^\w-]", "_", im.get("nome", uuid.uuid4().hex[:8]))
                open(f"{EXTRA}/{nome}.jpg", "wb").write(base64.b64decode(im["jpg"]))
                open(f"{EXTRA}/{nome}.txt", "w").write(im.get("legenda") or "1girl, tmkshion, solo")
            return self.js({"ok": True, "extras": len(glob.glob(EXTRA + "/*.jpg"))})
        if self.path == "/treinar":
            if self.treinando(): return self.js({"erro": "já tem um treino rodando"}, 409)
            ep = max(2, min(12, int(p.get("epocas", 6))))
            threading.Thread(target=treinar, args=(ep, bool(p.get("originais", True)), str(p.get("gatilho") or "tmkshion")), daemon=True).start()
            return self.js({"ok": True})
        self.js({"erro": "não achei"}, 404)

carregar()
servidor = ThreadingHTTPServer(("0.0.0.0", 0), Porta)   # 0 = qualquer porta livre
PORTA = servidor.server_address[1]
threading.Thread(target=servidor.serve_forever, daemon=True).start()

# ---------- túnel e aviso para a Central ----------
CF = W + "/cloudflared"
if not os.path.exists(CF):
    rodar(f"wget -q -O {CF} https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x {CF}")
tunel = subprocess.Popen([CF, "tunnel", "--url", f"http://localhost:{PORTA}", "--no-autoupdate"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
URL, t0 = None, time.time()
while not URL and time.time() - t0 < 90:
    m = re.search(r"https://[-a-z0-9]+\.trycloudflare\.com", tunel.stdout.readline())
    if m: URL = m.group(0)
if not URL: raise RuntimeError("o túnel não abriu; rode a célula de novo")
threading.Thread(target=lambda: [None for _ in tunel.stdout], daemon=True).start()
for _ in range(30):
    try:
        if requests.get(URL + "/", timeout=5).ok: break
    except Exception: pass
    time.sleep(3)
avisa = lambda estado: requests.post("https://ntfy.sh/" + CODIGO, data=json.dumps({"estado": estado, "url": URL}).encode(), timeout=10)
avisa("ligado")
print(f"\n✅ Ligado! (versão {VERSAO}) Abra a Central › Tamaki › 🎨 Estúdio de imagem.")
print(f"Fica ligado por {HORAS} h. Para desligar antes, pare a célula (■).")
resumo_lora()
threading.Thread(target=carregar_texto, daemon=True).start()
try:
    fim = time.time() + HORAS * 3600
    while time.time() < fim or TREINO["estado"] in ("preparando", "treinando", "salvando"):
        time.sleep(20)
except KeyboardInterrupt: pass
finally:
    try: avisa("encerrado")
    except Exception: pass
    tunel.terminate(); servidor.shutdown(); print("Desligado.")
