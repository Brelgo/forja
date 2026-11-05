# O mapa de hoje — o que o jogo tem (F13-T113, parte 1)

Pedido do Leo (05/11/2026): "tem algo que não está certo… na saída do rio tem um arbusto no meio, não na borda,
isso é antigo… e tem as alterações das almas dos dragões no mapa". E: "você pode só extrair os mapas e trabalhar
nas malhas? aí sexta-feira a gente finaliza isso".

Tudo abaixo saiu do `Map11.wad.client` da instalação do LoL do Leo, com `data/extrair_mapa_do_jogo.py`
(imagens em `assets/mapa/`; as malhas de colisão em `data/mapa_variantes.js`; sem o Atakhan, que saiu do jogo). O app ainda não usa nada disso.

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

## 3. Decidido com o Leo

- **O Infernal muda só o covil do Dragão** (Leo, 05/11/2026: "só o covil, eu falei errado!"): a camada dele está
  certa, e as quatro paredes da selva queimadas que a imagem `infernal_baron1` mostra (captura
  `fase13-t113-diferencas.png`, embaixo à esquerda) são arte de uma temporada anterior. Na sexta, a imagem do
  Infernal é a de base com o covil do Dragão tirado da imagem dele (só a área da camada), para a figura não
  mostrar parede aberta que o jogo não abre.
- **A Quimtec** não tem imagem própria: a de base, com a camada dela.
- **A imagem do Infernal, na sexta: a de base.** O covil do Dragão na imagem dele é igual ao da base (nenhuma célula
  muda dentro da camada); só as paredes da selva mudam, e essas são as antigas. A parede do covil vem da camada.

## 3b. As malhas de colisão (Leo, 05/11/2026: "e as malhas de colisões?")

`data/mapa_variantes.js` (`window.MAPA_HOJE`, 48 KB), gerado pelo mesmo `data/extrair_mapa_do_jogo.py`: a malha de
base de hoje (a `AIPath_SRX_3`, no formato do `data/mapa.js`: paredes, arbustos e o que só para o passo) e, por
variante — `infernal`, `montanha`, `oceano`, `quimtec`, `barao2`, `barao3` —, as regiões que a camada do jogo troca,
com o tipo de cada célula já como o app usa. Conferido lendo o arquivo gerado de fora
(captura `fase13-t113-malhas.png`: cada variante por cima da imagem dela, as caixas em ciano são as regiões):
dentro das regiões, a parede da malha bate com a imagem da variante em 77% na Montanha (só a base: 70%), 83% na
forma 2 do Barão (65%), 82% na forma 3 (69%) e 90% no Oceano (90%: ele muda arbusto, que a imagem não desenha). O
Infernal fica em 44% (só a base: 81%) porque a imagem dele não mostra o covil novo — a camada é a fonte.

## 4. Para sexta (a parte 2)

- `data/gerar_mapa.py` passa a ler a `AIPath_SRX_3` (pede rodar de novo e conferir as sentinelas da QA).
- A imagem do minimapa de hoje no lugar do `map11.png`; o encaixe da grade sobre ela, medido como na T105.
- O seletor de alma e de covil no mapa: troca a imagem e aplica a camada na grade (a visão e a névoa seguem).
