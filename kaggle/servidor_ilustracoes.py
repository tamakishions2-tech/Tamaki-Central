# ============================================================
#  Tamaki · Servidor de ilustrações no Kaggle (GPU grátis)
#  Cole tudo numa célula de um notebook do Kaggle e rode.
#  Antes: Settings > Accelerator = "GPU T4 x2"  e  Internet = On.
# ============================================================

# ---------- Ajustes ----------
MODELO = "cagliostrolab/animagine-xl-4.0"   # anime. Outros SDXL: "stabilityai/stable-diffusion-xl-base-1.0"
SENHA = ""          # vazio = cria uma senha nova a cada sessão
PAGINA = "https://tamakishions2-tech.github.io/Tamaki-Central/ilustrar.html"
# -----------------------------

import subprocess, sys, os, re, time, threading, secrets, base64, io, uuid
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "diffusers", "transformers", "accelerate", "fastapi", "uvicorn"], check=True)
if not os.path.exists("/kaggle/working/cloudflared"):
    subprocess.run(["wget", "-q", "-O", "/kaggle/working/cloudflared",
                    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"], check=True)
    os.chmod("/kaggle/working/cloudflared", 0o755)

import torch
from diffusers import StableDiffusionXLPipeline, AutoencoderKL, EulerAncestralDiscreteScheduler
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

if not SENHA:
    try:
        from kaggle_secrets import UserSecretsClient
        SENHA = UserSecretsClient().get_secret("SENHA_ILUSTRA")   # opcional: Add-ons > Secrets
    except Exception:
        SENHA = secrets.token_urlsafe(12)

n_gpu = torch.cuda.device_count()
assert n_gpu, "Sem GPU: em Settings > Accelerator escolha GPU T4 x2."
print(f"Carregando {MODELO} em {n_gpu} GPU(s)... (a primeira vez demora uns minutos)")
PIPES = []
for i in range(n_gpu):
    # VAE "fp16-fix": evita imagens pretas em meia precisão
    vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
    p = StableDiffusionXLPipeline.from_pretrained(MODELO, vae=vae, torch_dtype=torch.float16, use_safetensors=True)
    p.scheduler = EulerAncestralDiscreteScheduler.from_config(p.scheduler.config)
    p.to(f"cuda:{i}"); p.set_progress_bar_config(disable=True)
    PIPES.append((p, threading.Lock()))

TAREFAS = {}            # id -> {estado, feitas, total, imagens, erro}
FILA = threading.Lock() # uma tarefa por vez (cada uma já usa todas as GPUs)

class Pedido(BaseModel):
    prompt: str
    negativo: str = ""
    largura: int = 832
    altura: int = 1216
    passos: int = 28
    cfg: float = 5.0
    semente: int = -1
    quantidade: int = 2

def gerar_uma(idx, ped, semente, tarefa):
    pipe, trava = PIPES[idx % len(PIPES)]
    with trava:
        g = torch.Generator(device=pipe.device).manual_seed(semente)
        img = pipe(prompt=ped.prompt, negative_prompt=ped.negativo or None,
                   width=ped.largura, height=ped.altura, num_inference_steps=ped.passos,
                   guidance_scale=ped.cfg, generator=g).images[0]
    buf = io.BytesIO(); img.save(buf, "PNG")
    tarefa["imagens"][idx] = {"png": base64.b64encode(buf.getvalue()).decode(), "semente": semente}
    tarefa["feitas"] += 1

def rodar(tid, ped):
    t = TAREFAS[tid]
    with FILA:
        t["estado"] = "gerando"
        try:
            base = ped.semente if ped.semente >= 0 else secrets.randbelow(2**31)
            fios = [threading.Thread(target=gerar_uma, args=(i, ped, base + i, t)) for i in range(ped.quantidade)]
            for f in fios: f.start()
            for f in fios: f.join()
            if t["feitas"] < ped.quantidade: raise RuntimeError("alguma imagem falhou (veja o log do Kaggle)")
            t["estado"] = "pronto"
        except Exception as e:
            t["estado"], t["erro"] = "erro", str(e)
        torch.cuda.empty_cache()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def conferir(senha):
    if not secrets.compare_digest(senha or "", SENHA):
        raise HTTPException(401, "senha errada")

@app.get("/status")
def status(x_senha: str = Header(None)):
    conferir(x_senha)
    return {"ok": True, "modelo": MODELO, "gpus": [torch.cuda.get_device_name(i) for i in range(n_gpu)],
            "ocupado": FILA.locked()}

@app.post("/gerar")
def gerar(ped: Pedido, x_senha: str = Header(None)):
    conferir(x_senha)
    ped.quantidade = max(1, min(ped.quantidade, 4))
    ped.passos = max(1, min(ped.passos, 60))
    ped.largura = max(512, min(ped.largura, 1536)) // 8 * 8
    ped.altura = max(512, min(ped.altura, 1536)) // 8 * 8
    tid = uuid.uuid4().hex[:10]
    TAREFAS[tid] = {"estado": "na fila", "feitas": 0, "total": ped.quantidade,
                    "imagens": [None] * ped.quantidade, "erro": None, "criada": time.time()}
    for k in [k for k, v in TAREFAS.items() if time.time() - v["criada"] > 3600]: TAREFAS.pop(k, None)
    threading.Thread(target=rodar, args=(tid, ped), daemon=True).start()
    return {"id": tid}

@app.get("/tarefa/{tid}")
def tarefa(tid: str, x_senha: str = Header(None)):
    conferir(x_senha)
    t = TAREFAS.get(tid)
    if not t: raise HTTPException(404, "tarefa não encontrada")
    r = {k: t[k] for k in ("estado", "feitas", "total", "erro")}
    if t["estado"] == "pronto": r["imagens"] = t["imagens"]
    return r

threading.Thread(target=uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")).run,
                 daemon=True).start()

# Túnel grátis da Cloudflare (não precisa de conta): gera um endereço https público
tunel = subprocess.Popen(["/kaggle/working/cloudflared", "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8000"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
url = None
for linha in tunel.stdout:
    m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", linha)
    if m: url = m.group(0); break
# continua lendo o log do túnel em segundo plano (senão ele trava quando o buffer enche)
threading.Thread(target=lambda: [None for _ in tunel.stdout], daemon=True).start()

from urllib.parse import quote
from IPython.display import display, HTML
link = f"{PAGINA}#url={quote(url)}&senha={quote(SENHA)}"
print("Endereço:", url, "\nSenha:   ", SENHA)
display(HTML(f'<h2><a href="{link}" target="_blank">▶ Abrir o Ilustrador já conectado</a></h2>'
             '<p>Deixe esta aba do Kaggle aberta enquanto desenha. Quando terminar, clique em '
             '<b>Stop session</b> para não gastar sua cota de GPU.</p>'))
