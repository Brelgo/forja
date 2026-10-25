# Robô de patch

Pedido do Leo (16/10/2026): "precisamos fazer com que os itens e o conteúdo sempre sejam atualizados, mas sem depender do Claude para isso". Plano aprovado no mesmo dia (CHECKPOINT, seção 4): um robô que todo dia lê a fonte do Capítulo 1 e, em patch novo, aplica sozinho só o que é seguro e avisa o resto.

## As quatro partes

| Parte | Tarefa | O que faz | Estado |
|---|---|---|---|
| 1 | F13-T73 | **O leitor**: baixa a fonte, guarda a foto do patch e compara com o catálogo, sem mexer em nada | feita |
| 2 | F13-T74 | **A regra de segurança**: foto antiga × foto nova × catálogo; aplica só o que mudou na fonte **e** que o catálogo tinha igual à fonte antiga, numa camada à parte (`data/atualizacao_patch.js`, aprovada pelo Leo em 24/10/2026); o resto vira "a conferir" | feita |
| 3 | F13-T77 | **O app lê a camada** por cima do `catalog.js`, com o selo "patch novo: a conferir" | a fazer |
| 4 | F13-T78 | **No GitHub Actions**, todo dia; grava a camada e abre um aviso (Issue) com o que mudou | a fazer (enviar o robô e dar escrita a ele pedem o OK do Leo) |

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

## Parte 2 — a regra de segurança

```
python data/robo/aplicar_patch.py                 # do patch do catálogo à foto mais nova
python data/robo/aplicar_patch.py --para 16.22.1
```

A foto "antiga" é a do patch do catálogo (`catalog.js` → `meta.patch`); a "nova", a mais recente em `data/robo/fonte/`. Campo a campo, item a item:

| Caso | O que o robô faz |
|---|---|
| a fonte que o catálogo seguia mudou, e o catálogo estava igual a ela | **aplica** o valor novo na camada |
| a fonte que o catálogo segue não mudou (a outra pode ter mudado) | nada — o Atma segue o Data Dragon; a wiki mudar não mexe nele |
| o catálogo não seguia a fonte antiga | **a conferir** |
| as fontes que o catálogo seguia divergem agora (uma mudou, a outra não) | **a conferir** |
| a fonte não tem mais o dado (o valor novo é nada ou vazio) | **a conferir** — nunca vira valor |
| o item sai do Data Dragon da Summoner's Rift e do ARAM (ou muda de id), a wiki o tira de todos os modos, ou tem referência `=>` sem destino | **a conferir** o item inteiro |
| atributo que o robô não lê (chave nova, valor que não é número — o `true` do Lua também) ou a tabela de atributos que some | **a conferir** — não vira "o item não tem"; o atributo ilegível segura o item inteiro (pode ser edição pela metade) |
| item com nota no preço ("não comprável", "gratuito", "aprimoramento gratuito; valor de venda…") | o preço é **a conferir** (o número e a nota são do Capítulo 1) |
| número que triplica, cai a um terço, vai a zero ou sai do zero (preço ou atributo, em qualquer das fontes — medido na fonte, antes de decidir); atributo que entra com 0 ou menos, acima do maior ou abaixo do menor que o catálogo tem; atributo que muda para mais de 1,5 × o maior (ou menos de ⅔ do menor) do catálogo — o dígito a mais na frente, 55 → 155 | **a conferir** — e o item inteiro espera: no dia de patch a wiki passa por edições no meio do caminho ("Letalidade 1038", 21/10/2026) |
| chave de atributo que sai e outra da mesma família que entra (plano ↔ percentual: `msflat`/`ms`, `mpenflat`/`mpen`, `hp5flat`/`hp5`, `lethality`/`armpen`) | **a conferir** — a unidade mudou |
| chave de modo (das que o robô lê: Summoner's Rift, ARAM, Mayhem) que some, entra ou muda de nome | **a conferir** — a wiki mudou a forma da tabela, não "o item saiu do modo" |
| receita e nome em português | **a conferir** — a receita muda o "Vira componente de" dos outros itens, e o texto do Capítulo 1 cita nomes ("Limitado a 1 Tiara Sussurrante") |
| texto de efeito, grupo/limite, item que sai ou muda de nome em inglês; o tier (`type`/`tier`), a condição de compra (`req`), o valor de venda (`sell`/`sellratio`) e o atributo em texto livre (`stats.spec`, a Vida ao contato da Abatedora) | **a conferir** (é texto do Capítulo 1) |
| item novo no jogo (Summoner's Rift ou ARAM), o que volta (a wiki já tinha a entrada, sem SR nem ARAM) e o que só o Data Dragon traz | listado em "novos" — entra pelo Capítulo 1 (a variante de um item do catálogo — o mesmo nome, ou o id 22xxxx/32xxxx/66xxxx/77xxxx/12xxxx de um item do catálogo — não é item novo) |

Campos que o robô sabe aplicar: preço (wiki e Data Dragon), cada atributo da tabela `stats` (inclusive o que entra ou sai, com a tabela legível) e modos (a wiki e os mapas 11/12 do Data Dragon — o catálogo segue os dois em 212 dos 225 itens). Refeito pela fórmula do próprio dado: o preço de componente nos itens que o usam, o custo de combinação (preço − componentes; só com o preço do item resolvido, se a conta antiga fechava, e conferido contra o `gold.base` do Data Dragon — se não bate, a conferir) e o Reembolso (a porcentagem do campo). O resto que depende de regra do Capítulo 1 — análise de custo e eficiência, eficiência no Ápice, soma por núcleo, Passiva do Ornn, categoria de atributo (quando um atributo entra ou sai) — fica marcado como **conta do patch anterior** (`contaVelha`), para o app avisar (parte 3) e o Capítulo 1 refazer. Se o que mudou é um item de referência do valor em ouro dos atributos (`meta.statPrices`: a Espada Longa dá o valor do Dano de Ataque), a análise de custo e o núcleo de **todo** item com atributo ficam marcados, e a camada diz quais referências mudaram (`statPricesVelhos`) — os fragmentos do Aumento de Atributo (atributo × valor em ouro) também. Todo número que muda — atributo, preço, custo de combinação, Reembolso, preço de componente — marca também o texto do item que o cita (Mecânica, Ápice, notas, notas de ARAM e de Mayhem: "13,75 só com os 550 de Vida do item", "2.250g ÷ 2.300g", "55 + 15 + 3N"), e o atributo marca o texto que fala "do (próprio) item"; o modo aplicado marca as notas de ARAM e de Mayhem ("Item desativado em ARAM."); o valor em ouro velho marca toda conta de ouro no texto ("÷", "385g"). Marcar demais é leve; deixar sem marca, não. O item que espera inteiro não recebe campo nenhum, mas leva a marca da conta que **outro** item deixou velha (o preço de um componente, o valor em ouro).

**A wiki assentada**: o robô só aplica quando **viu** a revisão da wiki da foto nova com pelo menos 24 h de idade **e** pelo menos 24 h depois da 1ª foto do patch novo (a edição feita antes de o Data Dragon trocar o patch não passa direto). "Viu" é a hora da foto ou a da última leitura boa que achou a wiki com o mesmo texto (`fonte/_baixado/conferido.json`, que o leitor grava; fica fora do git, e no GitHub Actions o leitor e o aplicar rodam no mesmo serviço) — pelo conteúdo, não pelo número da revisão: a edição desfeita e a revisão nula de proteção mudam o número sem mudar o texto; a idade, nesse caso, conta da revisão mais nova. A foto de dia de patch que o leitor não conseguiu refazer (texto quebrado, sem rede) não envelhece sozinha no disco. Antes disso ele não aplica e tenta de novo no dia seguinte; a camada de antes fica se nasceu deste catálogo — se não (o catálogo subiu de patch, ou o Capítulo 1 mexeu nele), ela sai vazia.

**A foto que serve de base** é a do patch do catálogo e é sempre a revisão do `Module:ItemData/data` que o Capítulo 1 registrou na seção de reconciliação daquele patch ("# Ajustes — reconciliação do patch 16.21.1 (…)", a última se houver duas; dentro dela, "`Module:ItemData/data` (revisão 4088750)"). A revisão citada noutra seção — um Ajuste fora de patch, um Ajuste de sessão com "`versions.json` = 16.21.1" — não conta; sem revisão na seção, ou com duas diferentes, o leitor avisa e o `aplicar_patch` não aplica nada (a camada sai vazia) até o Capítulo 1 resolver. A base nova é conferida — a página é o `Module:ItemData/data`, lida inteira, com quase todos os 225 itens; se não passa, o leitor avisa e segue com a foto do dia, e o `aplicar_patch` se recusa a aplicar com a base de outra revisão (a camada sai vazia). Se a base não existe (o catálogo subiu para um patch nunca fotografado) ou é de outra revisão (a foto do dia virou base quando o catálogo subiu), o leitor a faz ou refaz daquela revisão, com o Data Dragon do patch do catálogo. Fora isso não se regrava, e o relatório dela sai da própria base contra o catálogo de agora: se a wiki muda antes de o Data Dragon trocar o patch, o leitor avisa e guarda a base; o que mudou entra quando sair a foto do patch novo. A foto de um patch mais novo se refaz enquanto a wiki se completa (e nem se regrava quando nada mudou). O download só grava quando as três fontes chegam; o `item.json` de um patch que ainda não saiu para tudo, sem gravar nada.

### A revisão adversarial (24/10/2026)

Três revisores independentes (a regra, o leitor, a camada), cada achado sério reproduzido do zero por um cético. Confirmados e consertados: a fonte sem o dado virava valor aplicado (nome em branco, modos vazios, preço nulo — num item que sai do jogo, por exemplo); a referência `=>` sem destino era lida como "não tem" (e chegava a quebrar o robô); o item que saía do Data Dragon tinha o nome trocado por nada; o comentário longo com nível (`--[=[ … ]=]`) era lido como dado; `chave = nil` virava chave com nada (no Lua ela não existe); a foto base era regravada todo dia; a receita esvaziada voltava para a velha na camada; o custo de combinação se refazia com o preço do item em aberto; o item não comprável recebia preço; o Ápice não era marcado como conta velha; receita e nome aplicados quebravam o "Vira componente de" e o "Limitado a 1 <nome>". Cada um tem um caso no QA.

Na **2ª rodada** (o robô já consertado, dois revisores e um cético por achado), confirmados e consertados: o item mandado inteiro para a conferir ainda ganhava custo de combinação na camada; o item de referência do valor em ouro (`statPrices`) deixava velhas, sem aviso, a análise de custo e o núcleo de dezenas de itens; a chave de modo renomeada na wiki tirava a Summoner's Rift de 185 itens; a foto do dia de patch, no meio da edição, era aplicada (Letalidade 18 → 1038). E, não conferidos mas procedentes: o preço com nota ("gratuito") passava; o atributo que entra não marcava a categoria; a contagem por fora travava o robô por formatação (tab, espaço no colchete); a base podia nascer de outra revisão que não a do Capítulo 1; com a base protegida, o relatório deixava de bater com a foto. Também com caso no QA.

Na **3ª rodada**, confirmados e consertados: o zero escapava do salto (preço 0 e Letalidade 0 eram aplicados), e o atributo que entra não tinha teto (Vida 1038); os modos eram decididos só pela wiki, com os mapas do Data Dragon dizendo o contrário; a edição feita antes de o Data Dragon trocar o patch passava pela espera de 24 h; a base podia ser de outra revisão que não a do Capítulo 1 sem jeito de corrigir. E os procedentes não conferidos: a troca de unidade (plano ↔ percentual) era aplicada como "sai um, entra outro"; os Elixires ficavam fora da conta velha; uma entrada repetida na wiki travava a contagem; o catálogo num patch nunca fotografado ficava sem base; o relatório da base envelhecia.

Na **4ª rodada** (quatro lentes — os números, os modos e a estrutura, o leitor e a base, ponta a ponta — e dois céticos de lentes diferentes por achado sério; 12 confirmados), consertados: o atributo que entra com 0, negativo ou fração ("+0,45% de Velocidade de Ataque") era aplicado, porque o teto só olhava para cima; a troca de unidade só era vista com o mesmo nome na tela (Regeneração de Vida, Letalidade ↔ Penetração de Armadura passavam); o salto só segurava o item quando caía num campo que ia ser aplicado (o preço que salta numa fonte só, o atributo que o catálogo não seguia e o ilegível deixavam o resto da revisão entrar); o item que espera inteiro perdia a marca da conta que outro item deixava velha; a chave de modo que o robô nem lê (o Nexus Blitz) desligava a conferência pelo Data Dragon em todos os itens; a base vinha da última revisão citada no arquivo inteiro, sem ligação com o patch; a espera de 24 h contava até a hora de aplicar, e não até a leitura; a camada de outro catálogo ficava por cima do catálogo novo; o atributo aplicado deixava velha, sem marca, a conta escrita na Mecânica; o `stats.spec` (a Vida ao contato da Abatedora) mudava sem aviso. E os procedentes não conferidos: o `true` do Lua passava por número; os fragmentos do Aumento de Atributo ficavam fora do valor em ouro velho; o item que volta ao jogo e o que só o Data Dragon traz não entravam em "novos"; a base de outra página virava base (ou derrubava o robô todo dia); o tier, a condição de compra e o valor de venda da wiki mudavam sem aviso.

Na **5ª rodada** (três lentes sobre o que a 4ª mexeu — as regressões, o fluxo de vários dias com o relógio trocado, o contrato da camada para a parte 3 — e dois céticos por achado; 7 confirmados), consertados: o atributo que **muda** para longe da faixa do catálogo (Dano de Ataque 55 → 155, Vida 900 → 1.900) era aplicado, porque a faixa só valia para o que entra; o preço, o modo e o valor em ouro aplicados não marcavam o texto que faz conta com eles (as notas da Redenção, o Ápice da Abatedora, o "Item desativado em ARAM." do Anjo Guardião), e o atributo só marcava o número seguido de "de" (o Ápice da Húbris, "55 + 15 + 3N", e a Mecânica do Atma, "700 do próprio item", ficavam sem marca); a revisão de texto igual (desfeita, nula) travava a espera de 24 h pelo resto do patch; o Ajuste de sessão com "`versions.json` = P" deixava a base sem revisão registrada, e a foto do dia virava base em silêncio; o sha do catálogo mudava com o fim de linha (CRLF no Windows, LF no GitHub) e esvaziava a camada válida. E o procedente não conferido: as variantes de itens do catálogo (22xxxx, 32xxxx, 66xxxx, 77xxxx) entravam em "novos" às dezenas.

**A camada** (`data/atualizacao_patch.js`, gerada; não se edita à mão):

```
window.ATUALIZACAO_PATCH = {
  de, para, gerado, catalogo: { patch, sha256 },        // o catálogo de que a camada nasceu (sha do conteúdo, CRLF = LF)
  fonte: { wiki: {de, para}, ddragon: {de, para} },
  itens: { <slug>: { campos: { priceGold, attributes, components, combineCost, cashback, gameModes },
                     base: { <campo>: o valor do catálogo de que nasceu },
                     mudou: [{ campo, de, para, fonte }], contaVelha: ["costAnalysis", …] } },
  aConferir: [{ slug, item, campo, porque, … }],
  novos: [{ nome, id, tipo, modos, preco, volta?, fonte? }],
  statPricesVelhos: ["Espada Longa", …]   // só quando um item de referência mudou
}
```

Com o catálogo já no patch mais novo, a camada sai vazia (`de` = `para`). O relatório de cada troca fica em `data/robo/mudancas_<de>_<para>.md`. Para a parte 3: o app só usa a camada cujo `de` é o `meta.patch` do catálogo, e só põe um campo por cima se o catálogo ainda disser o `base` dele — o campo `attributes` é a lista inteira, e o Capítulo 1 pode ter mexido no item depois que a camada nasceu.

## QA

**O teste com dado real** (24/10/2026): a regra rodada sobre um patch que já aconteceu — o catálogo 16.20.1 (o do commit da reconciliação, lido do git) e a foto do 16.20.1 (`data/robo/fonte/16.20.1/`, refeita da revisão 4082420 que o Capítulo 1 registrou), para a foto do 16.21.1 — contra o que o Capítulo 1 de fato pôs no catálogo 16.21.1. Resultado: os 4 campos que o robô aplicaria são os do Capítulo 1 (nenhum errado), e as outras mudanças dele estão marcadas como conta do patch anterior ou com o item a conferir (a única fora disso é uma data citada num texto, "pt_BR 16.20.1" → "16.21.1", que não é dado). Fica no QA para sempre.

Grupo "robô: a regra" (sem rede): um patch simulado a partir da foto do patch do catálogo, com um caso de cada linha da tabela acima — preço nas duas fontes (com Reembolso e custo de combinação refeitos), só na wiki com o catálogo seguindo o Data Dragon (Atma: nada), só no Data Dragon (Redenção: aplica), componente (Espada Longa chega a 20 itens), atributo que muda e que entra, o catálogo que não seguia a fonte, fontes divergindo, texto de efeito, item que sai e item novo — e a camada do repositório batendo com o catálogo.

Grupo "robô de patch" do `docs/qa_roteiro.py` (sem navegador e sem rede): o leitor de Lua com um texto de prova (escapes, comentário longo, chave repetida, texto cortado), as referências `=>` (a sem destino e a que dá volta), as regras da comparação num catálogo de mentira e a conta refeita sobre a foto guardada — o relatório no repositório tem de dizer o mesmo que ela.
