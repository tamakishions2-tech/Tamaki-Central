# Tamaki Central · notas para o Claude

## O Estúdio (`estudio.html`)
Página com as abas Biblioteca, Editor, Efeitos, Voz, Motion, ✦ Claude e ⚠ Erros. Ela também fica colada como aba na Central.

## "Pedido pro Claude" (PDF do Estúdio › ✦ Claude › Pedir edição)
Quando chegar um PDF chamado `claude-<projeto>.pdf` com o título "Pedido pro Claude · Tamaki Central",
é um pedido de edição de vídeo. Responda sempre com um **.zip** (ou .json) no formato que o Estúdio recebe
em ✦ Claude › Respostas e prévia › Receber resposta. Não responda com receita do Editor.

- Os dados do pedido estão dentro do PDF, em base64 no campo `/TamakiPedido` do Info
  (`video.id`, `video.dur`, `quadros.intervalo`, `roteiro`). As folhas de quadros mostram o tempo no canto.
- Uma resposta por arquivo .json:
```json
{"tamaki":"resposta-claude","versao":1,"projeto":"<nome único>","video":"<video.id do pedido>",
 "formato":"9:16","crop":{"l":0,"t":0,"r":0,"b":0},"notas":"texto curto para ela",
 "cortes":[{"ini":12.0,"fim":15.5,"fala":"trecho narrado","nota":"emoção · estilo","vel":1,"fx":"kenburns","crop":{"l":0,"t":0,"r":0,"b":0}}],
 "motions":[{"nome":"…","papel":"titulo|impacto|personagem|nome|aviso|transicao|batalha|vida|captura|fala|final","texto":"…","sub":"…","dur":2.5,"fmt":"9:16","onde":"quando entra"}]}
```
- Em cada motion, diga o tempo com `"corte": N` (1 = primeiro corte; conta só os cortes marcados) e, se quiser, `"atraso": 0.5` (segundos depois do começo do corte). Sem `corte`, use `"ini"` (segundos no vídeo editado). O título vai no corte 1 e o `final` entra sozinho no fim. Assim "🎬 Mandar tudo pro Editor" põe cada motion no tempo certo, como camada.
- `fx` aceitos ao mandar pro Editor: none, kenburns, pulse, heart, shake, sway, blurin, flash, glitch.
- Respostas com o mesmo `projeto` e `video` se substituem: dê um nome diferente para cada parte.
- Vários Shorts: um .json por parte dentro do .zip (sem compressão). Pode juntar os roteiros em .txt.
- Roteiro para a narração (aba Voz › Falas): uma fala por linha, com a emoção em cada linha, ex.: `(brava) Chamei ele na chincha!`.
- Gameplay gravada no tablet (XRecorder 1152×720): a tela do jogo fica em crop l .215, r .045, t .1, b .1.
- Personagem: palavrões da Tamaki são suavizados; manter o jeito de falar dela (guris, bicha, é bica).
- A usuária usa ".." no lugar de "?" (o teclado dela não tem): troque por "?" nas perguntas.

## Pacote (mudanças nos arquivos do repositório)
A Central salva direto no GitHub (⋮ › 🐙 GitHub). Para mudar arquivos deste repositório, entregue um **pacote**:
um arquivo `.json` (pode ser grande) que ela aplica num commit só, mostrando antes o que muda.
```json
{"tamaki":"pacote","versao":1,"mensagem":"o que mudou, curto",
 "arquivos":[{"caminho":"motion.html","texto":"arquivo completo"},{"caminho":"img/x.png","base64":"..."}],
 "apagar":["arquivo-velho.html"]}
```
- Caminhos relativos a este repositório. Nunca mande nada para `universo` ou `Tamaki_Personagem`.
- Sempre o arquivo completo em `texto` (não é patch). `apagar` é opcional.
- Ele cola o pacote em ⋮ › 🐙 GitHub › Pacote do Claude, ou em Reunião › Colar resposta do Claude (a Central reconhece sozinha).

## Biblioteca automática (`organizador.js`)
Carregado pela Central e pela Biblioteca. Toda vez que algo entra no IndexedDB `tamaki-biblioteca` (aviso `{novo:id}` no BroadcastChannel do mesmo nome), ele dá nome claro aos genéricos, etiqueta emoções das falas, marca `#repetido` e põe na pasta do "vídeo em andamento".
Configuração em localStorage `tamaki-bib-auto` (`ligado`, `pasta`, `desde`, `renomear`, `emocoes`, `repetidos`). Itens arrumados ganham `auto:1`; nome trocado à mão ganha `nomeManual:1`. Abas novas que guardarem na Biblioteca só precisam mandar `{novo:id}`.

## Linha de produção (`producao.js`)
Aba Escrita › nota em Roteiros da Tamaki › 🎬 Vídeo (ou ao salvar um roteiro novo/mudado, ela pergunta).
Roteiro: uma fala por linha, `[m:ss] (emoção, tom) texto`; linhas com `#` são anotação. Gera cada fala no Estúdio de voz (mesmo `tvz_codigo`/ntfy),
guarda na Biblioteca na pasta do vídeo em andamento (ou cria uma com o título), e manda `{tipo:"montar"}` no BroadcastChannel `tamaki-editor`:
o Editor (`montarRoteiro`) põe as falas em sequência, o gameplay da pasta por baixo (volume baixo, crop do XRecorder), título no começo e "Até a próxima!" no fim.
A Central abre abas a pedido: `parent.postMessage({central:"abrir", aba:"editor", fica:true})` (`fica` carrega sem trocar de aba).

### Tom das falas (o Claude escolhe por linha)
Dentro dos parênteses, depois da emoção, separado por vírgula: `(brava, forte, rápida, pausa) Chamei ele na chincha!`
- intensidade: `suave` · `normal` · `forte` · `exagerada` (exaggeration .35 / .6 / .85 / 1.2)
- ritmo: `lenta` · `calma` · `rápida` (cfg_weight .3 / .35 / .7)
- jeito: `firme` (sempre igual, temperature .6) · `solta` (mais variada, 1.0)
- silêncio depois: `pausa` (.9 s) · `pausa longa` (1.6 s) · `sem pausa` (.1 s); padrão .35 s
- números exatos (com ponto): `exag=1.1`, `cfg=.4`, `temp=.9`, `pausa=1.2`
Cena do gameplay: `[6:24]` no começo da linha (antes dos parênteses) faz o vídeo de fundo pular para esse momento quando a fala entra; sem marca, ele continua de onde estava. Use os tempos das folhas de quadros do PDF do pedido.
Sem tom, vale o padrão "vivo" (exaggeration ≥ .65, cfg_weight ≤ .42, temperature ≥ .9), porque o padrão do Estúdio soava robótico. Ao escrever roteiros a partir de um vídeo, use o tom para dar ritmo: falas de impacto `forte`, piadas com `pausa` antes da resposta, cochichos `suave, lenta`.

### Montagem estilo Shorts (`montarRoteiro` no editor.html)
Regras aplicadas sozinhas: sem abertura parada (a primeira fala entra em 0,2 s; o título é um texto no topo por cima da ação); jogo inteiro com fundo desfocado no 9:16;
corte a cada ~2,4 s dentro da fala com zoom alternado (1,06 / 1,28); efeito curto no começo da fala pela emoção (brava/assustada = shake, animada/feliz/rindo = pulse, forte = flash);
legendas de 2–3 palavras no terço de baixo (y .26), amarelas quando a fala é forte, tem MAIÚSCULAS ou "!". Sem cartão de "Até a próxima" (só se o link trouxer `final`).
Ao escrever o roteiro (você é o editor e criador dos Shorts dela):
- A 1ª fala é o gancho: o momento mais surpreendente ou a pergunta/promessa, com a cena do clímax (`[11:48]`), não o começo do jogo.
- 15–40 s, 6–10 falas curtas (até ~12 palavras), cada uma com a cena exata em que aquilo acontece no vídeo; uma ideia por fala.
- Arco: gancho → contexto rápido → escalada → virada → reação; a última fala puxa de volta pro gancho (loop).
- Ênfase em MAIÚSCULAS em 1 palavra por fala no máximo. Link `#roteiro=` em base64url de `{titulo, texto, pasta, video, final}`.

### Layout do Tama (`montarLayoutPalco`, padrão da linha de produção)
9:16 em 720×1280: em cima (0–520) a cena gravada do Palco (a Tamaki falando, sem o balão do Palco); no meio (530–780) caixa de diálogo preta com borda branca dupla e o texto da fala digitando em Press Start 2P; embaixo (800–1280) a tela do jogo inteira (crop só das bordas do XRecorder), sem zoom.
Som: só as falas. O áudio da gravação do jogo é mudo (é um vídeo que ele assiste de fundo). A Central abre a aba Palco, injeta `palco-gravar.js` (`window.__tamakiGravar({ids, textos, pausas, ini, semBalao})` → `{id, dur}`) e o Palco toca as falas e grava a cena; O palco.html do repositório é a versão do Tama (Ator, Luz, Partículas) com `window.__tamakiGravar` dentro do IIFE (o código do Palco é todo fechado num `(() => {…})()`, então injetar de fora não enxerga nada). Se a aba Palco estiver com código guardado no aparelho sem o gravador, a Central oferece trocar pela versão do GitHub. Ao mudar o Palco, mantenha o bloco do gravador no fim do IIFE. O Palco precisa estar na tela enquanto grava.
Futuro: poses/expressões da Tamaki por emoção no Palco (por enquanto só parada/falando/falando2).

### Close, intro e finalização
`[close]` no começo da linha (no lugar do tempo) põe a câmera perto do rosto da Tamaki, com a cena do Palco na tela toda e legenda grande; a próxima fala sem `[close]` volta pro layout padrão (com um flash).
Use `[close]` na 1ª fala (o gancho) e na última (a chamada). O link aceita `final` (faixa no topo, ex.: "Segue pra ver a vingança do Bulba!") e `redes` (linha amarela embaixo, ex.: "@tamakishion no YT e no Insta").
Ajuste fino do close, se precisar: `closeAjuste:{s,x,y}` no montar (padrão s 1.15, y .07).

### Como escrever o roteiro (estudo: estrutura de Shorts, timing de comédia, finalização)
- **Gancho (0–3 s):** uma frase só, em close, que promete algo específico ou mostra o absurdo ("Hoje eu vou te mostrar como perder pra um RATTATA"). Nada de "oi gente".
- **Ponte (1 fala):** contexto mínimo para quem não conhece o jogo.
- **Corpo:** mudança visual a cada 3–5 s (cada fala = uma cena); nunca mais de 8 s de fala sem trocar de cena. Use "mas"/"aí" entre as falas (causa e virada), não "e depois".
- **Piada = preparação + pausa + punchline.** A preparação cria a expectativa, um `pausa` (0,6–1 s) segura, o punchline é curto e vem por último na frase (a palavra engraçada no fim). Regra de três: duas iguais e a terceira quebra. Depois do punchline, `pausa` pra respirar antes da próxima preparação.
- **Virada/payoff nos últimos 10–20%:** entrega exatamente o que o gancho prometeu.
- **Final (2–4 s, em close):** um pedido só e ligado ao vídeo ("segue pra ver a vingança do Bulba"), sempre depois do payoff. A última frase deve poder emendar na primeira (loop). Só prometa parte 2 se ela vai existir.
- 20–40 s no total (~2,5 palavras por segundo → 50–100 palavras).

### Séries de roteiros (`roteiros/`)
Só depois que o Tama aprovar o roteiro na conversa (a reunião é no chat: o Claude escreve o roteiro na própria mensagem, em texto bom de ouvir — ele escuta as mensagens com o áudio do app —, um episódio por vez, com as falas numeradas; eles ajustam e só então vai pra Central). Para uma série aprovada, salve `roteiros/<nome>.json` = `{"serie", "episodios":[{titulo, texto, pasta, video, final, redes}]}` e acrescente `{arquivo, nome}` em `roteiros/indice.json` (a mais nova por último). Aparece em ⋮ › 🎬 Produção › Roteiros prontos, com 🎬 por episódio e 🎬 Todos (um depois do outro na mesma linha do tempo, para ele cortar depois).
Tom das séries de gameplay: **diário em call com os amigos** — a Tamaki conta o que aconteceu ("Gente, …"), título "Diário da Tamaki #N · …", gancho e chamada em `[close]`, e a chamada final aponta para o próximo episódio.

## Voz da Tamaki: naturalidade
- O código do Kaggle fica em `kaggle/tamaki_estudio_voz_kaggle.py` (versão 4). Ao mudar, mande o arquivo pro Tama colar na célula (Save & Run All) e suba a versão em `/status`.
- O treino só ajusta o T3 do Chatterbox (texto → códigos de fala); o timbre vem da referência (conds). Por isso treinar com fala de outras pessoas muda o ritmo, não o timbre.
- Não treinar a voz com frases faladas por ela mesma (Treinar › Gerar frases): é cópia de cópia e deixa a voz metálica.
- Estúdio de voz › Treinar › 🗣️ Baixar conversas reais: `/dataset/coraa` baixa a parte dev do CORAA v1.1 (gabrielrstan/CORAA-v1.1, 1,3 GB), pega só falas espontâneas sem ruído/hesitação, de preferência de SP, e põe como frases de treino. Depois: treinar como voz nova com "Começar do português original" (`do_zero`). O Tama liberou o uso.
- O pajubá e os trejeitos vêm do roteiro, não do treino.
