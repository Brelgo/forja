# Pendências das runas

Arquivo único de tudo o que falta nas runas. Estão aqui:
- os dados da sua fonte, `data/Runas_League_of_Legends.md`;
- o que o app faz errado com eles (o leitor `data/gerar_runas_json.py` e a tela);
- os documentos que ficaram para trás;
- e o histórico do que já foi resolvido.

A fonte é sua. Em 23/09/2026 você autorizou corrigir o que a conferência achou (F13-T16). Fora isso, eu leio, aponto e sigo.

Última revisão: 26/10/2026 (F13-T86: o A4 e o bug nº 13 dados como resolvidos; patch do app: 16.21.1).

Para ver o que o leitor aponta hoje:

```bash
python data/gerar_runas_json.py
```

## Resumo

| # | Pendência | Quem resolve | Estado |
|---|---|---|---|
| F1–F8, F10 | Números, descrições, trocas automáticas, notas técnicas, nomes, `Atributos:`, lemas e as notas opcionais | Leo (fonte) | ✔ resolvido em 23/09/2026 (F13-T16) |
| F9 | Cabeçalho: nota de Força Adaptativa | Leo | ✔ resolvido (F13-T16) |
| F9b | Cabeçalho: o que é "movimento debilitado" (as páginas da wiki divergem entre si) | Leo | ✔ decidido em 25/10/2026 (F13-T84): inclui também Ancoragem e Sonolência |
| A1 | O leitor jogava fora o bloco "Controle de grupo válido" de 5 runas, calado | Forjador | ✔ resolvido em 23/09/2026 (F13-T17) |
| A2 | Bug nº 35: o texto perde a primária e a secundária quando a primária está sem runa | Forjador | ✔ resolvido em 17/10/2026 (F13-T38); resta o aviso para `RUNAS 2:` escrito à mão sem `RUNAS:` |
| A3 | Bug nº 19: "Copiar como texto" do lote não leva runas | Forjador | ✔ resolvido em 01/10/2026 (F13-T37, aprovada em 17/10/2026): o lote usa o mesmo escritor da build |
| A4 | Bug nº 29: build publicada aberta "só para ver" tem as runas editáveis | Forjador | ✔ resolvido em 23/10/2026 (F13-T59): sem o Editar, a build só se lê — as runas também |
| A5 | O app não aplica nenhuma troca automática, só avisa, e a tela não dizia isso | Forjador | ✔ resolvido em 23/09/2026 (F13-T18) |
| A6 | Documentos desatualizados (o SQL do servidor é o que tem risco) | Forjador | parcial: ✔ o SQL e o README do servidor (F13-T87, 26/10/2026); o resto, aberto (baixa) |

---

## Parte 1: da fonte (`data/Runas_League_of_Legends.md`)

### Aberto
- **F9b. "Movimento debilitado" = Imobiliza + Lentidão** (linha 23 do cabeçalho). Na página geral de controle de grupo da wiki, a categoria inclui também **Ancoragem** e **Sonolência**. A Velocidade de Aproximação usa esse termo e o próprio MD lista Ancoragem nela. Só que a página da Fonte da Vida define o termo como imobilizar + lentidão. As páginas da wiki divergem entre si, e a escolha é sua.

### Resolvido em 23/09/2026 (F13-T16)
Corrigido com a sua autorização. As decisões foram:
- os números seguem a Riot 16.18.1;
- os lemas usam o texto do cliente;
- na linha `Atributos:`, o tipo de dano não conta: atributo é o que a runa dá ou com que escala, e `—` quer dizer "nenhum, de propósito";
- as runas que não tinham a linha foram preenchidas pelo texto.

Capturas de antes e depois: `docs/screenshots/fase13-t16-*.png`.

**Números errados que o app mostrava (F1):**

| Runa | Antes | Agora | De onde vinha o erro |
|---|---|---|---|
| Osso Revestido | Recarga: 555s | **55s** | um 5 a mais |
| Sexto Sentido | revela a sentinela por 106s | **10s** | um 6 a mais |
| Livro de Feitiços Deslacrado | recarga inicial de 3s | **270s** | marcador vazio no texto da Riot (`@f3@`); o valor vem da wiki, V25.19 |
| Agilidade nos Pés | cura 10 - 130 | **15 - 160** | mudou no V26.16 |
| Tônico Triplo | Elixir da Força +5 de DdA ou 9 de PdH | **+15 ou 25** | era o valor do fragmento de Força Adaptativa |
| Tônico Triplo | Elixir da Avareza: 40 de ouro | **60** | mudou no V25.22 |
| Manto de Nimbus | dura 2.5s | **2s** | mudou no V10.21 |
| Ventos Revigorantes | ao longo de 10.5s | **10s** | a duração nunca mudou |

**O resto:**
- **Descrições (F2):** o Toque Ígneo ganhou "Dano ao longo do tempo: 1s", e a Aery ganhou a regra de "só volta quando retorna".
- **Trocas automáticas (F3):** eram 14 e agora são **24**, tiradas dos arquivos do cliente do jogo 16.18. A lista está completa: os 173 campeões e os modos dos mapas do Summoner's Rift e do ARAM.
  - Saiu: a da Cassiopeia (acabou no 16.1).
  - Corrigidas: a do Yorick, que estava escrita ao contrário, e as de URF, Demolir e Livro Supremo de Ultimates (era "Feitiço Supremo").
  - Novas, por campeão: Yuumi (Pós-choque vira Guardião), Ambessa (Faixa de Fluxo de Mana vira Manto de Nimbus), Fiddlesticks (Sentinela Profunda vira Lembranças Aterrorizantes) e Corki (Fonte da Vida vira Demolir).
  - Novas, por modo: **ARAM** (Entrega de Biscoitos vira Tônico de Distorção no Tempo), Lua Sangrenta, A Lenda do Rei Poro, Confronto e URFeA na Neve.
- **Notas técnicas de mecânica que mudou (F4):**
  - Conquistador: 4s;
  - Ritmo Fatal: não passa do limite de Velocidade de Ataque;
  - Presença de Espírito: saiu a nota do efeito antigo;
  - Aperto dos Mortos-Vivos: 40% à distância;
  - Tônico de Distorção no Tempo: 40% a mais, só com poções;
  - Celeridade: amplia também os bônus percentuais.
- **Notas com erro de sentido (F5):**
  - o corte do Ritmo Fatal é para quem ataca à distância;
  - as Lendas vão até 10 acúmulos, e a Linhagem até 15;
  - a Flashtração Hextec;
  - o exemplo da Nami;
  - as ondas de fogo da Kayle vêm da passiva.
- **Nomes (F6):** a primeira auditoria achou 6 runas com nome errado. A verificação das mudanças conferiu **213 nomes** contra o Data Dragon pt-BR e confirmou mais **39 problemas**, a maioria de nome, e todos foram corrigidos. Exemplos:
  - Golpear (era "Executar/Smite"), Proteção do Crepúsculo, Refúgio da Ovelha, Visões Maléficas, Parede de Vento, Voragem Afiada, Roubo Arcano, Pinstouro;
  - Flash Hextec (era "Hexflash"), Quebra-galho (com g minúsculo, como na Riot);
  - Jogo Dinâmico e Blitz do Nexus;
  - os talentos antigos com o nome pt-BR.
- **`Atributos:` (F7):**
  - 22 linhas pelo critério;
  - as 7 runas sem a linha agora têm, e 5 delas ficaram com `—`;
  - 3 mais apontadas pela verificação: Aprimoramento Glacial com Escudo no lugar de "Aplica Lentidão / CC"; Avanço da Tempestade e o fragmento de Tenacidade com Resistência a Lentidão.
- **Lemas (F8):** os cinco agora usam o texto do cliente. "Caçe" saiu.
- **Cabeçalho (F9):**
  - a nota de Força Adaptativa fala de quem concede Força Adaptativa;
  - a definição de `Atributos` descreve o critério novo;
  - o glossário não chama mais PdH de "dano mágico".
- **Notas opcionais (F10):**
  - Ritmo Fatal: o texto da Riot mostra 4% e 6-24 à distância, e o jogo usa 4,8% e cerca de 6-20;
  - Fonte da Vida: cura de 10–50, e 7–35 à distância.

  A nota da Fonte da Vida primeiro saiu com os números da wiki até o nível 20, contra a regra deste mesmo arquivo. A verificação pegou, e agora ela usa o dado do jogo, até o 18.
- **O leitor** (`gerar_runas_json.py`) mudou em duas coisas:
  - entende `Atributos: —` como vazio de propósito, sem etiqueta "—" e sem pendência;
  - lê o destino da troca pelo nome de runa mais longo. Antes, "Tônico de Distorção no Tempo no ARAM" era cortado em "Tônico de Distorção". A checagem de integridade do próprio leitor pegou isso na hora.

---

## Parte 2: do app, quem corrige é o Forjador

Cada item vira uma tarefa com o seu aprovado, como sempre.

### A1. ✔ O leitor jogava fora o bloco "Controle de grupo válido" — resolvido na F13-T17
**Como ficou:** o leitor lê o bloco (categoria, Inclui, Não inclui, Obs) e a ficha mostra, junto com as notas técnicas: no modo Completo aberto, no Resumido pelo botão "controle de grupo". O leitor também passou a **acusar toda linha que não entende**, em vez de pular calado, e a conferir nos dois sentidos se a linha "Substituição automática:" da ficha bate com a lista de substituições. As quatro falhas foram vistas numa cópia estragada do MD. Na tela apareceu um estouro antigo, o bug nº 36 (etiqueta da runa com a Leitura calma em 1280), consertado junto.

O registro original:

O `gerar_runas_json.py` só reconhece `Atributos:`, `Classes:`, `Força Adaptativa destrinchada` e notas que começam com "- ". As **13 linhas** dos blocos "Controle de grupo válido / Inclui / Não inclui / Obs" de 5 runas somem sem virar pendência:
- Golpe Desleal (linhas 143–145);
- Pós-choque (304–306);
- Fonte da Vida (334–335);
- Aprimoramento Glacial (394–396, inclusive a explicação do Yorick);
- Velocidade de Aproximação (468–469).

O conteúdo desses blocos confere com a wiki. É o mesmo defeito do leitor que descartava 4 runas em 18/09: ele ignora o que não entende e não avisa. O conserto é ler o bloco e mostrá-lo na ficha, ou no mínimo contar as linhas que não reconhece e apontar como pendência. (A parte do `Atributos: —` já foi feita na F13-T16.)

### A2. ✔ Bug nº 35 (reproduzido em 23/09/2026; consertado na F13-T38, 17/10/2026): o texto perde a primária e a secundária
A linha `RUNAS:` só sai quando alguma runa da primária está escolhida. Com a trilha primária escolhida mas sem runa, e a secundária completa, o texto leva só `RUNAS 2:` e `FRAGMENTOS:`. Na volta, o `normRunas` sem primária descarta também a secundária. Resultado: a página volta só com os fragmentos, sem aviso nenhum. É da mesma família dos nºs 6 e 16. O link e a publicação não têm esse problema.

### A3. ✔ Bug nº 19 (a parte das runas; consertado na F13-T37): "Copiar como texto" do lote
`loteParaTexto` não chama `linhasDeRunas`. Quem usa o lote como cópia de segurança perde a página de runas, a ordem de habilidades e o Mestre Forjador. A outra metade do nº 19 (várias builds reimportadas viram uma só) não é de runa.

### A4. ✔ Bug nº 29: build publicada aberta "só para ver" tem as runas editáveis — resolvido na F13-T59 (23/10/2026)
**Como ficou:** sem o Editar, a build só se lê — a aba Runas também (o roteiro: "visualização só lê", com clique de verdade); e a pública aberta para ver não liga o Editar (o roteiro: "vendo uma pública: só visualização, sem Editar"; o nº 40, na F13-T51).

**Como era:** a aba Runas não conferia se a build é só para ver: `escolherRuna`, a troca de trilha e o Limpar gravam na hora. A grade de habilidades confere. De quebra: abrir uma publicada com o Editar já ligado deixa a build temporária em modo edição (`activateBuild`).

### A5. ✔ O app só avisa as trocas automáticas, e agora diz isso — resolvido na F13-T18
**Como ficou:**
- abaixo das runas da trilha (no Ler e no Montar) aparece, uma vez só: "As linhas 'Vira…' são trocas que o próprio jogo faz, conforme o campeão ou o modo de jogo. O app só avisa: a runa escolhida na página não muda.";
- cada linha "Vira…" repete isso ao passar o mouse;
- o sufixo "(ainda não vale no app)" saiu, e com ele o campo `vigente` do `runas.js`.

O registro original:

O app **não aplica nenhuma** das 24 trocas: todas são só um aviso na ficha ("Vira X quando..."). Não existe lógica por campeão nem por modo. O sufixo "(ainda não vale no app)" dependia de um comentário do MD e ficou sem uso quando a troca da Cassiopeia saiu. Proposta: tirar o código do sufixo e dizer uma vez, na tela de Runas, que as trocas são informativas.

### A6. Documentos desatualizados
- ✔ **Resolvido na F13-T87 (26/10/2026):** o `supabase.sql` virou o banco inteiro (runas, habilidades e rota dentro), ensaiado no projeto no ar; o README manda mudança nova entrar nele; os arquivos antigos têm trava. Como era: **`docs/servidor/supabase.sql` e o README do servidor** não conhecem runas e habilidades. O README manda "colar o supabase.sql inteiro de novo" quando o SQL muda. Seguindo isso hoje, a view pública perde as colunas `runas` e `habilidades`, e as Públicas deixam de mostrar runas, caladas. Ainda ficariam duas versões de `publicar_build`. O `runas_e_habilidades.sql` precisa entrar no `supabase.sql`, ou o README precisa mandar rodá-lo depois. **É o único destes com risco real.**
- **`docs/formato_de_importacao.md`**: ~~a linha 86 diz "Runas ficam de fora", e as linhas 49–54 documentam `RUNAS:`, `RUNAS 2:` e `FRAGMENTOS:`~~ — a frase saiu em 30/09/2026 (F13-T36b). Continua aberto: o prompt pronto para IA não pede runas, e os nomes válidos de runas não estão em nenhuma lista como a de `marcadores.md`.
- **`docs/qa.md`**: não lista as checagens de runa que o roteiro ganhou nas F13-T8, T12, T13 e T17 (controle de grupo na ficha; resoluções medindo as runas no Completo, nas cinco trilhas, com a Leitura calma). O roteiro está em dia, o documento não.
- **`docs/direcao_de_arte.md`**: não tem a tela de Runas (cores das trilhas lidas do ícone, a lombada da ficha, a faixa na forja).
- **`index.html`**, comentário do `vagaHtml`: ainda fala de "Absorvição Vital" e de fragmento sem arte. O código está certo, só o comentário é velho.
- **`docs/prompts_claude_design.md`**: o Prompt C (tela de Runas) nunca foi usado e ainda diz "Domínio".

Relacionado, mas não é de runa: ✔ o bug nº 13 ("Última atualização" pula ao trocar de build) foi consertado na F13-T33 (27/09/2026), e a parte das runas (comparar runas cruas com runas normalizadas) junto.

---

## Para conhecimento (não é pendência)

### Como foi conferido (23/09/2026)
- **Fontes:**
  - Data Dragon 16.18.1 em pt-BR (`data/_runesReforged.json`);
  - dados do cliente do jogo pelo CommunityDragon 16.18: `perks.json`, `trans-perks.json`, o arquivo de dados das runas, os arquivos dos **173 campeões** e os dos mapas do Summoner's Rift e do ARAM (as trocas automáticas saem daí);
  - wiki oficial em inglês, com o histórico de patches.
- **Nenhuma runa mudou no 26.19:** os arquivos de runas do cliente no 16.18, no 16.19 e no "latest" são idênticos byte a byte.
- **Números:** das 62 descrições, 7 têm número diferente do da Riot: 6 estão em F1 e o Toque Ígneo em F2. O Livro de Feitiços entra em F1 pelo marcador vazio. Os 71 ícones (62 runas e 9 fragmentos) conferem.
- **Leitura:** uma leitura independente do MD bate com o `runas.js` em tudo, menos nos blocos de controle de grupo (A1).
- **Fragmentos:** estão todos certos: composição dos três grupos, valores (Velocidade de Movimento 2,5%, Tenacidade 15%, Vida 65, Escalamento de Vida 10–180) e as linhas "Força Adaptativa destrinchada". Armadura, Resistência Mágica e Escalamento de Resistência ainda existem no dado do cliente, mas não estão em grupo nenhum no 16.18 (os dois primeiros saíram no V14.2). Estão certos em não aparecer.
- **Trabalho feito:** 7 conferências (uma por trilha, fragmentos, e substituições com cabeçalho) e 59 achados. Cada achado passou por dois céticos, com desempate quando discordaram, e **50 foram confirmados**. Reli os 9 derrubados e 4 voltaram: o Corki (com prova do cliente do jogo), a grafia do lema da Dominação, a etiqueta `roubo_vida` e o critério dos atributos. Os outros ficaram em "Para conhecimento". Na Cassiopeia, os céticos corrigiram a causa: a troca não existe mais, e eu conferi isso no cliente. A varredura do repositório juntou 38 registros espalhados.
- **Verificação das correções (F13-T16):** 6 conferências, uma por trecho do MD, olharam cada mudança e cada nome próprio (213 nomes). Cada problema passou por dois céticos: **39 foram confirmados** e corrigidos. O roteiro de QA passou depois de cada leva.

### Não "corrija" o MD com estes números da wiki
- **Faixas por nível:** a wiki leva a conta até o nível 20 (existe desde o V26.01 para quem completa a missão da rota do Topo). A Riot mostra só até o 18. Por isso a wiki diz, por exemplo, Eletrocutar 70–260, Chuva de Lâminas 2–22,12, Golpe Desleal 10–49,12, Gosto de Sangue 16–42,82 e Escalamento de Vida 10–200. O MD está certo com os números da Riot.
- **Guardião:** a wiki diz 3s de proteção e 2s de escudo, e a Riot diz 2,5s e 1,5s. O arquivo de dados do jogo no 16.18 usa 2,5 e 1,5. Quem erra é a wiki.

### Outras coisas que vale saber
- **`forja-de-runas.html`**, a sua página de estudo, fora do repositório por decisão sua de 20/09: ela tem uma **segunda cópia dos dados das runas**, digitada à mão, e não lê o `runas.js`. O texto é igual ao do app, com duas exceções: ainda diz "Absorvição Vital" (4 lugares) e tem a troca da Cassiopeia ativa. O app não usa essa página.
- Builds publicadas antes de 20/09 só mostram runas depois de republicadas. É por desenho: a coluna nasceu vazia.
- As runas ficam fora do JSON do cliente do LoL (Arsenal), por decisão sua. O cliente não importa runas.
- Os "fragmentos" do Atributo adicional (Stat Bonus) são de **item**, não de runa. Estão em `docs/pendencias_capitulo1.md`, D3.
- O mapa do Summoner's Rift tem mais um modo com trocas próprias, cujo nome o cliente guarda só como código (`{6462680f}`): Perspicácia Cósmica vira Velocidade de Aproximação, Faixa de Fluxo de Mana vira Arcanista do Axioma, Presença de Espírito vira Triunfo e Caça Suprema vira Caçador de Tesouros. Ficou fora do MD porque não dá para dizer que modo é.
- A wiki diz que, na Lua Sangrenta, o Livro de Feitiços Deslacrado vira Primeiro Ataque. O dado do cliente 16.18 diz Aprimoramento Glacial, e o MD segue o cliente.

---

## O que o arquivo tem

5 trilhas · **62 runas** · 9 fragmentos · 24 substituições automáticas. Não são cinco keystones por trilha: são **3 ou 4 keystones e 3 runas em cada um dos três slots**, que é o desenho do jogo. Comparando com o `runesReforged.json` em pt-BR da Riot: **62 de um lado, 62 do outro**, sem diferença em nenhuma direção.

| Trilha | Keystone | Slot 1 | Slot 2 | Slot 3 |
|---|---|---|---|---|
| Precisão | 4 | 3 | 3 | 3 |
| Dominação | 3 | 3 | 3 | 3 |
| Feitiçaria | 4 | 3 | 3 | 3 |
| Determinação | 3 | 3 | 3 | 3 |
| Inspiração | 3 | 3 | 3 | 3 |

### A arte dos fragmentos
Os fragmentos não estão no `runesReforged.json`. A arte deles vem do `perks.json` do CommunityDragon (os dados do próprio cliente do jogo), casada pelo nome em pt-BR. Cada endereço é pedido de verdade antes de entrar, e o que não responder fica sem ícone e vira pendência.

| Fragmento | Arquivo |
|---|---|
| Força Adaptativa | `StatModsAdaptiveForceIcon.png` |
| Velocidade de Ataque | `StatModsAttackSpeedIcon.png` |
| Aceleração de Habilidade | `StatModsCDRScalingIcon.png` |
| Velocidade de Movimento | `StatModsMovementSpeedIcon.png` |
| Vida | `StatModsHealthScalingIcon.png` |
| Escalamento de Vida | `StatModsHealthPlusIcon.png` |
| Tenacidade e Resistência a Lentidão | `StatModsTenacityIcon.png` |

---

## Resolvido (histórico)
- **18/09 — o leitor descartava 4 runas** (Tônico Triplo, Aperto dos Mortos-Vivos, Transcendência, Tempestade Crescente): a descrição delas ocupa mais de uma linha, e o leitor exigia abrir e fechar o colchete na mesma. Por causa disso a troca do Pós-choque parecia apontar "para o nada". Eu cheguei a dizer que podia ser curadoria sua. O leitor agora conta colchetes, e a comparação com o Data Dragon virou pendência automática. 58 → 62. Commit `ed7a42d`.
- **18/09 — "Absorvição Vital" → "Absorção Vital"** no MD, com a sua autorização: era a única runa sem ícone. Foi a única edição que fiz no seu arquivo.
- **20/09 — arte de Vida e de Escalamento de Vida trocada**, achada por você. Eu tinha escrito à mão a tabela nome → arquivo, e o nome do arquivo da Riot engana: Vida usa `HealthScaling` e Escalamento de Vida usa `HealthPlus`. A tabela à mão saiu (commit `a72fe36`).
- **20/09 — runas na build publicada**, pedido seu. No caminho houve o bug de produção "permission denied" (coluna nova fora do grant), consertado no mesmo dia.
- **F12-T2b — faixa de runas vazia aparecendo em toda build** (`hidden` perdia para `display:flex`).
- **F13-T8 (nº 4) — Duplicar e "Copiar e editar" perdiam as runas.** Os quatro caminhos de cópia agora concordam.
- **F13-T10 (nºs 9 e 10) — acessibilidade e resolução alcançam a tela de Runas.**
- **F13-T12 (nºs 6 e 16) — runa fora do 1º slot e fragmento no grupo errado na ida e volta por texto.** A vaga vazia sai como `-`. De brinde: `normRunas` apagava a página inteira quando não havia primária, inclusive os fragmentos.
- **F13-T13 (nº 7) — o link da build não levava runas.** Agora leva runas, habilidades, layout e Mestre Forjador.
- **23/09 (F13-T16) — a fonte de runas corrigida**, com a sua autorização: F1–F8, F9 (Força Adaptativa) e F10, mais os 39 problemas da verificação e as trocas por campeão e por modo tiradas do cliente. Ver "Resolvido em 23/09/2026" no topo.

## Lições (para não repetir)
- **Um leitor que ignora o que não entende mente por omissão.** Todo padrão que pode não casar precisa de uma contagem por fora que confira o resultado. O A1 é esta mesma lição, de novo.
- **O nome do arquivo da Riot mente.** A única tabela digitada à mão no projeto foi justamente a que errou.
- **O texto da Riot também erra.** Tem marcador vazio (Livro de Feitiços, Fonte da Vida) e número velho (Ritmo Fatal à distância). Quando o texto e o dado do jogo discordam, vale o dado do jogo.
- **A lista de trocas automáticas vem do cliente, não da wiki.** A lista geral da wiki não tinha Yuumi, Ambessa, Fiddlesticks nem Corki, e errava a Lua Sangrenta. Os arquivos de campeão e de mapa do cliente dão a lista inteira, e ela pode ser relida a cada patch.
- **Nome próprio escrito de memória erra.** Dezenas de nomes estavam traduzidos à mão do inglês da wiki. Todo nome de habilidade, item ou modo se confere no Data Dragon ou no stringtable pt-BR.
- **Checagem que nunca foi vista falhando não prova nada.** O roteiro de QA comparava o número de chaves das runas (sempre 6) em vez do conteúdo.
