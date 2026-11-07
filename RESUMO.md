# Resumo — a Forja em uma página (07/11/2026)

Para começar uma sessão com pouco uso: ler o CLAUDE.md e **este arquivo**. O CHECKPOINT.md (≈320 mil caracteres) é o
histórico completo; leia só a seção que a tarefa pedir (procure pelo número `F13-T…` ou pela palavra).

## O que é e onde está
- **Site:** https://brelgo.github.io/forja/ · **repo:** Brelgo/forja (`main`) · **pasta:** esta. Versão no ar: `ATUALIZACAO` **13.122**.
- **O app:** `index.html` (tudo num arquivo, abre com dois cliques). Dados gerados em `data/` — `catalog.js` (225 itens,
  patch 16.21.1, do Capítulo 1; nunca editar à mão), `runas.js`, `habilidades.js` (Capítulo 1.1), `mudancas.js`,
  `notas.js`, `mapa.js`, `mapa_variantes.js`, `regioes.js`. Sons em `assets/audio`, mapa em `assets/mapa`.
- **Servidor:** Supabase `okifbriwwxohkjxhqzfc` (builds publicadas, popularidade). SQL ou ação lá: só com o OK do Leo.
- **Robôs no GitHub Actions** (gravam no `main` — `git pull --rebase` antes de enviar): `robo.yml` (o patch, diário,
  é o "Update Tracker" na tela) e `cards.yml` (o card das builds no Discord, a cada 30 min, só `b/`).

## O que o app já faz
Entrada animada da loja (Freljord, Noxus, Shurima e Águas de Sentina sorteadas) · Catálogo com filtros, ficha do item (Shift), árvore de
receita · Build (forja) com caixas, arrastar, Passiva do Ornn, Reembolso, Ápice, rota com cadeado, runas, habilidades ·
Biblioteca (exportar/importar, texto do jogo) · Builds publicadas (link curto, card no Discord) · Calculadora ·
Aba Mapa (independente das builds: o plano fica no navegador): o mapa de hoje (alma do Dragão e covil do Barão mudam o terreno), sentinelas com névoa viva (cada moita vê só a si mesma), Vidente com 500 · a forma do Kayn (ícone e card) · Update Tracker (os cartazes de "procurado" do que mudou em cada
patch) · Mural de notas · Dicas na hora · som com lojista, volume e mudo.

## Como cada tarefa anda
Implementar → `python -X utf8 -I docs/qa_roteiro.py` (roteiro inteiro, ~500 checagens, zero erro) → captura em
`docs/screenshots/` → mostrar ao Leo → **"aprovado"** → commit `F13-T<n>: …` com a linha `Notas: Adicionado|Ajustado|Removido — …`
→ `python -X utf8 -I docs/gerar_notas.py` → commit do CHECKPOINT + `data/notas.js` → `git pull --rebase` → push → conferir o
Pages. Amostra leva "(amostra)" no assunto do commit. Mutante só em worktree no scratchpad.

## O que falta (em ordem)
| Quando | O quê | Custo (Max) |
|---|---|---|
| **primeiro** | **O catálogo no 16.22.1** (Capítulo 1 entregou em 07/11; está no ramo local `catalogo-16.22.1`, não publicado). Já feito: o catálogo copiado, o gerador lê o campo novo `Interações[]` (72 de 72; OK do Leo), `catalog.js` e `mudancas.js` gerados. O Leo escolheu deixar a Passiva do Ornn arredondada contar como mudança: 76 itens no 16.22.1, 70 só por ela — **consequência a confirmar com ele: as 44 builds publicadas ficam desatualizadas e a lista Públicas esvazia.** Falta: consertar 12 falhas do QA (os testes do robô presos ao 16.21.1, o Update Tracker, as Públicas, uma de redesenho), conferir o robô de patch no 16.22.1, captura, aprovado, merge no `main` | 4–6% |
| depois | **O grupo "duas abas" da QA falha às vezes** (2 de 3 no código da T113; os testes do 16.22.1 já foram consertados em 07/11). Diário na aba antes de teorizar | 2–3% |
| quando o Cap. 1 entregar | **Filtro "Escala com"** (PdH, DdA, Vida, Mana, Armadura, RM) no grupo Atributo, com Maior/Menor pela porcentagem. Com a base (base · bônus · total · máxima) à vista e filtrável. Espera a **D5** de `docs/pendencias_capitulo1.md` (Leo, 06/11/2026: adição ao Capítulo 1, não leitura do texto) | 2–3% |
| próxima | **A Ilha das Sombras: amostra feita (07/11, `ae65b2d`)** — `docs/amostras/fase13-t122-entrada-ilha-das-sombras-a.html` (o Relicário de Helia; juiz A 7,6 · B 6,8; capturas `fase13-t122-sombras-*`). **Aprovada pelo Leo (07/11: "escolho A").** Falta a integração como em Águas de Sentina (`<template id="en-tema-sombras">`, `TEMAS`, `REGIOES`, QA da entrada) | 3–5% |
| depois | **Planos de mapa** (desde a T119 há um plano só, no navegador; tirar o `mapa` que as builds antigas ainda guardam; biblioteca própria Minhas/Publicadas, tabela própria no Supabase, link próprio; só a Selva liga com build) | grande |
| depois | Calculadora de armadura · app instalável (PWA) · "Mandar para o jogo" · overlay (para pensar) | — |
| depende | Capítulos de dado 1.1–1.4 (campeões, Bestiário, Gerador) e a calculadora de monstros épicos | — |

## Esperando o Leo
- Conferir no navegador dele se o Freljord ainda pula quadros em 1440×900.

## Regras que mais pegam
- Nada de dado digitado: o que o catálogo não tem é pedido ao Capítulo 1 (item) ou 1.1 (campeão).
- Nunca ler, mostrar ou digitar token (GitHub, Supabase); nunca publicar ou registrar evento no servidor real em teste.
- Pop-up: só fechar. Não abrir o Opera GX. Não propor de novo o ajudante de runas no cliente.
- Medir em 1440, 1080 e 900 (celular não é alvo). Testar arrastar e duplo clique com mouse real (CDP).
- Com o plano Max acabando (07/11 17:00), um plano menor pede tarefas ainda menores: uma coisa visível por sessão.
