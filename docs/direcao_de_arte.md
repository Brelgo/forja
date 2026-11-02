# Direção de Arte — Montador de Itens

> Aprovada pelo Leo em 13/09/2026 (Fase 1, Opção A — "Taverna e pergaminho"). Amostra de referência: `docs/amostras/fase1-amostra.html` (coluna A) e `docs/screenshots/fase1-tarefa2-amostra.png`. Este documento só cresce: nada aqui volta atrás sem novo aprovado.

## Briefing (do Leo, 13/09/2026)
- Catálogo = **loja medieval**: papel envelhecido (texturas em assets/textures), madeira, latão, um lojista que fala.
- Build = **forja**: ferro escuro, brasa, faísca, martelo.
- Do HTML anterior, **manter**: o efeito de hover dos ícones (aprovado como "maravilhoso"), a estrutura Catálogo / Build / Calculadora, a biblioteca de builds.
- Do HTML anterior, **abandonar**: a paleta e a aparência dos cards com ícones ("genérico, sem personalidade"); falta de animações.
- Animações de clique diferentes por tier; som por núcleo (AD / AP / Vitalidade) e por tier — ver docs/mapa_de_audio.md.
- Classe como 4 abas (TODOS · AD · AP · VITALIDADE), modelo Deadlock, com cor própria.

## Paleta (Opção A)
| Papel | Uso | Código |
|---|---|---|
| Papel | fundo de card, busca, barra de filtros, placa de entrada, pergaminho da Calculadora | `#e5d3ad` |
| Papel escuro | sombra/borda de papel, fundos secundários | `#cdb689` |
| Borda de papel | contorno dos cards | `#a88f60` |
| Tinta ferrogálica | texto principal sobre papel | `#2c1d12` |
| Tinta suave | texto secundário, nome em inglês, contornos de chip | `#5a4630` |
| Madeira | fundo do Catálogo (tábuas), painéis | `#3b2617` → `#2a1a0f` → `#21130a` (gradiente vertical, veios `rgba(0,0,0,.09)` a cada 11px) |
| Madeira escura | fundo geral da tela | `#1c120b` com linhas finas `#241810` |
| Latão | selo de Lendário, detalhes, títulos sobre madeira | `#b6873a` (claro `#d5b35a`, escuro `#8a5f18`) |
| Cera | preço, chip ativo, botão "Entrar na loja", carimbo "NO BUILD" | `#8d2c22` (borda `#5c150d`, sombra `#4a1109`) |
| Texto sobre madeira | títulos e legendas fora do papel | `#e8d3a2` (títulos), `#b89a66` (legendas), `#d9c08a` (rótulos de seção) |

Classe (`itemClass.core`), iguais no Catálogo e na forja:
| Classe | Cor |
|---|---|
| AD | `#c8641e` (laranja) |
| AP | `#7b4fb5` (roxo místico) |
| Vitalidade | `#4d8b3a` (verde) |
| AD e AP (só Filhote de Garrabrasa) | aparece nas abas AD e AP; faixa dividida laranja/roxo |

Forja (Build):
| Papel | Código |
|---|---|
| Ferro (fundo) | `#1a1614` → `#100d0b`, borda `#3a2f28` |
| Molde vazio | radial `#2b2521` → `#15110f`, rebites `#5a4d42` |
| Brasa | `#ff7a1e` (claro `#ffd27a`, glow `rgba(255,120,30,.55)`) |
| Placa de atributos | `#2a2420` → `#1a1512`, borda `#443a32`, números `#ffb257` |
| Interruptor ligado | trilho `#5a2a10`, botão radial `#ffd08a` → `#ff7a1e` |
| Título da forja | `#e9b36a`, Cinzel maiúsculo espaçado |
| Caixas da build (Fase 3, T5) | Comum ferro claro `#9a8875`; Prioridade latão `#c9973f` (não brasa: cansa os olhos em área grande, decisão do Leo); Opcional aço `#7f8a96`. Brasa `#ff7a1e` só em ações e realces pequenos. |

## Tipografia
- **Títulos** (nome do app, "Catálogo", nome do item no card, botão de entrada): `'IM Fell English SC', 'IM Fell English', Georgia, serif`, peso 400. Tamanhos: app 40px, seção 30px, card 18px.
- **Texto** (atributos, chips, legendas, busca): `'Alegreya', Georgia, serif`. 13–15px; itálico para nome em inglês e legendas.
- **Rótulos gravados** (selos, carimbos, títulos da forja, rótulos de seção): `'Cinzel', serif`, 9–14px, maiúsculas, espaçamento .15–.28em.
- Google Fonts com fallback serif; o app deve continuar legível sem internet (Georgia).

## Texturas e materiais
As três texturas são papel amassado quase branco; nunca usadas cruas. Aplicação: elemento com `background: var(--paper)` e um pseudo-elemento por cima com `background-image` da textura, `background-size: 420px`, `mix-blend-mode: multiply`, `opacity .9`.
- As três texturas são **sorteadas** entre as superfícies de papel (decisão do Leo, 13/09/2026), não fixas por função: card = sorteio estável pelo slug do item (o mesmo item tem sempre o mesmo papel); modal = novo sorteio a cada abertura; busca, painel de filtros e abas de Classe = sorteio ao carregar. No CSS, toda superfície de papel lê `--tex-pick`, gravada pelo JS (`paperFor`/`randomPaper`).
- Madeira e latão são gradientes CSS (sem imagem). Sombras fortes e quentes: `rgba(0,0,0,.55–.7)`.

## Componentes
**Card de item (Catálogo)**: papel (textura 01), borda `#a88f60`, sombra 0 4px 10px; grade 56px (ícone) + texto; faixa vertical de 6px na cor da classe à esquerda; nome em IM Fell English SC 18px, nome em inglês + classe em itálico suave; preço em cera à direita; atributos em lista com travessão "—"; ícone em moldura 2px `#5a4630` sobre `#1b120a`. Tier em **selo** no canto inferior direito: Lendário = cera dourada radial (`#d5b35a` → `#8a5f18`) com letra L; Básico = círculo vazio de tinta suave com B. (Os demais tiers definem seu selo na Fase 2, na mesma lógica: cera colorida para os raros, tinta para os comuns.) Estados: **hover** = o efeito aprovado do HTML anterior (inclinação 3D + brilho), com o brilho na cor de latão claro `rgba(232,200,120,.45)` e contorno `#d8b96a`; **já no Build** = opacidade .45, leve dessaturação, carimbo inclinado "NO BUILD" em cera. O card **não** traz a marca "Mestre Forjador" (decisão do Leo, 13/09/2026): elegibilidade fica no filtro lateral e no modal. Selos por tier (implementado na Fase 2, T2): Lendário e Lendário (Evolução) latão `#b6873a`; Épico e Épico (Evolução) azul `#3f5a8a`; Evolução vinho `#7a2f5a`; Bota `#7a4a2a`; Trinket `#a56a2c`; Consumível `#3d6b4a`; Distribuído `#6f6a66`; Starter e Básico tinta `#5a4630`. Nome limitado a duas linhas; preço nunca desce de linha.

**Chip de filtro**: etiqueta arredondada (999px) com contorno 1.5px de tinta sobre papel; ativo = fundo de cera, texto `#f4e6c4`.

**Abas de Classe**: TODOS em tinta; AD/AP/VITALIDADE com a cor da classe (definir forma na Fase 2, tarefa 3, seguindo a anatomia dos chips).

**Cabeçalho do Catálogo**: painel de madeira (tábuas), título em IM Fell English SC `#e8d3a2` com sombra 0 2px `#1a0d05`, busca em papel (textura 02) com sombra interna.

**Placa de entrada** (implementada na Fase 2, T10; textura sorteada como as demais): papel com borda dupla 3px de tinta suave, correntes (barras listradas `#7a6a4a`/`#3a2e1c`) presas ao topo, título 40px, frase em itálico, botão "Entrar na loja" em cera com relevo (sombra 0 3px `#4a1109`).

**Slot da forja (Build)**: quadrado com raio 6px, fundo radial de ferro, sombra interna funda, rebites nos cantos; preenchido = contorno `#6a3a18` + glow de brasa, ícone a 68% com borda `#7a4a20`, 3 faíscas (`#ffd27a`, sombra `#ff9b2f`); vazio = texto itálico "molde N" em `#5f5248`.

**Placa de atributos da caixa**: ferro escuro com linhas tracejadas `#3a3029`, título Cinzel `#b89a72`, valores `#ffb257`.

**Interruptores (Reembolso, Ápice, Mestre Forjador, Editar)** (Fase 3): trilho 36×19px na barra da build; desligado ferro, ligado brasa com glow; rótulo em Cinzel.

**Controle de som (Fase 4)**: sino de balcão em latão no cabeçalho (brasa na forja) que silencia/reativa, com régua de volume ao lado; riscado quando mudo, apagado antes de entrar na loja.

**Forja consolidada (Fase 3)**: bancadas de ferro com placa de tipo (ferro/latão/aço), moldes com rebites e brasa (placa MF apagada = elegível, acesa = o único item forjado, escolhido clicando no ícone do molde na edição; placa ÁPICE), tooltip e editor de observação em placa de ferro com borda de brasa, placas "Atributos da caixa" e "Atributos da build" (números em brasa clara, MF em latão, Ápice em brasa), picker em papel de balcão. Animações: molde levanta ao pegar, placa de pedra cai ao soltar (bancada treme, baforada de brasa), brasa apaga e placa afunda ao remover; loja ↔ forja com o fundo escurecendo/clareando e a vista subindo/descendo.

## Animações (a definir nas Fases 2–3, dentro desta paleta)
- Catálogo (implementado na Fase 2, T9): uma animação de clique por tier, 350–750 ms, só CSS sobre o DOM — cera derretendo no selo (Lendário e Lendário (Evolução)), carimbo batendo (Starter, Básico), tinta espirrando do ponto do clique (Épico e Épico (Evolução)), página virando (Consumível), sino de balcão (Trinket), moeda girando no ícone (Distribuído), bota batendo (Bota), brasa acendendo no ícone e na faixa (Evolução). Respeita prefers-reduced-motion.
- Forja: pegar = molde acende; arrastar = faíscas seguem; soltar = martelada (som na Fase 4); remover = brasa apaga.
- Transição loja → forja: o papel escurece e o ferro sobe de baixo (sair da loja, entrar na forja).

## Campeão da build (Fase 7, T2 — 14/09/2026)
- Retrato do campeão (Data Dragon, mesma versão do catálogo) em medalhão redondo de 46 px antes do nome da build, borda de latão #c9973f com brilho fraco; na barra da biblioteca, versão de 26 px dentro do botão "Campeão". O seletor é próprio (não o `<select>` do sistema): painel de ferro com busca e lista em 3 colunas, cada campeão com retrato de 30 px em medalhão de latão; o escolhido leva borda de latão e tinta de brasa; "Todos os campeões" ocupa a primeira linha com o símbolo ∞. Sem campeão, nada aparece no cabeçalho (a build vale para todos).

## Arsenais — lista de builds (Fase 7, T3 — 14/09/2026)
- A aba Build abre numa tabela de ferro (mesma placa da forja): cabeçalho gravado em Cinzel (Nome · Campeão · Modo · Itens), linhas com o nome em IM Fell, o retrato do campeão em medalhão de latão de 36 px (∞ para todos), modo e contagem em Alegreya itálico, e duas ações discretas (⧉ ✕). Hover acende o nome em brasa; a build ativa leva um friso de brasa à esquerda. Referência: a tela "Arsenais" do cliente do LoL.
- Na forja, "‹ Arsenais" volta à lista e o nome da build ganha um seletor ▾ (painel de ferro igual ao de campeão) para trocar de build sem sair.

## Marcadores da build (Fase 7, T5 — 14/09/2026)
- Até três por build. Na forja, três quadrados de ferro (40 px, borda tracejada quando vazios, latão quando cheios) ao lado do nome; na lista de Arsenais, a coluna "Marcadores" com os mesmos ícones a 30 px. Os SVGs dos marcadores padrão são os do Deadlock, colocados pelo Leo em `assets/Icon/panorama/images/builds`, usados nas cores originais sobre o ferro; habilidades e itens levam moldura de latão.
- Diálogo "Selecionar marcador": placa de ferro centrada, filete de brasa no topo, título em IM Fell, três grupos rotulados em Cinzel gravado (Marcadores padrão · Habilidades · Itens no guia), células de 54 px que acendem em brasa no hover e ganham borda de latão quando são a escolha atual.

## Tela "Builds" (Fase 8, T1 — 14/09/2026)
- Referência: "Explorar guias" do Deadlock, traduzido para a forja. Título em IM Fell, abas Minhas/Públicas como lingüetas de ferro (a ativa com filete de brasa no topo), barra de ações e busca. Lista à esquerda em placa de ferro: retrato em medalhão de latão, nome em IM Fell, etiqueta pequena gravada em latão ("na forja"; depois "Popular hoje/da semana"), três marcadores, coração de favorita em brasa. Linha selecionada: friso de brasa à esquerda e fundo levemente aceso.
- Detalhe à direita: placa de ferro com filete de brasa no topo, retrato grande, marcadores com rótulo em fichas de ferro (vazios tracejados), metadados gravados em Cinzel (versão, ID, última atualização), descrição em Alegreya, itens em molduras de latão, botões da forja. Descrição na forja: caixa escura sob o nome, em itálico até ganhar foco.
- Chuva de entrada: a tela aparece por pingos — círculos que crescem em pontos aleatórios e revelam o conteúdo, como tinta molhada, em menos de um segundo.

## Publicação e aba Públicas (Fase 8, T2–T4 — 14/09/2026)
- Placas de publicação: a mesma placa de ferro dos diálogos, filete de brasa no topo enquanto "Publicando a build" (reticências animadas), filete verde #4d8b3a no sucesso, cera #8d2c22 no erro.
- Etiquetas da lista, todas gravadas em Cinzel miúdo: "Popular hoje" em brasa #ff7a1e sobre tinta escura, "Popular da semana" em bronze #7a5a1e, "desatualizada" em cera, "favorita" só contorno de latão, "publicada" em azul-aço #3b4a6b, "na forja" em latão.
- Na aba Públicas, o seletor de quantidade e o botão ↻ entram na barra de ações; o coração da linha acende em brasa quando favorita.

## Soltar em posição (Fase 8, T7 — 14/09/2026)
- Ao arrastar um molde sobre outro, o alvo abre um vão de 5 px para o lado e uma barra vertical de brasa com brilho marca onde a placa vai cair: à esquerda quando o ponteiro está na metade esquerda, à direita na outra metade. Sobre o vazio da bancada, sem barra: cai no fim.

## Layouts de build (Fase 9, T3 — 15/09/2026)
- **Tabuleiro** (padrão, o estilo do Leo) é a própria forja. A caixa **Escolha 1** empilha os moldes na vertical, com o primeiro em moldura de latão e o selo "padrão"; o **marco** da caixa é um badge de latão gravado ao lado do tipo.
- **Núcleo + bandeja**, **Trilha por fases** e **Grade categoria × custo** são leituras: cards menores em ferro com moldura de latão (ou da classe: AD laranja, AP roxo, Vitalidade verde), preço e tier gravados nos cantos. A bandeja é tracejada em azul-aço; na trilha, os marcos ficam sobre um trilho de ferro com pontos de brasa (bandeja em azul); a grade tem cabeçalhos nas cores das classes e a etiqueta da caixa na base de cada card.

## Grade de encaixes (Fase 9, T4 — 15/09/2026)
- Cada caixa do tabuleiro é uma grade de encaixes de 84 × 96 px com 7 px de vão; a largura da caixa é a das colunas. Encaixe vazio: retângulo tracejado no ferro escuro, apagado em visualização. Ao puxar o canto, a caixa acende em brasa e uma etiqueta "3 × 2" em brasa clara mostra a grade.

## Daltonismo por tipo (Fase 13, T50 — 18/10/2026)
- No menu de acessibilidade, o daltonismo é uma escolha: Desligado, Geral, Protanopia, Deuteranopia, Tritanopia. Cada fileira mostra as três bolinhas do núcleo (AD, AP, Vitalidade) daquele modo — quem não sabe o próprio tipo escolhe a fileira que mais separa. O modo troca só as `--loja-ad/ap/vit` (e a cor das letras Q W E R); tudo o que lê essas variáveis acompanha: faixa do card, abas de núcleo (o metal sai da cor por `color-mix`), estandarte, régua, calculadora, a borda do ícone nas leituras alternativas da build. A brasa da forja não muda (F13-T50b). Na calculadora, sobre o papel, o texto na cor do núcleo vira tinta tingida (45% da cor, ≥ 4,8:1); a cor pura fica na barra e nos filetes. O hover por núcleo fica com as cores do jogo (é intocável), e a bancada da oficina do AP continua violeta em todo modo.
- Os trios não são de gosto, são medidos (simulação de Machado et al., 2009, com a tabela publicada em todas as severidades de 0,1 a 1,0; menor ΔE2000 entre as três): Geral `#c03802` ferrugem · `#5a4aae` violeta · `#44bdaf` verdete (≥ 33,8 nos três tipos); Protanopia `#b70012` · `#247dbf` · `#42c421` (45); Deuteranopia `#fa8f46` · `#e784ff` · `#036651` (41); Tritanopia `#e70123` · `#6f33cc` · `#00bfb8` (41). A Okabe-Ito que a Geral usava antes caía a 12 na tritanopia. Mudar um trio pede refazer a conta: o roteiro de QA reprova abaixo dos limites.

## A entrada da loja por região (Fase 13, T96 — 01/11/2026)
- Escolhida pelo Leo: **o posto de troca na nevasca** do Freljord, `docs/amostras/fase13-t96-entrada-freljord-3.html` (ele escolheu primeiro o salão de madeira e gelo, `…-1.html`, e trocou no mesmo dia: "E pode trocar para a entrada b"; capturas das duas em `docs/screenshots/fase13-t96-entrada-freljord-opcoes.png`). O Freljord vem primeiro (a região preferida do Leo); as outras regiões seguem o mesmo molde.
- **Arte própria**, toda desenhada em SVG e CSS (nada de arte da Riot nem imagem da internet): a fachada cobre a tela (alvo 1440×900, depois 1920×1080 e 1280×800). Um posto de troca de troncos e peles, perto e com cara de loja: toldo de couro carregado de neve, galhada com runa no frontão, janela de postigos acesa, lenha, barril, marco rúnico e um escudo pendurado; dois braseiros acesos (a brasa da forja anunciando o app); aurora verde e violeta, montanha e pinheiros; nevasca.
- **A porta** é a protagonista: a tranca gira e sai do vão, as duas folhas em camadas giram nas dobradiças em CSS 3D, raios de luz e a poça quente crescem na neve, e a **câmera** avança por `requestAnimationFrame` com paralaxe (os braseiros de primeiro plano passam mais rápido); por trás, o interior com o lojista de elmo com chifres; um clarão quente dá lugar à loja. Com "menos movimento", as portas só esmaecem.
- **A placa** de contatos pendurada por cordas sob o toldo (madeira com o pergaminho), com os textos exatos do app; a nota "League of Legends · Atualização · patch" numa etiqueta logo abaixo; a plaqueta com a bigorna da Forja sobre a porta é a marca da loja.
- "(Clique em qualquer local para abrir)" discreto no pé, ao centro; abre com clique em qualquer lugar (menos nos IDs, que se selecionam) e com Enter; o som nasce nesse clique.
- **Noxus — o arsenal da praça** (F13-T99, `docs/amostras/fase13-t99-entrada-noxus.html`): torre de pedra negra com merlões de ponta de ferro, estandartes carmim rasgados, vitrine de armas em grade, portão de ferro com o ferrolho que corre e solta faíscas, céu de fuligem com o sol vermelho; cai cinza e sobem brasas. A chapa de ferro da placa e a etiqueta ficam por cima da cinza (camada própria, com a mesma câmera); o primeiro plano (braseiros, frades com corrente) passa na frente dela.
- **Shurima — a tenda das relíquias** (F13-T99, `docs/amostras/fase13-t99-entrada-shurima.html`): tenda de lona listrada entre colunas de arenito, o disco solar partido no alto do portal (sem a lasca no chão), a mesa e os jarros de relíquias, lanternas de latão, dunas e ruínas no poente; a areia corre no vento. A placa é a tábua com o papiro.
- **O sorteio** (F13-T99): cada visita sorteia uma das três regiões (o Freljord, Noxus, Shurima), com a mesma porta, câmera, dica e placa (as mesmas classes e textos); cada região é um molde (`<template>`) e só a sorteada é montada. `?entrada=freljord|noxus|shurima` força uma (o roteiro e as capturas).

## As dicas na hora — o tour (Fase 13, T101 — 02/11/2026)

O Leo escolheu a opção 2 entre duas amostras (`docs/screenshots/fase13-t101-tour-opcoes.png`, `docs/amostras_tour.py`): nada de passeio guiado ("o tour não deve ser algo massante", "pensando para um leigo"). Na primeira visita a cada tela, 1 ou 2 balões apontam o que importa ali, sem escurecer nada.

- **O balão veste a tela:** pergaminho da loja (a textura 02, tinta ferrogálica, rubrica em vermelho de cera, botão de lacre) na loja, nas runas e na calculadora; placa de ferro com rebites e o botão em brasa na forja e na lista de builds.
- **O anel:** contorno de latão (brasa, na forja) em volta do que a dica aponta, pulsando devagar; parado com "Menos movimento"; sem o halo com "Menos brilho".
- **A seta** sai do lado do balão voltado para o alvo; o balão fica à direita do alvo se couber, senão à esquerda, embaixo ou em cima, sempre inteiro na janela e sem cobrir o alvo.
- **Os textos** são de quem nunca montou uma build: o que fazer, não o nome da função. Nenhum número, nenhum dado de item.
- **Os botões:** "Próxima"/"Entendi" (o lacre), "Sem dicas" (sublinhado discreto), o × no canto. O "?" redondo do cabeçalho, ao lado das notas, mostra as dicas da tela de novo.
