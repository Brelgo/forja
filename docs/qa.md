# Roteiro de QA

Um comando que abre o app, percorre os caminhos de sempre com clique de verdade
e diz o que quebrou.

```bash
python docs/qa_roteiro.py
```

Outras formas:

| Comando | O que faz |
|---|---|
| `python docs/qa_roteiro.py` | esta pasta, servida numa porta livre |
| `python docs/qa_roteiro.py --site` | o que está no ar, no GitHub Pages |
| `python docs/qa_roteiro.py --offline` | pula o que precisa do servidor das builds |
| `python docs/qa_roteiro.py -k marcador` | só o grupo com essa palavra no nome |
| `python docs/qa_roteiro.py --captura x.png` | salva uma captura do catálogo no fim |

Precisa de Chrome instalado e de `pip install websocket-client`. Sai com código
diferente de zero quando alguma checagem falha.

## Por que ele existe

Em 20/09/2026 dois bugs foram parar no ar e quem achou foi o Leo: a aba Públicas
vazia (`permission denied for table builds`) e os marcadores que abriam o
diálogo e não gravavam nada. Nenhum dos dois era difícil de pegar — bastava
abrir o app e fazer o de sempre. Os dois entraram no roteiro como checagem
própria, e é assim que ele cresce: **todo bug que o Leo achar vira uma linha
aqui**, para não achar duas vezes.

Os cliques são de verdade (CDP, `Input.dispatchMouseEvent`), não evento
sintético — evento sintético já passou verde com o drag e o duplo clique
quebrados.

## O que ele confere

**Arquivos** (sem abrir navegador, só quando roda nesta pasta)

- `.nojekyll` existe e nenhum caminho absoluto (`/assets/...`) no HTML.
- Todo `assets/...` citado no index.html existe **com a mesma caixa de letra** —
  o Pages é case-sensitive e o Windows não é, então `Assets/X.PNG` passa aqui e
  quebra lá.
- Todo MP3 do mapa de som existe em `assets/audio`.
- O `docs/servidor/supabase.sql` cobre o que a página manda e lê (F13-T87): cada função que a página chama
  (`publicar_build`, `apagar_build`, `registrar_evento`) criada uma vez só e com todos os parâmetros que ela manda; a
  `builds_publicas` com todas as colunas da tabela e tudo o que a página publica (`p_rota` → `rota`…), sem o hash; e o
  grant por coluna com as mesmas. O arquivo de antes da T87 reprova (sem runas, habilidades e rota).
- E o limite de 5 por IP (F13-T88) continua no `registrar_evento` do `supabase.sql`: o IP pelo `cf-connecting-ip`, o
  teto 5, o sal do dia e as duas tabelas fechadas ao público. (O comportamento foi provado no banco, no ensaio que
  aborta; o roteiro não registra evento no servidor de verdade.)
- Todo card de região que o `data/regioes.js` aponta existe na pasta.

**Fundação** — 225 itens; as runas contadas pela estrutura batem com o número
que o gerador anotou (foi um leitor calado que escondeu 4 runas em 18/09);
a placa de entrada diz "Este é um projeto feito por hobby sem fins lucrativos." e o contato do autor
(League of Legends Brelgo#RPG, Discord brelgo; F13-T54), com os dois canais numa linha, um clique selecionando
o ID inteiro e a placa cabendo na tela nas quatro resoluções; a placa diz "Bem Vindo(a)!", "Meus Contatos" e
"League of Legends · Atualização <fase.tarefa> · patch <patch>" (F13-T57), e o número da atualização
(`ATUALIZACAO` no index.html) não fica para trás do último commit "F13-T…" — com o index.html mexido, uma tarefa
está em andamento e ele tem de estar à frente; entrar na loja sem exceção.

**Catálogo** — 225 cards desenhados; a busca filtra; a aba de núcleo vira
oficina com o estandarte de 46 px; a aba Todos volta a ser uma grade só.
No modo Ícones, o mouse não aciona o golpe do AD nem apaga o ícone (F13-T29,
bug nº 46); nos Cards, o golpe continua.
O número que a tela mostra é o que o resto usa (F13-T43, nºs 24, 32 e 33): a
eficiência nunca arredonda para cima — a Joia da Ruína e o Cetro Vampírico
saem 99,9%, fora do filtro "100% a 119%" e no grupo que vai até 99; o seletor de atributo conta itens; o preço com Reembolso sai
com as casas do catálogo (2.543,75g, 3.083,03g) e a soma da caixa fecha.
Ordenar por atributo não mistura pontos com % (F13-T43b, nº 25): primeiro os
pontos, depois a %, e o card dos Sapatos Enfeitiçados mostra "+20 · +8%".

**Calculadora** (F13-T42, bugs nºs 23 e 31) — o "Puxar da build ativa" usa
os itens que a build compra: sem as caixas Opcionais e, na Escolha 1, só o
padrão, e o painel "Atributos da build" da forja conta a mesma build; itens
sem vida não apagam a vida digitada. Roda depois dos grupos da
forja, porque troca de aba e de caixas.

**Falta pouco para publicar** (F13-T45, nºs 45, 49, 50 e 53) — com rascunho na
forja, publicar pergunta antes de abrir a janela; o campo do nome fica na tela
(e com o foco) enquanto se digita; o mesmo marcador ou o mesmo nome não
carimbam a "Última atualização"; tirar do site duas vezes faz o segundo
esperar, sem erro falso.

**Ficha do item** (F13-T55; Leo, 19/10/2026: "os jogadores lembram dos itens pela imagem e não pelo nome") — a
receita em árvore da ficha com mais peças do catálogo (a Dança da Morte no 16.21.1) bate com a conta feita por fora,
direto do `catalog.js` (`components` × `qty`): nós, peças na ponta, galhos com ouro de juntar e a conta embaixo
fechando no preço; o clique de verdade numa peça abre a ficha dela (depois do pergaminho desenrolar); a troca para
a conta de somar mostra uma linha por receita com a do item por último, e o app lembra depois de recarregar; o
"Vira componente de" do item que mais vira (a Espada Longa, 21) tem um ícone por item, por etapa e do mais barato
ao mais caro, o nome no `title`, e o clique abre; o "Exibir detalhes" começa fechado (Atributos, a receita e a
habilidade no texto curto à vista; Análise de custo, Passiva do Ornn, as etiquetas, a Mecânica das habilidades e as
notas do item não — Leo, 23/10/2026: "ao clicar em ver detalhes estes campos de habilidades se expandem para a
versão detalhada"), abre no clique e o app lembra; e nas 225 fichas a
árvore cabe na largura e só quem tem receita mostra a seção.

**Forja** — a build nova nasce com as 8 caixas; item entra na caixa; o modo
leitura esconde os atributos.

**Marcadores** — escolher, o segundo espaço, trocar um já preenchido e tirar no
`×`. O `×` só existe no hover, então o roteiro passa o mouse antes; sem isso o
clique cai num retângulo de tamanho zero e acusa bug que não existe.

**Visualização só lê** (F13-T59; Leo, 23/10/2026: "sem estar ativa a edição eu posso simplesmente trocar o
campeão, trocar o modo de jogo… isso não é para ser possível") — com a build aberta sem o Editar, por clique de
verdade e por `change` forçado (o teclado, ou alguém tirando o `disabled`): o campeão não troca (nem pelo botão
nem pela lista), nem o modo, nem o nome, nem os marcadores (o espaço vazio some), nem o Mestre Forjador, e a
assinatura da build sai igual. Na aba Runas a faixa leva à página da build ("· ver"), que aparece só para ver:
escolher runa e trocar trilha não mudam nada (era o nº 29 numa pública); o "Ligar Editar" dali libera a página.
Com o Editar, campeão e modo trocam como antes. E o seletor de campeão: em 1920 três colunas; com o menu
apertado (janela estreita, zoom alto) ele perde coluna em vez de espremer — nenhuma com menos de 130 px. E as
listas com rolagem não espremem as linhas (F13-T63, a print de um jogador: retratos e nomes empilhados): a de
campeões medida como o Firefox mede (pela altura máxima — a altura fica fixa em 380 px) e o menu de troca de
build com 25 builds a mais, só na memória; nenhuma linha cortada, nenhuma de campeão com menos de 30 px.

**Teclado e o coração** (F13-T64; nºs 22, 43 e 44 da caçada) — com teclas de verdade (CDP): com uma caixa escolhida,
o Esc fecha o diálogo aberto (observação, marcador, tipo da caixa, fragmento, campeão, troca de build) e a caixa
continua escolhida; sem diálogo, o Esc ainda larga a caixa. Na lista, o Enter com o foco no coração favorita (e a
tela fica na lista), com o foco na linha abre a build. O coração da visualização de uma pública favorita a pública
de origem: o ID entra nos favoritos e o coração acende na linha da visualização e na aba Públicas.

**Redesenho** (F13-T65; nºs 18, 30 e 52 da caçada) — com a Ahri na build e os ícones dela na grade de habilidades,
tirar o campeão pelo seletor (clique de verdade) deixa a grade só com as letras, e trocar para uma build sem
campeão também (sem internet o caso é pulado, não aprovado); importar um texto com `DESCRIÇÃO:` e `LAYOUT:` (sem
campeão nem Passiva do Ornn) mostra os dois na hora; e um clique parado no canto de uma caixa cuja grade gravada
difere da vista não grava nem suja o rascunho — arrastar uma coluna para o lado ainda grava.

**Importação** (F13-T66; nºs 54, 55 e 56 da caçada) — pelo botão de verdade: um texto com um link de markdown e um
"[Dica]" no meio das caixas importa só as caixas de verdade (o colchete que não é tipo é texto, e os itens de
baixo ficam na caixa certa), e `[ESCOLHA]` sem o 1 vale; um Arsenal.json com um bloco de 2 itens tem a mesma grade
(6 colunas, como a caixa do texto importado sem grade) antes e depois do F5; e a régua abaixo do título com o cabeçalho depois dela é enfeite (o `BUILD:` repetido
só renomeia), enquanto a régua do lote exportado (cercada de linhas em branco) ainda separa as builds.

**Lote e a Passiva do Ornn** (F13-T67; nºs 51 e 58 da caçada) — excluir pelo lote (cliques de verdade, o `confirm`
lido na página) só a visualização de uma pública pergunta "Fechar 1 visualização de pública? (a pública continua no
site)", sem "saem do site", e diz "1 visualização fechada."; com uma build sua não publicada junto, pergunta "Excluir 1
build(s)? / E fechar 1 visualização…", com "Isso não dá pra desfazer." e sem "saem do site", e diz "1 build(s)
excluída(s) e 1 visualização fechada.". E a Passiva do Ornn na alternativa de baixo de uma Escolha 1 aparece na nota
da soma como "fora da soma"; no padrão, não.

**Conferência das abas** (F13-T68; Leo, 20/10/2026: "acho bem mais prático ser um ícone no canto inferior da tela ao
invés de um pop up imenso") — com a aba conferindo a trava: invisível no começo (sem piscar), depois de meio segundo
um ícone de 38 px no canto inferior direito, sem fundo escurecendo a tela, com o título explicando ao passar o mouse
e o "Conferindo as abas" para o leitor de tela; a página continua parada (é a proteção) e volta a responder quando a
trava decide. O "Aberto em outra aba" segue no centro (grupo "duas abas").

**Rota** (F13-T69; Leo, 24/10/2026: a rota num seletor da barra da build) — o seletor não muda sem o Editar (o
`change` forçado volta), some no ARAM e a rota escolhida fica no disco depois do F5; a rota vai e volta no texto
(`ROTA: Top`; `ROTA: jungle` vira Selva), no link e no lote, e o texto de uma build de ARAM não a escreve; importar
pelo botão, duplicar e "Copiar e editar" uma pública levam a rota; e publicar manda `p_rota` — com o servidor sem a
coluna (o `fetch` simulado recusa como o PostgREST recusa), publica de novo sem ela e com as runas. F13-T71: o link
de uma build com rota **e** runas leva as duas (a rota foi para a chave `ro`; na `r`, a das runas, a página a
apagava), e o link que a T69 gerou — sem runas, a rota como texto na `r` — ainda abre com a rota.

**Reembolso e topo** (F13-T71) — a runa Reembolso posta na página (pelo `gravarPagina`, o caminho da tela de runas)
liga o Reembolso na loja, na faixa e na forja, e o interruptor da forja ganha o ícone da runa; desligar à mão (clique
de verdade no interruptor) vale até a próxima troca — outro redesenho não religa; tirar a runa desliga; sem a runa,
ligar à mão continua valendo (o caminho de sempre); o "Duplicar" da forja mostra a cópia inteira (a descrição e a
rota na tela — antes ficavam em branco) e, com a runa, liga mesmo desligado à mão na original; trocar para uma build
sem a runa desliga, e voltar liga. O Udyr (a ficha do Capítulo 1.1 fala da missão do Topo): sem rota a grade tem 18
colunas; na rota Top, 20 numa linha só, dentro da caixa, e o R entra no 19 e no 20 com cliques de verdade ("20/20
níveis"); passando para a Meio, os dois pontos ficam, em vermelho, com o motivo; o Garen na Top segue com 18; e o
formato guarda 18 casas quando o 19 e o 20 estão vazios (a build de sempre grava e assina igual), com texto e link
levando os 20 quando têm ponto.

**Filtro de rota** (F13-T75; Leo, 24/10/2026: "implementar a rota no sistema de busca, acho bom colocar em baixo dos
marcadores padrão") — com cliques de verdade: no "Filtrar por marcador", a seção Rota vem logo abaixo dos marcadores
padrão, com as cinco rotas; em Minhas, a Selva mostra só a build da Selva — a de rota "Qualquer" e a de ARAM (que não tem
rota) ficam de fora —, o botão diz "Filtro: Selva" e o segundo clique solta; em Públicas (uma lista de mentira, sem
tocar no servidor), a Meio mostra as duas da Meio, e "Limpar filtro" solta a rota.

**Cadeado: os ajustes** (F13-T76; Leo, 24/10/2026) — com a rota Suporte, a Lâmina de Doran fica trancada ("o Atlas Mundial já
vem comprado"), o Atlas e a Canção de Sangue (a linha dele) não, e com a Top a Doran volta; escolhida a caixa pelo "Marcar em"
da loja, a Comum tranca a Doran e a segunda Hidra, a Opcional e a Escolha 1 não, e o ladrilho da Escolha 1 fica sem cadeado;
sem o Editar, a loja não mostra cadeado nenhum, o clique (de verdade) no item não mexe na build e avisa, o botão "Ligar
Editar" do aviso pulsa três vezes e liga; na forja, o toque no modo de jogo (desligado) avisa e o interruptor Editar pulsa;
nas Runas, trocar a trilha avisa e o "Ligar Editar" de lá pulsa; com "menos movimento", o brilho fica parado. E o grupo
"Limitado a 1" e o efeito único só valem entre itens do mesmo tier (Leo, 25/10/2026: "o Fulgor ainda pode se tornar Trindade"):
o Fulgor com a Força da Trindade não tem aviso nem cadeado, a Trindade com Aurora e Crepúsculo continua trancada, e o par do
aviso passou a ser o Morellonomicon com o Lembrete Mortal (os dois Lendários com Feridas Dolorosas).

**Camada do robô** (F13-T77) — a camada do repositório (do próprio patch) não liga nada, e a de outro patch é ignorada; numa
aba própria, a camada de um patch simulado entra pelo caminho de verdade (a página carrega o `data/atualizacao_patch.js`; o
roteiro só troca o que ele diz, antes da carga): o preço e a Letalidade do Quebra-Bastião aplicados, o selo "patch 16.22.1"
no card, "a conferir" na Máscara Abissal, o aviso no alto da loja; a Redenção, com o `base` trocado (o Capítulo 1 mexeu nela
depois), fica com o preço do catálogo e sem selo; e a ficha diz o que já foi aplicado, o que está a conferir e as contas do
patch anterior. E a build com item que o robô viu mudar (F13-T82) fica "desatualizada", com a
borda vermelha nele — o item numa Opcional não conta, e o que não mudou fica sem a borda.

**O robô no GitHub Actions** (F13-T78, no grupo do robô) — a camada igual não se regrava (a hora em que ela foi gerada fica a de
antes; sem isso, um commit por dia só de data) e a que mudou se regrava; o `.github/workflows/robo.yml` tem o agendamento, o
botão de rodar, a escrita, o aviso, os dois passos e o que entra no commit.

**Notas de atualização** (F13-T80; o mural da loja, a opção B do Leo) — o `data/notas.js` em dia com os commits de tarefa
(`docs/gerar_notas.py --conferir`) e nenhuma tarefa sem nota; com clique de verdade: o ícone ao lado da Acessibilidade mostra o
número da atualização e fica aceso até a versão ser vista; abre o mural com o "Em breve na loja", o "Apoie o projeto" e as notas
por data (Adicionado · Ajustado · Removido); o Esc, o × e o clique fora fecham.

**Endereço por tela** (F13-T81; Leo, 22/10/2026: "ao clicar em Builds fica /builds, em Runas /runas") — com clique de verdade
nas abas, o endereço acompanha (#builds, #runas, #calculadora, #catalogo, e #forja com a build aberta); o voltar e o avançar do
navegador trocam de tela; numa aba nova, o link #runas abre nas Runas, e trocar o # na barra leva à Calculadora.

**Autor na publicação** (F13-T83; servidor SIMULADO: o roteiro segura o `publicar_build` e só lê o que sairia) — o campo
"Autor nas suas publicações" no resumo da build começa vazio; o apelido digitado (com espaços nas pontas) vai no `p_autor` limpo,
fica lembrado no navegador e volta no campo; apagado, a publicação seguinte sai sem autor.

**Link curto da build publicada** (F13-T91; Leo, 30/10/2026: o endereço `#build/<id de 6>`, inspirado no cblow.xyz; servidor
SIMULADO numa aba própria: o fetch ao Supabase é respondido na página e o `navigator.clipboard.writeText` só anota) — a página
aberta com `#build/<id>` de uma pública conhecida abre direto na forja, só visualização, com o nome dela, e o endereço fica no
link; com clique de verdade, sair para o Catálogo escreve `#catalogo` e o voltar do navegador reabre a pública; ID que não existe
e rede que cai dão a placa com o motivo e deixam o app na lista das Públicas (`#builds`), sem exceção; # torto (maiúsculas, 7
letras, aspas) é ignorado sem pedido ao servidor; o "Copiar link" da não publicada copia o `#b=`, e o da publicada (Minhas), o
da pública (Públicas) e o da aberta para ver (forja) copiam o curto, com o title dizendo qual sai; o caminho antigo — o link
`#b=` abre a build na forja, e `#runas` e `#builds` trocam de tela — continua. Vista falhando: sem a rota no `aplicarRota`,
caem a abertura, o voltar, a placa e o link da forja; o `#b=` segue passando.
Revisão do cético (30/10/2026), com servidor simulado LENTO (a pública do link responde depois de 1,5–2,5 s; a lista vem na
hora, com outra build) e clique de verdade: enquanto a build vem, o resumo mostra a placa "Abrindo a build <id>" e a lista das
Públicas não escolhe outra sozinha; clicar numa linha das Públicas, na aba Minhas ou digitar na busca cancela (a build do link não
abre por cima e o # vira `#builds`); o voltar do navegador durante a espera cancela — a forja fica com a build de antes e o #
volta a `#forja`; na pública aberta pelo link, "Copiar e editar" e o × da plaqueta esquecem o link (o # vira o da tela e o F5 abre
a build da forja, não a pública); com rascunho sujo, abrir o link e escolher "Continuar editando" deixa tudo como antes (a forja,
`#forja`, o rascunho, nada marcado); o "Copiar link" da forja numa publicada sem caixas copia o curto, e a não publicada sem
caixas segue recusando. Antes, o grupo passava 5/5 com o cancelamento arrancado (nunca havia demora). Vista falhando, cada
conserto revertido num mutante (index.html servido da memória, o arquivo intacto): sem o cancelamento inteiro caem a espera com clique e o voltar; sem o cancelar no popstate cai o voltar; sem esquecer ao sair cai o Copiar e editar/×; sem o cancelar na aba Minhas, na linha ou na busca cai a espera com clique; sem o "voltar" do diálogo cai o Continuar editando; sem a placa ou com a lista escolhendo sozinha cai a placa; com a recusa de volta cai o link da publicada sem caixas — 10 de 10 mortos.
Os dois casos raros que a revisão deixou (F13-T92, 31/10/2026), com clique e tecla de verdade e o voltar do navegador: com
rascunho sujo, o link chega e o "Salvar e sair?" abre; o voltar com ele aberto vale "Continuar editando" — o diálogo fecha, a
forja fica com a build e o rascunho em `#forja` e a pública não abre (antes o diálogo ficava e o Descartar abria a pública que o
jogador tinha deixado para trás); voltar duas casas de uma vez com o diálogo aberto leva à tela de destino com o # dela (`#runas`);
o Esc segue valendo "Continuar editando". Durante a espera, o voltar devolve a tela de antes do link: a aba Minhas com a mesma
linha escolhida (`#builds`), e, aberto por um `#b=`, a forja com a build dele e o `#b=` no endereço (antes ficava a lista das
Públicas). O achado do cético da T92 (já vinha da T91): durante a espera, o gesto que pergunta ("Nova build", o × da
plaqueta, "parar de editar") também cancela o link — antes a resposta chegava com o diálogo aberto e o Descartar ou o "Salvar e
sair" abria a pública; agora cada um faz o que o gesto pediu, e o "Continuar editando" fica nas Públicas em `#builds`, sem a placa.
Vista falhando, cada conserto num mutante: sem fechar o diálogo no voltar caem o voltar e as duas casas; sem voltar à tela de
antes caem Minhas e o `#b=`; sem forçar o # de destino caem as duas casas; com o Esc desligado cai o Esc; sem o cancelar no gesto
que pergunta cai o gesto na espera — 5 de 5 mortos.

**Fonte para dislexia** (F13-T85; Leo, 18/10/2026, escolheu a OpenDyslexic em 25/10/2026) — com clique de verdade no
interruptor da Acessibilidade, a OpenDyslexic carrega e vale no texto e nos títulos, e fica lembrada; nada estoura para o lado
em 1600 e 1280, na loja e na forja (a plaqueta da bigorna passava 57 px em 1280 — agora para a 16 px da borda); nenhum card corta
atributo nem nome com "…" (eram 225 em 1600: a linha quebra e o card cresce); desligada, volta à Alegreya, e a plaqueta, à aba
Builds (o caminho antigo).

**Tags somam** (F13-T89; Leo, 29/10/2026: "o que eu quero é que sejam exibidos os itens que tem a tag A+B") — com clique de
verdade nos chips da loja: num grupo de várias tags, marcar A e depois B estreita a grade para quem tem as duas (Efeitos
Especiais e Atributo; o par é escolhido no catálogo para que "A e B" fique menor que "A ou B" sem zerar, e o esperado é contado
por fora); num grupo de valor único (Tier), dois chips somam. Com o "ou" de antes, Acúmulos + Ativa davam 68 itens em vez de 9.

**Cadeado** (F13-T70; Leo, 15/10 e 24/10/2026: o cadeado impede nas caixas que contam — Comum, Prioridade e o
padrão da Escolha 1; a Opcional e as alternativas aceitam) — o que o cadeado lê do catálogo bate (3 itens de Selva, 7
botas da Missão do Meio, 8 da linha do Atlas, 5 itens que pedem runa, 24 grupos, as Botas Levemente Mágicas no lugar
das Botas); pela bandeja, com cliques de verdade: com a rota Top, o item de selva fica com o cadeado e não entra na
Prioridade (o aviso diz "só na rota Selva"), e entra na Opcional; com uma Hidra numa caixa que conta, a segunda fica
trancada na Prioridade, entra como alternativa da Escolha 1 e não sobe a padrão; as Botas Levemente Mágicas pedem a
Calçados Mágicos e, com ela na página de runas, entram — e as Botas comuns ficam trancadas; o item de selva que já
estava numa caixa que conta ganha o cadeado quando a rota muda; e na loja o card trancado mostra o cadeado (também
depois de a busca redesenhar a grade) e o clique não entra.

**Aviso** (F13-T72; Leo, 15/10/2026: "como o sistema de lentidão, que sempre prioriza o valor mais alto, e o Feridas
Dolorosas") — o que o aviso lê do catálogo bate: a passiva (ou ativa) única de mesmo nome — fora as sem nome ("—") — e
as etiquetas Lentidão e Anti-Cura dão 81 pares em 32 itens; a mensagem exata da passiva (Morellonomicon e Orbe do
Oblívio, sem repetir o Anti-Cura dos dois) e da etiqueta (Serrespada, Presságio); a cópia repetida também avisa; e o
par que já divide um grupo "Limitado a 1" (as Hidras, Manamune e Muramana) fica só com o cadeado. Com cliques de
verdade: na bandeja, a Orbe com o selo para a Comum (não para a Opcional), entra e o recado da forja diz com o que não
acumula; no molde, o selo nos dois que contam — não na Opcional nem na alternativa da Escolha 1 — e o motivo no balão;
na loja, o card com o selo, também quando a build muda com a loja aberta (a Zeke ganha o selo quando o Presságio
entra), a Zhonya sem; o clique no Rylai entra e o recado da loja diz a Lentidão.

**Robô de patch** (F13-T73; `docs/robo_de_patch.md`) — sem navegador e sem rede, roda junto com os arquivos: o leitor de
Lua (`data/robo/lua_tabela.py`) com um texto de prova — escapes, comentário longo, chave por nome, `nil`, a chave
repetida que vale a última e vira aviso, e o texto cortado que para com erro (antes estourava sem dizer onde); as
referências `=>` da wiki — a que resolve, a que aponta para um campo que o destino não tem e a que dá volta, as duas
no aviso; as regras da comparação num catálogo de mentira (id de variante 22xxxx, item não comprável, Elixir por
extenso e efeito sem nome passam; a fonte dividida e o erro de verdade aparecem); e a foto do patch do catálogo
inteira, com o relatório no repositório dizendo o mesmo que a conta refeita sem rede.

**Robô: a regra** (F13-T74; `docs/robo_de_patch.md`) — sem rede, roda junto com os arquivos: um patch simulado a
partir da foto do patch do catálogo, com um caso de cada — preço nas duas fontes (aplica, e refaz Reembolso e custo de
combinação: 7,5% de 3.100 = 232,5; 763), só na wiki com o catálogo seguindo o Data Dragon (o Atma: nada), só no Data
Dragon (a Redenção: aplica), o preço da Espada Longa chegando aos itens que a usam, atributo que muda e que entra, o
catálogo que não seguia a fonte (a AdH do Atma), as fontes divergindo (a Máscara Abissal), texto de efeito, item que
sai e item novo — e a camada do repositório (`data/atualizacao_patch.js`) sendo a do patch do catálogo. Os preços sobem
como no jogo: a Espada Longa leva junto toda a árvore acima dela, e o custo de combinação refeito bate com o `gold.base`
do Data Dragon. E um caso para cada achado da revisão adversarial (24/10/2026), nenhum podendo virar "aplica": item
que sai do Data Dragon, item sem modos, `=>` sem destino, preço que some, receita, item não comprável, nome em
português, atributo que o robô não lê; o pai com o preço em aberto e a conta que não fecha com o `base` ficam com o
custo de combinação marcado; o Ápice marcado como conta velha. No leitor: o comentário com nível, o `= nil` que não
cria chave e a foto base que não se regrava. Na 2ª rodada: o item inteiro na conferência sem conta na camada, o valor
em ouro velho em todo item quando muda a Espada Longa (`statPricesVelhos`), o preço com nota ("gratuito"), a chave de modo
renomeada, o salto (Letalidade 18 → 1038), a wiki com menos de 24 h, a categoria marcada quando um atributo entra, a
contagem por fora que não depende da formatação e a foto base sendo a revisão que o Capítulo 1 registrou. Na 3ª: o zero
(Letalidade 0, preço 0), o teto do atributo que entra (Vida 1038), o item com salto esperando inteiro, os modos contra o
Data Dragon (a wiki tira o ARAM da Tiamat, o Data Dragon não), a troca de unidade (as Botas: plano → percentual), os
Elixires na conta velha, a espera que conta também da 1ª foto do patch, a entrada repetida na contagem e o que fazer com a
base (fazer, refazer, avisar sem rede). Na 4ª: o que entra com 0, negativo, fração ou `true`, a troca de unidade pela
família (o Berrante do Guardião, o Quebra-Bastião), o salto por outra porta (o preço que salta só na wiki, o atributo
ilegível) segurando o item, a marca da conta que outro item deixa velha no item que espera (componente, fragmentos), a
chave de modo que o robô não lê, a Mecânica marcada, o `spec`, o `req` e o tier, os novos que voltam e os que só o Data
Dragon traz, o `base` de cada campo da camada, a camada presa ao catálogo, a revisão da base ligada ao patch (um Ajuste
fora de patch não muda a base) e a base que não é o módulo; a espera contando até a última leitura (com datas de janeiro,
longe de "agora"). Na 5ª: o atributo que muda para longe da faixa (55 → 155; o Sanguinário 80 → 85 passa), o texto que faz
conta com o preço (as notas da Redenção, o Ápice da Abatedora), com o atributo sem "de" (a Húbris, o Atma), com o modo (o Anjo
Guardião volta ao ARAM) e com o valor em ouro (os fragmentos), cada porta da marca de texto isolada numa cópia do catálogo com
uma nota escrita de propósito (a combinação, o Reembolso, o componente, o componente do item que espera, e o controle sem
número), a variante que não é item novo, o sha pelo conteúdo, a revisão da seção da reconciliação (o Ajuste de sessão, a Fonte
noutro parágrafo, a seção refeita) e a espera pelo conteúdo (a revisão desfeita).

**O clique do roteiro espera a animação** (F13-T73) — o `clicar` espera acabar a animação finita no caminho do
elemento (ele ou quem o contém) antes de medir. O painel que acaba de abrir desenrola (`modal-unroll`, 0,25 s) e o
`hover` mede, espera 0,25 s e clica: o botão já estava em outro lugar e o clique caía no painel. Era o "Usar esta
aba" da aba de link no grupo "duas abas" — quatro falhas em cascata, um roteiro sim, outro não, sem nada mudado no
app. O diário da aba (cada carga e cada `pointerdown`/`click` com o alvo, gravado no `sessionStorage`) é que mostrou:
o clique chegava no lugar medido, e o alvo era o painel.

**Passiva do Ornn** (F13-T60; Leo, 23/10/2026) — o "Mestre Forjador" virou "Passiva do Ornn" na tela e a placa
"MF" do item virou "Ornn": nenhum texto do app diz mais o nome velho — o HTML inteiro (inclusive o que está
escondido, menos script e style), os `title` e os `placeholder`, com o item forjado na forja, o balão aberto e a
ficha de um elegível aberta. O formato de texto continua escrevendo `MESTRE FORJADOR:` (escolha do Leo).

**Runas** — a página fecha em 9 de 9 e a faixa aparece na forja.

**Habilidades** — o nível 1 aceita clique (já ficou inalcançável uma vez), o
supremo é recusado no nível 5 e aceito no 6. Desde a F13-T58, com as regras do
Capítulo 1.1 (`data/habilidades.js`; esquema em `docs/esquema_habilidades.md`),
por cliques de verdade: a regra de nível vale para todos (rank 2 só no nível 3; o
5º ponto só no 9); o supremo pode atrasar, como no jogo (R no 7; o 2º só a partir
do 11); as fichas valem (Udyr com 6 ranks e o R desde o nível 1; o R do Jayce
sozinho no nível 1 e sem ponto; o Azir sem Q antes do W); o ponto que já estava
fora da regra fica, em vermelho e com o motivo; e importar ou copiar não corta
pontos (6º rank, R no 7).

**Texto** — exportar e reimportar devolve a mesma build (itens, marcadores,
habilidades e runas). F13-T36 (bugs nºs 17 e 28): a descrição e a observação
de várias linhas voltam iguais, pela interface (Copiar esta build → Importar)
e pelo texto de várias builds, com o pior dado — barras coladas, barra solta,
barra dupla, link, e linhas que parecem cabeçalho do formato (#, -, =, [ ]);
texto escrito à mão: " / " separa a descrição, " ¶ " a observação, "/"
colado é barra; texto exportado antes: a barra na observação continua barra;
quebras que chegam por fora (U+2028, \r, observação só de espaço, nome com
quebra) não derrubam item, caixa nem descrição; F13-T37 (bug nº 19): o texto
de várias builds (Selecionar → Copiar como texto) volta como várias builds,
cada uma com runas, fragmentos, habilidades, Mestre Forjador e campeão, pelo
botão de verdade; o cabeçalho de cada build fica com ela (comentário no meio,
régua dentro da build, cabeçalho entre a régua e o BUILD:); a mensagem avisa a
build sem caixa e o campeão desconhecido sem apagar o resumo nem a mensagem
mais nova, e "sem internet" é uma frase só; importar 10 builds grava e
redesenha uma vez; fragmento e modo que chegam
de fora não desmontam a linha; texto antigo com uma quebra invisível no meio
da linha fica inteiro; um campo de uma linha com uma quebra dentro não abre
linha nova.

**Texto, a trilha sem runa** (F13-T38, bug nº 35) — a primária escolhida sem
runa não leva a secundária junto na ida e volta; só a trilha, ou a secundária
escolhida sem runa, também voltam.

**Texto, o que o formato promete** (F13-T36b, achados da revisão da T36) —
pelo botão Importar: tópico de IA (`* dica`, `• dica`) antes da primeira caixa
vai para o "não encontrei" sem deixar uma caixa "Importados" vazia; texto só de
tópicos não importa build vazia, avisa que não achou nada; caixa sem grade
nasce com 6 colunas, como `docs/formato_de_importacao.md` diz, e a
"Importados" também, inclusive depois do F5 — o caminho antigo continua (`| ½`
dá 6, `| 2×1` dá 2); o nome errado numa build que fica sem caixa aparece no
aviso (no lote e sozinha); um tópico de IA entre dois `BUILD:` não funde as
builds (a parte sem caixa fica de fora, avisada).

**Rascunho** (F13-T24, bug nº 37) — com o Editar ligado e um item não salvo,
reabrir a build que já está na forja (duplo clique na linha, o Editar do
detalhe) mantém o rascunho; o coração da lista grava na hora sem gravar o
rascunho; e o Descartar continua voltando à cópia salva. Olha o
`rascunho.sujo` e o localStorage, não só a forja: um conserto que gravasse o
rascunho calado também deixaria o item na tela.

**Troca de build** (F13-T25, bug nº 38) — com o rascunho sujo, abrir outra
build pela lista, "+ Nova build" e Importar perguntam Salvar/Descartar como a
forja pergunta, e "Salvar e sair" grava e segue; excluir outra build e digitar
o nome na janela "Falta pouco para publicar" gravam o que é deles sem gravar as
caixas do rascunho; um Ctrl+S com essa janela aberta não solta a cópia (o
que se digita depois ainda grava); e o Enter da lista abre o diálogo com o
foco nele. Cada checagem monta o próprio estado e só responde o diálogo se ele
apareceu, para falhar sozinha no código de antes.

**Salvar** (F13-T31, bug nº 14; o `setItem` da biblioteca recusado) — o Salvar
não diz "salvo" (o botão fica aceso, o aviso de saída armado, sem o som); a placa
explica, com o foco nela; o "Salvar e sair" não sai; o Ctrl+S numa build limpa
não a suja; a cópia na memória não fica com o que não gravou, e o Descartar
descarta de verdade; o coração recusado avisa; a publicação que passou sem
gravar aqui pede para anotar o ID; com a gravação de volta, o aviso some
sozinho e o Salvar salva.

**Duas abas** (F13-T35, bug nº 27; várias abas de verdade no mesmo Chrome, a
mesma trava do navegador) — a aba nova já nasce parada enquanto confere a
trava; a segunda fica sob o véu, com a página por baixo sem resposta, e não
grava por cima; "Usar esta aba" recarrega do disco e assume, e a outra para;
parada, a aba não obedece a atalhos (Esc, Ctrl+S); a troca é recusada com
rascunho, com gravação recusada, com publicação, exclusão ou importação
esperando a internet — e o véu diz qual; a marca de uma aba que já perdeu a
vez não recusa; F5 mantém a dona; a dona que vai a outra página e volta pelo
Voltar volta inteira; a outra fechou: a parada avisa e assume; um link #b=
numa aba parada avisa e arma o aviso de saída; a dona presa num diálogo não
grava por cima da que assumiu; o "Limpar build" numa aba que perdeu a vez não
mexe em nada; a aba nova que esperou a vez relê o disco; "Usar esta aba" numa
aba de link assume sem o aviso falso de saída; a dona que quebra sem avisar é
percebida pela parada; a página de captura da observação fica com o foco no
editor; F5 da dona com outra aba na fila continua dona; outra aba que toma a
trava enquanto esta confere não deixa duas donas; o "saiu" que a dona regrava
logo depois não faz a aba nova tomar a vez; a trava negada pelo navegador não
prende a aba.
O controle remoto (F13-T93, 31/10/2026): a segunda aba não fica mais sob o véu —
abre sem nada inerte, com a faixa no pé da tela, e entra na loja; não grava por
cima; a build que a dona cria aparece na bigorna e na lista dela; o rascunho da
dona aparece ao vivo (o item na caixa, a plaqueta "não salva"), sem Editar nem
rascunho na remota e nada novo no disco; o Editar, o Excluir (sem chegar ao
confirm), o ×, a Nova build, o clique no item da loja e o Ctrl+S avisam "Edite
na outra aba" e não mexem em nada; o que escapar e tentar gravar volta ao disco
e à build da dona; navegar é livre (Runas, Calculadora, Catálogo, Builds, cada
uma com o seu #); a dona fecha a build e a forja da remota vira a lista
(`#builds`); "Usar esta aba" é o da faixa; um `#b=` numa remota avisa na faixa e
não entra na memória; a dona que quebra é percebida também pela faixa; e a dona
que vai a outra página volta inteira mesmo com um recado do controle remoto
chegando na espera (o canal fecha na saída — sem isso o navegador a tirava do
cache do Voltar, visto). O véu continua para o conferindo, o recusado e o
perdeu. Vista falhando, cada peça num mutante: sem o controle remoto, sem a dona
anunciar, sem a remota aplicar, sem reler o disco, sem parar os gestos da dona,
com o Editar ligando, sem o aviso do chamarEditar, com o Ctrl+S livre, sem a
rede de baixo, com a plaqueta sem o estado da dona, com a build do `#b=` na
memória, sem a faixa conferir a trava, com o canal aberto na saída e com a forja
sem build parada — 14 de 14 mortos. A revisão do cético (Opus xhigh, na janela;
211 controles e 27 gestos na remota sem nenhuma violação) achou seis casos, todos
consertados e com checagem: o `#b=` que saía do endereço ao navegar e se perdia
no "Usar esta aba" (o único que era regressão); o link curto respondido antes da
trava decidir, que abria na forja e sumia (agora vai para as Públicas, achado pela
busca por ID — a lista só mostra as N primeiras); o foco que cada mudança da dona
tirava da calculadora e da lista; o rascunho morto da dona que saiu ou quebrou
(a remota volta ao disco; um recado recente prova que ela está viva); a plaqueta
com o erro e o título da dona ("não deu para salvar"; o Salvar é na outra aba); e
o coração de uma pública na dona, que não redesenhava a lista daqui. De quebra,
um defeito antigo da calculadora: cada tecla a redesenha, e o focus() punha o
cursor no começo do campo de número — "12" digitado tecla a tecla virava "21";
agora fica no fim (grupo "calculadora"). Vista falhando cada conserto num
mutante: M15 a M23.
A remota manda os itens para a dona (F13-T94, 31/10/2026), com cliques e teclas de
verdade e os sons anotados nas duas abas: sem caixa, o clique no item pergunta a
caixa NA remota e a escolha vai para a dona, que põe o item no rascunho dela (o
som toca na remota, não lá; o disco não muda); com a caixa da dona, o clique põe
direto, a segunda bota já vem com o cadeado na carta e cai nele (o recado aparece
na remota), e clicar de novo tira; o "Marcar em", o "soltar", o Esc e o clique numa
caixa da forja da remota escolhem e soltam a caixa da dona; o Editar da remota é
o da dona (com rascunho lá, desligar é recusado e o recado diz por quê; o
interruptor mostra o dela); sem o Editar na dona, o clique avisa "ligue o Editar",
e o botão do aviso liga o de lá; o pedido não passa por cima de uma pergunta aberta
na dona, nem vale para outra build; sem resposta, a faixa diz em 3 s. O resto da
forja segue "Edite na outra aba" (o Duplicar, o Excluir, o ×, a Nova build, o × da
loja, o Ctrl+S). Vista falhando cada peça num mutante (N1 a N18) — 18 de 18. A
revisão do cético (Opus xhigh) achou seis casos, cinco consertados com checagem: a
pergunta da caixa velha (fecha quando a build da dona muda; "pôr" não vira "tirar";
a caixa que saiu não cai noutra), a escolha do fragmento aberta na dona (o pedido
tirava um item e o fragmento caía no vizinho — o único que era regressão; agora o
pedido espera), o cadeado que sumia da grade nova da remota, o pedido que chegava
depois do "não respondeu" (a dona num confirm: agora não vale mais) e o som de
tirar no duplo clique; e o "ligue o Editar" também na faixa (o recado da loja mora
no topo da grade). O sexto — trocar de dona no meio de um pedido deixa o item no
rascunho de quem perdeu a vez — é a mesma corrida da T35 com um rascunho da própria
dona, de gravidade baixa, e fica anotado. Vista falhando cada conserto: O1 a O9.

O card da build no Discord (F13-T95, 31/10/2026), grupo "card do Discord": o molde
data/robo/card.html desenhado de verdade, com a rede do Data Dragon e do Google Fonts.
As peças, em 15 casos montados do catálogo: a bigorna com os 3 primeiros Lendários do
Total sem opcionais; a bota da build (não a peça "Botas"), a evolução de bota; sem
Lendário, o resto, sem a sentinela; item fora do catálogo, repetido e com nome de
propriedade ("constructor", "__proto__"), que não é item. O nome curto, comprido,
enorme, com acentos e com emoji (o corte é feito no JS: sem a 4ª linha escondida e sem
partir o emoji). O rodapé com autor comprido e sem autor; sem campeão e com um que o
Data Dragon não tem; HTML no nome e no autor. A rede: sem a folha das fontes, sem o
arquivo, só sem o itálico da Alegreya, com a folha que nunca responde e com um endereço
que pendura — o molde abre e o desenho sai no prazo, marcado "sem as fontes". O robô
data/robo/cards.py numa pasta temporária: a página b/<id>/ escapada, com a imagem e o
endereço inteiros (o ?v= vem dos bytes do card); a assinatura (refaz só o que mudou); o
que ele apaga e o que não apaga; a incompleta (tenta de novo, guarda o card que já
estava, atualiza os textos); cada build por si (a que quebra fica de fora e o Chrome é
reaberto; a fonte que falha tenta num Chrome novo); o orçamento de tempo; a lista de
página em página; o molde que não abre (sem Chrome órfão). No "link curto": fora do
Pages, o curto segue #build/<id>; num GitHub Pages de mentira (pages_falso: a aba busca
https://brelgo.github.io/forja/… e o roteiro responde com os arquivos desta pasta, a
página gerada e o 404.html, como o Pages), o Copiar link copia b/<id>/ e fala do card,
a página e o 404.html levam à pública no app (com barra, sem barra, com index.html e
com barra a mais no começo), e o endereço errado ganha o Voltar; aberto do disco, o
caminho antigo. O arnês: a Sessao.envia espera a resposta do próprio pedido (o _anota
também manda comandos — o diálogo, o Pages de mentira — e subia o número). Duas rodadas
do cético (Opus xhigh): a 1ª, em três lentes com reverificação, confirmou 13 defeitos —
o mais grave, uma build publicada com o itemId "constructor" derrubava todas as rodadas
do robô — e a 2ª, sobre os consertos, achou 5 restos de gravidade baixa; todos
consertados com checagem. Vista falhando cada peça num mutante: P1 a P46, 47 de 47.
O item de suporte (F13-T95b, a opção B do Leo): a Dádiva dos Mundos e o que ela vira
saem da bigorna e vão para a fileira, com a bota (o virado no lugar da Dádiva; um inicial
só, para caberem três ícones). Três casos novos nas peças; vistos falhando os mutantes da
regra (P1 a P4, P31, P37, P38) e os novos P47 a P49.
A entrada da loja (F13-T97, 01/11/2026), grupo "entrada da loja": o posto de troca na
nevasca do Freljord (o conceito B da F13-T96) no lugar da placa. Com perfil limpo, a
fachada, a placa, a dica e o foco no #entrar; o clique de verdade em qualquer lugar abre
(as portas giram, a câmera anda, um som só) e fecha aos ~2,15 s; o clique no ID só
seleciona; o Enter abre uma vez; com menos movimento do sistema, nada de câmera e fecha
aos ~0,85 s; o link com # entra direto, mudo; fechada, nenhum quadro da entrada roda; e
nenhum new Audio fora do Som. A "fundação" confere a placa nova nas quatro resoluções
(textos exatos, IDs selecionáveis, tudo na tela, a letra como aparece na tela ≥ 10 px
nos rótulos e ≥ 12 px na nota e nos IDs), e o Sessao.entrar() espera a entrada fechar
em vez de um tempo fixo. A revisão do cético (Opus xhigh, duas lentes e uma
reverificação) achou nove defeitos, todos consertados com checagem: o 2º clique durante
a abertura atravessava a cena e abria a ficha de um item; com o "Menos movimento" da
loja a cena congelava e sumia de golpe; arrastar para selecionar o ID abria a loja; a
roda do mouse rolava a loja escondida; o Tab fugia para as abas escondidas; com a fonte
para dislexia o Riot ID saía cortado (a mais grave); o pulso da dica ocupava ~90% da
thread principal; a letra da placa caía abaixo do piso em 1366×768 e 1024×768; e a
janela da fachada baixava uma textura de 2,8 MB. Vista falhando cada conserto num
mutante: Q1 a Q9.

A Ficha da build (F13-T98, Leo: "os usuários gostaram mais do conceito 1"): o molde passa
a ser a Ficha — o retrato, as runas, a ordem das habilidades, os iniciais, o Core, a bota
e o suporte, os situacionais — e o grupo foi reescrito para ela. Os quadros, em 22 casos
montados do catálogo pelo tier (o Core sem Opcional e da Escolha só a 1ª; a bota e não a
peça; o virado da Dádiva em "Bota e suporte"; os iniciais com a sentinela, até 6; os
situacionais das Escolhas, só Lendário ou bota, sem repetir, até 15 e o "+ N"; sem
Lendário; fora do catálogo; "constructor"/"__proto__"/"toString"); a ordem das
habilidades em 9 casos (vale quem chega a 5 primeiro; só R, vazia, nula, lixo). O desenho
com builds do roteiro (as runas tiradas de data/runas.js): o retrato, a arte, as runas e
"sem runas" (também com runas que não existem), a ordem com os ícones e "sem a ordem", o
nome comprido numa linha com "…", sem campeão (o nome grande vira o da build), HTML no
nome, no autor e na descrição, o rodapé (sem "por" sem autor; o autor comprido cortado
dentro do card — o "cabe" contava esse corte como estouro, e o molde foi ajustado). A
rede: as fontes como antes e, novo, o JSON do campeão bloqueado (CDP) e o retrato
bloqueado — o desenho sai e "faltou" diz o quê. O robô: a assinatura e o pedido ao
servidor com as runas e as habilidades, a base com data/runas.js, a foto com "faltou"
dada por incompleta e tentada de novo. As 44 públicas renderizadas: 0 incompletas, 0
falhas, todas cabem. Vistos falhando, cada um numa cópia com o conserto desfeito, 19 de
19: no molde, os iniciais sem a sentinela, os situacionais até 16, a bota da Escolha fora
dos situacionais, a Dádiva no lugar do virado, a peça "Botas" no lugar da bota, o porSlug
num objeto comum, a ordem sem o 5º ponto e com as letras sem ponto, o "faltou" sem as
habilidades e sem o retrato, o nome da build sem escapar, o "por" sem autor, o nome da
build em várias linhas, o rodapé cortado contado como estouro, as runas tortas contadas,
o nome vazio sem campeão; no robô, os campos sem runas e habilidades, o falta_algo sem o
"faltou" e a base sem data/runas.js.

A entrada por região (F13-T99, 01/11/2026): a entrada sorteia a região a cada visita — o
Freljord, Noxus (o arsenal da praça) ou Shurima (a tenda das relíquias) —, e o parâmetro
?entrada=freljord|noxus|shurima força uma. O grupo "entrada da loja" roda inteiro em cada
uma das três, forçada pelo parâmetro (a fachada da região desenhada, o clique, o Enter, o
ID, o arraste no ID, o Tab, a rolagem, menos movimento do sistema e da loja, o #calc sem
montar a cena, o 2º clique, a thread principal parada, a letra em 1366×768 e 1024×768, a
dislexia), e a "fundação" confere a placa das três nas quatro resoluções. Novas: o peso
(o que a entrada usa — fundos, máscaras e <image> — tem menos de 300 KB cada, e a textura
de 2,8 MB nunca baixa); em Noxus a placa é pintada depois da camada da cinza (a cinza não
passa nem para em cima do texto); em Shurima o disco partido aparece uma vez só (a lasca
caída saiu); sem o parâmetro, 12 cargas dão pelo menos duas regiões e cada carga monta só
a sorteada (um tema, um <style>, nenhum molde sobrando, nada das outras). Vistos falhando,
cada um num mutante: o sorteio fixo, as três montadas juntas, a cinza de novo por cima da
placa de Noxus, a lasca de volta, o #calc montando a cena, as portas de Noxus sem o
"Menos movimento" da loja, o Discord errado só na placa de Noxus (a fundação), a textura
de 2,8 MB de volta e a placa sem o piso de escala (falha nas três).

O som e os quadros da abertura (F13-T100, 01/11/2026; Leo: "o som está mal sincronizado
com a animação de abertura" — chegava tarde; "tem vezes que os frames pulam"). Medido no
Chrome sem janela (que nesta máquina usa a RTX 3060): o open_catalog só começava a baixar no
clique, junto com os outros ~80 sons, e o "playing" chegava 0,2–1,0 s depois; agora a entrada
pede o arquivo dele enquanto está parada (Som.preparar, só preload — nada toca antes do
clique), o resto baixa depois da abertura, e o som começa em ~20–30 ms. O arquivo não tem
silêncio no começo (som a partir de ~30 ms, pico em 110–200 ms, junto da tranca, e outro em
310–330 ms, quando as folhas começam a girar): nada foi pulado nem deslocado. Os quadros: por
baixo da entrada, os 225 raios dos cards giravam sem parar (450 camadas na conta de cada
quadro da câmera); com a entrada de pé eles não giram e voltam ao fechar. A soma dos quadros
longos (> 34 ms) caiu ~40–55% em Noxus e Shurima (1440×900 e 1920×1080) e no Freljord em
1920×1080; no Freljord em 1440×900, ~15%. Novas no grupo "entrada da loja": o som pronto antes
do clique e tocando em até 80 ms dele; o clique não baixa os outros sons; a loja escondida não
gira os raios (e os 225 voltam depois); e os quadros das três regiões abaixo do teto de 200 ms
(melhor de duas) com a soma dos longos ao menos 20% menor que o comportamento antigo medido na
mesma rodada (os raios girando e os sons baixando no clique, injetados só naquela carga).
Vistos falhando: sem o Som.preparar (o som não está pronto e toca a 217–365 ms), o
pré-carregamento de volta no clique (82 áudios criados), os raios girando por baixo (225 no
meio da abertura) e o conserto inteiro desfeito (as quatro; a soma dos longos fica igual ao
comportamento antigo). O teto de 200 ms sozinho não separa: o de antes também passa nele.

As dicas na hora (F13-T101, 02/11/2026; a opção 2 do tour — Leo: "o tour não deve ser algo
massante", "pensando para um leigo"). O roteiro inteiro roda com elas desligadas: a barreira
da Sessao grava "dicas.desligadas" em toda carga, menos quando a aba tem "qa.dicas" no
sessionStorage — um balão aberto por cima de um botão comeria o clique de verdade dos outros
grupos. O grupo "dicas" liga e confere: com a entrada de pé nenhuma dica aparece, e ao fechar a
1ª da loja aparece (1 de 2) e a loja fica vista; "Próxima" passa; o clique fora do balão fecha e
segue para onde foi dado (a busca ganha o foco; a aba Runas abre e mostra a sua); o Esc fecha;
recarregando, as telas vistas não repetem; "Sem dicas" desliga as automáticas e o "?" ainda
mostra as da tela; o × fecha; nas três resoluções (1440×900, 1920×1080, 1600×900) cada uma das
7 dicas fica inteira na janela e não cobre o que aponta; a "Caixa vazia" da forja, que já usava a
classe .dica, segue intacta com o balão aberto (o primeiro desenho do balão usava .dica e a
transformava em balão — a medida pegou); com "Menos movimento" (o da loja e o do sistema) o anel
não pulsa; e nenhum texto de dica traz número. Vistos falhando, cada um num mutante: a dica com
a entrada de pé, o clique fora que não fecha, a tela vista que volta, o "Sem dicas" que não
desliga, o estilo do balão de volta na classe antiga, o balão que não vira de lado (cobre o
que aponta) e o anel pulsando com o menos movimento do sistema. A regra própria do anel
para o "Menos movimento" da loja saiu: o mutante mostrou que a regra geral já o parava.

A entrada casada com o som (F13-T102, 02/11/2026; Leo: "a duração da animação não é muito
sincronizada com o som" e "pega a duração do áudio e sincronize para a duração da animação").
O open_catalog dura 1,13 s e a cena, 2,15 s. Agora os primeiros 300 ms correm no tempo do som (a
tranca e o começo das folhas casam com os golpes aos 150 e 300 ms) e o resto da cena — as
animações finitas do CSS (playbackRate) e a câmera (o mesmo relógio da cena) — acelera pela
razão tirada da duração do áudio lida no clique (Som.duracao): o esmaecer acaba junto com o
som. Novas no grupo "entrada da loja": em cada região, a abertura fecha entre o fim do som (a
duração decodificada do próprio arquivo pelo roteiro) e 120 ms depois, com a câmera no fim do
zoom e a cena já esmaecida no último quadro; e, no Freljord, com um som fingido de 1,7 s, ela
fecha aos ~1,75 s (a duração vem do arquivo, não de um número escrito). Vistos falhando, numa
cópia da pasta (desde a T102 os mutantes não rodam na pasta do Leo: ele testou a entrada com um
mutante aplicado e viu a versão antiga): a duração escrita em vez da lida, a câmera no tempo
antigo e as animações do CSS no tempo antigo. Duas da T100 mudaram com a abertura curta: os
outros sons não baixam "até a abertura fechar" (em vez de "nos 1,5 s depois do clique"), e os
quadros longos somam no máximo 30% da abertura, na média — a comparação com o comportamento
antigo (cair 20%) virou ruído com as somas pequenas (137% numa rodada, 84% na seguinte).

O tour que ensina o Montador (F13-T103, 02/11/2026; Leo: "acho que tá muito pobre de conteúdo
esse tour" e "e a parte de importar? deve ensinar os principais funcionamentos do montador"):
24 dicas com id — as de chegada (até 4 por tela) e as da hora (o primeiro item, o Editar ligado,
o primeiro Salvar, o Montar das runas, a segunda visita). O grupo "dicas" foi reescrito: a loja
abre com as suas 4; "Próxima", o clique fora (que segue para a busca e para a aba Runas), o Esc
(a leva inteira fica vista; recarregar na mesma aba não traz nada, nem a dica da segunda visita);
"Sem dicas" e o "?" (as 3 da lista); os momentos, cada um na hora, numa segunda visita limpa
(loja 4 + a da volta; forja 4; Editar 3; o item na loja; os totais; o Salvar; o Publicar na lista;
runas 2; o Montar); nas três resoluções, as 24 dicas inteiras na janela, sem cobrir o alvo e com o
anel em volta dele (72 medidas), e a "Caixa vazia" intacta; a dica mostrada enquanto a tela entra
animada segue o alvo (a lista de builds sobe: o anel ficava abaixo do Importar — visto na captura,
consertado); quem viu as dicas da T101 só ganha as novas; menos movimento e nenhum número nos
textos. Vistos falhando, numa cópia da pasta, 11 mutantes: o Salvar que não vira momento, o
Editar que não chama as dicas, o F5 contando como visita, a memória da T101 ignorada, a leva que
não fica vista, o "quando" ignorado, o clique fora que não fecha, a dica com a entrada de pé, o
"Sem dicas" que não desliga, o balão que não vira de lado e o balão que não segue o alvo.

**Publicação órfã** (F13-T34, bug nº 42; servidor simulado, espera encurtada) —
com a publicação no ar, a build não se exclui (lista, forja, lote); despublicar
durante o "Atualizar publicação" espera; publicar durante uma exclusão no ar
espera; se a build some mesmo assim, a publicação recém-criada sai do site.

**Atualização** (F13-T33, bugs nºs 13 e 41) — abrir outra build depois de
recarregar não muda a "Última atualização" (e a publicada continua "Publicada");
uma mudança de verdade ainda carimba; o Mestre Forjador não acende a nota da
publicação; um Salvar durante uma publicação lenta acende; a build migrada do
formato antigo tem data.

**Última build** (F13-T32, bug nº 15) — com uma pública aberta, a última build
própria não se exclui (o Excluir desligado) e o "Fechar visualização" ainda
fecha; a exclusão da última própria não deixa cópia fantasma (e, desde a
F13-T53, nem uma "Build sem nome" no lugar); com uma visualização aberta, a
ativa gravada é a sua; o Excluir da forja numa visualização fecha sem
perguntar; a biblioteca gravada vazia não traz de volta a build do formato
antigo nem cria uma.

**Publicar** (F13-T30, bugs nºs 11, 12 e 26; servidor simulado) — o hidden
esconde sempre (Descartar sem rascunho, ⟳ em Minhas); o "+ Nova categoria" não
anda quando o rascunho aparece; durante "Publicando…" não há Fechar e o Enter
não manda outro pedido; depois de um erro o Enter fecha a placa; servidor lento:
o Fechar aparece (os 30 s encurtados trocando o relógio da página), a trava
segura e a resposta atrasada vale; a placa atrasada fica por cima do
"Alterações não salvas" e o Esc fecha só ela; ao salvar, o Descartar some na hora.

**Acessibilidade** — os quatro interruptores ligam, o "menos movimento" zera as
transições de verdade, e tudo sobrevive ao recarregar.
O daltonismo por tipo (F13-T50) é medido como a pessoa vê: o roteiro escolhe
cada modo com clique, lê a cor da faixa de núcleo dos cards de verdade (AD, AP,
Vitalidade) e passa as três pela simulação de Machado, Oliveira e Fernandes
(2009), com a tabela publicada em cada severidade de 0,1 a 1,0 (o pior caso
não é sempre a plena); a menor distância ΔE2000 entre elas tem
de ficar alta. A Geral não desce de 33 em nenhum dos três tipos (as cores do
jogo caem a 6; a Okabe-Ito de antes caía a 12 na tritanopia); cada tipo passa
de 40 no seu e ganha da Geral por 4 ou mais — senão o modo não teria razão de
existir. A ordem das habilidades (Q, W, E, R) é medida do mesmo jeito. E ainda:
a bolinha do menu é a cor que vai à tela, a calculadora segue a cor do núcleo,
o Desligado volta às cores do jogo e o "ligado" guardado antes vira a Geral.
Depois da revisão (F13-T50b): o texto da calculadora fica legível no papel
(contraste ≥ 4,5:1), as leituras alternativas da build seguem o núcleo, a brasa
da forja não muda, o menu se usa pelo teclado (Esc devolve o foco, Tab para fora
fecha, a explicação do tipo é anunciada) e cada tipo sobrevive ao recarregar.

**Bigorna** (F13-T51, o nº 39; a build sempre aberta, opção B do Leo) — a plaqueta sob a aba Builds nomeia a
build em todas as telas (loja, lista, forja, Runas, Calculadora); fora da forja diz "editando" e "● não salva";
no pior estado (nome de 63 letras, editando, não salva, caixa escolhida) nada estoura e o cabeçalho não muda de
altura em nenhuma resolução; o Ctrl+S salva da loja; "parar de editar" pergunta com rascunho e devolve o foco;
o nome leva à forja; renomear pelo campo muda a plaqueta e a faixa na hora; a faixa fica presa no topo ao rolar;
a gravação recusada aparece na hora; e uma pública aberta para ver não fica com o Editar ligado (o nº 40). E trocar
de aba com clique de verdade deixa a plaqueta 4 px depois da aba Builds em todas (F13-T86: a aba ativa é ~2 px mais
larga, e a plaqueta ficava atrás).

**Fechar a build** (F13-T52; Leo, 19/10/2026: "deveria ter uma opção de fechar") — o × da plaqueta fecha a
build (a plaqueta some, a build continua na lista, o disco não guarda build aberta, a aba Builds fica na lista,
o foco vai para a aba Builds); com rascunho, o × (o da plaqueta e o da faixa) pergunta antes; nada da build
fechada sobra na memória; sem build, o clique num item só abre a ficha (nenhuma pergunta, nada gravado); fechar
uma pública volta para a build de antes (ou para a bigorna vazia); e sem build as Runas só leem, a calculadora
não puxa, a forja não abre e o "Marcar em" fica parado.

**Entrada sem build** (F13-T53; Leo, 19/10/2026: "ao recarregar mantenha a build que já estava aberta, e o
primeiro acesso fica completamente vazio por conta do tour") — o primeiro acesso começa sem build nenhuma (nada
no disco; a lista diz "Nenhuma build ainda"); o F5 volta a build que estava aberta, e com a bigorna vazia fica
vazio; excluir a build aberta deixa a bigorna vazia, sem outra no lugar; e o #build-observacao sem build não
liga o Editar.

**Builds publicadas** — a lista vem do servidor e não traz "permission denied"; nenhuma desatualizada aparece
(a nota no pé diz quantas ficaram de fora); e o roteiro não registra evento no servidor de verdade.

**A barreira dos eventos** (F13-T56) — toda sessão do roteiro (e toda aba que ele abre) carrega, antes do app,
um `fetch` que responde "ok" ao `registrar_evento` sem sair da página. Antes, cada rodada (perfil novo, memória
limpa) registrava no Supabase do Leo uma "impressão" por build da aba Públicas — e a impressão alimenta a
popularidade. O contador `window.__eventosBarrados` mostra o que foi segurado.

**Públicas desatualizadas** (F13-T56; Leo, 19/10/2026: "builds marcadas como desatualizada não devem aparecer
nas públicas") — com uma lista montada no roteiro (sem servidor): a aba tira a desatualizada, nem na
popularidade; a nota diz quantas ficaram de fora; pelo ID exato a desatualizada ainda se acha, com a etiqueta;
e as impressões da lista ficam na página. Desde a F13-T61 desatualizada é a de **item mudado** desde o patch
dela (núcleo ou alternativa de uma Escolha 1): a de patch antigo sem item mudado, ou com ele só na Opcional,
continua na lista.

**Desatualizada só com item mudado** (F13-T61; Leo, 21/10/2026: "marcar como desatualizada builds que contêm —
opcional não conta — os itens que foram atualizados; builds que não têm nenhum item modificado se mantêm") — o
registro `data/mudancas.js` acompanha o catálogo (no 16.21.1, exatamente os 5 itens da entrega do Capítulo 1 —
ícone e fonte mudaram nos 225 e não contam); oito builds gravadas no disco e a página recarregada: ficam em
revisão a de item mudado no núcleo, na alternativa de uma Escolha 1, dois patches atrás, a de item que saiu e a
revisão gravada pelo código antigo com item mudado; não ficam a de item mudado só na Opcional, a de nada mudado e
a revisão antiga sem item mudado; a etiqueta só nelas, e no resumo da lista a borda no item que mudou; na forja, a borda vermelha (rgb 224, 80, 60) no item que
mudou e em nenhum outro, com a linha no balão e o aviso falando da borda; nas leituras alternativas também; a
Opcional não ganha borda; salvar fecha a revisão e tira a borda; e as cópias de uma pública desatualizada
("Copiar e editar" e o lote) herdam a revisão. Nos **Arquivos**, o `mudancas.js` tem de ser igual ao que o
`data/gerar_mudancas.py` gera agora — trocar o catálogo e esquecer o gerador acusa.

**Resoluções** — 2560×1440, 1920×1080 e 1600×900, a ordem do Leo, mais
1280×800 como piso de notebook: sem rolagem horizontal e nada fora da tela. E a grade de habilidades com casas
de 24 px ou mais, lendo e editando (F13-T59: ela dividia a linha com o nome e encolhia até 337 px — casas de
10 px em qualquer tela; o menor caso é 2560 editando e 1280 lendo).
**Celular não é alvo** (Leo, 21/09/2026: "não tenho a intenção de fazer para o
celular"): o app é ferramenta de mesa, e 375px não entra na conta — medido, a
página abre com viewport de 513px e os cards têm 281px fixos.

**Console** — nenhuma exceção e nenhum 404 durante o percurso inteiro.

## Achado na primeira volta — e consertado (21/09/2026)

Com as **38 builds publicadas na tela**, a página travava: o Chrome queimava um
núcleo inteiro e parava de responder por mais de um minuto. Acontecia nas duas
pontas — no navegador do roteiro e no navegador embutido, contra o site no ar.

Causa, medida por dentro: cada marcador de **habilidade** sem a lista do campeão
no cache pedia a lista ao Data Dragon e, na resposta, mandava redesenhar a lista
inteira. 38 linhas × até 3 marcadores = dezenas de pedidos, e cada redesenho
fazia os pedidos de novo. **`renderBuildIndex` rodava ~80 vezes em 4 segundos.**

Conserto: `pedirRedesenho()` junta os pedidos e redesenha **uma vez por quadro**.
De ~80 para **7**, a página continua respondendo e a arte da habilidade chega
igual. Duas checagens novas seguram isso: "sem tempestade de redesenho" e "a
arte da habilidade chega no marcador".

O grupo das públicas continua sendo o **último** do roteiro: é o estado mais
pesado do app, e depois dele qualquer medida sai contaminada.

## O que ele não faz

Não olha. Cor, alinhamento, peso da animação, se o card ficou bonito — isso
continua sendo captura de tela e o aprovado do Leo. O roteiro só garante que o
caminho ainda anda.
