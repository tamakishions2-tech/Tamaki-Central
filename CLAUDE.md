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
- Caminhos relativos a este repositório. Nunca mande nada para `universo`. O `Tamaki_Personagem` (aba Tamaki: rede social da Tamaki + 📸 Gerar foto) o Claude pode mudar direto (o Tama liberou acesso a todo o GitHub em 2026-11-15). Antes de mudar, peça o código do tablet se puder estar mais novo que o do GitHub (aconteceu: o tablet estava na v11 e o GitHub na v9).
- Gerador de imagem: `kaggle/tamaki_imagem_kaggle.py` (versão 2), célula em `kaggle/celula-imagem.py` (CODIGO `tamaki-img-…` só na célula, nunca no repositório). Animagine XL 4.0 + LoRA `tmkshion` (treino kohya no Animagine 4.0 Zero), Compel (prompt longo não é cortado). v2: `/pedido` = IA de texto Qwen2.5 (7B 4-bit na 2ª GPU, 3B com 1 GPU) que transforma o pedido em português em etiquetas Danbooru {tags, lugar, formato, evitar, resposta}, editando as etiquetas anteriores quando é mudança; `caprichar` = hires fix (1,5x, img2img .35). Aba Tamaki v12: "Peça do seu jeito", lugares com etiquetas (S.lugares), gosto (EST.gosto) e ⭐ favoritas como exemplos, LoRA .75. v3 do Kaggle: `/pedido` confere cada etiqueta no Danbooru (tags/aliases/autocomplete; <30 imagens = o modelo mal conhece) e devolve `avisos`; recebe `conhecidos` (fichas do Saber citadas); `/aprender` {url|texto} lê a página no Kaggle (sem CORS; página protegida → colar texto) e devolve {universo, resumo, fichas[{nome,tipo,apelidos,resumo,tags,danbooru}]}; `/gerar` aceita `extras` (várias LoRAs juntas); `/treinar` aceita `gatilho` (LoRA de outro personagem, arquivo `<gatilho>_MMDD_HHMM`). v4 do Kaggle (treino): legendas automáticas com WD Tagger (SmilingWolf/wd-vit-tagger-v3, onnx na CPU) sem as etiquetas de identidade (cabelo, olhos, pele, orelhas → ficam no gatilho), repetições ~150/n por volta, dim 16/alpha 8, lr 8e-5, salva toda volta. O LoRA antigo (1104) era forte demais: fundo neutro, cabelo e roupa errados. Aba v15: 'safe' no prompt e nsfw/bikini/roupa curta no negativo. Aba Tamaki v13: 🧠 Saber (S.saber; imagens de referência no IndexedDB `tamaki-saber`), entra em quemE() e no pedido de foto.
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
Poses por emoção: ver "Sentimentos dos atores" abaixo. Na gravação, a emoção de cada linha do roteiro (`emos`) vira a pose do ator, se ele tiver esse sentimento.

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
- O código do Kaggle fica em `kaggle/tamaki_estudio_voz_kaggle.py` (versão 6). A célula do Kaggle é só `kaggle/celula.py` (define CODIGO e baixa o .py do GitHub a cada execução): para atualizar o Kaggle, basta commitar o .py e pedir pro Tama rodar de novo (Save & Run All). Nunca ponha o CODIGO no repositório (é público).
- O treino só ajusta o T3 do Chatterbox (texto → códigos de fala); o timbre vem da referência (conds). Por isso treinar com fala de outras pessoas muda o ritmo, não o timbre.
- Não treinar a voz com frases faladas por ela mesma (Treinar › Gerar frases): é cópia de cópia e deixa a voz metálica.
- Estúdio de voz › Treinar › 🗣️ Baixar conversas reais: `/dataset/coraa` baixa a parte dev do CORAA v1.1 (gabrielrstan/CORAA-v1.1, 1,3 GB), pega só falas espontâneas sem ruído/hesitação, de preferência de SP, e põe como frases de treino. Depois: treinar como voz nova com "Começar do português original" (`do_zero`). O Tama liberou o uso.
- Versão 5: `/falar` confere cada pedaço com o Whisper e refaz até 3 vezes se embolar (`conferir`, ligado por padrão); o CORAA só entra quando o Whisper confirma que o texto bate com o áudio (≥ 0,85).
- Versão 6: o treino de 2026-11-14 do zero com o CORAA deixou a voz com "língua presa" (gravações antigas NURC/ALIP abafam o "s"). Agora o CORAA exclui NURC e ALIP, e o padrão é **treino leve** (`leve`: 2 voltas, lr 4e-6) partindo da Tamaki Shion (sem `do_zero`), que tem a dicção boa.
- O Tama voltou para a Tamaki Shion original: não treinar mais o jeito de falar (os testes com o CORAA ficaram ruins). Foco: emoções e som.
- Som macio: `voz/polir.js` (`TamakiPolir(blob)`) filtra o metálico/estridente no aparelho (EQ + compressor). Usado no Estúdio de voz (opção "Som macio", ligada) e nas falas da linha de produção.
- Emoções como "DLC": `voz/pacote-emocoes-tamaki.json` (frases no jeito dela). Estúdio de voz › Emoções › 📦 Instalar na voz em uso manda o pacote para `/emocoes/treinar` como emoções "sua" (mesmo nome = troca a do catálogo). Para melhorar as emoções, edite esse JSON e suba `versao`; não precisa mexer no Kaggle.
- O pajubá e os trejeitos vêm do roteiro, não do treino.
- Versão 7 (emoções): `fazer_emocao` ouve cada versão com o emotion2vec+ base (funasr, `emotion2vec/emotion2vec_plus_base`, 9 rótulos) e mede ritmo (sílabas/s de fala), tom (semitons) e volume contra a referência da voz; pontos = .45 emoção + .35 jeito (perto do `alvo` da emoção no EMO_CAT) + .2 Whisper. `/emocoes/analisar` ouve as que já existem. `sua` e `ajustes` aceitam cfg/temp. Pacote v2 com exag/cfg/temp por emoção.
- Diagnóstico das emoções antigas da Tamaki (cartão de 2026-11-15): todas saíram ~+3–4 semitons mais agudas que a voz normal e com o mesmo ritmo (triste tão rápida quanto brava) — por isso soavam parecidas e estridentes. Os alvos v7 põem triste/calma/cochicho mais graves e lentas.

## Novel (`novel.html`)
Engine de visual novel point-and-click do Tama (evolução do "Ninho", repositório `Visual-novel-`). Tudo é desenhado num canvas (16:9 ou 9:16) para a gravação em vídeo (⏺) ir direto para a Biblioteca (`origem:"novel"`).
- Roteiro estilo Ren'Py em localStorage `nv_roteiro` (na 1ª vez lê o `ne_roteiro` da engine antiga); saves `nv_saves`; ajustes `nv_cfg`; falas lidas `nv_lidas`. Senha opcional usa o `ne_senha` antigo.
- Artes no IndexedDB `tamaki-novel` (store `artes`, chave `nome`): o nome da arte é o que vai no roteiro (`cena ninho`, `mostra sato feliz`, `musica tema`, `voz fala1`). Pode puxar imagens e áudios da Biblioteca.
- Comandos novos além do Ninho: `titulo`, `item`/`pega`/`larga`/`tem x`, `explorar:` com áreas `"Nome" x y largura altura:` (em % da tela) e `sai`, `cena x com fade|preto|flash|nada`, `zoom z x y [s]`, `treme [forte]`, `flash [cor]`, `espera s`, `voz`. Labels seguem para o próximo quando acabam (como no Ren'Py).
- Jogador: voltar fala, histórico, automático, pular lidas, lupa (mostra áreas), esconder botões. Editor: moldes (＋ Fala, ＋ Explorar…), ▶ Daqui (testa do label do cursor) e 📐 Marcar área (desenha a área com o dedo sobre o fundo).
- Roteiros prontos: `novel/<arquivo>.txt` + entrada `{arquivo, nome, nota}` em `novel/indice.json`; aparecem em Roteiro › 📥 Prontos (o roteiro anterior fica em `nv_roteiro_antes`). `cena preto`/`cena branco` dão tela lisa.
- Roteiros da campanha do RPG do Kaoro: caminho principal = o que foi jogado (canon); escolhas alternativas dão outras falas e voltam ao canon (ramifica e reencontra); nada do Cofre do mestre entra. Falas curtas (até ~2 linhas na caixa), uma ideia por fala; investigação com `explorar:` nos lugares cheios de detalhe.
- Vários roteiros: ＋ Novo roteiro (página em branco, escrita livre), 💾 Salvar manda para a aba Escrita (localStorage `kurogane:data`, nota na pasta `novel` "Visual novel"; o id da nota fica em `nv_nota`, o nome em `nv_nome`, mudanças não salvas em `nv_sujo`), 📥 Abrir lista os roteiros da Escrita e os prontos do GitHub, ⬇ Baixar salva .txt com o nome do roteiro. Linhas viram `<p>` (recuo em &nbsp;).
- Partes: o roteiro é um texto só com linhas `### PARTE: Nome` (⚙ Definições primeiro, depois Prólogo, Cena 1…); o editor mostra uma parte por vez (`PROJ.partes`, parte aberta em `nv_parte`). Erros apontam "Parte X, linha N". O jogo começa no `label inicio` ou, se não houver, no primeiro label. Roteiros de capítulo devem vir com as marcas de parte, uma cena por parte.
- 🎬 Montar cena (menu e barra do Roteiro; tela `#montar`): cenas montadas em localStorage `nv_cenas` = {chave: {nome, camadas:[{id, tipo:'cenario'|'ator'|'item', ref, nome, x, y, s, r, flip, alpha, vis, lock, emo}]}}. Cenário: x,y centro em %, s = zoom sobre "cobrir a tela"; ator/item: x centro, y = pés (% da tela), s = altura em % da tela. `cena <nome>` com o nome de uma cena montada desenha as camadas (`pintaMont` dentro de `fundo`); cada camada de ator ligada a um `personagem … ator X` vira esse personagem no lugar montado (`st.mmap` camada→personagem, `st.chars[id].m`), fala/pisca/sentimento normais; ator sem personagem = figurante (`NVA.desenharId`, só pisca). `esconde` tira; `mostra x` volta ao lugar montado; `mostra x direita` sai do lugar montado. Lista de camadas com 👁/🔒, frente/trás, duplicar, espelhar, girar, transparência, sentimento; arrastar move, dois dedos = tamanho; ✎ Pôr no roteiro escreve `cena nome com fade` e oferece criar os personagens que faltam.
- Futuro pedido pelo Tama: janela 🎙 Vozes na Novel (escolher a voz de cada personagem e do narrador com os ícones da aba Voz; por personagem, todas as falas com gerar/ouvir/refazer/trocar voz; no fim, baixar e pôr na Biblioteca com nomes automáticos que a Novel toca sozinha).

## Sentimentos dos atores (Animador › 😮 Sentimentos)
Cada ator da aba Atriz (`palco-animacao.html`) pode ter sentimentos: a personagem inteira com outra expressão, com as mesmas 5 poses (idle, talk, talk2, idleBlink, talkBlink).
- Config do ator (`palco-animador-v1[:id]`): `emocoes: [{id, palavras}]`, `emoAuto` (escolher pelas palavras). Imagens no IndexedDB `palco-animador`: `chaveImg(ator, "emo-<id>-<pose>")`. O "normal" são as poses da aba Imagens.
- Arquivos em lote: `Tamaki_surpresa.png`, `_fala`, `_fala2`, `_pisca`, `_fala_pisca` (o nome do ator na frente sai sozinho).
- O bloco `EMO` (lerNome, dividir, detectar, pose) está copiado igual no Animador, no Palco e na Novel: ao mudar, mude nos três.
- Palco: o texto é dividido em frases; `[surpresa]` ou `(surpresa)` no começo vale até o fim da frase, depois volta ao normal; `Tamaki: …` no começo da linha faz só esse ator falar (`FALA.quem`). Sem tag, o sentimento sai das palavras (se `emoAuto`). Botões de sentimento no painel Animação do ator.
- Novel: `personagem tamaki "Tamaki" #cor ator Tamaki` liga ao ator (pisca e mexe a boca enquanto a fala aparece ou a voz toca); `tamaki [surpresa] "fala"` ou `tamaki (surpresa) "fala"` vale só nessa fala e volta ao do `mostra`. Sem ator, `[surpresa]` usa a arte `tamaki surpresa`.
- Sentimentos prontos no repositório: `atores/indice.json` = `[{nome, pasta, nota, arquivos}]`, imagens em `atores/<ator>/` (WebP, mesma tela das poses originais, nomes `Tamaki_<sentimento>[_fala|_fala2|_pisca|_fala_pisca].webp`). Atriz › 😮 Sentimentos › 📥 Sentimentos prontos pergunta qual pronto (o do ator aberto vem marcado), troca para o ator com esse nome ou cria o ator se ele não existe, e instala. Arquivos sem sentimento no nome (`Kaoro.webp`, `Kaoro_fala.webp`…) vão para as poses normais (aba Imagens). Além disso, a Central (`atoresProntos()` no index.html) cria sozinha, ao abrir, todo ator do índice que ainda não existe no aparelho (uma vez só por nome: `central-atores-prontos`; apagou, não volta) e recarrega o Palco Animação. Atores prontos do Capítulo 1 (2026-11-20, folhas geradas no GPT pelo Tama): Tora, Goro, Reika, Yoru, Kiyoshi, Midori, Gen, Yuzu, Tetsuo, Banji, Hiyori, Shun, Kenichi, Momo, Kaname, Kaede, Haru e "Tamaki criança" (arquivos `Tamaki*.webp` em `atores/tamaki-crianca/`), só poses normais, WebP q92; o campo `tamanho` do índice vira o `size` do ator (crianças menores). Kaoro: só as 5 poses normais (fundo tirado com isnet-anime; todas usam o corpo da Parada e só a cabeça muda, alinhada pelo rosto, para não tremer na troca). Tamaki: feliz, animada, surpresa, convencida, emburrada, pensativa (feitas de 6 desenhos do Tama; olhos fechados = traço do olho fechado da feliz; bocas trocadas entre os desenhos dela).
- Atores no estilo novo (bíblia de personagens, doc claude.ai/artifact/UmTf5SAu5teoMsUEmK7AdF): o Tama gera no GPT uma "ficha de expressões" = corpo inteiro com ROSTO LISO à esquerda e, à direita, grade 5 linhas × 3 colunas só de cabeças (linhas: normal, feliz, bravo, triste, surpreso; colunas: boca fechada, falando, olhos fechados). O Claude recorta (isnet-anime), acha escala/posição de cada cabeça no corpo (matchTemplate), alinha pelo nariz e cola só a pele do rosto (máscara do rosto liso do corpo), assim o cabelo e o corpo são sempre os mesmos. Vira poses normais + sentimentos (`_fala2` e `_fala_pisca` = cópia do `_fala`; sem `_pisca` quando a coluna 3 veio de olho aberto). Kaoro já está assim (versao 2; bravo, triste e surpreso ainda sem piscar).
- Atualizar um ator que já existe no aparelho: suba `versao` no item do índice. `atoresProntos()` guarda as versões em `central-atores-versao`; versão maior apaga as poses normais e as dos sentimentos do pacote e grava as novas no mesmo ator (mantém sentimentos que ele já tinha). `palavras` no item do índice = palavras de cada sentimento; `tamanho` só entra se o ator ainda não tem size.
- Novel › 🎭 Atores (no menu e na barra do Roteiro): lista cada `personagem` com a foto, se está ligado (✅ / ⚠ ator não existe / sem ator), os sentimentos prontos e os que o roteiro pede sem pose (!). A lista de atores reescreve a linha `personagem … ator X`; os atores soltos têm ＋ Criar personagem.
