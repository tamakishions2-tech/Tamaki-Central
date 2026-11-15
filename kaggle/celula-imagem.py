# ============================================================
#  TAMAKI · GERADOR DE IMAGEM — célula do Kaggle (cole só isto, uma vez)
#  A cada "Save & Run All" ela baixa a versão mais nova do gerador do GitHub.
#  Você não precisa mais colar código: as melhorias do Claude entram sozinhas.
#  Settings: Accelerator = GPU T4 x2 · Internet = On · Secrets: HF_TOKEN ligado.
# ============================================================
CODIGO = "tamaki-img-COLE-SEU-CODIGO"   # o mesmo do campo "Código de ligação" do Estúdio de imagem (não compartilhe)
HORAS = 3            # quanto tempo fica ligado
SATURACAO = 1.12     # cor mais viva (1 = sem realce)
CONTRASTE = 1.04
COR_TREINO = 1.18

import urllib.request, time
URL = "https://raw.githubusercontent.com/tamakishions2-tech/Tamaki-Central/main/kaggle/tamaki_imagem_kaggle.py"
for tentativa in range(5):
    try:
        codigo_gerador = urllib.request.urlopen(f"{URL}?v={int(time.time())}", timeout=60).read().decode("utf-8")
        break
    except Exception as e:
        print("Tentando baixar o gerador de novo…", e); time.sleep(10)
else:
    raise SystemExit("Não consegui baixar o gerador do GitHub. Confira se a Internet do notebook está ligada.")
exec(compile(codigo_gerador, "tamaki_imagem_kaggle.py", "exec"))
