# ============================================================
#  TAMAKI · ESTÚDIO DE VOZ BR — célula do Kaggle (cole só isto, uma vez)
#  A cada "Save & Run All", ela baixa a versão mais nova do Estúdio de voz do GitHub.
#  Você nunca mais precisa colar código: as atualizações do Claude entram sozinhas.
#  Settings: Accelerator = GPU T4 x2 · Internet = On · Secrets: HF_TOKEN ligado.
# ============================================================
CODIGO = "tamaki-COLE-SEU-CODIGO-AQUI"   # o mesmo da aba Kaggle do Estúdio de voz (não compartilhe)

import urllib.request, time
URL = "https://raw.githubusercontent.com/tamakishions2-tech/Tamaki-Central/main/kaggle/tamaki_estudio_voz_kaggle.py"
for tentativa in range(5):
    try:
        codigo_estudio = urllib.request.urlopen(f"{URL}?v={int(time.time())}", timeout=60).read().decode("utf-8")
        break
    except Exception as e:
        print("Tentando baixar o Estúdio de voz de novo…", e); time.sleep(10)
else:
    raise SystemExit("Não consegui baixar o Estúdio de voz do GitHub. Confira se a Internet do notebook está ligada.")
exec(compile(codigo_estudio, "tamaki_estudio_voz_kaggle.py", "exec"))
