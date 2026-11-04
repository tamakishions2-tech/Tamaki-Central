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
