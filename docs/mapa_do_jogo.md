# O mapa de hoje — o que o jogo tem (F13-T113, parte 1)

Pedido do Leo (05/11/2026): "tem algo que não está certo… na saída do rio tem um arbusto no meio, não na borda,
isso é antigo… e tem as alterações das almas dos dragões no mapa". E: "você pode só extrair os mapas e trabalhar
nas malhas? aí sexta-feira a gente finaliza isso".

Tudo abaixo saiu do `Map11.wad.client` da instalação do LoL do Leo, com `data/extrair_mapa_do_jogo.py`
(imagens em `assets/mapa/`, camadas em `data/mapa_camadas.json`; sem o Atakhan, que saiu do jogo). O app ainda não usa nada disso.

## 1. Por que o mapa estava errado

- **A imagem é a antiga.** O `map11.png` do Data Dragon é a arte de Summoner's Rift de antes das mudanças de
  parede e arbusto. O jogo traz o minimapa de agora (`2dlevelminimap_base_baron1`), 512 × 512, com as paredes
  transparentes.
- **A grade também era uma versão anterior.** O `data/gerar_mapa.py` lê a `AIPath_SRX_2` (a que o `map11.bin`
  cita). O jogo tem também a **`AIPath_SRX_3`**, e é ela que casa com o minimapa de hoje — nas saídas do rio as
  paredes e o arbusto mudam de lugar (captura `fase13-t113-grade-srx2-srx3.png`: à esquerda a SRX_2, à direita a
  SRX_3, as duas por cima do minimapa atual; rosa = parede da grade, verde = arbusto).
  Concordância parede × imagem, célula a célula: SRX_2 88,2%, **SRX_3 90,7%** (o resto é a borda: a imagem é
  desenhada e suavizada).

## 2. As variantes

| O que muda | Imagem | Camada de navegação |
|---|---|---|
| Alma do Infernal | `infernal_baron1` | `Infernal_SEASONAL` — só o covil do Dragão (2 regiões) |
| Alma da Montanha | `mountain_baron1..3` | `Mountain_SEASONAL` — o covil e 5 trechos da selva (6 regiões) |
| Alma do Oceano | `ocean_baron1..3` | `Ocean_SEASONAL` — arbustos e trechos (11 regiões) |
| ~~Alma da Nuvem~~ | — | nenhuma: as correntes de vento não mudam o terreno — fica de fora |
| ~~Alma Hextec~~ | — | nenhuma: só os portais, desenhados na imagem — fica de fora (Leo, 05/11/2026: "eu quero as almas que realmente afetam o mapa… o Hextec só adiciona portais") |
| Alma Quimtec | não tem imagem | `Chemtech` — 4 × 2 células no covil |
| Covil do Barão, forma 2 | `*_baron2` | `Tunnel_Base` (7 regiões) |
| Covil do Barão, forma 3 | `*_baron3` | `Cup_Base` (2 regiões) |
| ~~Covil do Atakhan~~ | — | — (o Atakhan saiu do jogo — Leo, 05/11/2026: "o atakhan foi removido"; os arquivos dele seguem no jogo, `NavGrid_AtakhanTop/Bot` e os adesivos, e ficam de fora) |

Conferido pela diferença entre as imagens: das células em que a imagem da Montanha difere da de base, 501 de 633
caem dentro das regiões da camada dela; a forma 2 do covil do Barão difere da base dentro da `Tunnel_Base` (356
de 454) e a forma 3 dentro da `Cup_Base` (118 de 136). As marcas da camada são as mesmas da grade (a 128 é o
rio). Captura `fase13-t113-almas.png`: cada variante, a imagem dela à esquerda e a grade com a camada à direita
(as caixas em ciano são as regiões).

## 3. Em aberto — para o Leo conferir no jogo

- **O Infernal:** a imagem do Infernal mostra quatro paredes da selva queimadas (abertas), mas a camada dele só
  mexe no covil do Dragão (captura `fase13-t113-diferencas.png`, embaixo à esquerda, em vermelho). Ou o jogo
  ainda abre essas paredes por outro caminho, ou a imagem ficou de uma temporada anterior. No jogo: com a alma
  do Infernal, essas paredes da selva se abrem?
- **A Quimtec** não tem imagem própria: na sexta, ela usaria a imagem de base com a camada dela.

## 4. Para sexta (a parte 2)

- `data/gerar_mapa.py` passa a ler a `AIPath_SRX_3` (pede rodar de novo e conferir as sentinelas da QA).
- A imagem do minimapa de hoje no lugar do `map11.png`; o encaixe da grade sobre ela, medido como na T105.
- O seletor de alma e de covil no mapa: troca a imagem e aplica a camada na grade (a visão e a névoa seguem).
