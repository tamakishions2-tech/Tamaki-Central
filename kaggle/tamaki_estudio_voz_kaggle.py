# ============================================================
#  TAMAKI · ESTÚDIO DE VOZ BR (célula única do Kaggle)
#  Voz: Chatterbox pt-BR (licença MIT, pode monetizar)
#  Criar voz do nada: Qwen3-TTS VoiceDesign (só para criar o timbre)
#
#  1. Settings: Accelerator = GPU T4 x2 e Internet = On.
#  2. Cole TUDO isto numa célula só (apague as células antigas).
#  3. Save Version → "Save & Run All (Commit)" → Save.
#     Roda em segundo plano por até 12 h. Pode fechar o Kaggle.
#  Opcional: Add-ons → Secrets → HF_TOKEN (guarda vozes, frases e treinos no Hugging Face).
#  Versão 2: várias vozes salvas com nome e foto, cartão de voz e treino que atualiza a mesma voz.
#  Versão 5: confere cada fala (ouve de volta e refaz se embolar) e só usa trechos do CORAA
#            em que o texto bate com o áudio.
#  Versão 4: treino com conversas reais (CORAA): a Tamaki aprende o ritmo de gente conversando,
#            sem perder o timbre dela (o timbre vem da voz de referência, não do treino).
#  Versão 3: emoções. Cada voz guarda um exemplo de cada emoção (feliz, brava, triste…),
#            e as falas usam a emoção escrita entre parênteses: (brava) Que absurdo!
#  Na primeira vez a instalação leva uns 8–12 min. O HTML mostra o andamento.
#
#  PACOTE DE INSTALAÇÃO GUARDADO (para não instalar tudo de novo):
#  - Na 1ª sessão completa, ele cria tamaki_cache.tar na saída (Output) do notebook.
#  - Depois que essa sessão terminar: Add Input → Your Work → Notebooks → este notebook.
#  - Nas próximas, ele acha o pacote sozinho e só desempacota (2–3 min).
# ============================================================
CODIGO = "tamaki-f7d1a24c4ee30ad1f758"   # tem que ser o mesmo do HTML
NOME   = "tamaki"                        # prefixo dos arquivos (tamaki_0000.wav…)
HORAS  = 2.5                            # o Kaggle corta em 12 h: antes disso salva tudo

import os, sys, re, io, json, time, glob, random, shutil, zipfile, threading, traceback, subprocess, collections, urllib.request, unicodedata

INICIO = time.time()
FIM = INICIO + HORAS * 3600
ERROS = collections.deque(maxlen=40)
LOG = collections.deque(maxlen=60)
_nerro = [0]

def log(m):
    linha = time.strftime("%H:%M:%S") + "  " + m
    LOG.append(linha)
    print(linha, flush=True)

def erro(onde, e, detalhe=None):
    _nerro[0] += 1
    item = {"id": _nerro[0], "hora": time.strftime("%H:%M:%S"), "onde": onde,
            "msg": f"{type(e).__name__}: {e}" if isinstance(e, BaseException) else str(e),
            "detalhe": (detalhe or traceback.format_exc())[-3000:]}
    ERROS.append(item)
    print("\n=========== ERRO (copie e mande no chat) ===========\n"
          f"[{item['hora']}] {onde}\n{item['msg']}\n{item['detalhe']}\n"
          "====================================================\n", flush=True)

# ---------- 1. pacotes do servidor (o Chatterbox fica num ambiente separado, mais abaixo) ----------
log("Instalando o servidor (1–3 min)…")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "qwen-tts==0.1.1", "soundfile", "librosa",
                "fastapi", "uvicorn", "python-multipart", "uv"])
import numpy as np, soundfile as sf, librosa, torch, warnings, logging
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)
from fastapi import FastAPI, Request, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse
import uvicorn

# ---------- 2. pastas e configuração ----------
BASE = "/kaggle/working/voz_br"
DS, MODELO, DESIGN, TMP = f"{BASE}/dataset", f"{BASE}/modelo", f"{BASE}/design", f"{BASE}/tmp"
WAVS, REFS = f"{DS}/wavs", f"{DS}/refs"          # refs: a voz de referência de cada voz salva (e das emoções dela)
REF, REFTXT, CFG = f"{DS}/referencia.wav", f"{DS}/referencia.txt", f"{DS}/config.json"   # (formato antigo)
VOZES_ARQ, DSINFO = f"{DS}/vozes.json", f"{DS}/dataset.json"
for p in (WAVS, REFS, MODELO, DESIGN, TMP):
    os.makedirs(p, exist_ok=True)

PADRAO = {"quantidade": 300, "exaggeration": 0.5, "cfg_weight": 0.5, "temperature": 0.8, "epocas": 5, "ativa": "padrao"}
def ler_cfg():
    try:
        return {**PADRAO, **json.load(open(CFG))}
    except Exception:
        return dict(PADRAO)
CONF = ler_cfg()
def gravar_cfg():
    json.dump(CONF, open(CFG, "w"))

# ---------- 3. nuvem (Hugging Face), opcional ----------
HF_TOKEN, hf, HF_USUARIO = None, None, None
try:
    from kaggle_secrets import UserSecretsClient
    HF_TOKEN = UserSecretsClient().get_secret("HF_TOKEN")
except Exception:
    HF_TOKEN = os.environ.get("HF_TOKEN")
NUVEM = {"estado": "desligada (sem HF_TOKEN)"}
LOCK_NUVEM = threading.Lock()
if HF_TOKEN:
    try:
        from huggingface_hub import HfApi, snapshot_download
        hf = HfApi(token=HF_TOKEN)
        HF_USUARIO = hf.whoami()["name"]
        NUVEM["estado"] = "ligada"
        log(f"Nuvem ligada (Hugging Face: {HF_USUARIO})")
    except Exception as e:
        hf = None; NUVEM["estado"] = "erro no HF_TOKEN"; erro("ligar a nuvem (HF_TOKEN)", e)
REPO_DS = f"{HF_USUARIO}/{NOME}-voz-br-dataset" if HF_USUARIO else None
REPO_MOD = f"{HF_USUARIO}/{NOME}-voz-br-modelo" if HF_USUARIO else None

def backup(modelo=False):
    if not hf:
        return
    with LOCK_NUVEM:
        try:
            escrever_metadata()
            hf.create_repo(REPO_DS, repo_type="dataset", private=True, exist_ok=True)
            hf.upload_folder(folder_path=DS, repo_id=REPO_DS, repo_type="dataset", commit_message="backup automático",
                             ignore_patterns=[".cache/*", "*.lock"])
            if modelo and os.listdir(MODELO):
                hf.create_repo(REPO_MOD, private=True, exist_ok=True)
                hf.upload_folder(folder_path=MODELO, repo_id=REPO_MOD, commit_message="voz treinada")
            NUVEM["estado"] = "salvo às " + time.strftime("%H:%M")
        except Exception as e:
            NUVEM["estado"] = "falhou às " + time.strftime("%H:%M"); erro("backup na nuvem", e)

def restaurar_nuvem():
    if not hf:
        return
    try:
        if not os.listdir(WAVS) and hf.repo_exists(REPO_DS, repo_type="dataset"):
            snapshot_download(REPO_DS, repo_type="dataset", local_dir=DS, token=HF_TOKEN)
            CONF.update(ler_cfg())
            log(f"Recuperado da nuvem: {len(os.listdir(WAVS))} frases e a voz de referência")
        if not os.listdir(MODELO) and hf.repo_exists(REPO_MOD):
            snapshot_download(REPO_MOD, local_dir=MODELO, token=HF_TOKEN)
            log("Voz treinada recuperada da nuvem")
    except Exception as e:
        erro("recuperar da nuvem", e)

# ---------- vozes salvas (cada uma: nome, foto, voz de referência e, se treinada, o "cérebro" treinado) ----------
LOCK_VOZES = threading.Lock()
VREV = [int(time.time())]   # muda sempre que a lista muda (o HTML só baixa as fotos de novo quando muda)

def ler_vozes():
    try:
        v = json.load(open(VOZES_ARQ, encoding="utf-8"))
        return v if isinstance(v, dict) and all(isinstance(x, dict) for x in v.values()) else {}
    except Exception:
        return {}

def gravar_vozes(v):
    json.dump(v, open(VOZES_ARQ, "w", encoding="utf-8"), ensure_ascii=False)
    VREV[0] += 1

def novo_id():
    return "v" + time.strftime("%Y%m%d%H%M%S")

def arq_ref(vid): return f"{REFS}/{vid}.wav"
def arq_conds(vid): return f"{REFS}/{vid}.pt"
def arq_t3(vid): return f"{MODELO}/t3_{vid}.pt"
def arq_emo(vid, eid, alt=None): return f"{REFS}/{vid}__{eid}" + ("" if alt is None else f"_alt{alt}") + ".wav"
def arq_emo_conds(vid, eid): return f"{REFS}/{vid}__{eid}.pt"

def migrar():
    """Converte o formato antigo (uma referência + treinos soltos) para vozes salvas com nome."""
    try:
        bruto = {}
        try:
            bruto = json.load(open(VOZES_ARQ, encoding="utf-8"))
        except Exception:
            pass
        nomes_antigos = {k: v for k, v in bruto.items() if isinstance(v, str)} if isinstance(bruto, dict) else {}
        vozes = {k: v for k, v in bruto.items() if isinstance(v, dict)} if isinstance(bruto, dict) else {}
        agora = int(time.time())
        for t3 in sorted(glob.glob(f"{MODELO}/t3_*.pt"), key=os.path.getmtime):
            vid = os.path.basename(t3)[3:-3]
            if vid in vozes:
                continue
            if os.path.exists(f"{MODELO}/voz_{vid}.pt"):
                shutil.move(f"{MODELO}/voz_{vid}.pt", arq_conds(vid))
            if os.path.exists(REF) and not os.path.exists(arq_ref(vid)):
                shutil.copy(REF, arq_ref(vid))
            vozes[vid] = {"nome": nomes_antigos.get(vid, "Tamaki treinada"), "foto": "", "criado": agora, "atualizado": agora,
                          "versao": 1, "treinos": 1, "treinada": True,
                          "texto_ref": open(REFTXT, encoding="utf-8").read().strip() if os.path.exists(REFTXT) else ""}
        if os.path.exists(REF) and not vozes:
            vid = novo_id(); shutil.copy(REF, arq_ref(vid))
            vozes[vid] = {"nome": "Minha voz", "foto": "", "criado": agora, "atualizado": agora, "versao": 1, "treinos": 0,
                          "treinada": False, "texto_ref": open(REFTXT, encoding="utf-8").read().strip() if os.path.exists(REFTXT) else ""}
        for vid, v in vozes.items():   # treino que voltou da nuvem
            v["treinada"] = os.path.exists(arq_t3(vid))
        gravar_vozes(vozes)
        if (CONF.get("ativa") not in vozes and CONF.get("ativa") != "padrao") or (not CONF.get("v2") and vozes):
            CONF["ativa"] = max(vozes, key=lambda k: vozes[k]["atualizado"]) if vozes else "padrao"
        CONF["v2"] = True; gravar_cfg()
        if os.path.exists(DSINFO) is False and contar() and vozes:
            json.dump({"voz": CONF["ativa"]}, open(DSINFO, "w"))
        if vozes:
            log(f"Vozes salvas: {', '.join(v['nome'] for v in vozes.values())}")
    except Exception as e:
        erro("organizar as vozes salvas", e)

def lista_vozes(fotos=False):
    vozes = ler_vozes()
    saida = [{"id": "padrao", "nome": "Voz padrão do modelo", "tipo": "padrao", "foto": "", "versao": 0, "treinos": 0, "atualizado": 0, "emocoes": []}]
    for vid, v in sorted(vozes.items(), key=lambda kv: kv[1].get("criado", 0)):
        saida.append({"id": vid, "nome": v["nome"], "tipo": "treinada" if v.get("treinada") else "referencia",
                      "versao": v.get("versao", 1), "treinos": v.get("treinos", 0), "atualizado": v.get("atualizado", 0),
                      "emocoes": sorted(v.get("emocoes", {})), **({"foto": v.get("foto", "")} if fotos else {})})
    return saida

# ---------- 4. o "motor" Chatterbox, num ambiente separado (evita briga de versões com o Qwen) ----------
WORKER = r'''
import os, sys, json, time, threading, traceback, copy, random
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import numpy as np, soundfile as sf, torch
import torch.nn.functional as F

ST = {"estado": "carregando", "pack": "", "aviso": "", "treino": {"rodando": False, "msg": "ainda não treinou", "epoca": 0,
      "epocas": 0, "passo": 0, "passos": 0, "perda": None, "historico": [], "saida": ""}}
M, LOCK, PARAR = {}, threading.Lock(), {"v": False}

def limpo(sd):
    """Tira as cópias internas "patched_model.*" (o Chatterbox cria na 1ª fala; são os mesmos pesos de tfmr.*)."""
    return {k: v for k, v in sd.items() if not k.startswith("patched_model.")}

def por_t3(mod, sd):
    falt, sobra = mod.load_state_dict(limpo(sd), strict=False)
    falt = [k for k in falt if not k.startswith("patched_model.")]
    if falt or sobra:
        raise RuntimeError(f"a voz não encaixou no modelo ({len(falt)} faltando, {len(sobra)} sobrando)")

def carregar():
    try:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        try:
            m = ChatterboxMultilingualTTS.from_pretrained(device="cuda", t3_model="v3")
        except TypeError:
            m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
            ST["aviso"] = "versão antiga do Chatterbox (sem V3). "
        ST["pack"] = "multilíngue"
        try:   # o pacote só do Brasil (troca o "cérebro" T3 pelo treinado em português brasileiro)
            from huggingface_hub import hf_hub_download
            from safetensors.torch import load_file
            sd = load_file(hf_hub_download("ResembleAI/Chatterbox-Multilingual-pt-br", "t3_pt_br.safetensors"))
            atual = m.t3.state_dict()
            ruins = [k for k, v in sd.items() if k in atual and atual[k].shape != v.shape]
            if ruins:
                raise RuntimeError(f"{len(ruins)} pesos com formato diferente (ex.: {ruins[0]})")
            falt, sobra = m.t3.load_state_dict(sd, strict=False)
            ST["pack"] = "pt-BR"
            if falt or sobra:
                ST["aviso"] += f"pt-BR carregado ({len(falt)} faltando, {len(sobra)} sobrando). "
        except Exception as e:
            ST["aviso"] += "Não carreguei o pacote pt-BR, usando o multilíngue: " + f"{type(e).__name__}: {e}"[:300]
        M["m"] = m
        M["base"] = {k: v.detach().cpu().clone() for k, v in limpo(m.t3.state_dict()).items()}
        M["padrao"] = copy.deepcopy(m.conds)   # a voz que já vem no modelo
        ST["estado"] = "pronto"
    except Exception as e:
        ST["estado"] = "erro"; ST["aviso"] = f"{type(e).__name__}: {e}\n" + traceback.format_exc()[-2500:]

def ler_conds(arq, dev=None):
    m = M["m"]
    return type(M["padrao"]).load(arq).to(dev or m.device)

def conds(d):
    """Prepara a "impressão" de uma voz a partir do áudio de referência e salva no arquivo pedido."""
    m = M["m"]
    with LOCK:
        guardada = m.conds
        try:
            m.prepare_conditionals(d["ref"], exaggeration=float(d.get("exaggeration", 0.5)))
            m.conds.save(d["saida"])
        finally:
            if d.get("manter"):   # emoção: prepara o arquivo sem trocar a voz que está em uso
                m.conds = guardada
    return {"ok": True}

def usar(d):
    """Põe uma voz em uso: o cérebro (t3, ou o pt-BR original) e a impressão da voz (conds, ou a padrão)."""
    m = M["m"]
    with LOCK:
        por_t3(m.t3, torch.load(d["t3"], map_location="cpu") if d.get("t3") else M["base"])
        m.conds = ler_conds(d["conds"]) if d.get("conds") else copy.deepcopy(M["padrao"])
        m.t3.eval()
    return {"ok": True}

def falar(d):
    m = M["m"]
    with LOCK, torch.no_grad():
        guardada = m.conds
        if d.get("conds"):   # emoção: usa a impressão da voz naquela emoção só nesta fala
            m.conds = ler_conds(d["conds"])
        elif d.get("padrao"):
            m.conds = copy.deepcopy(M["padrao"])
        try:
            wav = m.generate(d["texto"], language_id="pt", exaggeration=float(d.get("exaggeration", 0.5)),
                             cfg_weight=float(d.get("cfg_weight", 0.5)), temperature=float(d.get("temperature", 0.8)))
        finally:
            m.conds = guardada
    sf.write(d["saida"], wav.squeeze().detach().cpu().numpy(), m.sr)
    return {"ok": True, "sr": m.sr}

def treinar(d):
    T = ST["treino"]
    epocas, lr = int(d.get("epocas", 5)), float(d.get("lr", 1e-5))
    T.update(rodando=True, msg="preparando as frases…", epoca=0, epocas=epocas, passo=0, passos=0, perda=None, historico=[], saida="", erro="")
    PARAR["v"] = False
    dev = "cuda:1" if torch.cuda.device_count() > 1 else "cuda:0"
    t3 = opt = None
    try:
        import librosa
        m = M["m"]
        try:
            from chatterbox.mtl_tts import punc_norm
        except Exception:
            punc_norm = lambda t: t
        pasta = d["pasta"]
        linhas = [l.rstrip("\n").split("|", 1) for l in open(f"{pasta}/metadata.csv", encoding="utf-8") if "|" in l]
        dados = []
        for k, (arq, texto) in enumerate(linhas):
            if PARAR["v"]:
                raise RuntimeError("parado por você")
            T["msg"] = f"preparando a frase {k + 1} de {len(linhas)}"
            caminho = f"{pasta}/wavs/{arq}" + ("" if arq.endswith(".wav") else ".wav")
            if not os.path.exists(caminho):
                continue
            w, sr = sf.read(caminho)
            w = (w if w.ndim == 1 else w.mean(1)).astype(np.float32)
            w16 = librosa.resample(w, orig_sr=sr, target_sr=16000)
            if not 0.8 <= len(w16) / 16000 <= 20:
                continue
            with LOCK, torch.no_grad():
                st, _ = m.s3gen.tokenizer.forward([w16])
                tt = m.tokenizer.text_to_tokens(punc_norm(texto), language_id="pt")
            st, tt = st.cpu().long(), tt.cpu().long()
            dados.append((tt if tt.dim() == 2 else tt.unsqueeze(0), st if st.dim() == 2 else st.unsqueeze(0)))
        if len(dados) < 20:
            raise RuntimeError(f"só {len(dados)} frases válidas: precisa de pelo menos 20")
        T["msg"] = "preparando o modelo…"
        with LOCK:
            t3 = copy.deepcopy(m.t3)
        t3 = t3.to(dev)
        por_t3(t3, torch.load(d["t3_inicio"], map_location="cpu") if d.get("t3_inicio") else M["base"])
        cond = ler_conds(d["conds"], dev).t3
        t3.train()
        hp = t3.hp
        opt = torch.optim.AdamW([p for p in t3.parameters() if p.requires_grad], lr=lr, weight_decay=0.01)
        ACUM, passo, media = 4, 0, None
        T["passos"] = epocas * len(dados)
        for ep in range(epocas):
            T["epoca"] = ep + 1
            random.shuffle(dados)
            for tt, st in dados:
                if PARAR["v"]:
                    raise RuntimeError("parado por você")
                tt2 = F.pad(F.pad(tt.to(dev), (1, 0), value=hp.start_text_token), (0, 1), value=hp.stop_text_token)
                st2 = F.pad(F.pad(st.to(dev), (1, 0), value=hp.start_speech_token), (0, 1), value=hp.stop_speech_token)
                if hasattr(cond, "cond_prompt_speech_emb"):
                    cond.cond_prompt_speech_emb = None   # recalcula a cada passo (senão o treino quebra)
                args = dict(t3_cond=cond, text_tokens=tt2, text_token_lens=torch.tensor([tt2.size(1)], device=dev),
                            speech_tokens=st2, speech_token_lens=torch.tensor([st2.size(1)], device=dev))
                try:
                    out = t3.forward(**args, training=True)
                except TypeError:
                    out = t3.forward(**args)
                # cada posição prevê a próxima: compara a saída com os códigos deslocados uma casa
                ls = F.cross_entropy(out.speech_logits[:, :-1].transpose(1, 2).float(), st2[:, 1:])
                lt = F.cross_entropy(out.text_logits[:, :-1].transpose(1, 2).float(), tt2[:, 1:])
                ((ls + 0.1 * lt) / ACUM).backward()
                passo += 1
                if passo % ACUM == 0:
                    torch.nn.utils.clip_grad_norm_(t3.parameters(), 1.0)
                    opt.step(); opt.zero_grad(set_to_none=True)
                v = float(ls.detach())
                media = v if media is None else 0.98 * media + 0.02 * v
                T.update(passo=passo, perda=round(media, 3), msg=f"treinando: volta {ep + 1} de {epocas}")
            T["historico"].append(round(media, 3))
        T["msg"] = "salvando a voz treinada…"
        torch.save({k: v.detach().cpu() for k, v in limpo(t3.state_dict()).items()}, d["saida"])
        T.update(msg="pronto", saida=d["saida"])
    except Exception as e:
        T["msg"] = "parado por você" if "parado" in str(e) else f"erro: {type(e).__name__}: {e}"
        T["erro"] = "" if "parado" in str(e) else traceback.format_exc()[-2500:]
    finally:
        del t3, opt
        torch.cuda.empty_cache()
        T["rodando"] = False

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def responder(self, obj, cod=200):
        b = json.dumps(obj).encode()
        self.send_response(cod); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            r = self.path
            if r == "/estado":
                return self.responder(ST)
            if ST["estado"] != "pronto":
                raise RuntimeError("o motor de voz ainda está carregando")
            if r == "/conds": return self.responder(conds(d))
            if r == "/usar": return self.responder(usar(d))
            if r == "/falar": return self.responder(falar(d))
            if r == "/treinar":
                if ST["treino"]["rodando"]:
                    raise RuntimeError("já está treinando")
                threading.Thread(target=treinar, args=(d,), daemon=True).start()
                return self.responder({"ok": True})
            if r == "/parar_treino":
                PARAR["v"] = True; return self.responder({"ok": True})
            self.responder({"erro": "rota desconhecida"}, 404)
        except Exception as e:
            self.responder({"erro": f"{type(e).__name__}: {e}", "detalhe": traceback.format_exc()[-2500:]}, 500)

threading.Thread(target=carregar, daemon=True).start()
ThreadingHTTPServer(("127.0.0.1", 8100), H).serve_forever()
'''

VENV = "/tmp/chatterbox_env"
W = {"estado": "esperando", "msg": "", "info": {}}

def motor(rota, dados=None, timeout=300):
    req = urllib.request.Request("http://127.0.0.1:8100" + rota, data=json.dumps(dados or {}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        corpo = json.loads(e.read() or b"{}")
        raise RuntimeError(corpo.get("erro", str(e)) + ("\n" + corpo["detalhe"] if corpo.get("detalhe") else ""))

CACHE_SAIDA = "/kaggle/working/tamaki_cache.tar"
CACHE = {"usado": False, "estado": "sem pacote guardado"}

def pasta_python_uv():
    try:
        r = subprocess.run([sys.executable, "-m", "uv", "python", "dir"], capture_output=True, text=True)
        return r.stdout.strip()
    except Exception:
        return ""

def restaurar_cache():
    """Se o pacote guardado de uma sessão anterior foi adicionado como entrada, só desempacota."""
    achados = glob.glob("/kaggle/input/**/tamaki_cache.tar", recursive=True)
    if not achados or os.path.exists(f"{VENV}/.pronto"):
        return False
    W.update(estado="instalando", msg="desempacotando a instalação guardada (2–3 min)…")
    log(W["msg"])
    r = subprocess.run(["tar", "-xf", achados[0], "-C", "/"], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(f"{VENV}/.pronto"):
        erro("usar o pacote guardado (vou instalar do zero)", r.stderr[-1500:] or "pacote incompleto", r.stderr[-1500:])
        return False
    CACHE.update(usado=True, estado="instalação guardada usada")
    log("Instalação guardada desempacotada")
    return True

def guardar_cache():
    """Empacota a instalação e os modelos baixados na saída do notebook, para as próximas sessões."""
    if CACHE["usado"] or os.path.exists(CACHE_SAIDA):
        return
    try:
        CACHE["estado"] = "guardando a instalação…"
        casa = os.path.expanduser("~")
        itens = [VENV, pasta_python_uv()] + glob.glob(f"{casa}/.cache/huggingface/hub/models--ResembleAI--*") \
                + glob.glob(f"{casa}/.cache/huggingface/hub/models--openai--whisper-small") \
                + glob.glob(f"{casa}/.cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign")
        itens = [i.lstrip("/") for i in itens if i and os.path.exists(i)]
        r = subprocess.run(["nice", "-n", "15", "tar", "-cf", CACHE_SAIDA + ".parcial", "-C", "/", *itens], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-1500:])
        os.replace(CACHE_SAIDA + ".parcial", CACHE_SAIDA)
        CACHE["estado"] = f"guardada ({os.path.getsize(CACHE_SAIDA) / 1e9:.1f} GB): vai para a saída do notebook quando a sessão terminar"
        log("Instalação guardada em tamaki_cache.tar")
    except Exception as e:
        CACHE["estado"] = "não consegui guardar"; erro("guardar a instalação", e)

def ambiente_gpu():
    """Ambiente do motor com o caminho do driver da GPU (o Python separado nem sempre acha sozinho)."""
    amb = dict(os.environ, HF_HUB_DISABLE_PROGRESS_BARS="1")
    pastas = []
    try:
        for linha in subprocess.run(["ldconfig", "-p"], capture_output=True, text=True).stdout.splitlines():
            if "libcuda.so" in linha and "=>" in linha:
                pastas.append(os.path.dirname(linha.split("=>")[1].strip()))
    except Exception:
        pass
    for p in ("/usr/local/nvidia/lib64", "/usr/local/nvidia/lib", "/usr/lib64-nvidia", "/usr/lib/x86_64-linux-gnu",
              "/usr/local/cuda/compat", "/usr/local/cuda/lib64", "/opt/conda/lib"):
        if glob.glob(f"{p}/libcuda.so*"):
            pastas.append(p)
    pastas = list(dict.fromkeys(pastas))
    amb["LD_LIBRARY_PATH"] = ":".join(pastas + [amb.get("LD_LIBRARY_PATH", "")]).strip(":")
    return amb, pastas

def preparar_motor():
    try:
        if not torch.cuda.is_available():
            raise RuntimeError("A GPU está desligada neste notebook. No Kaggle: Settings → Accelerator → GPU T4 x2, "
                               "depois Save Version → Save & Run All. Se a opção não aparecer, a cota semanal de GPU pode ter acabado.")
        py = f"{VENV}/bin/python"
        restaurar_cache()
        if not os.path.exists(f"{VENV}/.pronto"):
            W.update(estado="instalando", msg="criando o ambiente do Chatterbox (5–10 min na primeira vez)…")
            log(W["msg"])
            subprocess.run([sys.executable, "-m", "uv", "venv", "--python", "3.11", VENV], check=True, capture_output=True)
            extras = ["huggingface_hub", "safetensors", "soundfile", "librosa"]
            r = subprocess.run([sys.executable, "-m", "uv", "pip", "install", "--python", py,
                                "git+https://github.com/resemble-ai/chatterbox.git", *extras], capture_output=True, text=True)
            if r.returncode != 0:
                log("Instalação pelo GitHub falhou, tentando pelo PyPI…")
                r = subprocess.run([sys.executable, "-m", "uv", "pip", "install", "--python", py, "chatterbox-tts", *extras],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    raise RuntimeError("não consegui instalar o Chatterbox:\n" + r.stderr[-2500:])
            open(f"{VENV}/.pronto", "w").write("ok")
        open("/tmp/cb_worker.py", "w", encoding="utf-8").write(WORKER)
        W.update(estado="carregando", msg="carregando a voz brasileira (2–4 min)…")
        log(W["msg"])
        amb, pastas = ambiente_gpu()
        teste = subprocess.run([py, "-c", "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"],
                               capture_output=True, text=True, env=amb)
        log(f"GPU vista pelo motor: {teste.stdout.strip() or teste.stderr.strip()[-200:]}")
        if not teste.stdout.startswith("True"):
            raise RuntimeError("o motor não enxerga a GPU, mas o notebook enxerga.\n"
                               f"Pastas do driver achadas: {pastas or 'nenhuma'}\n{teste.stdout}\n{teste.stderr[-1500:]}")
        W["proc"] = subprocess.Popen([py, "/tmp/cb_worker.py", MODELO], stdout=open("/tmp/cb_worker.log", "w"),
                                     stderr=subprocess.STDOUT, env=amb)
        while True:
            time.sleep(3)
            if W["proc"].poll() is not None:
                raise RuntimeError("o motor fechou sozinho:\n" + open("/tmp/cb_worker.log").read()[-2500:])
            try:
                info = motor("/estado", timeout=10)
            except Exception:
                continue
            W["info"] = info
            if info["estado"] == "pronto":
                W.update(estado="pronto", msg="")
                log(f"Motor pronto · pacote {info['pack']}" + (f" · {info['aviso']}" if info["aviso"] else ""))
                break
            if info["estado"] == "erro":
                raise RuntimeError("o motor não carregou:\n" + info["aviso"])
        migrar()
        preparar_vozes()
        threading.Thread(target=guardar_cache, daemon=True).start()
    except Exception as e:
        W.update(estado="erro", msg=str(e)[:400]); erro("preparar o motor de voz (Chatterbox)", e)

TAREFA = {"msg": ""}   # tarefas longas (preparar voz importada etc.), mostradas no HTML

def garantir_conds(vid):
    if not os.path.exists(arq_conds(vid)):
        if not os.path.exists(arq_ref(vid)):
            raise RuntimeError("essa voz está sem o áudio de referência")
        motor("/conds", {"ref": arq_ref(vid), "saida": arq_conds(vid), "exaggeration": CONF["exaggeration"]}, timeout=180)

def aplicar_voz(vid):
    """Põe a voz em uso no motor."""
    if vid == "padrao":
        motor("/usar", {}, timeout=180)
    else:
        if vid not in ler_vozes():
            raise RuntimeError("essa voz não existe mais")
        garantir_conds(vid)
        motor("/usar", {"t3": arq_t3(vid) if os.path.exists(arq_t3(vid)) else None, "conds": arq_conds(vid)}, timeout=180)
    CONF["ativa"] = vid; gravar_cfg()

def preparar_vozes():
    for vid in ler_vozes():
        try:
            garantir_conds(vid)
        except Exception as e:
            erro(f"preparar a voz {vid}", e)
    try:
        aplicar_voz(CONF["ativa"] if CONF["ativa"] == "padrao" or CONF["ativa"] in ler_vozes() else "padrao")
        log("Voz em uso: " + nome_voz(CONF["ativa"]))
    except Exception as e:
        erro("pôr a voz em uso", e)

def nome_voz(vid):
    return "Voz padrão do modelo" if vid == "padrao" else ler_vozes().get(vid, {}).get("nome", "?")

TREINO = {"pendente": None}   # o que fazer quando o treino terminar

def finalizar_treino(p):
    try:
        with LOCK_VOZES:
            vozes, agora = ler_vozes(), int(time.time())
            vid = p["destino"]
            if p["nova"]:
                for ext in (".wav", ".pt"):
                    origem = f"{REFS}/{p['origem']}{ext}"
                    if os.path.exists(origem):
                        shutil.copy(origem, f"{REFS}/{vid}{ext}")
                antiga = vozes.get(p["origem"], {})
                for eid in antiga.get("emocoes", {}):   # a voz nova leva as emoções da antiga
                    for arq in glob.glob(f"{REFS}/{p['origem']}__{eid}*"):
                        shutil.copy(arq, arq.replace(f"/{p['origem']}__", f"/{vid}__"))
                vozes[vid] = {"nome": p["nome"] or "Voz treinada", "foto": p["foto"], "criado": agora, "atualizado": agora,
                              "versao": 1, "treinos": antiga.get("treinos", 0) + 1, "treinada": True, "texto_ref": antiga.get("texto_ref", ""),
                              "emocoes": json.loads(json.dumps(antiga.get("emocoes", {})))}
            else:
                v = vozes[vid]
                v.update(atualizado=agora, versao=v.get("versao", 1) + (1 if v.get("treinada") else 0), treinos=v.get("treinos", 0) + 1, treinada=True)
            os.replace(p["saida"], arq_t3(vid))
            gravar_vozes(vozes)
        aplicar_voz(vid)
        if contar():   # as frases passam a ser desta voz
            json.dump({"voz": vid}, open(DSINFO, "w"))
        log(f"Treino salvo em “{nome_voz(vid)}” e já em uso")
        threading.Thread(target=backup, args=(True,), daemon=True).start()
    except Exception as e:
        erro("salvar a voz treinada", e)

def vigiar_motor():   # atualiza o estado do motor para o HTML sem travar as respostas
    while True:
        time.sleep(3)
        if W["estado"] != "pronto":
            continue
        try:
            W["info"] = motor("/estado", timeout=10)
            t = W["info"]["treino"]
            if t.get("erro") and t["erro"] != W.get("ultimo_erro_treino"):
                W["ultimo_erro_treino"] = t["erro"]; erro("treinar a voz", t["msg"], t["erro"])
            p = TREINO["pendente"]
            if p and not t.get("rodando"):
                TREINO["pendente"] = None
                if t.get("msg") == "pronto" and t.get("saida") == p["saida"] and os.path.exists(p["saida"]):
                    finalizar_treino(p)
        except Exception:
            pass

# GPU 0 fica para o motor de voz; GPU 1 para o criador de vozes, o Whisper e o treino
G2 = 1 if torch.cuda.device_count() > 1 else 0

# ---------- 5. Whisper (confere se as frases geradas estão inteligíveis) ----------
ASR = {"p": None}
LOCK_ASR = threading.Lock()
def transcrever(arq):
    from transformers import pipeline
    with LOCK_ASR:
        if ASR["p"] is None:
            ASR["p"] = pipeline("automatic-speech-recognition", model="openai/whisper-small", device=G2)
        txt = ASR["p"](arq, chunk_length_s=30, generate_kwargs={"language": "portuguese", "task": "transcribe"})["text"]
    return " ".join(txt.split())

def parecido(a, b):
    import difflib
    lim = lambda t: " ".join("".join(c for c in unicodedata.normalize("NFKD", t.lower()) if c.isalnum() or c.isspace()).split())
    a, b = lim(a), lim(b)
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 2) if a and b else 0.0

# ---------- 6. frases de treino ----------
FRASES_BR = """Gente, vocês não vão acreditar no que aconteceu comigo hoje!
Tá bom, tá bom, eu admito que errei, mas só um pouquinho.
Você viu o tamanho da fila do mercado? Eu quase desisti.
A gente podia pedir uma pizza e ver um filme, que tal?
Nossa, que calor! Alguém liga esse ventilador, por favor.
Eu fui de ônibus até o shopping e voltei de metrô.
Você tá de brincadeira comigo, né?
Calma, respira, vai dar tudo certo no final.
Fala sério, isso não faz o menor sentido!
Meu celular descarregou bem na hora que eu mais precisava.
Bora tomar um açaí depois da aula?
Eu tô morrendo de fome, faz horas que não como nada.
Que legal! Eu nem sabia que você gostava de videogame.
Ontem choveu tanto que a rua virou um rio.
Deixa comigo, eu resolvo isso rapidinho.
Será que dá tempo de passar na padaria antes de ir?
Esse café tá muito bom, quem foi que fez?
Ai, que preguiça de acordar cedo na segunda-feira.
Olha só quem resolveu aparecer!
Não acredito que você comeu o último pedaço do bolo.
Bom dia, gente! Hoje à noite a cidade inteira vai sair pra ver o jogo.
De verdade, você tem que tomar leite quente antes de dormir.
A tia do Daniel mora perto da praia e adora tirar foto do pôr do sol.
Tudo bem com você? Faz tempo que a gente não se vê, que saudade!
O time ganhou de virada e a torcida cantou até de madrugada.
Que dia lindo! Vamos tomar um sorvete de chocolate no parque?
Minha mãe faz o melhor pudim de leite condensado do mundo inteiro.
Natal no Brasil é calor, praia e muita comida na casa da avó.
Amanhã cedo a gente pega a estrada, tá bom?
Pode deixar que eu cuido de tudo, você só precisa descansar.
Oi, miga! Nem te conto o que aconteceu comigo hoje.
Bicha, para tudo que eu preciso te contar uma fofoca!""".split("\n")

_portugal = re.compile(r"\b(tu|vós|vosso|vossa|estás|tens|podes|queres|fazes|sabes|foste|giro|gira|fixe|bué|malta|gajo|gaja|"
                       r"euros?|comboio|autocarro|telemóvel|facto|equipa|ecrã|utilizador\w*|registo|contacto|receção|"
                       r"rapariga|miúd\w+|frigorífico|sumo|talho|dezassete|dezasseis|dezanove)\b"
                       r"|\b(est\w+|and\w+|fic\w+|continu\w+) a \w+r\b", re.I)

def nome_arq(i):
    return f"{NOME}_{i:04d}"

def frases_atuais():
    arq = f"{DS}/frases.txt"
    return [l.rstrip("\n") for l in open(arq, encoding="utf-8")] if os.path.exists(arq) else []

def lista_de_frases(qtd):
    frases = frases_atuais()
    if len(frases) < qtd:
        banco = list(FRASES_BR)
        try:
            url = "https://raw.githubusercontent.com/common-voice/common-voice/main/server/data/pt/sentence-collector.txt"
            todas = urllib.request.urlopen(url, timeout=60).read().decode("utf-8").splitlines()
            boas = [f.strip() for f in todas if 6 <= len(f.split()) <= 18 and f.strip()[:1].isupper()
                    and f.strip()[-1:] in ".!?" and not re.search(r"[0-9%&@#/\\()\[\]{}<>_=+*\"]", f) and not _portugal.search(f)]
            random.seed(42); random.shuffle(boas)
            banco += boas
        except Exception as e:
            erro("baixar o banco de frases", e)
        usadas = set(frases)
        frases += [f for f in banco if f not in usadas][:qtd - len(frases)]
        open(f"{DS}/frases.txt", "w", encoding="utf-8").write("\n".join(frases))
    return frases[:qtd]

def escrever_metadata():
    frases = frases_atuais()
    linhas = [f"{nome_arq(i)}|{frases[i]}" for i in range(len(frases)) if os.path.exists(f"{WAVS}/{nome_arq(i)}.wav")]
    open(f"{DS}/metadata.csv", "w", encoding="utf-8").write("\n".join(linhas) + ("\n" if linhas else ""))
    return len(linhas)

def contar():
    return len(glob.glob(f"{WAVS}/*.wav"))

# ---------- 7. gerar o dataset (a voz em uso fala as frases) ----------
D = {"rodando": False, "parar": False, "msg": "parado", "descartadas": 0, "amostra": None, "ultima": None}

def voz_do_dataset():
    try:
        return json.load(open(DSINFO)).get("voz")
    except Exception:
        return None

def gerar_dataset():
    D.update(rodando=True, parar=False, descartadas=0, msg="preparando as frases…")
    try:
        liberar_design()
        if W["estado"] != "pronto":
            raise RuntimeError("o motor de voz ainda não está pronto")
        if CONF["ativa"] == "padrao":
            raise RuntimeError("escolha ou crie uma voz sua antes de gerar as frases")
        if contar() and voz_do_dataset() not in (None, CONF["ativa"]):
            raise RuntimeError("as frases que já existem são de outra voz: apague-as antes")
        json.dump({"voz": CONF["ativa"]}, open(DSINFO, "w"))
        frases = lista_de_frases(int(CONF["quantidade"]))
        desde_backup = 0
        for rodada in range(3):
            faltam = [i for i in range(len(frases)) if not os.path.exists(f"{WAVS}/{nome_arq(i)}.wav")]
            for i in faltam:
                if D["parar"] or time.time() > FIM - 900:
                    break
                D["msg"] = f"gerando ({contar()} de {len(frases)})" + (f" · rodada {rodada + 1}" if rodada else "")
                tmp = f"{TMP}/ds.wav"
                motor("/falar", {"texto": frases[i], "saida": tmp, "exaggeration": CONF["exaggeration"],
                                 "cfg_weight": CONF["cfg_weight"], "temperature": min(0.8, CONF["temperature"])})
                ouvido = transcrever(tmp)
                nota = parecido(ouvido, frases[i])
                D["ultima"] = {"frase": frases[i], "ouvido": ouvido, "nota": nota}
                if nota < 0.8:
                    D["descartadas"] += 1; continue
                shutil.move(tmp, f"{WAVS}/{nome_arq(i)}.wav")
                D["amostra"] = i; desde_backup += 1
                if desde_backup >= 25:
                    backup(); desde_backup = 0
            if D["parar"]:
                break
        D["msg"] = "pausado" if D["parar"] else ("completo" if contar() >= len(frases) else "parou: algumas frases não passaram")
    except Exception as e:
        D["msg"] = "erro: " + str(e)[:120]; erro("gerar as frases de treino", e)
    finally:
        escrever_metadata(); backup(); D["rodando"] = False
        log("Frases de treino: " + D["msg"])

# ---------- 7b. conversas reais (CORAA v1.1, parte "dev": ~11 h de português brasileiro, 1,3 GB) ----------
# Só falas espontâneas (entrevista, diálogo, conversa), sem ruído, sem gente falando junto e sem "éé"/hesitação,
# de preferência de São Paulo. Os áudios entram como frases de treino da voz em uso (substituem as frases antigas).
CO = {"rodando": False, "parar": False, "msg": "", "feitas": 0, "total": 0}
SOTAQUES = ["sao paulo capital", "sao paulo cities", "misc", "minas gerais", "recife"]

def texto_coraa(t):
    t = re.sub(r"\(\(.*?\)\)|\[.*?\]|\(.*?\)|<.*?>", " ", t or "")
    t = re.sub(r"[^\w\sáàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ,.!?'-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" -,")
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    return t if t[-1] in ".!?" else t + "."

def job_coraa(qtd):
    CO.update(rodando=True, parar=False, msg="baixando a lista de conversas…", feitas=0, total=qtd, descartados=0)
    pasta = f"{TMP}/coraa"
    try:
        from huggingface_hub import hf_hub_download
        import csv
        repo = "gabrielrstan/CORAA-v1.1"
        meta = hf_hub_download(repo, "metadata_dev_final.csv", repo_type="dataset", local_dir=pasta)
        num = lambda r, k: int(float(r.get(k) or 0)) if str(r.get(k) or "0").replace(".", "", 1).isdigit() else 0
        boas = []
        for r in csv.DictReader(open(meta, encoding="utf-8")):
            estilo = (r.get("task", "") + " " + r.get("speech_style", "")).lower()
            texto = texto_coraa(r.get("text", ""))
            if "spont" not in estilo or not 4 <= len(texto.split()) <= 30:
                continue
            if num(r, "votes_for_noise_or_overlap") or num(r, "votes_for_filled_pause") or num(r, "votes_for_hesitation"):
                continue
            if num(r, "down_votes") or num(r, "up_votes") < 1:
                continue
            sot = sem_acento((r.get("accent") or "misc").lower())
            boas.append((SOTAQUES.index(sot) if sot in SOTAQUES else 2, random.random(), r, texto))
        boas.sort(key=lambda x: (x[0], x[1]))
        log(f"CORAA: {len(boas)} falas espontâneas boas")
        if len(boas) < 20:
            raise RuntimeError("não achei falas boas na lista do CORAA")
        CO["msg"] = "baixando as conversas (1,3 GB, uns 3–6 min)…"
        z = hf_hub_download(repo, "dev.zip", repo_type="dataset", local_dir=pasta)
        CO["msg"] = "separando os trechos…"
        frases = []
        with zipfile.ZipFile(z) as zf:
            nomes = {os.path.basename(n): n for n in zf.namelist() if n.lower().endswith(".wav")}
            for f in glob.glob(f"{WAVS}/*.wav"):
                os.remove(f)
            for _, _, r, texto in boas:
                if CO["parar"] or len(frases) >= qtd:
                    break
                n = nomes.get(os.path.basename(r.get("file_path", "")))
                if not n:
                    continue
                try:
                    w, sr = sf.read(io.BytesIO(zf.read(n)))
                except Exception:
                    continue
                w = w if w.ndim == 1 else w.mean(1)
                if not 2.0 <= len(w) / sr <= 12.0 or float(np.abs(w).max()) < 0.02:
                    continue
                w = (w / max(1e-6, float(np.abs(w).max())) * 0.9).astype(np.float32)   # volume parecido em todas
                arq = f"{WAVS}/{nome_arq(len(frases))}.wav"
                sf.write(arq, w, sr)
                try:   # o texto tem que bater com o que a pessoa falou, senão a voz aprende a embolar
                    if parecido(transcrever(arq), texto) < 0.85:
                        os.remove(arq); CO["descartados"] = CO.get("descartados", 0) + 1; continue
                except Exception as er:
                    erro("conferir trecho do CORAA", er)
                frases.append(texto)
                CO.update(feitas=len(frases), msg=f"separando os trechos ({len(frases)} de {qtd}, {CO.get('descartados', 0)} descartados por não baterem)")
        open(f"{DS}/frases.txt", "w", encoding="utf-8").write("\n".join(frases))
        json.dump({"voz": CONF["ativa"], "origem": "coraa"}, open(DSINFO, "w"))
        CONF["quantidade"] = max(20, len(frases)); gravar_cfg(); escrever_metadata()
        CO["msg"] = f"pronto: {len(frases)} trechos de conversa real. Agora treine como voz nova, começando do português original."
        log(f"CORAA: {len(frases)} trechos prontos para o treino")
        threading.Thread(target=backup, daemon=True).start()
    except Exception as e:
        CO["msg"] = "erro: " + str(e)[:160]; erro("baixar as conversas do CORAA", e)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
        CO["rodando"] = False

# ---------- 8. criar voz do nada (Qwen3-TTS VoiceDesign: só cria o timbre) ----------
VD = {"modelo": None, "rodando": False, "versoes": [], "msg": "", "texto": ""}
_BR = ("Native Brazilian Portuguese speaker from Brazil, natural everyday Brazilian accent, "
       "warm and melodic Brazilian intonation")

def job_design(descricao, texto, n):
    VD.update(rodando=True, versoes=[], texto=texto)
    try:
        if VD["modelo"] is None:
            VD["msg"] = "carregando o criador de vozes (3–5 min na primeira vez)…"
            from qwen_tts import Qwen3TTSModel
            tipo = torch.bfloat16 if torch.cuda.get_device_capability(G2)[0] >= 8 else torch.float32
            VD["modelo"] = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", device_map=f"cuda:{G2}",
                                                         dtype=tipo, attn_implementation="sdpa")
        for f in glob.glob(f"{DESIGN}/*.wav"):
            os.remove(f)
        for i in range(n):
            VD["msg"] = f"criando a versão {i + 1} de {n}…"
            torch.manual_seed(int(time.time()) + i)
            wavs, sr = VD["modelo"].generate_voice_design(text=texto, language="Portuguese",
                                                          instruct=_BR + ". " + descricao, do_sample=True)
            arq = f"{DESIGN}/versao_{i + 1}_{int(time.time())}.wav"
            sf.write(arq, np.asarray(wavs[0], dtype=np.float32).reshape(-1), sr)
            VD["versoes"].append(arq)
        VD["msg"] = "pronto: escute e escolha uma"
    except Exception as e:
        VD["msg"] = "erro"; erro("criar voz nova", e)
    VD["rodando"] = False

def liberar_design():
    """Tira o criador de vozes da memória da GPU (ele volta sozinho se você criar vozes de novo)."""
    if VD["modelo"] is not None and not VD["rodando"]:
        VD["modelo"] = None
        import gc; gc.collect(); torch.cuda.empty_cache()
        VD["msg"] = ""
        log("Criador de vozes descarregado para liberar memória")

# ---------- 8b. emoções: cada voz guarda um exemplo dela mesma em cada emoção ----------
# Como funciona: a voz (com o treino dela) fala uma frase cheia daquela emoção, em várias versões.
# O Whisper confere se dá para entender e a mais expressiva vira o "exemplo" da emoção.
# Depois, toda fala com (brava), (triste)… usa esse exemplo, e a voz copia o jeito de falar dele.
EMO_CAT = [
    {"id": "feliz", "nome": "Feliz", "emoji": "😄", "exag": 0.8, "cfg": 0.4, "temp": 0.8, "energia": 1,
     "texto": "Ai, gente, eu tô tão feliz! Vocês não fazem ideia! Deu tudo certo, tudo mesmo! Eu quase chorei de alegria quando vi o resultado. Que dia maravilhoso!"},
    {"id": "animada", "nome": "Animada", "emoji": "🤩", "exag": 1.0, "cfg": 0.3, "temp": 0.85, "energia": 1,
     "texto": "Bora, bora, bora! Hoje vai ser incrível! Eu preparei uma surpresa enorme pra vocês e não tô aguentando esperar! Vem comigo que vai ser épico!"},
    {"id": "brava", "nome": "Brava", "emoji": "😠", "exag": 1.0, "cfg": 0.3, "temp": 0.8, "energia": 1,
     "texto": "Não, não e não! Eu já falei mil vezes! Quem foi que mexeu nas minhas coisas? Isso é um absurdo! Eu tô muito irritada, de verdade!"},
    {"id": "triste", "nome": "Triste", "emoji": "😢", "exag": 0.6, "cfg": 0.5, "temp": 0.7, "energia": -1,
     "texto": "Eu... eu não sei o que dizer. Achei que ia ser diferente, sabe? Eu tentei tanto. Às vezes dá vontade de sumir um pouquinho e ficar quietinha no meu canto."},
    {"id": "assustada", "nome": "Assustada", "emoji": "😱", "exag": 1.1, "cfg": 0.3, "temp": 0.85, "energia": 1,
     "texto": "Que barulho foi esse?! Gente, tem alguma coisa ali no escuro! Não, não, não, eu não vou lá de jeito nenhum! Alguém acende a luz, por favor!"},
    {"id": "sarcastica", "nome": "Sarcástica", "emoji": "😏", "exag": 0.7, "cfg": 0.4, "temp": 0.8, "energia": 0,
     "texto": "Ah, claro. Que ideia brilhante. Ninguém nunca pensou nisso antes, né? Parabéns, de verdade. Você é um gênio incompreendido."},
    {"id": "cochicho", "nome": "Cochichando", "emoji": "🤫", "exag": 0.35, "cfg": 0.5, "temp": 0.7, "energia": -1,
     "texto": "Psiu, fala baixinho... ninguém pode saber disso, tá? É segredo. Chega mais perto que eu vou te contar bem devagarinho."},
    {"id": "rindo", "nome": "Rindo", "emoji": "😂", "exag": 1.2, "cfg": 0.3, "temp": 0.9, "energia": 1,
     "texto": "Hahaha, não acredito! Para, para, que eu não aguento! Você viu a cara dele? Eu tô chorando de rir aqui, sério mesmo!"},
    {"id": "calma", "nome": "Calma", "emoji": "😌", "exag": 0.4, "cfg": 0.5, "temp": 0.7, "energia": -1,
     "texto": "Respira fundo. Tá tudo bem. A gente vai com calma, um passo de cada vez. Não precisa ter pressa nenhuma, tá? Eu tô aqui com você."},
]
CAT = {e["id"]: e for e in EMO_CAT}
APELIDOS = {"alegre": "feliz", "contente": "feliz", "felicidade": "feliz", "empolgada": "animada", "animado": "animada", "empolgado": "animada",
            "bravo": "brava", "irritada": "brava", "irritado": "brava", "raiva": "brava", "nervosa": "brava", "chorando": "triste", "tristeza": "triste",
            "assustado": "assustada", "medo": "assustada", "com medo": "assustada", "sarcastico": "sarcastica", "ironica": "sarcastica",
            "ironico": "sarcastica", "deboche": "sarcastica", "debochada": "sarcastica", "cochicho": "cochicho", "cochichando": "cochicho",
            "sussurro": "cochicho", "sussurrando": "cochicho", "baixinho": "cochicho", "risada": "rindo", "risos": "rindo", "rindo": "rindo",
            "gargalhada": "rindo", "tranquila": "calma", "tranquilo": "calma", "calmo": "calma", "suave": "calma"}
NEUTRAS = {"normal", "neutra", "neutro", "sem emocao", "padrao"}
EMO = {"fila": [], "rodando": False, "parar": False, "msg": "", "atual": None, "feitas": [], "passo": 0, "passos": 0}
TAG = re.compile(r"[\(\[]\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ ]{1,22})\s*[\)\]]")

def sem_acento(t):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", (t or "").lower()) if not unicodedata.combining(c)).split())

def slug_emo(nome):
    s = re.sub(r"[^a-z0-9]+", "_", sem_acento(nome)).strip("_")[:24]
    return s if s in CAT else "c_" + (s or "emocao")

def emocoes_da(vid):
    return ler_vozes().get(vid, {}).get("emocoes", {}) if vid != "padrao" else {}

def achar_emocao(nome, emos):
    """(brava) → ("brava", True); (normal) → (None, True); (oi gente) → (None, False): não é emoção, fica no texto."""
    n = sem_acento(nome)
    if n in NEUTRAS:
        return None, True
    eid = APELIDOS.get(n, n)
    if eid in CAT:
        return eid, True
    for k, e in emos.items():
        if sem_acento(e.get("nome")) == n or k == "c_" + n.replace(" ", "_"):
            return k, True
    return None, False

def medir(arq):
    """Energia e quanto o tom sobe e desce: emoções agitadas pedem mais dos dois; as calmas, menos."""
    w, sr = librosa.load(arq, sr=16000, mono=True)
    rms = float(np.sqrt(np.mean(w ** 2)) + 1e-9)
    try:
        f0 = librosa.yin(w, fmin=70, fmax=600, sr=sr)
        f0 = f0[(f0 > 75) & (f0 < 580)]
        var = float(np.std(np.log(f0))) if len(f0) > 10 else 0.0
    except Exception:
        var = 0.0
    return rms, var, len(w) / sr

def fazer_emocao(it):
    vid, eid, n = it["voz"], it["id"], it["versoes"]
    if CONF["ativa"] != vid:
        raise RuntimeError("a voz em uso mudou no meio do caminho")
    cands = []
    for k in range(n):
        if EMO["parar"]:
            raise RuntimeError("parado por você")
        EMO["msg"] = f"{it['emoji']} {it['nome']}: gravando a versão {k + 1} de {n}…"
        arq = f"{TMP}/emo_{eid}_{k}.wav"
        motor("/falar", {"texto": it["texto"], "saida": arq, "exaggeration": it["exag"], "cfg_weight": it["cfg"], "temperature": it["temp"]})
        EMO["msg"] = f"{it['emoji']} {it['nome']}: conferindo a versão {k + 1}…"
        nota = parecido(transcrever(arq), it["texto"])
        rms, var, dur = medir(arq)
        cands.append({"arq": arq, "nota": nota, "rms": rms, "var": var, "dur": dur})
        EMO["passo"] += 1
    minimo = 0.5 if eid == "rindo" else 0.7
    boas = [c for c in cands if c["nota"] >= minimo] or sorted(cands, key=lambda c: -c["nota"])[:1]
    def z(chave):
        xs = np.array([c[chave] for c in boas]); d = xs.std()
        return (xs - xs.mean()) / d if d > 1e-9 else np.zeros(len(xs))
    agitacao = z("rms") + z("var")
    energia = CAT.get(eid, {}).get("energia", 0)
    for c, a in zip(boas, agitacao):
        c["pontos"] = c["nota"] + 0.15 * energia * float(a)
    boas.sort(key=lambda c: -c["pontos"])
    outras = boas[1:] + [c for c in cands if c not in boas]
    for velha in glob.glob(arq_emo(vid, eid, "*")):
        os.remove(velha)
    shutil.copy(boas[0]["arq"], arq_emo(vid, eid))
    for i, c in enumerate(outras):
        shutil.copy(c["arq"], arq_emo(vid, eid, i))
    EMO["msg"] = f"{it['emoji']} {it['nome']}: guardando na voz…"
    motor("/conds", {"ref": arq_emo(vid, eid), "saida": arq_emo_conds(vid, eid), "exaggeration": it["exag"], "manter": True}, timeout=180)
    salvar_emocao(vid, eid, it, nota=boas[0]["nota"], alts=len(outras), origem="gerada")
    EMO["feitas"].append({"id": eid, "nome": it["nome"], "ok": True, "nota": boas[0]["nota"]})
    log(f"Emoção pronta: {it['emoji']} {it['nome']} em “{nome_voz(vid)}” (entendi {round(boas[0]['nota'] * 100)}%)")

def salvar_emocao(vid, eid, it, **extra):
    with LOCK_VOZES:
        vozes = ler_vozes()
        if vid not in vozes:
            raise RuntimeError("essa voz não existe mais")
        agora = int(time.time())
        antes = vozes[vid].setdefault("emocoes", {}).get(eid, {})
        vozes[vid]["emocoes"][eid] = {**antes, "nome": it["nome"], "emoji": it["emoji"], "texto": it.get("texto", antes.get("texto", "")),
                                      "exag": round(float(it["exag"]), 2), "cfg": round(float(it["cfg"]), 2), "temp": round(float(it["temp"]), 2),
                                      "atualizado": agora, **extra}
        vozes[vid]["atualizado"] = agora   # o HTML vê a mudança e guarda o cartão novo no aparelho
        gravar_vozes(vozes)
    threading.Thread(target=backup, daemon=True).start()

def job_emocoes():
    EMO.update(rodando=True, parar=False, feitas=[], passo=0)
    try:
        liberar_design()
        while EMO["fila"] and not EMO["parar"]:
            it = EMO["fila"].pop(0)
            EMO["atual"] = it["id"]
            try:
                fazer_emocao(it)
            except Exception as e:
                if EMO["parar"]:
                    break
                EMO["feitas"].append({"id": it["id"], "nome": it["nome"], "ok": False, "msg": str(e)[:200]})
                erro(f"treinar a emoção {it['nome']}", e)
        EMO["msg"] = "parado por você" if EMO["parar"] else "pronto: as emoções já estão na voz"
    finally:
        EMO["fila"].clear()
        EMO.update(rodando=False, atual=None, passos=0, passo=0)

def garantir_emo_conds(vid, eid, e):
    if not os.path.exists(arq_emo_conds(vid, eid)):
        if not os.path.exists(arq_emo(vid, eid)):
            return False
        motor("/conds", {"ref": arq_emo(vid, eid), "saida": arq_emo_conds(vid, eid), "exaggeration": e.get("exag", 0.5), "manter": True}, timeout=180)
    return True

def ocupado_emocoes():
    if EMO["rodando"]:
        raise RuntimeError("espere as emoções terminarem (ou toque em Parar na aba Emoções)")

# ---------- 9. servidor ----------
import base64
app = FastAPI()

@app.middleware("http")
async def senha(request: Request, chamar):
    if request.method != "OPTIONS" and request.url.path != "/" and request.headers.get("x-codigo") != CODIGO:
        return JSONResponse({"erro": "código de ligação errado"}, status_code=401)
    try:
        return await chamar(request)
    except Exception as e:
        erro("servidor " + request.url.path, e)
        return JSONResponse({"erro": f"{type(e).__name__}: {e}"}, status_code=500)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["X-Emocoes-Faltando", "X-Emocoes-Usadas"])

def falha(msg, cod=400):
    return JSONResponse({"erro": msg}, status_code=cod)

def precisa_motor():
    if W["estado"] != "pronto":
        raise RuntimeError("o motor de voz ainda não está pronto")

@app.get("/")
def raiz():
    return {"ok": True, "servico": "voz-br-tamaki", "versao": 3}

def emocoes_publicas(vid):
    """O catálogo com o estado de cada emoção na voz em uso (e as emoções criadas por você)."""
    emos, saida = emocoes_da(vid), []
    for e in EMO_CAT + [{"id": k, **v, "sua": True} for k, v in emos.items() if k not in CAT]:
        tem = emos.get(e["id"])
        saida.append({"id": e["id"], "nome": (tem or e)["nome"], "emoji": (tem or e)["emoji"], "texto": (tem or e).get("texto", ""),
                      "exag": (tem or e)["exag"], "cfg": (tem or e)["cfg"], "temp": (tem or e)["temp"], "sua": bool(e.get("sua")),
                      "pronta": bool(tem), "nota": (tem or {}).get("nota"), "alts": (tem or {}).get("alts", 0),
                      "origem": (tem or {}).get("origem", ""), "atualizado": (tem or {}).get("atualizado", 0)})
    return saida

@app.get("/status")
def status():
    info = W["info"] or {}
    dv = voz_do_dataset()
    return {"ok": True, "versao": 5, "coraa": CO, "fim_em": int(FIM - time.time()), "nuvem": NUVEM["estado"], "conf": CONF, "cache": CACHE["estado"],
            "motor": {"estado": W["estado"], "msg": W["msg"], "pack": info.get("pack", ""), "aviso": info.get("aviso", "")},
            "ativa": CONF["ativa"], "vozes": lista_vozes(), "vozes_rev": VREV[0], "tarefa": TAREFA["msg"],
            "design": {"rodando": VD["rodando"], "n": len(VD["versoes"]), "msg": VD["msg"], "texto": VD["texto"]},
            "dataset": {"feitas": contar(), "total": int(CONF["quantidade"]), "rodando": D["rodando"], "msg": D["msg"],
                        "descartadas": D["descartadas"], "ultima": D["ultima"], "amostra": D["amostra"],
                        "voz": dv if contar() else None, "voz_nome": nome_voz(dv) if dv and contar() else ""},
            "treino": info.get("treino", {}),
            "emocoes": {"rodando": EMO["rodando"], "msg": EMO["msg"], "atual": EMO["atual"], "fila": [x["id"] for x in EMO["fila"]],
                        "feitas": EMO["feitas"][-20:], "passo": EMO["passo"], "passos": EMO["passos"], "lista": emocoes_publicas(CONF["ativa"])},
            "erros": list(ERROS), "log": list(LOG)[-12:]}

@app.post("/config")
async def config(request: Request):
    d = await request.json()
    for k, (lo, hi) in {"exaggeration": (0.25, 2.0), "cfg_weight": (0.0, 1.0), "temperature": (0.3, 1.5),
                        "quantidade": (20, 2000), "epocas": (1, 20)}.items():
        if k in d:
            v = max(lo, min(hi, float(d[k])))
            CONF[k] = int(v) if k in ("quantidade", "epocas") else round(v, 2)
    gravar_cfg()
    return {"ok": True, **CONF}

# ----- vozes salvas -----
@app.get("/vozes")
def vozes_get():
    return {"ativa": CONF["ativa"], "rev": VREV[0], "vozes": lista_vozes(fotos=True)}

def criar_voz(origem, texto, nome, foto):
    precisa_motor(); ocupado_emocoes()
    vid = novo_id()
    wav, sr = librosa.load(origem, sr=None, mono=True)
    wav, _ = librosa.effects.trim(wav, top_db=40)
    if sr > 24000:
        wav, sr = librosa.resample(wav, orig_sr=sr, target_sr=24000), 24000
    sf.write(arq_ref(vid), wav, sr)
    agora = int(time.time())
    with LOCK_VOZES:
        vozes = ler_vozes()
        vozes[vid] = {"nome": (nome or "").strip()[:60] or "Voz nova", "foto": foto or "", "criado": agora, "atualizado": agora,
                      "versao": 1, "treinos": 0, "treinada": False, "texto_ref": (texto or "").strip()}
        gravar_vozes(vozes)
    aplicar_voz(vid)
    log(f"Voz nova: {nome_voz(vid)} ({len(wav) / sr:.1f} s)" + (" · curta: o ideal é 10–15 s" if len(wav) / sr < 9 else ""))
    threading.Thread(target=backup, daemon=True).start()
    return vid

@app.post("/vozes/nova")
def vozes_nova(arquivo: UploadFile = File(...), texto: str = Form(""), nome: str = Form(""), foto: str = Form("")):
    tmp = f"{TMP}/envio" + (os.path.splitext(arquivo.filename or "")[1] or ".wav")
    open(tmp, "wb").write(arquivo.file.read())
    return {"ok": True, "id": criar_voz(tmp, texto, nome, foto)}

@app.post("/vozes/nova_design")
def vozes_nova_design(corpo: dict = Body(...)):
    i = int(corpo.get("i", -1))
    if not 0 <= i < len(VD["versoes"]):
        return falha("essa versão não existe mais", 404)
    return {"ok": True, "id": criar_voz(VD["versoes"][i], VD["texto"], corpo.get("nome", ""), corpo.get("foto", ""))}

@app.post("/vozes/usar")
def vozes_usar(corpo: dict = Body(...)):
    precisa_motor()
    vid = str(corpo.get("id", "padrao"))
    if vid != CONF["ativa"]:
        ocupado_emocoes()
    aplicar_voz(vid)
    log("Voz em uso: " + nome_voz(CONF["ativa"]))
    return {"ok": True}

@app.post("/vozes/editar")
def vozes_editar(corpo: dict = Body(...)):
    vid = str(corpo.get("id", ""))
    with LOCK_VOZES:
        vozes = ler_vozes()
        if vid not in vozes:
            return falha("essa voz não existe", 404)
        if "nome" in corpo:
            nome = " ".join(str(corpo["nome"]).split())[:60]
            if not nome:
                return falha("escreva um nome")
            vozes[vid]["nome"] = nome
        if "foto" in corpo:
            foto = str(corpo["foto"] or "")
            if foto and (not foto.startswith("data:image/") or len(foto) > 400_000):
                return falha("foto inválida ou grande demais")
            vozes[vid]["foto"] = foto
        vozes[vid]["atualizado"] = int(time.time())
        gravar_vozes(vozes)
    threading.Thread(target=backup, daemon=True).start()
    return {"ok": True}

@app.post("/vozes/apagar")
def vozes_apagar(corpo: dict = Body(...)):
    vid = str(corpo.get("id", ""))
    if vid == CONF["ativa"]:
        ocupado_emocoes()
    with LOCK_VOZES:
        vozes = ler_vozes()
        if vid not in vozes:
            return falha("essa voz não existe", 404)
        vozes.pop(vid); gravar_vozes(vozes)
    if CONF["ativa"] == vid and W["estado"] == "pronto":
        aplicar_voz("padrao")
    for arq in [arq_t3(vid), arq_ref(vid), arq_conds(vid)] + glob.glob(f"{REFS}/{vid}__*"):
        if os.path.exists(arq):
            os.remove(arq)
    if hf:
        for repo, caminho, tipo in ((REPO_MOD, f"t3_{vid}.pt", None), (REPO_DS, f"refs/{vid}.wav", "dataset"), (REPO_DS, f"refs/{vid}.pt", "dataset")):
            try:
                hf.delete_file(path_in_repo=caminho, repo_id=repo, repo_type=tipo)
            except Exception:
                pass
    threading.Thread(target=backup, daemon=True).start()
    log("Voz apagada")
    return {"ok": True}

def b64_wav(arq):
    w, sr = sf.read(arq)
    buf = io.BytesIO(); sf.write(buf, w, sr, format="WAV", subtype="PCM_16")
    return base64.b64encode(buf.getvalue()).decode()

@app.get("/vozes/{vid}/cartao")
def vozes_cartao(vid: str):
    v = ler_vozes().get(vid)
    if not v:
        return falha("essa voz não existe", 404)
    ref = b64_wav(arq_ref(vid)) if os.path.exists(arq_ref(vid)) else ""
    emocoes = {eid: {**{k: x for k, x in e.items() if k != "alts"}, "ref_wav": b64_wav(arq_emo(vid, eid))}
               for eid, e in v.get("emocoes", {}).items() if os.path.exists(arq_emo(vid, eid))}
    return {"tipo": "tamaki-voz", "formato": 2, "id": vid, "nome": v["nome"], "foto": v.get("foto", ""),
            "criado": v.get("criado", 0), "atualizado": v.get("atualizado", 0), "versao": v.get("versao", 1),
            "treinos": v.get("treinos", 0), "treinada": bool(v.get("treinada")), "repo": REPO_MOD if v.get("treinada") else None,
            "texto_ref": v.get("texto_ref", ""), "ref_wav": ref, "emocoes": emocoes}

def importar(c):
    vid = c["id"]
    try:
        TAREFA["msg"] = f"preparando a voz “{c.get('nome', '')}”…"
        if vid not in ler_vozes():
            if not c.get("ref_wav"):
                raise RuntimeError("o cartão está sem o áudio da voz")
            open(arq_ref(vid), "wb").write(base64.b64decode(c["ref_wav"]))
            emocoes = {}
            for eid, e in (c.get("emocoes") or {}).items():   # as emoções vêm junto no cartão
                if e.get("ref_wav") and re.fullmatch(r"[a-z0-9_]{2,30}", eid):
                    open(arq_emo(vid, eid), "wb").write(base64.b64decode(e["ref_wav"]))
                    emocoes[eid] = {k: x for k, x in e.items() if k != "ref_wav"}
                    emocoes[eid]["alts"] = 0
            treinada = False
            if c.get("treinada"):
                if hf:
                    TAREFA["msg"] = f"baixando o treino de “{c.get('nome', '')}” da nuvem (1–3 min)…"
                    try:
                        from huggingface_hub import hf_hub_download
                        hf_hub_download(repo_id=c.get("repo") or REPO_MOD, filename=f"t3_{vid}.pt", local_dir=MODELO, token=HF_TOKEN)
                        treinada = True
                    except Exception as e:
                        erro("baixar o treino da voz (vai usar só a voz de referência)", e)
                else:
                    erro("importar cartão", "a nuvem está desligada: a voz entra sem o treino, só com a voz de referência", "")
            agora = int(time.time())
            with LOCK_VOZES:
                vozes = ler_vozes()
                vozes[vid] = {"nome": c.get("nome") or "Voz importada", "foto": c.get("foto", ""), "criado": c.get("criado") or agora,
                              "atualizado": c.get("atualizado") or agora, "versao": c.get("versao", 1), "treinos": c.get("treinos", 0),
                              "treinada": treinada, "texto_ref": c.get("texto_ref", ""), "emocoes": emocoes}
                gravar_vozes(vozes)
            threading.Thread(target=backup, daemon=True).start()
        aplicar_voz(vid)
        log(f"Voz pronta para usar: {nome_voz(vid)}")
    except Exception as e:
        erro("preparar a voz do cartão", e)
    TAREFA["msg"] = ""

@app.post("/vozes/importar")
def vozes_importar(corpo: dict = Body(...)):
    c = corpo.get("cartao") or {}
    if c.get("tipo") != "tamaki-voz" or not c.get("id"):
        return falha("isso não é um cartão de voz")
    precisa_motor()
    if TAREFA["msg"]:
        return falha("espere a tarefa atual terminar", 409)
    if EMO["rodando"]:
        return falha("espere as emoções terminarem", 409)
    threading.Thread(target=importar, args=(c,), daemon=True).start()
    return {"ok": True}

@app.get("/vozes/{vid}/referencia")
def vozes_referencia(vid: str):
    return FileResponse(arq_ref(vid), media_type="audio/wav") if os.path.exists(arq_ref(vid)) else falha("sem áudio de referência", 404)

# ----- criar voz do nada -----
@app.post("/design")
def design(corpo: dict = Body(...)):
    if VD["rodando"]:
        return falha("já estou criando versões, espere", 409)
    if EMO["rodando"]:
        return falha("espere as emoções terminarem", 409)
    texto = (corpo.get("texto") or "").strip()
    if not texto:
        return falha("escreva a frase que a voz nova vai falar")
    n = max(1, min(8, int(corpo.get("quantidade", 4))))
    threading.Thread(target=job_design, args=((corpo.get("descricao") or "").strip(), texto, n), daemon=True).start()
    return {"ok": True}

@app.get("/design/{i}")
def design_audio(i: int):
    if not 0 <= i < len(VD["versoes"]):
        return falha("essa versão não existe mais", 404)
    return FileResponse(VD["versoes"][i], media_type="audio/wav")

# ----- falar -----
def pedacos(texto, maximo=250):
    partes, atual = [], ""
    for f in re.split(r"(?<=[.!?…])\s+", " ".join(texto.split())):
        if atual and len(atual) + len(f) > maximo:
            partes.append(atual); atual = f
        else:
            atual = (atual + " " + f).strip()
    return partes + ([atual] if atual else [])

def trechos_com_emocao(texto, inicial=""):
    """Separa o texto pelas marcas (brava), (triste)… Cada marca vale até a próxima. Devolve [(emoção ou None, trecho)]."""
    emos = emocoes_da(CONF["ativa"])
    atual = achar_emocao(inicial, emos)[0] if inicial else None
    saida, pos = [], 0
    for m in TAG.finditer(texto):
        eid, e_marca = achar_emocao(m.group(1), emos)
        if not e_marca:
            continue
        antes = texto[pos:m.start()]
        if antes.strip():
            saida.append((atual, antes))
        atual, pos = eid, m.end()
    resto = texto[pos:]
    if resto.strip():
        saida.append((atual, resto))
    return saida

@app.post("/falar")
def falar(corpo: dict = Body(...)):
    texto = (corpo.get("texto") or "").strip()[:1500]
    if not texto:
        return falha("escreva um texto")
    precisa_motor()
    vid, emos = CONF["ativa"], emocoes_da(CONF["ativa"])
    audios, sr, faltando, usadas = [], 24000, [], []
    k = 0
    for eid, trecho in trechos_com_emocao(texto, str(corpo.get("emocao") or "")):
        e = emos.get(eid) if eid else None
        if eid and (not e or not garantir_emo_conds(vid, eid, e)):
            faltando.append(eid); e = None
        if e:
            usadas.append(eid)
        for parte in pedacos(trecho):
            arq = f"{TMP}/fala_{k}.wav"; k += 1
            if e:   # a emoção decide a intensidade; "Emoção" dos ajustes soma um pouquinho por cima
                extra = float(corpo.get("exaggeration", CONF["exaggeration"])) - 0.5
                params = {"exaggeration": max(0.25, min(2.0, e["exag"] + 0.5 * extra)), "cfg_weight": e["cfg"], "temperature": e["temp"],
                          "conds": arq_emo_conds(vid, eid)}
            else:
                params = {p: float(corpo.get(p, CONF[p])) for p in ("exaggeration", "cfg_weight", "temperature")}
            # confere: ouve de volta e, se embolou, refaz (até 3 vezes, cada vez mais firme) e fica com a melhor
            melhor, nota_m = None, -1.0
            for tent in range(3 if corpo.get("conferir", True) else 1):
                p2 = dict(params)
                if tent:
                    p2["temperature"] = max(0.5, p2["temperature"] - 0.15 * tent); p2["cfg_weight"] = min(0.7, p2["cfg_weight"] + 0.1 * tent)
                alvo = f"{arq}.t{tent}.wav"
                motor("/falar", {"texto": parte, "saida": alvo, "padrao": bool(corpo.get("padrao")), **p2})
                if not corpo.get("conferir", True):
                    melhor = alvo; break
                try:
                    nota = parecido(transcrever(alvo), parte)
                except Exception as er:
                    erro("conferir a fala", er); melhor = alvo; break
                if nota > nota_m:
                    melhor, nota_m = alvo, nota
                if nota >= 0.85:
                    break
            shutil.move(melhor, arq)
            w, sr = sf.read(arq)
            audios += [np.asarray(w, dtype=np.float32), np.zeros(int(sr * .3), dtype=np.float32)]
    if not audios:
        return falha("só tinha marcas de emoção, sem texto para falar")
    wav = np.concatenate(audios[:-1])
    wav = 0.95 * wav / max(1e-6, float(np.abs(wav).max()))
    buf = io.BytesIO(); sf.write(buf, wav, sr, format="WAV")
    cab = {}
    if faltando:
        cab["X-Emocoes-Faltando"] = ",".join(dict.fromkeys(faltando))
    if usadas:
        cab["X-Emocoes-Usadas"] = ",".join(dict.fromkeys(usadas))
    return Response(buf.getvalue(), media_type="audio/wav", headers=cab)

# ----- emoções -----
@app.get("/emocoes")
def emocoes_get():
    return {"voz": CONF["ativa"], "lista": emocoes_publicas(CONF["ativa"])}

@app.post("/emocoes/treinar")
def emocoes_treinar(corpo: dict = Body(...)):
    """corpo: {ids: [...], sua: [{nome, emoji, texto}], ajustes: {id: {exag}}, versoes: 3}. Entra na fila; cada uma fica pronta sozinha."""
    precisa_motor()
    vid = CONF["ativa"]
    if vid == "padrao":
        return falha("escolha ou crie uma voz sua antes de treinar emoções", 409)
    if D["rodando"] or (W["info"] or {}).get("treino", {}).get("rodando"):
        return falha("espere as frases de treino ou o treino da voz terminarem", 409)
    if VD["rodando"]:
        return falha("espere o criador de vozes terminar", 409)
    n = max(1, min(5, int(corpo.get("versoes", 3))))
    emos, ajustes, novos = emocoes_da(vid), corpo.get("ajustes") or {}, []
    for s in corpo.get("sua") or []:
        nome = " ".join(str(s.get("nome", "")).split())[:24]
        texto = " ".join(str(s.get("texto", "")).split())[:400]
        if nome and len(texto) > 20:
            eid = slug_emo(nome)
            novos.append({"id": eid, "nome": nome, "emoji": str(s.get("emoji") or "🎭")[:4], "texto": texto,
                          "exag": float(s.get("exag", 0.8)), "cfg": 0.4, "temp": 0.8})
    for eid in corpo.get("ids") or []:
        base = CAT.get(eid) or emos.get(eid)
        if base:
            novos.append({"id": eid, **{k: base[k] for k in ("nome", "emoji", "texto", "exag", "cfg", "temp")}})
    if not novos:
        return falha("marque pelo menos uma emoção")
    na_fila = {x["id"] for x in EMO["fila"]} | ({EMO["atual"]} if EMO["atual"] else set())
    for it in novos:
        aj = ajustes.get(it["id"]) or {}
        if "exag" in aj:
            it["exag"] = max(0.25, min(2.0, float(aj["exag"])))
        if it["id"] in na_fila:
            continue
        it.update(voz=vid, versoes=n)
        EMO["fila"].append(it); EMO["passos"] += n
    if not EMO["rodando"]:
        EMO["passos"] = sum(x["versoes"] for x in EMO["fila"])
        threading.Thread(target=job_emocoes, daemon=True).start()
    log(f"Emoções na fila: {', '.join(x['nome'] for x in EMO['fila'])}")
    return {"ok": True, "fila": [x["id"] for x in EMO["fila"]]}

@app.post("/emocoes/parar")
def emocoes_parar():
    EMO["parar"] = True
    return {"ok": True}

@app.get("/emocoes/{eid}/audio")
def emocoes_audio(eid: str, alt: int = -1):
    arq = arq_emo(CONF["ativa"], eid, alt if alt >= 0 else None)
    return FileResponse(arq, media_type="audio/wav") if os.path.exists(arq) else falha("essa emoção ainda não tem áudio", 404)

@app.post("/emocoes/escolher")
def emocoes_escolher(corpo: dict = Body(...)):
    """Troca o exemplo da emoção por outra versão já gravada (a antiga vira a outra versão)."""
    precisa_motor(); ocupado_emocoes()
    vid, eid, alt = CONF["ativa"], str(corpo.get("id", "")), int(corpo.get("alt", 0))
    e = emocoes_da(vid).get(eid)
    if not e or not os.path.exists(arq_emo(vid, eid, alt)):
        return falha("essa versão não existe", 404)
    tmp = f"{TMP}/troca.wav"
    shutil.move(arq_emo(vid, eid), tmp); shutil.move(arq_emo(vid, eid, alt), arq_emo(vid, eid)); shutil.move(tmp, arq_emo(vid, eid, alt))
    motor("/conds", {"ref": arq_emo(vid, eid), "saida": arq_emo_conds(vid, eid), "exaggeration": e["exag"], "manter": True}, timeout=180)
    salvar_emocao(vid, eid, e, nota=None)
    return {"ok": True}

@app.post("/emocoes/ajustar")
def emocoes_ajustar(corpo: dict = Body(...)):
    vid, eid = CONF["ativa"], str(corpo.get("id", ""))
    e = emocoes_da(vid).get(eid)
    if not e:
        return falha("essa emoção ainda não foi treinada", 404)
    for k, (lo, hi) in {"exag": (0.25, 2.0), "cfg": (0.0, 1.0), "temp": (0.3, 1.5)}.items():
        if k in corpo:
            e[k] = max(lo, min(hi, float(corpo[k])))
    salvar_emocao(vid, eid, e)
    return {"ok": True}

@app.post("/emocoes/gravar")
def emocoes_gravar(arquivo: UploadFile = File(...), id: str = Form(""), nome: str = Form(""), emoji: str = Form("🎭"), texto: str = Form("")):
    """Usa uma gravação sua (ou de qualquer áudio) como exemplo da emoção. É o jeito que fica mais fiel."""
    precisa_motor(); ocupado_emocoes()
    vid = CONF["ativa"]
    if vid == "padrao":
        return falha("escolha ou crie uma voz sua antes", 409)
    base = CAT.get(id) or emocoes_da(vid).get(id)
    eid = id if base else slug_emo(nome)
    it = {"nome": (base or {}).get("nome") or nome.strip()[:24] or "Minha emoção", "emoji": (base or {}).get("emoji") or emoji[:4] or "🎭",
          "texto": texto.strip()[:400] or (base or {}).get("texto", ""), "exag": (base or {}).get("exag", 0.6),
          "cfg": (base or {}).get("cfg", 0.4), "temp": (base or {}).get("temp", 0.8)}
    tmp = f"{TMP}/emo_envio" + (os.path.splitext(arquivo.filename or "")[1] or ".wav")
    open(tmp, "wb").write(arquivo.file.read())
    wav, sr = librosa.load(tmp, sr=None, mono=True)
    wav, _ = librosa.effects.trim(wav, top_db=40)
    if len(wav) / sr < 4:
        return falha("a gravação está curta demais: grave de 8 a 15 segundos")
    if sr > 24000:
        wav, sr = librosa.resample(wav, orig_sr=sr, target_sr=24000), 24000
    for velha in glob.glob(f"{REFS}/{vid}__{eid}_alt*.wav"):
        os.remove(velha)
    sf.write(arq_emo(vid, eid), wav[: sr * 20], sr)
    motor("/conds", {"ref": arq_emo(vid, eid), "saida": arq_emo_conds(vid, eid), "exaggeration": it["exag"], "manter": True}, timeout=180)
    salvar_emocao(vid, eid, it, nota=None, alts=0, origem="gravada")
    log(f"Emoção com gravação sua: {it['emoji']} {it['nome']}")
    return {"ok": True, "id": eid}

@app.post("/emocoes/apagar")
def emocoes_apagar(corpo: dict = Body(...)):
    ocupado_emocoes()
    vid, eid = CONF["ativa"], str(corpo.get("id", ""))
    with LOCK_VOZES:
        vozes = ler_vozes()
        if eid not in vozes.get(vid, {}).get("emocoes", {}):
            return falha("essa emoção não existe", 404)
        vozes[vid]["emocoes"].pop(eid); vozes[vid]["atualizado"] = int(time.time())
        gravar_vozes(vozes)
    for arq in glob.glob(f"{REFS}/{vid}__{eid}.*") + glob.glob(f"{REFS}/{vid}__{eid}_alt*"):
        os.remove(arq)
    threading.Thread(target=backup, daemon=True).start()
    return {"ok": True}

# ----- frases de treino -----
@app.post("/dataset/iniciar")
def dataset_iniciar():
    if (W["info"] or {}).get("treino", {}).get("rodando"):
        return falha("espere o treino terminar", 409)
    if EMO["rodando"]:
        return falha("espere as emoções terminarem", 409)
    if CONF["ativa"] == "padrao":
        return falha("escolha ou crie uma voz sua antes de gerar as frases", 409)
    if contar() and voz_do_dataset() not in (None, CONF["ativa"]):
        return falha(f"as frases que já existem são da voz “{nome_voz(voz_do_dataset())}”: apague-as ou volte para ela", 409)
    if not D["rodando"]:
        threading.Thread(target=gerar_dataset, daemon=True).start()
    return {"ok": True}

@app.post("/dataset/parar")
def dataset_parar():
    D["parar"] = True
    return {"ok": True}

@app.post("/dataset/limpar")
def dataset_limpar():
    D["parar"] = True
    while D["rodando"]:
        time.sleep(1)
    for f in glob.glob(f"{WAVS}/*.wav"):
        os.remove(f)
    if os.path.exists(DSINFO):
        os.remove(DSINFO)
    escrever_metadata(); D["amostra"] = None
    threading.Thread(target=backup, daemon=True).start()
    log("Frases geradas apagadas")
    return {"ok": True}

@app.get("/dataset/amostra")
def dataset_amostra():
    if D["amostra"] is None or not os.path.exists(f"{WAVS}/{nome_arq(D['amostra'])}.wav"):
        return falha("nenhuma frase gerada ainda", 404)
    return FileResponse(f"{WAVS}/{nome_arq(D['amostra'])}.wav", media_type="audio/wav")

@app.get("/dataset/baixar")
def dataset_baixar():
    escrever_metadata()
    arq = shutil.make_archive(f"{TMP}/{NOME}_dataset", "zip", DS)
    return FileResponse(arq, filename=f"{NOME}_dataset_br.zip")

@app.post("/dataset/coraa")
def dataset_coraa(corpo: dict = Body({})):
    """Baixa trechos de conversa real do CORAA e usa como frases de treino da voz em uso."""
    if CONF["ativa"] == "padrao":
        return falha("escolha ou crie uma voz sua antes", 409)
    if CO["rodando"]:
        return falha("já estou baixando as conversas", 409)
    if (W["info"] or {}).get("treino", {}).get("rodando") or EMO["rodando"]:
        return falha("espere o treino ou as emoções terminarem", 409)
    D["parar"] = True
    while D["rodando"]:
        time.sleep(1)
    qtd = max(50, min(1500, int(corpo.get("qtd", 600))))
    threading.Thread(target=job_coraa, args=(qtd,), daemon=True).start()
    return {"ok": True}

@app.post("/dataset/coraa/parar")
def dataset_coraa_parar():
    CO["parar"] = True
    return {"ok": True}

@app.post("/dataset/zip")
def dataset_zip(arquivo: UploadFile = File(...)):
    """Suas próprias frases: zip com metadata.csv (arquivo|texto) e a pasta wavs/. Ficam valendo para a voz em uso."""
    D["parar"] = True
    while D["rodando"]:
        time.sleep(1)
    tmp = f"{TMP}/envio.zip"
    open(tmp, "wb").write(arquivo.file.read())
    pasta = f"{TMP}/zip"; shutil.rmtree(pasta, ignore_errors=True)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(pasta)
    meta = glob.glob(f"{pasta}/**/metadata.csv", recursive=True)
    if not meta:
        return falha("o zip precisa ter um metadata.csv (arquivo|texto) e a pasta wavs")
    raiz_zip = os.path.dirname(meta[0])
    for f in glob.glob(f"{WAVS}/*.wav"):
        os.remove(f)
    frases = []
    for linha in open(meta[0], encoding="utf-8"):
        if "|" not in linha:
            continue
        arq, texto = linha.rstrip("\n").split("|")[:2]
        origem = f"{raiz_zip}/wavs/{arq}" + ("" if arq.endswith(".wav") else ".wav")
        if os.path.exists(origem):
            shutil.copy(origem, f"{WAVS}/{nome_arq(len(frases))}.wav"); frases.append(texto.strip())
    open(f"{DS}/frases.txt", "w", encoding="utf-8").write("\n".join(frases))
    json.dump({"voz": CONF["ativa"]}, open(DSINFO, "w"))
    CONF["quantidade"] = max(20, len(frases)); gravar_cfg(); escrever_metadata()
    threading.Thread(target=backup, daemon=True).start()
    log(f"Frases recebidas: {len(frases)}")
    return {"ok": True, "feitas": len(frases)}

# ----- treino -----
@app.post("/treino/iniciar")
def treino_iniciar(corpo: dict = Body({})):
    """corpo: {epocas, destino: "atualizar" | "nova", nome, foto}"""
    precisa_motor()
    ativa = CONF["ativa"]
    if ativa == "padrao":
        return falha("escolha ou crie uma voz sua antes de treinar", 409)
    if contar() < 20:
        return falha("gere ou envie pelo menos 20 frases antes de treinar", 409)
    if voz_do_dataset() not in (None, ativa):
        return falha(f"as frases são da voz “{nome_voz(voz_do_dataset())}”: volte para ela ou apague as frases", 409)
    if (W["info"] or {}).get("treino", {}).get("rodando"):
        return falha("já está treinando", 409)
    if CO["rodando"]:
        return falha("espere as conversas terminarem de baixar", 409)
    if EMO["rodando"]:
        return falha("espere as emoções terminarem", 409)
    D["parar"] = True
    while D["rodando"]:
        time.sleep(1)
    escrever_metadata(); liberar_design()
    if "epocas" in corpo:
        CONF["epocas"] = max(1, min(20, int(corpo["epocas"]))); gravar_cfg()
    nova = corpo.get("destino") == "nova"
    destino = novo_id() if nova else ativa
    garantir_conds(ativa)
    saida = f"{MODELO}/treinando_{destino}.pt"
    TREINO["pendente"] = {"destino": destino, "nova": nova, "origem": ativa, "saida": saida,
                          "nome": " ".join(str(corpo.get("nome", "")).split())[:60], "foto": str(corpo.get("foto") or "")[:400_000]}
    motor("/treinar", {"pasta": DS, "epocas": CONF["epocas"], "lr": 1e-5, "saida": saida, "conds": arq_conds(ativa),
                       "t3_inicio": arq_t3(ativa) if os.path.exists(arq_t3(ativa)) and not corpo.get("do_zero") else None})
    log(f"Treino começou ({CONF['epocas']} voltas, {contar()} frases) · " + ("vai virar uma voz nova" if nova else f"vai atualizar “{nome_voz(ativa)}”"))
    return {"ok": True}

@app.post("/treino/parar")
def treino_parar():
    motor("/parar_treino")
    return {"ok": True}

@app.post("/erros/limpar")
def erros_limpar():
    ERROS.clear()
    return {"ok": True}

PORTA = 8000
threading.Thread(target=uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=PORTA, log_level="warning")).run, daemon=True).start()
log(f"Servidor ligado na porta {PORTA}")

# ---------- 10. link público (Cloudflare) e aviso ao HTML (ntfy) ----------
T = {"proc": None, "url": None, "falhas": 0}

def avisar_html(estado="ligado"):
    try:
        corpo = json.dumps({"url": T["url"], "estado": estado, "fim": int(FIM)}).encode()
        urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{CODIGO}", data=corpo, method="POST"), timeout=20)
    except Exception as e:
        erro("avisar o HTML (ntfy)", e)

def abrir_tunel():
    try:
        cf = "/tmp/cloudflared"
        if not os.path.exists(cf):
            urllib.request.urlretrieve("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", cf)
            os.chmod(cf, 0o755)
        if T["proc"] and T["proc"].poll() is None:
            T["proc"].kill()
        registro = "/tmp/cloudflared.log"
        T["proc"] = subprocess.Popen([cf, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{PORTA}"],
                                     stdout=open(registro, "w"), stderr=subprocess.STDOUT)
        for _ in range(90):
            time.sleep(1)
            achado = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", open(registro).read())
            if achado:
                T["url"], T["falhas"] = achado.group(0), 0
                log("Link: " + T["url"]); avisar_html(); return
        raise RuntimeError("o Cloudflare não deu link em 90 s")
    except Exception as e:
        erro("abrir o link público", e)

def tunel_ok():
    if not T["url"] or not T["proc"] or T["proc"].poll() is not None:
        return False
    try:
        urllib.request.urlopen(T["url"] + "/", timeout=20); T["falhas"] = 0
    except Exception:
        T["falhas"] += 1
    return T["falhas"] < 3

# ---------- 11. começar e manter vivo ----------
abrir_tunel()
restaurar_nuvem()
migrar()
threading.Thread(target=preparar_motor, daemon=True).start()
threading.Thread(target=vigiar_motor, daemon=True).start()
print(f"\n✅ Pronto! Código de ligação: {CODIGO}\n   Abra o HTML: ele acha o link sozinho.\n", flush=True)

ultimo = 0
while time.time() < FIM:
    time.sleep(30)
    try:
        if not tunel_ok():
            log("Link caiu, abrindo outro…"); abrir_tunel()
        if time.time() - ultimo > 300:
            ultimo = time.time()
            log(f"Vivo · motor {W['estado']} · frases {contar()} · faltam {int((FIM - time.time()) / 60)} min")
    except Exception as e:
        erro("manter vivo", e)

D["parar"] = True
EMO["parar"] = True
try:
    motor("/parar_treino", timeout=10)
except Exception:
    pass
while D["rodando"] or EMO["rodando"]:
    time.sleep(2)
escrever_metadata(); backup(True)
avisar_html("encerrado")
log("Sessão no fim: tudo salvo. Rode de novo (Save & Run All) para continuar.")
