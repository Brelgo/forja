# Robô de patch — fonte × catálogo, patch 16.21.1

Gerado por `data/robo/ler_fonte.py` em 2026-10-24T15:19:12Z. **Só leitura**: nada do catálogo foi tocado.

| Fonte | O que foi lido |
|---|---|
| Data Dragon | patch do dia **16.21.1** · `item.json` pt_BR com 863 itens |
| Wiki `Module:ItemData/data` | revisão 4088750 de 2026-10-21T19:07:31Z · 334 itens lidos (334 entradas contadas por fora) |
| Catálogo | `data/catalog.js`, patch 16.21.1 · 225 itens |

**2 diferenças a conferir.** 225 itens do catálogo casados com a wiki (0 sem par); 3 em que a wiki diverge e o catálogo segue o Data Dragon.

| Campo | Itens comparados | A conferir |
|---|---:|---:|
| Id | 225 | 0 |
| Preço (buy) | 225 | 0 |
| Receita (recipe) | 178 | 0 |
| Atributos (stats) | 517 | 1 |
| Modos (modes) | 225 | 0 |
| Efeitos com nome (pass/act) | 162 | 1 |
| Grupo "Limitado a 1" (itemlimit) | 73 | 0 |
| Data Dragon (id, preço e nome pt_BR) | 225 | 0 |

## A conferir — Atributos (stats)

| Item | Catálogo | Fonte |
|---|---|---|
| Acerto de Contas de Atma (Atma's Reckoning) | Aceleração de Habilidade 10 | Aceleração de Habilidade — |

## A conferir — Efeitos com nome (pass/act)

| Item | Catálogo | Fonte |
|---|---|---|
| Berrante do Guardião (Guardian's Horn) | ["Recovery", "Undaunted"] | ["Undaunted"] |

## Fonte dividida — o catálogo segue o Data Dragon

A wiki diz outra coisa, e o Data Dragon do patch bate com o catálogo: foi o que o Capítulo 1 escolheu (pendências A1 e A2 em `docs/pendencias_capitulo1.md`). Não é erro do catálogo; o robô nunca troca esses campos sozinho.

| Campo | Item | Catálogo (= Data Dragon) | Wiki |
|---|---|---|---|
| preço | Acerto de Contas de Atma (Atma's Reckoning) | 2900 | 2500 |
| receita | Acerto de Contas de Atma (Atma's Reckoning) | ["Cloak of Agility", "Giant's Belt", "Giant's Belt"] | [] |
| preço | Redenção (Redemption) | 2300 | 2250 |

## O que o robô não compara (e por quê)

- **Atributos que só o catálogo tem** (25): não estão nos números da tabela `stats` da wiki — vêm do texto do efeito ou do texto livre `stats.spec` (a Vida ao contato da Abatedora); o robô vê a mudança pelo texto (do efeito ou do `spec`) e a manda para a conferir, na parte 2.
  - Abatedora (Cull): Vida ao contato 3
  - Biscoito Total da Determinação Eterna (Total Biscuit of Everlasting Will): Vida máxima permanente por biscoito consumido ou vendido 30
  - Botas da Rapidez (Boots of Swiftness): Resistência a Lentidão 25
  - Botas Ionianas da Lucidez (Ionian Boots of Lucidity): Aceleração de Feitiços de Invocador 10
  - Arco Recurvo (Recurve Bow): Dano Físico ao contato 15
  - Couraça do Defunto (Dead Man's Plate): Resistência a Lentidão 15
  - Hexoplaca Experimental (Experimental Hexplate): Aceleração de Ultimate 30
  - Dardos de Caça-Demônios (Fiendhunter Bolts): Aceleração de Ultimate 30
  - Lâmina da Fúria de Guinsoo (Guinsoo's Rageblade): Dano Mágico ao contato 30
  - Malevolência (Malignance): Aceleração de Ultimate 20
  - Dente de Na'Shor (Nashor's Tooth): Dano Mágico ao contato 15
  - Criafendas (Riftmaker): Vida bônus como Poder de Habilidade 2
  - Lança de Shojin (Spear of Shojin): Aceleração de Habilidade Básica 25
  - Sinal de Sterak (Sterak's Gage): DdA base como Dano de Ataque bônus 50
  - Terminus (Terminus): Dano Mágico ao contato 30
  - Armadura de Warmog (Warmog's Armor): Vida bônus de itens como Vida bônus 12
  - Limite da Razão (Wit's End): Dano Mágico ao contato 45
  - Convergência de Zeke (Zeke's Convergence): Aceleração de Ultimate 15
  - Lucidez Escarlate (Crimson Lucidity): Aceleração de Feitiços de Invocador 20
  - Diadema de Canções (Diadem of Songs): Mana bônus como Poder de Cura e Escudo 0.5
  - Fimbulwinter (Fimbulwinter): Mana bônus como Vida bônus 15
  - Muramana (Muramana): Mana máxima como Dano de Ataque bônus 2
  - Abraço de Seraph (Seraph's Embrace): Mana bônus como Poder de Habilidade 2
  - Marcha Célere (Swiftmarch): Resistência a Lentidão 25
  - Marcha Célere (Swiftmarch): Velocidade de Movimento total como Força Adaptativa 5
- **Texto curado** (Mecânica, Ápice, Passiva do Ornn, notas, interações): é de pessoa; o robô só marca "a conferir".
- **109 itens da wiki fora do catálogo** (Arena, Nexus Blitz, torres, tropas, os removidos…): o escopo são os 225 do Capítulo 1.

## Avisos do leitor

- chave repetida 'nickname' na linha 3626 (vale a última, como no Lua)

