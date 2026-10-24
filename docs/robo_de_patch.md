# Robô de patch

Pedido do Leo (16/10/2026): "precisamos fazer com que os itens e o conteúdo sempre sejam atualizados, mas sem depender do Claude para isso". Plano aprovado no mesmo dia (CHECKPOINT, seção 4): um robô que todo dia lê a fonte do Capítulo 1 e, em patch novo, aplica sozinho só o que é seguro e avisa o resto.

## As quatro partes

| Parte | Tarefa | O que faz | Estado |
|---|---|---|---|
| 1 | F13-T73 | **O leitor**: baixa a fonte, guarda a foto do patch e compara com o catálogo, sem mexer em nada | feita |
| 2 | F13-T74 | **A regra de segurança**: foto antiga × foto nova × catálogo; aplica só o que mudou na fonte **e** que o catálogo tinha igual à fonte antiga, numa camada à parte (`data/atualizacao_patch.js`); o resto vira "a conferir" | a fazer (o arquivo novo pede o aprovado do Leo: muda o esquema) |
| 3 | F13-T75 | **O app lê a camada** por cima do `catalog.js`, com o selo "patch novo: a conferir" | a fazer |
| 4 | F13-T76 | **No GitHub Actions**, todo dia; grava a camada e abre um aviso (Issue) com o que mudou | a fazer (enviar o robô e dar escrita a ele pedem o OK do Leo) |

O `data/Catalogo_Itens_LoL.md` (Capítulo 1) nunca é tocado pelo robô.

## Parte 1 — o leitor

```
python data/robo/ler_fonte.py            # baixa de novo
python data/robo/ler_fonte.py --offline  # usa o que já está em data/robo/fonte/_baixado
```

**Fontes** — as mesmas do Capítulo 1 (`Regras_de_Fonte.md` de lá):
- Data Dragon: `versions.json` (o patch do dia) e o `item.json` em pt_BR do patch;
- wiki do LoL: o `Module:ItemData/data`, pela API (`api.php?action=query&prop=revisions…`); a página HTML recusa robô.

**Saída**:
- `data/robo/fonte/<patch>/wiki_itemdata.json` — a tabela da wiki como veio (lida por `data/robo/lua_tabela.py`, sem resolver);
- `data/robo/fonte/<patch>/ddragon_itens.json` — do Data Dragon, os itens da Summoner's Rift e do ARAM, com nome, preço, receita e os dois mapas;
- `data/robo/fonte/<patch>/meta.json` — revisão da wiki (id, data, sha256), versão do Data Dragon, avisos do leitor;
- `data/robo/relatorio_<patch>.md` — fonte × catálogo, campo a campo.

O que vem cru (`data/robo/fonte/_baixado/`) fica fora do repositório.

**Leitura conferida por fora**: o número de entradas de 1º nível contado no texto tem de bater com o que o leitor leu; se não bate, nada é gravado. Chave repetida vale a última (como no Lua) e vira aviso — a wiki tem uma (`nickname` do Haunting Guise). A wiki escreve `=>Outro Item` para "igual ao Outro Item" (Muramana, Fimbulwinter…): o comparador resolve; referência sem destino vira aviso.

**Como compara** (por `wikiName` ou `nameEn`; o Data Dragon pelo `id`):

| Campo | Catálogo | Fonte |
|---|---|---|
| Id | `id` | `id` da wiki (a variante de ARAM leva 22xxxx na wiki) |
| Preço | `priceGold` | `buy` |
| Receita | `components` (× `qty`) | `recipe` |
| Atributos | `attributes` (stat + unidade) | `stats` (tabela de nomes em `ler_fonte.py`) |
| Modos | `gameModes` | `modes` (sem marca de Mayhem, segue o ARAM) |
| Efeitos com nome | `abilities[].nameEn` | `effects` pass/act |
| Grupo "Limitado a 1" | `condition` | `itemlimit` |
| Data Dragon | `id`, `priceGold`, `namePt` | existe, `gold.total` (de quem se compra), `name` |

O mesmo dado escrito de outro jeito não conta como diferença: o id 22xxxx, o preço 0 de item não comprável (o catálogo diz "não comprável"; o Data Dragon, `purchasable: false`), o grupo escrito por extenso ("1 efeito de Elixir por vez"), o efeito sem nome em português ("—") quando a wiki não tem o nome.

**Fonte dividida**: quando a wiki diverge e o Data Dragon bate com o catálogo, o relatório diz "o catálogo segue o Data Dragon" — foi a escolha do Capítulo 1 (pendências A1 e A2). O robô nunca troca esses campos sozinho.

**O que não compara**: os atributos que só o catálogo tem (saem do texto do efeito, não da tabela `stats`), o texto curado (Mecânica, Ápice, Passiva do Ornn, notas) e os itens da wiki fora dos 225 (Arena, Nexus Blitz, torres, tropas).

### O primeiro relatório (16.21.1, 24/10/2026)

334 itens lidos (334 contados por fora), revisão 4088750 de 21/10/2026 — a mesma que o Capítulo 1 usou. Os 225 do catálogo casam; **2 a conferir**, os dois antigos: a Aceleração de Habilidade do Atma (a entrada da wiki é a da Arena — a mesma raiz da A1) e a "Recuperação" do Berrante do Guardião (a wiki a guarda como atributo, `hp5flat` 20, e o catálogo tem o atributo e também o efeito com nome, como o Data Dragon em pt_BR). **3 com a fonte dividida**: preço e receita do Atma, preço da Redenção.

## QA

Grupo "robô de patch" do `docs/qa_roteiro.py` (sem navegador e sem rede): o leitor de Lua com um texto de prova (escapes, comentário longo, chave repetida, texto cortado), as referências `=>` (a sem destino e a que dá volta), as regras da comparação num catálogo de mentira e a conta refeita sobre a foto guardada — o relatório no repositório tem de dizer o mesmo que ela.
