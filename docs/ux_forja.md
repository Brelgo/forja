# O que confunde na forja

Levantamento feito antes de mexer em qualquer coisa (Fase 12, T2). Cada ponto tem o que é, por que confunde e onde está a prova no código — nada aqui é palpite sobre gosto, é coisa que dá para verificar abrindo o app.

Ordenado pelo que eu acho que dói mais. A ordem de execução é sua.

## 1. Tudo fica trancado até você achar o interruptor "Editar" — RESOLVIDO (F12-T2, 18/09/2026; F13-T76, 25/10/2026)

Abrindo uma build, não dá para renomear caixa, criar caixa, arrastar item nem remover nada. O único aviso é uma frase que aparece **no card vazio** (`body:not(.editando) .build-empty::after`) — e ele some no instante em que a build tem uma caixa. Ou seja: quem mais precisa do aviso (quem abriu uma build já montada e quer mexer) é exatamente quem não o vê.

**Proposta:** o aviso sai do card vazio e vira uma faixa junto do interruptor, visível sempre que a edição está desligada. Uma linha: "Modo leitura — ligue Editar para mexer".

## 2. Três verbos escondidos num balão — RESOLVIDO (F13-T3, 22/09/2026)

Duplo clique abre a observação do item, botão direito remove, arrastar move para outra caixa. As três coisas existem só no tooltip que aparece parando o mouse sobre o item (`.tt-hint`). Quem não para o mouse, não descobre; quem descobre, precisa lembrar.

**Feito:** no hover, o molde mostra uma faixa de ferro embaixo com dois botões — ✎ observação e ✕ tirar da caixa. Duplo clique, botão direito e arrastar continuam valendo: verbo visível não tirou o atalho de ninguém.

Três coisas que só apareceram olhando renderizado: o "✎" como texto virava **emoji colorido** (a única coisa de desenho infantil na tela) e foi refeito em SVG de traço; os botões nos cantos de cima **comiam a arte do item**, então desceram para a faixa; e com nome de três linhas a faixa deixava o texto aparecer por trás — agora ela é opaca e o nome desbota no hover, já que o balão mostra o nome inteiro.

## 3. O rótulo da caixa é um botão que dá a volta — RESOLVIDO (F13-T4, 22/09/2026)

`COMUM` → `PRIORIDADE` → `OPCIONAL` → `ESCOLHA 1` → `COMUM`, um clique de cada vez. Parece etiqueta e é controle. E para voltar um passo você dá a volta inteira.

**Feito:** o clique abre um menu com os quatro, o atual marcado com ✦, e **cada um dizendo o que faz** — texto escrito lendo o código (`itensContados`, `buildTotal`, `catCols` e os layouts da Fase 9), não de memória. Some a volta olímpica: qualquer tipo fica a um clique de qualquer outro.

O menu fecha ao clicar fora, no Esc, e ao rolar ou redimensionar — ele é ancorado no botão, e ficaria solto no ar.

## 4. Adicionar item pede um passo invisível antes — RESOLVIDO (F12-T2: o clique pergunta a caixa; F13-T51: a faixa diz a build e a caixa)

Para o clique no catálogo marcar um item, é preciso **antes** selecionar a caixa na forja. Sem caixa selecionada, o clique abre a ficha do item — e parece que não funcionou. A faixa "Forjando em X" (F10-T3) resolve o *depois*: ela só aparece quando você já acertou.

**Proposta:** sem caixa selecionada, o clique no item pergunta em qual caixa colocar, em vez de abrir a ficha. E o seletor "Marcar em" ganha um estado de convite quando está vazio.

## 5. O que você edita não está salvo — RESOLVIDO (F13-T51: a plaqueta "● não salva" na faixa e o Salvar aceso)

Em modo Editar as mudanças ficam em rascunho: `saveBuild()` só marca "não salvo" e quem grava é o botão Salvar (ou Ctrl+S). Existe o aviso ao sair, mas o estado "tem coisa não salva" mora numa palavra pequena ao lado do botão.

**Proposta:** com rascunho sujo, o botão Salvar fica aceso e a barra ganha uma marca clara. Nada de salvar sozinho — a decisão de quando gravar é sua, e mudá-la seria mexer no que já foi aprovado.

## 6. Os marcadores não dizem para que servem — RESOLVIDO (F13-T79, 25/10/2026)

Três espaços com `+`. O que eles fazem — filtrar na lista, aparecer na vitrine, e serem obrigatórios para publicar — não está escrito em lugar nenhum da forja.

**Proposta:** uma linha de ajuda ao lado do rótulo, como a que o popup de publicação já usa.

## 7. A alça de redimensionar não tem pista — RESOLVIDO (a alça fica à vista enquanto o Editar está ligado; some sem ele)

A caixa encaixa em ¼, ⅓, ½ e 1/1, mas isso só está no `title` da alça. Sem arrastar, ninguém sabe que existe.

**Proposta:** a alça fica visível (não só no hover) enquanto a edição está ligada.

---

## O que eu não vou mexer sem você mandar

- O interruptor Editar em si: ele foi decisão sua na Fase 3 (dois modos, visualização e edição).
- O rascunho não virar gravação automática.
- O efeito de hover dos ícones, a estrutura de três telas e a biblioteca — intocáveis por regra.
