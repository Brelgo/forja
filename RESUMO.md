# Resumo — a Forja em uma página (19/11/2026)

Para começar uma sessão com pouco uso: ler o CLAUDE.md e **este arquivo**. O CHECKPOINT.md (≈320 mil caracteres) é o
histórico completo; leia só a seção que a tarefa pedir (procure pelo número `F13-T…` ou pela palavra).

## O que é e onde está
- **Site:** https://brelgo.github.io/forja/ · **repo:** Brelgo/forja (`main`) · **pasta:** esta. Versão no ar: `ATUALIZACAO` **13.137**.
- **O app:** `index.html` (tudo num arquivo, abre com dois cliques). Dados gerados em `data/` — `catalog.js` (225 itens,
  patch 16.23.1, do Capítulo 1, com `interactions` (bloco Interações[]), `scaling` (Escalonamento[], 225 de 225 desde 21/11; sem bloco = não conferido) e `costAnalysis.threshold100` (Limiar de 100%); nunca editar à mão), `runas.js`, `habilidades.js` (Capítulo 1.1), `mudancas.js`,
  `notas.js`, `mapa.js`, `regioes.js` (o `mapa_variantes.js` não é mais carregado desde a F13-T135). Sons em `assets/audio`, mapa em `assets/mapa`.
- **Servidor:** Supabase `okifbriwwxohkjxhqzfc` (builds publicadas, popularidade). SQL ou ação lá: só com o OK do Leo.
- **Robôs no GitHub Actions** (gravam no `main` — `git pull --rebase` antes de enviar): `robo.yml` (o patch, diário,
  é o "Update Tracker" na tela) e `cards.yml` (o card das builds no Discord, a cada 30 min, só `b/`).

## O que o app já faz
Entrada animada da loja (Freljord, Noxus, Shurima, Águas de Sentina e Ilha das Sombras sorteadas) · Catálogo com filtros, ficha do item (Shift), árvore de
receita · Build (forja) com caixas, arrastar, Passiva do Ornn, Reembolso, Ápice, rota com cadeado, runas, habilidades ·
Biblioteca (exportar/importar, texto do jogo) · Builds publicadas (link curto, card no Discord) · Calculadora ·
Aba Mapa (independente das builds): biblioteca de planos no navegador (novo, nome, descrição, busca, excluir; planos de visão com as suas sentinelas e, desde a F13-T137, planos de selva com a rota de farm e a primeira rota, marcas numeradas por clique, lado e full clear ou gank com a lane), só o mapa padrão, sentinelas com névoa viva (cada moita vê só a si mesma), Vidente com 500 · a forma do Kayn (ícone e card) · Update Tracker (os cartazes de "procurado" do que mudou em cada
patch) · Mural de notas · Dicas na hora · som com lojista, volume e mudo.

## Como cada tarefa anda
Implementar → `python -X utf8 -I docs/qa_roteiro.py` (roteiro inteiro, ~500 checagens, zero erro) → captura em
`docs/screenshots/` → mostrar ao Leo → **"aprovado"** → commit `F13-T<n>: …` com a linha `Notas: Adicionado|Ajustado|Removido — …`
→ `python -X utf8 -I docs/gerar_notas.py` → commit do CHECKPOINT + `data/notas.js` → `git pull --rebase` → push → conferir o
Pages. Amostra leva "(amostra)" no assunto do commit. Mutante só em worktree no scratchpad.

## O que falta (em ordem)
| Quando | O quê | Custo (Max) |
|---|---|---|
| **primeiro** | **F13-T138, as rotas na build de selva** (Leo, 22/11: opção **B**): a build com rota Selva liga um plano de Selva e mostra só o botão "Rotas da selva"; o clique abre os dois minimapas num balão | 4–6% |
| depois | **F13-T139, publicar os planos**: tabela própria no Supabase (SQL só com o OK do Leo), aba Publicadas, link próprio | 6–10% |
| depois | **Estudo do app instalável (PWA)** antes de construir (Leo, 21/11: "essa função exerce mais do que qualquer criador consegue imaginar"): o que a instalação dá além de um site comum | estudo |
| final | **O app com overlay** só de builds (Leo, 21/11): na seleção de campeões, builds de outros usuários do campeão escolhido, informação rápida, counters (do Gerador) e os minimapas; na partida, ordem de level up, rota e a fila de itens com o ouro que falta. Só depois de o resto estar todo funcional. Exige app nativo (um PWA não desenha sobre o jogo) e a política de apps de terceiros da Riot | — |
| depende | Capítulos de dado 1.1–1.4 (campeões, Bestiário, Gerador) e a calculadora de monstros épicos | — |

## Esperando o Leo
- Regra do catálogo (Leo, 10/11/2026): **o arredondamento da Passiva do Ornn não conta como mudança** (`gerar_mudancas.py` compara o bônus arredondado para baixo).

## Regras que mais pegam
- Nada de dado digitado: o que o catálogo não tem é pedido ao Capítulo 1 (item) ou 1.1 (campeão).
- Nunca ler, mostrar ou digitar token (GitHub, Supabase); nunca publicar ou registrar evento no servidor real em teste.
- Pop-up: só fechar. Não abrir o Opera GX. Não propor de novo o ajudante de runas no cliente.
- Medir em 1440, 1080 e 900 (celular não é alvo). Testar arrastar e duplo clique com mouse real (CDP).
- Com o plano Max acabando (07/11 17:00), um plano menor pede tarefas ainda menores: uma coisa visível por sessão.
