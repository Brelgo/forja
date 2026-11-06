# Pendências do Capítulo 1

Este é o arquivo único do que o Montador precisa do Capítulo 1: dados errados, dados no lugar errado, atualizações de patch e campos novos. O Forjador **não corrige** o `data/Catalogo_Itens_LoL.md`. Ele aponta a pendência, mostra a prova e diz o que o app faz enquanto ela não se resolve. Quando o Capítulo 1 entrega, o `catalog.js` é gerado de novo e o item recebe ✔ com a data.

Fica fora daqui o que já foi decidido no Capítulo 1 (`docs/decisoes_capitulo1.md` e a seção "Divergências por lote" do catálogo). Essas decisões não são reabertas.

Última revisão: 23/09/2026 (patch do catálogo: 16.18.1; wiki consultada no V26.19).

## Resumo

**23/09/2026: o Leo entregou o Capítulo 1 corrigido** (seção "Ajustes — sessão de correção de 23/09/2026" no fim do catálogo), e o app passou a usar tudo nas F13-T19 a T23. **Aberta: a D5** (o escalonamento por habilidade, 06/11/2026). C1 e C2, as últimas, entraram com a entrega de 18/10/2026 (o 16.19.1 de 03/10 incluído), e o app passou ao 16.20.1 na F13-T49.

| # | Pendência | No Capítulo 1 | No app |
|---|---|---|---|
| A1 | Atma: eficiência sobre o preço errado | ✔ 91,95% | ✔ automático (F13-T19) |
| A2 | Redenção: eficiência sobre o preço errado | ✔ 97,83% | ✔ automático (F13-T19) |
| B1 | `goldValueTotal` com dois sentidos | ✔ "Valor de Ouro (atributos)" e "(base)" nos 225 | ✔ F13-T20: o valor em ouro é o `goldValueBase`, o contorno da T15 saiu, e a ficha mostra "Só atributos" quando o efeito conta |
| B2 | Biscoito: nota de pesquisa no atributo | ✔ nota movida para Notas | ✔ automático (F13-T19) |
| C1, C2 | Atlas Mundial e Bússola Rúnica no 26.19 | ✔ 16.19.1 (03/10) e 16.20.1 (18/10/2026) | ✔ F13-T49: o catálogo do app passou ao 16.20.1 |
| D1 | Ápice em números | ✔ "Ápice numérico" em 102 itens | ✔ F13-T21 (atributos: Atma 50%, Couraça 841,18) e F13-T22 (valor e eficiência no ápice; sem valor fixo, o texto do catálogo) |
| D2 | Ouro do Mestre Forjador | ✔ tabelas de preço + "Mestre Forjador (ouro)" (1.000g nos 109) | ✔ F13-T22: o item forjado soma os 1.000g na caixa e na build; a ficha mostra "Forjado" |
| D3 | Fragmentos do Atributo adicional | ✔ bloco `Fragmentos[]` (34) | ✔ F13-T23: cada Atributo adicional da build guarda o fragmento escolhido, que entra nos atributos e no ouro |
| E1 | Lentidão do Garrabrasa | ✔ 3s (cliente) | ✔ automático (F13-T19) |
| D5 | Escalonamento por habilidade (06/11/2026) | **aberta** | o filtro "Escala com" espera o campo |

O gerador (`data/gerar_catalog_json.py`) passou a ler o esquema novo na F13-T19, com o aprovado do Leo: `costAnalysis.goldValueStats` e `goldValueBase`, `apexNumeric`, `fragments`, `masterwork.bonusGold`, `meta.statPrices` e `meta.masterworkPrices` (ver `docs/esquema_catalog.md`). Relatório: 6 avisos (todos casos já decididos) e 0 linhas não reconhecidas.

O registro de cada pendência, como foi aberta, continua abaixo. A tabela como estava antes da entrega:

| # | Pendência | Tipo | O que o app mostrava | Prioridade |
|---|---|---|---|---|
| A1 | Acerto de Contas de Atma: eficiência calculada sobre 2.500g, com o item custando 2.900g | dado errado | 106,67% (deveria ser 91,95%) | alta |
| A2 | Redenção: eficiência calculada sobre 2.250g, com o item custando 2.300g | dado errado | 100% (deveria ser 97,83%) | alta |
| B1 | `goldValueTotal` significa coisas diferentes conforme o item | forma do dado | certo, por uma conta de contorno (F13-T15) | média |
| B2 | Biscoito: nota de pesquisa dentro do texto do atributo | forma do dado | o atributo quebra em várias linhas (F13-T11) | baixa |
| C1 | Atlas Mundial mudou no patch 26.19 | patch | valores de 16.18.1 (certos para o patch do catálogo) | quando o catálogo subir de patch |
| C2 | Bússola Rúnica mudou no patch 26.19 | patch | valores de 16.18.1 (certos para o patch do catálogo) | quando o catálogo subir de patch |
| D1 | Ápice em campos numéricos | adição | só o texto, mais uma extração cautelosa | média |
| D2 | Valor em ouro do bônus do Mestre Forjador | adição | a eficiência não muda com o Mestre Forjador | média |
| D3 | Fragmentos do Atributo adicional | adição | o texto de `mechanics` | baixa |
| E1 | Lentidão do Filhote de Garrabrasa, 2s ou 3s | dúvida de fonte | "[A CONFIRMAR]", como está no catálogo | baixa |

---

## A. Dado errado

### A1. ✔ Acerto de Contas de Atma: preço de um modo, eficiência de outro
- **No catálogo:** `priceGold` 2.900 (ARAM: Mayhem, V25.21, receita do Data Dragon: Cinto do Gigante + Capa da Agilidade + Cinto do Gigante + 500g). A Análise de custo diz 2.666,67g e **106,67%**.
- **A conta:** 2.666,67 ÷ 2.500 = 106,67%. Os 2.500g são o custo da **Arena** na infobox da wiki, e a Cost Analysis do artigo usa esse preço. O catálogo copiou a porcentagem sem refazer a divisão pelo preço dele.
- **Com o preço do catálogo:** 2.666,67 ÷ 2.900 = **91,95%**.
- **Já decidido, e não reaberto:** a Cost Analysis ignora o +10 de AdH (Divergências, Lote do Atma: "transcrita como está"). Se o Capítulo 1 refizer a conta, cabe a ele decidir se conta os 500g da AdH. Com eles, 3.166,67 ÷ 2.900 = 109,20%.
- **No app hoje:** 106,67%, e o item vale 3.093,43g na soma da build (a eficiência do catálogo × o preço, que é a regra da F13-T15).
- **O que o Capítulo 1 faz:** refaz `efficiency`/`efficiencyBase` sobre 2.900g. O app segue sozinho depois de regerar o `catalog.js`.

### A2. ✔ Redenção: preço de um patch, eficiência de outro
- **No catálogo:** `priceGold` 2.300 (Data Dragon 16.18.1, combinação de 850g). A Análise de custo diz 2.250g e **100%**.
- **A conta:** 2.250 ÷ 2.250 = 100%. O artigo da wiki dá o custo como 2.250g (combinação de 800g), e o catálogo dividiu pelo preço do artigo, não pelo dele.
- **Com o preço do catálogo:** 2.250 ÷ 2.300 = **97,83%**.
- **No app hoje:** 100%, e o item vale 2.300g na soma da build.
- **O que o Capítulo 1 faz:** confere qual preço vale no patch dele (Data Dragon diz 2.300g) e refaz a eficiência sobre esse preço.

## B. Forma do dado: o número está certo, o campo não

### B1. ✔ (dado) `goldValueTotal` não significa a mesma coisa em todos os itens — o app usa na F13-T20
Na wiki, "eficiência base" tem **dois sentidos**, e o catálogo mistura os dois:
- a **tabela** "Gold efficiency" conta **só os atributos**;
- o **artigo** de cada item diz que "os atributos base são X% eficientes", mas o X muitas vezes **inclui a passiva** (o Fascínio, a Mordida Icathiana, o Duelo, a Drenar...).

O `efficiencyBase` do catálogo segue o **artigo** em todos os itens conferidos. Já o `goldValueTotal` varia:
- em **19 itens** ele tem só os atributos, e a passiva fica fora dele, mas dentro do `efficiencyBase`: Anel de Doran, Orbe do Guardião, Cajado do Arcanjo, Auronúcleo, Lâmina da Fúria de Guinsoo, Manamune, Dente de Na'Shor, Armadura Sangrenta do Suserano, Criafendas, Semblante Espiritual, Terminus, Armadura de Warmog, Tiara Sussurrante, Aproximação Invernal, Limite da Razão, Diadema de Canções, Fimbulwinter, Muramana e Abraço de Seraph;
- em **5 itens** ele já inclui o efeito: Capuz da Morte de Rabadon (passiva, 39 de PdH), Arco Recurvo (dano ao contato) e os três Elixires de Ferro, da Feitiçaria e da Ira (o valor depois de consumido, como no artigo; a tabela dá 0% porque o elixir parado no inventário não dá nada);
- nos outros 184 com análise, os dois campos concordam porque o item não tem passiva avaliada.

- **No app hoje:** a F13-T15 ("com a passiva", escolha do Leo) tira o valor em ouro de `efficiencyBase × preço` quando os dois campos não concordam (tolerância de 0,6% do preço). A conta fica certa, mas é um contorno.
- **O que o Capítulo 1 faz (proposta):** dois campos numéricos com sentido fixo em todo item:
  - `goldValueStats`: só os atributos, igual à tabela da wiki;
  - `goldValueTotal`: sempre o numerador do `efficiencyBase` (atributos mais o que o artigo conta).

  Com isso o app tira o contorno e pode mostrar as duas leituras lado a lado ("só atributos 84,17% · com Duelo 118,99%").

### B2. ✔ Biscoito Total da Determinação Eterna: nota de pesquisa dentro do atributo
- **No catálogo:** o `attributes[0].raw` tem 262 caracteres. Junto do atributo ("+30 de Vida máxima permanente por biscoito consumido ou vendido") vem a nota de onde ele veio (a captura do tooltip de 12/09/2026, e que a wiki atribui o bônus à runa).
- **No app hoje:** a faixa de atributos da build quebra o texto em várias linhas. Antes da F13-T11 ela estourava a página em 1280 px (caçada de bugs, nº 34).
- **O que o Capítulo 1 faz:** passa a nota para `notes` ou para as Divergências e deixa no `raw` só o atributo.

## C. Atualização de patch (não é erro)

✔ **Resolvidas:** o Capítulo 1 aplicou o 16.19.1 (03/10/2026) e entregou o 16.20.1 em 18/10/2026; o app está nele desde a F13-T49. O texto abaixo é o de quando foram abertas: o catálogo estava no 16.18.1, e a wiki já trazia o **V26.19**.

### C1. ✔ Atlas Mundial
- V26.19: Vida de 30 para **0**; Regeneração de Vida base de 25% para **50%**.
- A wiki fica com 150 + 100 = 250g, ou **62,5%**. O catálogo tem 255g, ou 63,75%.

### C2. ✔ Bússola Rúnica
- V26.19: Vida de 100 para **60**; Regeneração de Vida base de 50% para **75%**.
- A wiki fica com 160 + 225 + 200 = 585g, ou **146,25%**. O catálogo tem 616,67g, ou 154,17%.

## D. Adições (campos que o catálogo não tem)

Estes dados existem hoje só como texto. O Forjador não os digita. Até o Capítulo 1 fornecer, a tela mostra o texto como está.

### D1. ✔ (dado) Ápice em campos numéricos — o app usa nas F13-T21 e T22
- **Hoje:** `apex` é texto (102 itens com Ápice diferente do base). O app extrai dele só os "+N de <atributo>" com sinal e nome conhecido, e desde a F13-T9 só **substitui** o número do item quando a grandeza é a mesma e o número do Ápice é maior. Assim 9 itens deixaram de sair errados, mas ainda tem caso que nenhuma regra acerta sem adivinhar.
- **O caso que prova:** Acerto de Contas de Atma. O texto diz "+30% de Chance de Acerto Crítico (50% no total com o atributo do item)", e o app mostra **30%**. O certo é 50%.
- **O que o Capítulo 1 faz:** `apexStats[] = {stat, value, unit, soma: "total" | "a mais"}`, mais `apexGoldValueTotal` (ou `apexEfficiencyBase`). Com isso o app desliga a extração de texto e a eficiência passa a mudar com o interruptor Ápice.

### D2. ✔ (dado) Valor em ouro do bônus do Mestre Forjador — o app usa na F13-T22
- **Hoje:** `masterwork.stats[].bonus` tem o número do bônus de cada atributo (109 itens). O valor em ouro dele está só no texto `masterwork.raw` ("3 categorias upgradáveis (333,33g cada)"), e a conta dá 1.000g nos 109 (51 × 2 de 500g, 28 × 1 de 1.000g, 25 × 3 de 333,33g, 5 × 4 de 250g). Por isso a eficiência não muda com o Mestre Forjador.
- **O que o Capítulo 1 faz, com uma das três formas:**
  1. `masterwork.bonusGoldTotal`, um número por item;
  2. `costAnalysis.parts[] = {stat, value, gold}`, para dar valor a cada ponto;
  3. uma tabela de preço por atributo no topo do catálogo (`statPrices`), copiada da "Base Statistic Prices" da wiki (DdA 35g, PdH 20g, Vida 2,666667g...), para o app valorar o bônus sozinho.
- **A regra que fica pronta para usar:** eficiência = (valor base + bônus do Mestre Forjador, ou valor no Ápice) ÷ (preço, ou preço líquido com Reembolso). O Reembolso já funciona (`cashback.netGold`, 109 itens; outros 11 têm o reembolso só em texto).

### D3. ✔ (dado) Fragmentos do Atributo adicional (Stat Bonus) — o app usa na F13-T23
- **Hoje:** os fragmentos estão em texto no `mechanics` da habilidade.
- **O que o Capítulo 1 faz:** `fragments[] = {tier: "Prata" | "Ouro" | "Prismático", stat, value, unit, gold}`. Com isso a build pode escolher qual fragmento o item dá.

### D4. ✖ Dispensada (21/10/2026) — Em que patch cada item mudou no jogo
- **Dispensada no mesmo dia:** o Leo escolheu o caminho automático — o Capítulo 2 compara as versões do catálogo ao regerar (`data/mudancas.js`) e não precisa deste campo. O registro abaixo fica como estava.
- **Pedido do Leo (21/10/2026):** "marcar como desatualizada builds que contêm (opcional não conta) os itens que foram atualizados… builds que não têm nenhum item que foi modificado na atualização se mantêm". Hoje o app marca desatualizada toda build de patch anterior (na aba Públicas, 51 de 65 ficaram de fora no 16.20.1, a maioria sem nenhum item mudado).
- **Hoje:** o que mudou em cada patch está no fim do catálogo, em texto ("Ajustes — reconciliação do patch 16.19.1" e "16.20.1"), misturando mudança de jogo (Bússola Rúnica: Vida 100 → 60 no V26.19), correção do próprio catálogo (Diadema de Canções passando a Evolução) e nome (Concretizador). Só a mudança de jogo deve desatualizar uma build — e quem sabe separar é o Capítulo 1.
- **O que o Capítulo 1 faz:** em cada item, uma linha com os patches em que o **jogo** mudou o item (atributo, preço, receita, efeito, modos), por exemplo `Mudou no jogo em[]: 16.19.1, 16.20.1` — o rótulo final é do Capítulo 1; correção de dado do catálogo e troca só de nome não entram. Preencher pelo menos o 16.19.1 e o 16.20.1 a partir das tabelas de reconciliação que já existem.
- **No Capítulo 2:** o gerador lê a linha (muda o esquema: aprovação do Leo) para `item.changedIn = ["16.19.1", "16.20.1"]`. A build feita no patch P fica desatualizada só se alguma caixa que não é Opcional tiver um item com mudança num patch depois de P (até o atual), ou um item que saiu do catálogo. Vale para a etiqueta e a revisão das suas builds e para a aba Públicas (F13-T56). O robô de atualização por patch passa a precisar desse dado também.

### D5. Aberta (06/11/2026) — Escalonamento (scaling) por habilidade
- **Pedido do Leo (06/11/2026):** "adicionar o scaling de ad, ap, mana, armadura, mr... para aquele filtro de maior e menor de atributo do catálogo". Ele escolheu este caminho, e não a leitura do texto pelo app.
- **Hoje:** o escalonamento só existe em campo no `attributes[].scaling`, com 2 itens. Nas habilidades ele está em texto no `mechanics`, escrito de três jeitos:
  - **razão entre parênteses**, "20 (+1,5% da Vida bônus)": 27 itens;
  - **conversão**, "concede DdA bônus igual a 2% da Mana máxima": mais 16 itens que não têm a razão entre parênteses (Manamune, Muramana, Cajado do Arcanjo, Abraço de Seraph, Tiara Sussurrante, Diadema de Canções, Aproximação Invernal, Armadura Sangrenta do Suserano, Armadura de Warmog, Sinal de Sterak, Marcha Célere...);
  - **"Sem scaling."**, escrito em 37 itens.
- **Por que o app não lê o texto:** o mesmo "X% da Vida máxima" ora é um atributo seu ("+4% da Vida bônus" de dano), ora do alvo ("5% da Vida máxima do alvo"), ora uma cura ("restaura 20% da Mana máxima"), ora uma amplificação ("recebe 4% de Poder de Habilidade"). Separar esses casos é decidir o que o dado significa, e isso é do Capítulo 1.
- **O que o Capítulo 1 faz:** `abilities[].scaling[] = {stat, pct, base, de, tipo}`:
  - `stat`: "PdH" | "DdA" | "Vida" | "Mana" | "Armadura" | "RM" | "VM" | "tamanho" | ...;
  - `pct`: o número, ou uma faixa por nível ("0–12");
  - `base`: "bônus" | "total" | "base" | "máxima" | "atual" | "perdida";
  - `de`: "seu" | "alvo";
  - `tipo`: "razão" (soma ao efeito) | "conversão" (vira outro atributo: o atributo que recebe vai junto).
  
  `[]` com "Sem scaling" para a habilidade que não escala, e ausente quando ainda não foi conferido.
- **No Capítulo 2:** o gerador lê o campo novo (muda o esquema: aprovação do Leo). No grupo Atributo do Catálogo entram os chips "Escala com" PdH, DdA, Vida, Mana, Armadura e RM, só com `de: "seu"`, e o Maior/Menor primeiro ordena pela maior porcentagem do atributo marcado. A ficha mostra a razão junto da habilidade. Custo estimado depois da entrega: 2–3% do semanal.

## E. Dúvida de fonte aberta

### E1. ✔ Filhote de Garrabrasa (Scorchclaw Pup): lentidão de 2s ou 3s — 3s, pelo cliente
A wiki diz 2s e o tooltip do cliente diz 3s. O catálogo marca "[A CONFIRMAR]" e o app mostra como está. Entra aqui só para a lista ficar completa: isso já está nas Divergências do catálogo e no `docs/decisoes_capitulo1.md`.

---

## Para conhecimento (não é pendência)

### A conferência com a wiki (23/09/2026)
- **Tabela "Gold efficiency"** (revisão 4014965): dos 216 itens que têm linha na tabela, **207** batem em preço e em `goldValueTotal ÷ preço`. Os 9 que não batem são A1, A2, C1, C2 e os 5 de B1 que incluem o efeito.
- **Artigos, item por item:** conferi os 28 itens em que o catálogo e a tabela divergem ou em que a passiva entra na conta. **26 batem** com o artigo. Os 2 que não batem são do patch 26.19 (C1, C2), confirmados por dois céticos cada. Atma e Redenção "batem" na porcentagem só porque o catálogo copiou a conta do artigo com o preço do artigo (A1, A2).

| Item | Preço no catálogo | `efficiencyBase` | Artigo da wiki | Tabela da wiki (só atributos) | Situação |
|---|---|---|---|---|---|
| Anel de Doran (Doran's Ring) | 400g | 225% | 225% | 150% | bate |
| Orbe do Guardião (Guardian's Orb) | 950g | 210,53% | 210,53% | 147,37% | bate |
| Atlas Mundial (World Atlas) | 400g | 63,75% | 62,5% | 62,5% | patch 26.19 (C1) |
| Elixir de Ferro (Elixir of Iron) | 500g | 160% | 160% | 0% | bate |
| Elixir da Feitiçaria (Elixir of Sorcery) | 500g | 380% | 380% | 0% | bate |
| Elixir da Ira (Elixir of Wrath) | 500g | 210% | 210% | 0% | bate |
| Arco Recurvo (Recurve Bow) | 700g | 100% | não declara (700g ÷ 700g = 100%) | 53,57% | bate |
| Cajado do Arcanjo (Archangel's Staff) | 2.900g | 116,21% | 116,21% | 112,07% | bate |
| Acerto de Contas de Atma (Atma's Reckoning) | 2.900g (artigo: 2.500g) | 106,67% | 106,67% | 106,67% | **preço errado (A1)** |
| Auronúcleo (Dawncore) | 2.500g | 96% | 96% | 84% | bate |
| Lâmina da Fúria de Guinsoo (Guinsoo's Rageblade) | 3.000g | 97,5% | 97,5% | 75,83% | bate |
| Manamune (Manamune) | 2.900g | 97,41% | 97,41% | 85,34% | bate |
| Dente de Na'Shor (Nashor's Tooth) | 2.900g | 144,31% | 144,31% | 124,14% | bate |
| Armadura Sangrenta do Suserano (Overlord's Bloodmail) | 3.300g | 90,85% | 90,85% | 76,26% | bate |
| Capuz da Morte de Rabadon (Rabadon's Deathcap) | 3.500g | 96,57% | 96,57% | 74,29% | bate |
| Redenção (Redemption) | 2.300g (artigo: 2.250g) | 100% | 100% | 100% | **preço errado (A2)** |
| Criafendas (Riftmaker) | 3.100g | 103,98% | 103,98% | 99,46% | bate |
| Semblante Espiritual (Spirit Visage) | 2.700g | 111,73% | 111,73% | 106,17% | bate |
| Terminus (Terminus) | 3.000g | 85,83% | 85,83% | 64,17% | bate |
| Armadura de Warmog (Warmog's Armor) | 3.100g | 106,02% | 106,02% | 95,7% | bate |
| Tiara Sussurrante (Whispering Circlet) | 2.250g | 71,48% | 71,48% | 68,15% | bate |
| Aproximação Invernal (Winter's Approach) | 2.400g | 121,53% | 121,53% | 113,19% | bate |
| Limite da Razão (Wit's End) | 2.800g | 118,99% | 118,99% | 84,17% | bate |
| Diadema de Canções (Diadem of Songs) | 2.250g | 114,81% | 114,81% | 103,7% | bate |
| Fimbulwinter (Fimbulwinter) | 2.400g | 150,69% | 150,69% | 134,03% | bate |
| Muramana (Muramana) | 2.900g | 135,69% | 135,69% | 102,59% | bate |
| Bússola Rúnica (Runic Compass) | 400g | 154,17% | 146,25% | 146,25% | patch 26.19 (C2) |
| Abraço de Seraph (Seraph's Embrace) | 2.900g | 139,66% | 139,66% | 125,86% | bate |

### Itens de um lado e não do outro
- **Estão na tabela da wiki e não no catálogo:** Cappa Juice, Rite of Ruin, Sword of Blossoming Dawn e Veigar's Talisman of Ascension. O escopo são os 225 itens: incluir algum deles é decisão do Capítulo 1, não do app. A Shattered Armguard também falta, mas essa já está decidida. E a "Stat Bonus (ARAM: Mayhem)" da wiki é o nosso Atributo adicional.
- **Estão no catálogo e não têm linha na tabela:** Atributo adicional, Alteração Vidente, Lente do Oráculo, Sentinela Invisível, Elixir da Avareza, Elixir da Força, Elixir da Habilidade, Botas Levemente Mágicas e Biscoito Total da Determinação Eterna. Não há nada a fazer, a tabela da wiki é que não os lista.

---

## Não é do Capítulo 1 (ponteiros)
- **Decisões já tomadas no Capítulo 1:** `docs/decisoes_capitulo1.md`. Não se reabrem.
- **Runas:** `docs/pendencias_runas.md`, sobre o que o conversor achou em `data/Runas_League_of_Legends.md`.
- **Dado de campeão (Capítulo 1.1):** `docs/proposta_capitulo_1_1.md`. O Capítulo 1 é só de itens (Leo, 18/09/2026).

## Histórico
- 13/09/2026: D1, D2 e D3 abertas (eram o `docs/propostas_capitulo1.md`, que virou ponteiro para cá).
- 22/09/2026: B2 achada na caçada de bugs (nº 34). O app passou a quebrar o texto (F13-T11). O caso do Atma no D1 veio da F13-T9.
- 23/09/2026: A1, A2, B1, C1 e C2 saíram da conferência com a wiki (tabela e 28 artigos). Arquivo único criado a pedido do Leo.
- 23/09/2026 (tarde): o Leo entregou o Capítulo 1 corrigido. A1, A2, B2 e E1 resolvidos no dado; B1, D1, D2 e D3 entregues como campos novos, que o app passa a usar nas F13-T20 a T23. C1 e C2 ficam para quando o catálogo subir de patch.
- 18/10/2026: C1 e C2 resolvidos — entrega do Capítulo 1 no 16.20.1, aplicada no app na F13-T49.
- 06/11/2026: D5 aberta (o escalonamento por habilidade, para o filtro do Catálogo).
