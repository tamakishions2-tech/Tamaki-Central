# Tamaki · Central

App que junta todos os projetos, um por aba, sem rolar a página.

| Aba | De onde vem |
|---|---|
| Universo | Site que já existe: `/universo/` |
| Tamaki | Site que já existe: `/Tamaki_Personagem/` |
| Escrita, Novel, Jogos | Pastas dentro deste repositório (`projetos/`) |
| Reunião | Junta Universo, Ficha da Tamaki, Biblioteca de Escrita e visual novel numa nota só |

## Ilustrar (GPU grátis do Kaggle)

A aba **Ilustrar** (`ilustrar.html`) gera ilustrações num servidor só seu, rodando num notebook do Kaggle.

1. No Kaggle, verifique o celular (sem isso não há GPU nem internet).
2. Crie um notebook e importe `kaggle/ilustrador_kaggle.ipynb` (ou cole `kaggle/servidor_ilustracoes.py` numa célula).
3. Settings: **Accelerator = GPU T4 x2**, **Internet = On**. Rode a célula.
4. Clique em **▶ Abrir o Ilustrador já conectado**. O endereço e a senha já vêm preenchidos.
5. Ao terminar, **Stop session** (cota grátis de cerca de 30 h de GPU por semana).

O modelo padrão é o Animagine XL 4.0 (anime); dá para trocar na linha `MODELO` por qualquer modelo SDXL do Hugging Face. A senha muda a cada sessão; para fixá-la, crie um Secret `SENHA_ILUSTRA` no notebook. As imagens ficam guardadas no aparelho (IndexedDB `tamaki-ilustrar`) e podem ir para a Biblioteca ou o Editor.

## Como publicar

1. Na conta **tamakishions2-tech**, crie um repositório novo (por exemplo `central`). Não crie uma conta nova.
2. Envie o conteúdo desta pasta, com o `index.html` na raiz.
3. Em Settings > Pages, escolha a branch principal e a pasta raiz.
4. Abra `https://tamakishions2-tech.github.io/central/` e instale pelo menu do navegador ("Adicionar à tela inicial").

Os repositórios `universo` e `Tamaki_Personagem` continuam como estão, com os mesmos nomes (maiúsculas e minúsculas contam). Quando você atualiza um deles, a central já mostra a versão nova.

## Por que na mesma conta

O navegador guarda os dados por endereço (`tamakishions2-tech.github.io`). Na mesma conta, a central enxerga e edita os mesmos dados dos outros sites. Numa conta nova, ela começaria vazia.

## Ainda faltam

- Biblioteca de Escrita: `service-worker.js` (sem ele, não funciona offline).
- Ícones originais do emulador.
