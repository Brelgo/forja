window.RUNAS = {
 "meta": {
  "fonte": "data/Runas_League_of_Legends.md",
  "gerado": "2026-10-25",
  "patch": "16.21.1",
  "trilhas": 5,
  "runas": 62,
  "fragmentos": 9
 },
 "trilhas": [
  {
   "id": "precisao",
   "nome": "Precisão",
   "lema": "Torne-se uma lenda",
   "slots": [
    {
     "nome": "Keystone",
     "tipo": "keystone",
     "runas": [
      {
       "id": "pressione-o-ataque",
       "nome": "Pressione o Ataque",
       "descricao": "Acertar um Campeão inimigo com 3 ataques básicos consecutivos causa 40 – 160 de Dano Adaptativo adicional (com base no nível) e amplifica o dano causado por você em 8% até sair de combate contra Campeões.",
       "atributos": [],
       "classes": [
        "Lutador",
        "Assassino",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [
        "O dano adaptativo é do tipo \"proc\" — não aciona efeitos de feitiço.",
        "Não é afetado por modificadores de dano on-hit.",
        "A aplicação é rastreada individualmente e não interage entre usuários diferentes atacando o mesmo alvo.",
        "Efeitos que aplicam mais de um efeito on-hit por ataque (Disparo Iluminado do Lucian, Predador Desumano do Renekton, Lâmina da Fúria de Guinsoo) também aplicam acúmulos extras de Pressione o Ataque.",
        "O próprio ataque que dispara o 3º acúmulo (e ativa o bônus de dano) não se beneficia do dano amplificado — mas dano contínuo/efeitos seguintes que vêm junto com esse ataque (ex: Hemorragia, Tiro Tóxico) são amplificados."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/PressTheAttack/PressTheAttack.png",
       "riotId": 8005
      },
      {
       "id": "conquistador",
       "nome": "Conquistador",
       "descricao": "Ataques básicos ou habilidades que causam dano a um Campeão inimigo concedem 2 acúmulos de Conquistador por 5s, recebendo 1.8 - 4 de Força Adaptativa por acúmulo. Acumula-se até 12 vezes. Campeões de ataque à distância recebem somente 1 acúmulo por ataque básico. Ao chegar no máximo de acúmulos, cura 8% do dano que você causa a Campeões (5% para Campeões de ataque à distância).",
       "atributos": [
        "Cura",
        "Dano de Ataque",
        "Poder de Habilidade"
       ],
       "classes": [
        "Atirador",
        "Lutador",
        "Assassino"
       ],
       "adaptativa": "1.08–2.4 de Dano de Ataque ou 1.8–4 de Poder de Habilidade — nunca as duas coisas juntas.",
       "notas": [
        "Só acumula uma vez por instância de conjuração — ex: as ondas de fogo da passiva da Kayle (Ascensão Divina, nível 11) compartilham a instância com o ataque básico que as originou, não empilham separadamente.",
        "Efeitos de dano ao longo do tempo ou fontes contínuas de dano só concedem acúmulo uma vez a cada 4 segundos."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/Conqueror/Conqueror.png",
       "riotId": 8010
      },
      {
       "id": "ritmo-fatal",
       "nome": "Ritmo Fatal",
       "descricao": "Atacar um Campeão inimigo concede a você (6% para atacantes corpo a corpo, 4% para atacantes à distância) de Velocidade de Ataque por 6s, até 6 acúmulos. Com o máximo de acúmulos, causa (9-30 para atacantes corpo a corpo e 6-24 para atacantes à distância) de Dano Adaptativo adicional ao contato, aumentado em 1% a cada 1% de Velocidade de Ataque adicional.",
       "atributos": [
        "Velocidade de Ataque"
       ],
       "classes": [
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [
        "Não permite exceder o limite de Velocidade de Ataque; a Velocidade de Ataque acima do limite ainda aumenta o dano do disparo.",
        "O dano do disparo (bolt) é do tipo \"proc\" — não aciona efeitos de feitiço.",
        "Os valores de ataque à distância vêm dos de corpo a corpo: a Velocidade de Ataque por acúmulo é multiplicada por 0,8 e o dano do disparo por 0,667 (é o ataque à distância que leva o corte de 1/3). A escala de 1% a cada 1% de Velocidade de Ataque adicional não muda.",
        "O texto oficial da Riot ainda mostra 4% e 6-24 para ataque à distância; o jogo usa 4,8% por acúmulo (6% × 0,8) e cerca de 6-20 de dano (× 0,667)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LethalTempo/LethalTempoTemp.png",
       "riotId": 8008
      },
      {
       "id": "agilidade-nos-pes",
       "nome": "Agilidade nos Pés",
       "descricao": "Ao atacar ou se mover, você recebe acúmulos de Energia. Com 100 acúmulos, seu próximo Ataque fica Energizado. Ataques Energizados curam em 15 - 160 (+0.1 de DdA adicional, +0.05 de PdH) e concedem 20% de Velocidade de Movimento por 1s. Para Campeões de ataque à distância, a cura é 60% eficaz e a Velocidade de Movimento é 75% eficaz. Toda a cura é 15% eficaz contra tropas.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade",
        "Velocidade de Movimento",
        "Cura"
       ],
       "classes": [
        "Atirador",
        "Assassino"
       ],
       "adaptativa": "",
       "notas": [
        "Cada ataque básico on-attack gera 6 pontos de acúmulo; também gera 1 ponto a cada 24 unidades de distância percorrida (por qualquer forma de movimento, incluindo dash/blink/deslocamento).",
        "Habilidades que aplicam efeitos on-hit também geram 6 pontos de acúmulo.",
        "Não é consumido contra sentinelas ou plantas da selva."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/FleetFootwork/FleetFootwork.png",
       "riotId": 8021
      }
     ]
    },
    {
     "nome": "Slot 1",
     "tipo": "slot",
     "runas": [
      {
       "id": "absorcao-vital",
       "nome": "Absorção Vital",
       "descricao": "Abater um alvo restaura 1-23 de Vida com base no nível.",
       "atributos": [
        "Cura"
       ],
       "classes": [
        "Lutador",
        "Assassino",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/AbsorbLife/AbsorbLife.png",
       "riotId": 9101
      },
      {
       "id": "triunfo",
       "nome": "Triunfo",
       "descricao": "Eliminações restauram 5% da sua Vida perdida, 2.5% da sua Vida Máxima e concedem 20 de ouro adicional.",
       "atributos": [
        "Vida Máxima",
        "Cura",
        "Ouro"
       ],
       "classes": [
        "Tank",
        "Lutador",
        "Assassino",
        "Atirador",
        "Suporte",
        "Mago"
       ],
       "adaptativa": "",
       "notas": [
        "A cura é calculada com base na vida que falta no momento exato do abate — se outro abate acontecer durante o pequeno atraso do efeito (~1s), a cura pendente é recalculada pelo valor do abate mais recente, não somada."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/Triumph.png",
       "riotId": 9111
      },
      {
       "id": "presenca-de-espirito",
       "nome": "Presença de Espírito",
       "descricao": "Causar dano a um Campeão inimigo restaura 6 - 50 (80% para Campeões à distância) de Mana ou 6 de Energia. Eliminações restauram 15% do seu Mana máximo ou da sua Energia máxima. Tempo de Recarga da restauração por dano: 8s.",
       "atributos": [
        "Mana / Energia"
       ],
       "classes": [
        "Mago",
        "Suporte",
        "Assassino"
       ],
       "adaptativa": "",
       "notas": [
        "Em abate, campeões que usam energia restauram 30 de energia (60 pra Shen, 42 pra Akali durante a Proteção do Crepúsculo)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/PresenceOfMind/PresenceOfMind.png",
       "riotId": 8009
      }
     ]
    },
    {
     "nome": "Slot 2",
     "tipo": "slot",
     "runas": [
      {
       "id": "lenda-espontaneidade",
       "nome": "Lenda: Espontaneidade",
       "descricao": "Recebe 3% de Velocidade de Ataque mais um adicional de 1.5% para cada acúmulo de Lenda (máximo de 10 acúmulos). Avance nos acúmulos de Lenda a cada abate de Campeão, abate de monstro épico, abate de monstro grande e abate de tropas.",
       "atributos": [
        "Velocidade de Ataque"
       ],
       "classes": [
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [
        "As 3 runas de Lenda (Espontaneidade, Aceleração, Linhagem) compartilham o mesmo sistema de acúmulo: 100 pontos por abate de campeão, 100 por abate de monstro épico, 25 por monstro grande, 4 por minion — até 10 acúmulos (15 na Linhagem)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LegendAlacrity/LegendAlacrity.png",
       "riotId": 9104
      },
      {
       "id": "lenda-aceleracao",
       "nome": "Lenda: Aceleração",
       "descricao": "Recebe 1,5 de Aceleração de habilidades básicas para cada acúmulo de Lenda (máximo de 10 acúmulos). Progride nos acúmulos de Lenda a cada eliminação de Campeão, eliminação de monstro épico, abate de monstro grande e abate de tropas.",
       "atributos": [
        "Aceleração de Habilidade"
       ],
       "classes": [
        "Lutador",
        "Mago"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LegendHaste/LegendHaste.png",
       "riotId": 9105
      },
      {
       "id": "lenda-linhagem",
       "nome": "Lenda: Linhagem",
       "descricao": "Recebe 0.45% de Roubo de Vida para cada acúmulo de Lenda (máximo de 15 acúmulos). Com o máximo de acúmulos de Lenda, recebe 85 de Vida máxima adicional. Progride nos acúmulos de Lenda a cada eliminação de Campeão, eliminação de monstro épico, abate de monstro grande e abate de tropas.",
       "atributos": [
        "Vida Máxima",
        "Roubo de Vida"
       ],
       "classes": [
        "Atirador",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LegendBloodline/LegendBloodline.png",
       "riotId": 9103
      }
     ]
    },
    {
     "nome": "Slot 3",
     "tipo": "slot",
     "runas": [
      {
       "id": "golpe-de-misericordia",
       "nome": "Golpe de Misericórdia",
       "descricao": "Causa 8% mais dano para Campeões que possuem menos de 40% de Vida.",
       "atributos": [],
       "classes": [
        "Assassino",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [
        "Só ativa em dano causado DEPOIS que o alvo já estiver abaixo de 40% de vida — o próprio golpe que derruba o alvo abaixo desse limite não recebe o bônus.",
        "Atualmente também se aplica a Dano Verdadeiro (exceto o de Golpear)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/CoupDeGrace/CoupDeGrace.png",
       "riotId": 8014
      },
      {
       "id": "dilacerar",
       "nome": "Dilacerar",
       "descricao": "Causa 8% a mais de dano a Campeões com mais de 60% de Vida.",
       "atributos": [],
       "classes": [
        "Atirador",
        "Lutador",
        "Assassino"
       ],
       "adaptativa": "",
       "notas": [
        "Atualmente também se aplica a Dano Verdadeiro (exceto o de Golpear)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/CutDown/CutDown.png",
       "riotId": 8017
      },
      {
       "id": "ate-a-morte",
       "nome": "Até a Morte",
       "descricao": "Causa de 5% a 11% a mais de dano a Campeões enquanto sua Vida estiver abaixo de 60%. O dano máximo é atingido com 30% de Vida.",
       "atributos": [],
       "classes": [
        "Lutador",
        "Assassino",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [
        "Atualmente também se aplica a Dano Verdadeiro (exceto o de Golpear)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/LastStand/LastStand.png",
       "riotId": 8299
      }
     ]
    }
   ],
   "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7201_Precision.png",
   "riotId": 8000,
   "cor": "#c0a878"
  },
  {
   "id": "dominacao",
   "nome": "Dominação",
   "lema": "Caçar e eliminar presa",
   "slots": [
    {
     "nome": "Keystone",
     "tipo": "keystone",
     "runas": [
      {
       "id": "eletrocutar",
       "nome": "Eletrocutar",
       "descricao": "Acertar um Campeão com 3 Ataques ou Habilidades separadas em até 3s causa Dano Adaptativo adicional. Dano: 70 - 240 (+0.1 de DdA adicional, +0.05 de PdH) de dano. Tempo de Recarga: 20s.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade"
       ],
       "classes": [
        "Assassino",
        "Mago",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [
        "Cegueira, Debilitação (Cripple), Sonolência (Drowsy), Kinemáticos, Visão Reduzida e Estase NÃO contam como Controle de Grupo válido pra gerar acúmulo.",
        "Pode ativar mesmo estando morto (se os 3 acúmulos já tiverem sido aplicados antes).",
        "A janela de 3s não reinicia a cada acúmulo — o terceiro precisa acontecer dentro de 3s do primeiro, não do segundo.",
        "Dano do tipo \"proc\" — não aciona efeitos de feitiço."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/Electrocute/Electrocute.png",
       "riotId": 8112
      },
      {
       "id": "colheita-sombria",
       "nome": "Colheita Sombria",
       "descricao": "Causar dano a um Campeão que esteja com menos de 50% de Vida causa Dano Adaptativo e colhe a alma dele, aumentando permanentemente o dano de Colheita Sombria em 11. Colheita Sombria Dano: 30 (+11 de dano por alma) (+0.1 de DdA adicional) (+0.05 de PdH). Tempo de Recarga: 35s (redefine para 1.0s ao abater).",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade"
       ],
       "classes": [
        "Assassino",
        "Mago"
       ],
       "adaptativa": "",
       "notas": [
        "Não ativa com dano menor que 2 (exceto a Labareda do Brand).",
        "Não ativa com dano do tipo \"proc\" de outras fontes (ex: Chamuscar, Tormento de Liandry, Ricochete da Sivir) — exceto o Tiro Tóxico do Teemo.",
        "Ativa em clones, mas não em zumbis.",
        "Não colhe uma Alma adicional durante o pequeno atraso entre causar a condição e efetivamente ganhar a Alma."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/DarkHarvest/DarkHarvest.png",
       "riotId": 8128
      },
      {
       "id": "chuva-de-laminas",
       "nome": "Chuva de Lâminas",
       "descricao": "Recebe 90% (60% para Campeões de ataque à distância) de Velocidade de Ataque e Dano Verdadeiro adicional ao atacar um Campeão inimigo por até 3 ataques. O efeito acabará caso passe mais de 3s entre os ataques. Tempo de Recarga: 10s. Dano ao contato: 2 - 20 (+0.12 de DdA adicional, +0.1 de PdH) de dano. Reinicializações de ataques aumentam o limite de ataques em 1. Permite exceder temporariamente o limite de Velocidade de Ataque.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade",
        "Velocidade de Ataque"
       ],
       "classes": [
        "Atirador",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "Dano do tipo \"proc\" — não aciona efeitos de feitiço.",
        "Só gera acúmulo extra a partir de reset de ataque se o efeito que resetou tiver uma marcação específica de \"reset de ataque\" — feitiços como Escolha uma Carta (Twisted Fate), Uivo Primitivo reconjurado (Warwick) e o Explocinturão Hextec resetam o temporizador de ataque mas NÃO têm essa marcação, então não geram acúmulo extra."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/HailOfBlades/HailOfBlades.png",
       "riotId": 9923
      }
     ]
    },
    {
     "nome": "Slot 1",
     "tipo": "slot",
     "runas": [
      {
       "id": "golpe-desleal",
       "nome": "Golpe Desleal",
       "descricao": "Causar dano a Campeões com movimento ou ações debilitadas causa 10 - 45 de Dano Verdadeiro adicional (com base no nível). Tempo de Recarga: 4s. É ativado pelo dano causado após a debilitação.",
       "atributos": [],
       "classes": [
        "Assassino",
        "Lutador",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [
        "O dano é do tipo \"proc\" — não aciona efeitos de feitiço (item/runa) que dependem de dano de habilidade ou de ataque básico.",
        "Verifica o status do alvo toda vez que dano é causado, não só uma vez — pode ativar em qualquer instância de dano após o alvo ficar debilitado.",
        "Não ativa se o dano ocorrer no mesmo tick de jogo em que a própria debilitação foi aplicada pela mesma instância de conjuração (exceto se o alvo já estava debilitado por outra fonte antes).",
        "Debilitação aplicada on-hit (ex: Atropelar do Alistar) já conta antes dessa checagem; debilitação aplicada on-pre-apply (ex: Cetro de Cristal de Rylai) não conta."
       ],
       "cg": {
        "categoria": "\"movimento ou ações debilitadas\"",
        "inclui": [
         "Aéreo",
         "Berserk",
         "Encantamento",
         "Fuga Forçada",
         "Provocação",
         "Enraizamento",
         "Sono",
         "Estase",
         "Atordoamento",
         "Supressão",
         "Lentidão",
         "Cegueira",
         "Desarmamento",
         "Ancoragem",
         "Visão Reduzida",
         "Metamorfose",
         "Silenciamento"
        ],
        "naoInclui": "Debilitação de Velocidade de Ataque (Cripple).",
        "obs": ""
       },
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/CheapShot/CheapShot.png",
       "riotId": 8126
      },
      {
       "id": "gosto-de-sangue",
       "nome": "Gosto de Sangue",
       "descricao": "Cura ao causar dano a um Campeão inimigo. Cura: 16-40 (+0.1 de DdA adicional, +0.05 de PdH) de Vida (com base no nível). Tempo de Recarga: 20s.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade",
        "Cura"
       ],
       "classes": [
        "Assassino",
        "Mago",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/TasteOfBlood/GreenTerror_TasteOfBlood.png",
       "riotId": 8139
      },
      {
       "id": "impacto-repentino",
       "nome": "Impacto Repentino",
       "descricao": "Depois de usar um avanço, salto, teleporte ou ao sair da furtividade, seus ataques básicos e habilidades de dano causam 20-80 de Dano Verdadeiro adicional com base no nível a Campeões inimigos por 4s. Tempo de Recarga: 10s.",
       "atributos": [],
       "classes": [
        "Assassino"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/SuddenImpact/SuddenImpact.png",
       "riotId": 8143
      }
     ]
    },
    {
     "nome": "Slot 2",
     "tipo": "slot",
     "runas": [
      {
       "id": "sexto-sentido",
       "nome": "Sexto Sentido",
       "descricao": "Detecta automaticamente uma sentinela oculta próxima, rastreando-a para a equipe. Nível 11: também revela a sentinela por 10s. O efeito tem um Tempo de Recarga de 250s.",
       "atributos": [
        "Visão"
       ],
       "classes": [
        "Suporte",
        "Assassino"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/SixthSense/SixthSense.png",
       "riotId": 8137
      },
      {
       "id": "lembrancas-aterrorizantes",
       "nome": "Lembranças Aterrorizantes",
       "descricao": "Colete 1 Lembrança ao eliminar Campeões, até um máximo de 18. Recebe 6 de Aceleração de Amuleto para cada Lembrança coletada. Em modos de jogo sem Amuletos de visão, recebe 3 de Aceleração de Feitiço de Invocador.",
       "atributos": [
        "Visão",
        "Aceleração de Feitiço de Invocador"
       ],
       "classes": [
        "Assassino",
        "Tank"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/GrislyMementos/GrislyMementos.png",
       "riotId": 8140
      },
      {
       "id": "sentinela-profunda",
       "nome": "Sentinela Profunda",
       "descricao": "Suas sentinelas na selva inimiga são Profundas. Sentinelas Profundas recebem +1 de Vida adicional e +(30-45)s de duração aumentada (+(45-150)s para o Amuleto de Sentinela Invisível). Nível 9: as sentinelas no rio também são Profundas.",
       "atributos": [
        "Visão"
       ],
       "classes": [
        "Suporte",
        "Assassino",
        "Tank"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/DeepWard/DeepWard.png",
       "riotId": 8141
      }
     ]
    },
    {
     "nome": "Slot 3",
     "tipo": "slot",
     "runas": [
      {
       "id": "cacador-de-tesouros",
       "nome": "Caçador de Tesouros",
       "descricao": "Receba 50 de ouro adicional na próxima vez que coletar um acúmulo de Caçador de Recompensas. Aumente o ouro recebido em 20 de ouro para cada acúmulo de Caçador de Recompensas, até 130 de ouro. Acúmulos de Caçador de Recompensas serão recebidos na primeira vez que você eliminar cada Campeão inimigo.",
       "atributos": [
        "Ouro"
       ],
       "classes": [
        "Assassino",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/TreasureHunter/TreasureHunter.png",
       "riotId": 8135
      },
      {
       "id": "caca-incansavel",
       "nome": "Caça Incansável",
       "descricao": "Recebe 8 de Velocidade de Movimento fora de combate para cada acúmulo de Caçador de Recompensas. Acúmulos de Caçador de Recompensas serão recebidos na primeira vez que você eliminar cada Campeão inimigo.",
       "atributos": [
        "Velocidade de Movimento"
       ],
       "classes": [
        "Assassino",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/RelentlessHunter/RelentlessHunter.png",
       "riotId": 8105
      },
      {
       "id": "caca-suprema",
       "nome": "Caça Suprema",
       "descricao": "Sua ultimate recebe 6 de Aceleração de Habilidade, além de 5 de Aceleração de Habilidade adicional por acúmulo de Caçador de Recompensas. Acúmulos de Caçador de Recompensas são recebidos na primeira vez que você conseguir uma eliminação em cada Campeão inimigo.",
       "atributos": [
        "Aceleração de Habilidade"
       ],
       "classes": [
        "Assassino",
        "Mago"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/UltimateHunter/UltimateHunter.png",
       "riotId": 8106
      }
     ]
    }
   ],
   "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7200_Domination.png",
   "riotId": 8100,
   "cor": "#c03030"
  },
  {
   "id": "feiticaria",
   "nome": "Feitiçaria",
   "lema": "Desferir destruição",
   "slots": [
    {
     "nome": "Keystone",
     "tipo": "keystone",
     "runas": [
      {
       "id": "invocar-aery",
       "nome": "Invocar Aery",
       "descricao": "Causar dano a Campeões inimigos com ataques básicos ou Habilidades envia Aery até eles, causando 10 - 50 de dano com base no nível (+0.05 de PdH) (+0.1 de DdA adicional). Fortalecer ou proteger aliados com Habilidades envia Aery até eles, concedendo um escudo de 20 - 100 com base no nível (+0.05 de PdH) (+0.1 de DdA adicional). Aery não é enviada novamente até que ela retorne a você.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade",
        "Escudo"
       ],
       "classes": [
        "Mago",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [
        "Dano do tipo \"proc\" — não aciona efeitos de feitiço.",
        "O efeito de aliado dispara em qualquer habilidade que afete aliados (mirada ou não) — inclui o Estandarte Demaciano do Jarvan IV (o escudo vai para o aliado mais perto da bandeira), o Refúgio da Ovelha (Kindred) e os Caprichos (Lulu). NÃO dispara com a Maré Oscilante da Nami (não dá pra escudar um aliado acertando-o com a Prisão Aquática).",
        "Ótima em habilidades de dano ao longo do tempo, já que pode ativar várias vezes durante a duração (ex: Visões Maléficas do Malzahar, Rastro de Veneno do Singed)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/SummonAery/SummonAery.png",
       "riotId": 8214
      },
      {
       "id": "cometa-arcano",
       "nome": "Cometa Arcano",
       "descricao": "Ao causar dano a um Campeão com uma Habilidade, um cometa é lançado onde ele estiver, causando dano aumentado com base na distância. Dano Adaptativo: 15 - 100 com base no nível (+0.05 de PdH e +0.1 de DdA adicional). Tempo de Recarga: 20 - 8s. A Amplificação de Dano escala até 100% a 750 de alcance.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade"
       ],
       "classes": [
        "Mago"
       ],
       "adaptativa": "",
       "notas": [
        "Dano do tipo \"proc\" e marcado como área de efeito — não aciona efeitos de feitiço.",
        "Pode ser bloqueado por escudos de feitiço, e é um projétil — pode ser interceptado pelo Inquebrável do Braum, Voragem Afiada da Samira e Parede de Vento do Yasuo.",
        "Não ativa causando 0 de dano.",
        "Fica visível mesmo sem visão do campeão que a usou — pode entregar a posição dele."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/ArcaneComet/ArcaneComet.png",
       "riotId": 8229
      },
      {
       "id": "avanco-da-tempestade",
       "nome": "Avanço da Tempestade",
       "descricao": "Causar 25% da Vida máxima de um Campeão como dano dentro de 3s concede 48% de Velocidade de Movimento e 50% de Resistência a Lentidão por 4s. A Velocidade de Movimento tem 75% de eficácia para Campeões de ataque à distância. Tempo de Recarga: 20s - 10s.",
       "atributos": [
        "Velocidade de Movimento"
       ],
       "classes": [
        "Mago",
        "Assassino"
       ],
       "adaptativa": "",
       "notas": [
        "Essa runa (Stormraider's Surge) voltou ao jogo em abril de 2026 (Patch 26.09) substituindo a antiga Ímpeto Gradual (Phase Rush) — ela mesma é o retorno de uma mastery da Season 6 removida em novembro de 2017 (Patch 7.22)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/PhaseRush/StormraidersSurgeRuneIcon2.png",
       "riotId": 8230
      },
      {
       "id": "toque-igneo",
       "nome": "Toque Ígneo",
       "descricao": "Causar dano a um Campeão com uma Habilidade o queima, causando 3-12 com base no nível (+2.5% do PdH) (+7% do DdA adicional) de Dano Mágico por segundo. Após queimar por 3s, o dano da Queimadura aumenta em 75% enquanto o alvo permanece em chamas. Duração: Alvo único: 4s. Área de ação: 2s. Dano ao longo do tempo: 1s.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade"
       ],
       "classes": [
        "Mago",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/DeathfireTouch/DEATHFIRE_TOUCH_KEYSTONE.png",
       "riotId": 8992
      }
     ]
    },
    {
     "nome": "Slot 1",
     "tipo": "slot",
     "runas": [
      {
       "id": "arcanista-do-axioma",
       "nome": "Arcanista do Axioma",
       "descricao": "Sua ultimate causa/concede 12% a mais de dano, cura e Escudo (o aumento do dano em área de ação é reduzido a 8%). Eliminar um Campeão inimigo reduz o Tempo de Recarga atual da sua ultimate em 7%.",
       "atributos": [
        "Cura",
        "Escudo"
       ],
       "classes": [
        "Mago",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [
        "Afeta os efeitos de dano da passiva da ultimate do usuário (com exceções específicas por campeão, ex: a passiva do Portal de Reinos do Ryze é um efeito de dano, mas não parece aumentar em 12% nem em 8% o dano do combo Fluxo de Feitiço + Sobrecarregar).",
        "Também amplifica dano/cura/escudo de pets invocados pela ultimate (exceto o Salto de Fé da Illaoi).",
        "Afeta dano da ultimate contra não-campeões e cura/escudo pra não-campeões aliados."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/NullifyingOrb/Axiom_Arcanist.png",
       "riotId": 8224
      },
      {
       "id": "faixa-de-fluxo-de-mana",
       "nome": "Faixa de Fluxo de Mana",
       "descricao": "Atingir um Campeão inimigo com uma habilidade aumenta permanentemente seu Mana máximo em 25, até o total de 250 de Mana. Após atingir 250 de Mana adicional, 1% do seu Mana perdido é restaurado a cada 5s. Tempo de Recarga: 15s.",
       "atributos": [
        "Mana / Energia"
       ],
       "classes": [
        "Mago",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [
        "\"Afetar\" um campeão inimigo, pro gatilho dessa runa, significa: causar algum tipo de dano de habilidade (dano de feitiço, de área, contínuo etc.) OU aplicar um dos seguintes: Controle de Grupo de imobilização, Lentidão, Dano ao Longo do Tempo, Veneno, Redução de Resistência.",
        "Leva no mínimo 150 segundos pra carregar completamente.",
        "Tecnicamente reduz a mana atual primeiro e só depois aumenta a mana máxima (pra não quebrar a regra de que aumentar o máximo também aumenta o atual) — isso conta como gasto de mana pra efeitos que dependem disso."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/ManaflowBand/ManaflowBand.png",
       "riotId": 8226
      },
      {
       "id": "manto-de-nimbus",
       "nome": "Manto de Nimbus",
       "descricao": "Depois de conjurar um Feitiço de Invocador, recebe um aumento de Velocidade de Movimento que dura 2s e permite atravessar unidades. Aumento: 15% - 45% de Velocidade de Movimento com base no Tempo de Recarga do Feitiço de Invocador (Feitiços de Invocador com Tempos de Recarga maiores concedem mais Velocidade de Movimento).",
       "atributos": [
        "Velocidade de Movimento"
       ],
       "classes": [
        "Mago",
        "Suporte",
        "Assassino"
       ],
       "adaptativa": "",
       "notas": [
        "O bônus de Velocidade de Movimento depende de qual faixa de tempo de recarga o feitiço de invocador usado se encaixa (existem 3 faixas).",
        "Teleporte é tratado como sempre estando na faixa mais alta (exceto quando usado via Roubo Arcano da Zoe, que usa a faixa mais baixa).",
        "Usar múltiplos feitiços só considera o de maior bônus; cada faixa de recarga tem sua própria ativação independente.",
        "Pra Teleporte/Flash Hextec, ativa quando a canalização termina OU é interrompida (o Flash Hextec precisa ter canalizado até o teleporte ficar disponível pra contar como interrompido)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/NimbusCloak/6361.png",
       "riotId": 8275
      }
     ]
    },
    {
     "nome": "Slot 2",
     "tipo": "slot",
     "runas": [
      {
       "id": "transcendencia",
       "nome": "Transcendência",
       "descricao": "Recebe efeitos adicionais ao atingir os seguintes níveis: - Nível 5: +5 de Aceleração de Habilidade - Nível 8: +5 de Aceleração de Habilidade - Nível 11: ao eliminar um Campeão inimigo, reduz o Tempo de Recarga restante das habilidades básicas em 20%",
       "atributos": [
        "Aceleração de Habilidade"
       ],
       "classes": [
        "Mago",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "Só concede o bônus exatamente nos níveis 5, 8 e 11 — não é um ganho contínuo, então só é efetiva a partir do meio de jogo."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Transcendence/Transcendence.png",
       "riotId": 8210
      },
      {
       "id": "celeridade",
       "nome": "Celeridade",
       "descricao": "Todos os efeitos de movimentação são 7% mais eficazes em você, além de conceder 1% de Velocidade de Movimento.",
       "atributos": [
        "Velocidade de Movimento"
       ],
       "classes": [
        "Mago",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [
        "Amplia em 7% os seus OUTROS bônus de Velocidade de Movimento: os fixos sempre — inclusive os negativos (ex: Caprichos da Lulu contra inimigos, Expurgar do Urgot) —, os percentuais aditivos só quando a soma deles passa de 5%, e os multiplicativos sempre."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Celerity/CelerityTemp.png",
       "riotId": 8234
      },
      {
       "id": "foco-absoluto",
       "nome": "Foco Absoluto",
       "descricao": "Acima de 70% de Vida, recebe um adicional adaptativo de até 18 de Dano de Ataque ou 30 de Poder de Habilidade (com base no nível). Concede 1.8 de Dano de Ataque ou 3 de Poder de Habilidade no nível 1.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade"
       ],
       "classes": [
        "Mago",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/AbsoluteFocus/AbsoluteFocus.png",
       "riotId": 8233
      }
     ]
    },
    {
     "nome": "Slot 3",
     "tipo": "slot",
     "runas": [
      {
       "id": "chamuscar",
       "nome": "Chamuscar",
       "descricao": "Sua próxima habilidade de dano a atingir o alvo incinera Campeões, causando de 20 a 40 de Dano Mágico adicional, com base no nível, após 1s. Tempo de Recarga: 10s.",
       "atributos": [],
       "classes": [
        "Mago"
       ],
       "adaptativa": "",
       "notas": [
        "Dano do tipo \"proc\", marcado como indireto e periódico — não aciona efeitos de feitiço.",
        "Só afeta UM campeão mesmo se disparado por uma habilidade em área — atinge o primeiro campeão a receber o efeito da habilidade."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Scorch/Scorch.png",
       "riotId": 8237
      },
      {
       "id": "caminhar-sobre-as-aguas",
       "nome": "Caminhar Sobre as Águas",
       "descricao": "Recebe 10 de Velocidade de Movimento e 13-30 de Força Adaptativa (com base no nível) enquanto estiver no rio.",
       "atributos": [
        "Velocidade de Movimento",
        "Dano de Ataque",
        "Poder de Habilidade"
       ],
       "classes": [
        "Mago",
        "Assassino",
        "Tank"
       ],
       "adaptativa": "7.8–18.0 de Dano de Ataque ou 13–30 de Poder de Habilidade — nunca as duas coisas juntas.",
       "notas": [
        "O bônus de Velocidade de Movimento decai ao longo de 1s depois de sair do rio, mas o bônus de Força Adaptativa é perdido imediatamente.",
        "Poças d'água criadas no território selvagem por efeitos de transformação em oceano também contam como \"rio\" pra ativar essa runa.",
        "A zona de \"rio\" inclui as partes fora das brenhas no meio do mapa também, não só o rio central."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Waterwalking/Waterwalking.png",
       "riotId": 8232
      },
      {
       "id": "tempestade-crescente",
       "nome": "Tempestade Crescente",
       "descricao": "A cada 10 minutos de jogo, recebe PdH ou DdA Adaptativo, crescendo continuamente: - 10 min: +8 PdH ou 5 DdA - 20 min: +24 PdH ou 14 DdA - 30 min: +48 PdH ou 29 DdA - 40 min: +80 PdH ou 48 DdA - 50 min: +120 PdH ou 72 DdA - 60 min: +168 PdH ou 101 DdA E assim por diante.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade"
       ],
       "classes": [
        "Mago",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [
        "O intervalo de 10 minutos muda por modo de jogo: ARAM e URF a cada 6min, Jogo Dinâmico a cada 7min, Blitz do Nexus a cada 4.5min."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/GatheringStorm/GatheringStorm.png",
       "riotId": 8236
      }
     ]
    }
   ],
   "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7202_Sorcery.png",
   "riotId": 8200,
   "cor": "#9090f0"
  },
  {
   "id": "determinacao",
   "nome": "Determinação",
   "lema": "Viva para sempre",
   "slots": [
    {
     "nome": "Keystone",
     "tipo": "keystone",
     "runas": [
      {
       "id": "aperto-dos-mortos-vivos",
       "nome": "Aperto dos Mortos-Vivos",
       "descricao": "A cada 4s em combate, seu próximo ataque básico contra um Campeão irá: - Causar Dano Mágico adicional equivalente a 3.5% da sua Vida máxima - Curar você em 1.3% da sua Vida máxima - Aumentar permanentemente sua Vida em 5 Campeões de ataque à distância: o dano, a cura e a Vida permanente recebidos têm 40% de eficácia.",
       "atributos": [
        "Vida Máxima",
        "Cura"
       ],
       "classes": [
        "Tank",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "Dano do tipo \"proc\" — não aciona efeitos de feitiço, e não é afetado por modificadores de dano on-hit.",
        "Pra campeões de ataque à distância, o dano, a cura e o ganho de Vida permanente têm 40% de eficácia (1.4% de dano, 0.52% de cura e 2 de Vida por ativação)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/GraspOfTheUndying/GraspOfTheUndying.png",
       "riotId": 8437
      },
      {
       "id": "pos-choque",
       "nome": "Pós-choque",
       "descricao": "Após imobilizar um Campeão inimigo, aumenta a própria Armadura e Resistência Mágica em 45 + 75% de suas resistências adicionais por 2.5s. Depois, ocorre uma explosão que causa Dano Mágico a inimigos próximos. Dano: 25 - 120 (+8% da sua Vida adicional). Tempo de Recarga: 20s. A resistência adicional de Pós-choque é limitada a: 80 - 150 (com base no nível).",
       "atributos": [
        "Armadura",
        "Resistência Mágica",
        "Vida Máxima"
       ],
       "classes": [
        "Tank",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [
        "Não ativa se o efeito de imobilização foi aplicado a um alvo imune a deslocamento (displacement immune).",
        "A resistência bônus não escala dinamicamente — só considera o valor de resistência que você tem no momento exato do gatilho."
       ],
       "cg": {
        "categoria": "\"imobilizar\" (categoria pura, sem Lentidão)",
        "inclui": [
         "Aéreo",
         "Berserk",
         "Encantamento",
         "Fuga Forçada",
         "Provocação",
         "Enraizamento",
         "Sono",
         "Estase",
         "Atordoamento",
         "Supressão"
        ],
        "naoInclui": "Lentidão — diferente de Fonte da Vida, que inclui.",
        "obs": ""
       },
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/VeteranAftershock/VeteranAftershock.png",
       "riotId": 8439
      },
      {
       "id": "guardiao",
       "nome": "Guardião",
       "descricao": "Protege por 2.5s aliados a até 350 unidades de distância de você e aliados nos quais você tenha conjurado habilidades. Durante a Proteção, caso você ou o aliado sofram uma quantidade significativa de dano ao longo da duração de Guardião, ambos ganham um escudo por 1.5s. Tempo de Recarga: 75s-40s. Escudo: 40 - 150 + 20% do seu Poder de Habilidade + 6% da sua Vida adicional. Limiar de acionamento: 50 - 165 de dano pós-mitigação.",
       "atributos": [
        "Poder de Habilidade",
        "Vida Máxima",
        "Escudo"
       ],
       "classes": [
        "Suporte",
        "Tank"
       ],
       "adaptativa": "",
       "notas": [
        "NÃO ativa com Curar (feitiço de invocador), Ária da Perseverança da Sona ou Barreira Prismática da Lux.",
        "ATIVA com a Passagem Sombria do Thresh quando conjurada num aliado.",
        "O \"Você e Eu!\" da Yuumi não aplica o Guardião por si só, mas o Guardião ainda ativa se ela estiver no alcance do aliado alvo.",
        "Não ativa se o usuário estiver morto."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Guardian/Guardian.png",
       "riotId": 8465
      }
     ]
    },
    {
     "nome": "Slot 1",
     "tipo": "slot",
     "runas": [
      {
       "id": "demolir",
       "nome": "Demolir",
       "descricao": "Seu terceiro ataque contra torres causa 85 (+28% da Vida máxima) corpo a corpo ou 50 (+20% da Vida máxima) à distância de Dano Físico adicional. Tempo de Recarga: 30s.",
       "atributos": [
        "Vida Máxima"
       ],
       "classes": [
        "Tank",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "Dano do tipo \"proc\", marcado como dano básico — não aciona efeitos de feitiço.",
        "Os acúmulos numa torre NÃO expiram sozinhos — ficam indefinidamente até serem consumidos.",
        "Dá pra acumular em várias torres ao mesmo tempo, contanto que a runa não esteja em recarga. Mas ao ativar numa torre, os acúmulos pendentes nas OUTRAS torres são perdidos."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Demolish/Demolish.png",
       "riotId": 8446
      },
      {
       "id": "fonte-da-vida",
       "nome": "Fonte da Vida",
       "descricao": "Debilitar o movimento de um Campeão Inimigo restaura Vida para o usuário e para o Campeão aliado próximo com a Vida mais baixa. 70% de eficácia para usuários de ataque à distância. Tempo de Recarga: 20s.",
       "atributos": [
        "Cura"
       ],
       "classes": [
        "Suporte",
        "Tank"
       ],
       "adaptativa": "",
       "notas": [
        "Não concede assistência (assist) pela cura.",
        "Ativa mesmo com o usuário ou alvo já em 100% de vida (o dano/cura listado no total pode não refletir cura real aplicada).",
        "O texto oficial da Riot não traz o valor da cura; pelo dado do jogo e pela wiki, 10 – 50 (corpo a corpo) e 7 – 35 (à distância), do nível 1 ao 18."
       ],
       "cg": {
        "categoria": "\"debilitar o movimento\" (Imobiliza + Lentidão + Ancoragem + Sonolência)",
        "inclui": [
         "Aéreo",
         "Berserk",
         "Encantamento",
         "Fuga Forçada",
         "Provocação",
         "Enraizamento",
         "Sono",
         "Estase",
         "Atordoamento",
         "Supressão",
         "Lentidão",
         "Ancoragem",
         "Sonolência"
        ],
        "naoInclui": "",
        "obs": ""
       },
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/FontOfLife/FontOfLife.png",
       "riotId": 8463
      },
      {
       "id": "golpe-de-escudo",
       "nome": "Golpe de Escudo",
       "descricao": "Sempre que receber um novo escudo, seu próximo ataque básico contra um Campeão causará 5-30 (+2.5% de Vida adicional) (+15.0% da quantidade do novo escudo) de Dano Adaptativo adicional. Você tem até 2s após o escudo acabar para usar este efeito.",
       "atributos": [
        "Vida Máxima",
        "Escudo"
       ],
       "classes": [
        "Tank",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "Dano do tipo \"proc\" — não aciona efeitos de feitiço.",
        "A escala é calculada pelo maior valor de escudo ativo OU que expirou nos últimos 2 segundos.",
        "Ganhar um escudo novo maior substitui o bônus anterior; só ativa uma vez por escudo ganho; funciona com escudo mágico ou físico."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/MirrorShell/MirrorShell.png",
       "riotId": 8401
      }
     ]
    },
    {
     "nome": "Slot 2",
     "tipo": "slot",
     "runas": [
      {
       "id": "condicionamento",
       "nome": "Condicionamento",
       "descricao": "Depois de 12min, recebe +8 de Armadura, +8 de Resistência Mágica e aumenta sua Armadura e Resistência Mágica em 3%.",
       "atributos": [
        "Armadura",
        "Resistência Mágica"
       ],
       "classes": [
        "Tank",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "O aumento de 3% na armadura e resistência mágica BASE não conta como armadura/RM \"bônus\" pra efeitos que escalam especificamente com resistência bônus."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Conditioning/Conditioning.png",
       "riotId": 8429
      },
      {
       "id": "ventos-revigorantes",
       "nome": "Ventos Revigorantes",
       "descricao": "Após sofrer dano de um Campeão inimigo, cura em 4% da sua Vida perdida ao longo de 10s.",
       "atributos": [
        "Cura"
       ],
       "classes": [
        "Tank",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "Não ativa com dano reduzido a 0, dano em escudos, ou dano absorvido por invulnerabilidade."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/SecondWind/SecondWind.png",
       "riotId": 8444
      },
      {
       "id": "osso-revestido",
       "nome": "Osso Revestido",
       "descricao": "Após sofrer dano de um Campeão inimigo, os próximos 3 Ataques ou Habilidades que você sofrer desse inimigo causarão 30 - 60 (com base no nível) a menos de dano. Duração: 1.5s. Tempo de Recarga: 55s.",
       "atributos": [],
       "classes": [
        "Tank"
       ],
       "adaptativa": "",
       "notas": [
        "O próprio golpe que ativa a runa não tem seu dano reduzido por ela.",
        "Só bloqueia dano de UM campeão por vez (quem ativou), e não ativa contra dano em escudos.",
        "A redução se aplica DEPOIS das resistências (no dano já mitigado).",
        "Não ativa com dano reduzido a 0, dano em escudos, ou dano absorvido por invulnerabilidade."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/BonePlating/BonePlating.png",
       "riotId": 8473
      }
     ]
    },
    {
     "nome": "Slot 3",
     "tipo": "slot",
     "runas": [
      {
       "id": "crescimento-excessivo",
       "nome": "Crescimento Excessivo",
       "descricao": "Absorve essência vital de monstros ou tropas inimigas que morrem perto de você, ganhando permanentemente 3 de Vida máxima a cada 8. Após absorver 120 monstros ou tropas inimigas, concede mais 3.5% de Vida máxima.",
       "atributos": [
        "Vida Máxima"
       ],
       "classes": [
        "Tank",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "Só conta mortes de unidades que o campeão tem visão DIRETA — terreno ou efeitos de visão reduzida diminuem o raio de detecção. Visão compartilhada de aliados não conta.",
        "Continua acumulando mesmo estando morto."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Overgrowth/Overgrowth.png",
       "riotId": 8451
      },
      {
       "id": "revitalizar",
       "nome": "Revitalizar",
       "descricao": "Recebe 5% de Cura e Resistência do Escudo. Curas e Escudos conjurados ou recebidos são 10% mais fortes em alvos com menos de 40% de Vida.",
       "atributos": [
        "Cura",
        "Escudo"
       ],
       "classes": [
        "Suporte",
        "Tank"
       ],
       "adaptativa": "",
       "notas": [
        "Combina os efeitos de dois talentos antigos removidos (Armadura Rúnica e Bênção da Voz do Vento) — inclusive o fato de ambos os efeitos empilharem multiplicativamente entre si."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Revitalize/Revitalize.png",
       "riotId": 8453
      },
      {
       "id": "inabalavel",
       "nome": "Inabalável",
       "descricao": "Recebe 10 de Armadura e Resistência Mágica ao sofrer Controle de Grupo e pelos 2s subsequentes.",
       "atributos": [
        "Armadura",
        "Resistência Mágica"
       ],
       "classes": [
        "Tank",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "Ativa com todas as formas de Controle de Grupo, EXCETO Kinemáticos e Interrupção (Disruption).",
        "Pra efeitos que causam dano e CG ao mesmo tempo, a runa só ativa depois de já ter recebido o dano — não ajuda a mitigar esse dano específico."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Unflinching/Unflinching.png",
       "riotId": 8242
      }
     ]
    }
   ],
   "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7204_Resolve.png",
   "riotId": 8400,
   "cor": "#78a860"
  },
  {
   "id": "inspiracao",
   "nome": "Inspiração",
   "lema": "Iludir os meros mortais",
   "slots": [
    {
     "nome": "Keystone",
     "tipo": "keystone",
     "runas": [
      {
       "id": "aprimoramento-glacial",
       "nome": "Aprimoramento Glacial",
       "descricao": "Imobilizar um Campeão inimigo fará com que 3 raios glaciais emanem dele em direção a você e a outros Campeões próximos, criando por 3s (+ a duração do efeito imobilizador) zonas congeladas que causam 20% (+90% a cada 100% de cura e Resistência do Escudo) (+6% a cada 100 de Poder de Habilidade) (+7% a cada 100 de Dano de Ataque adicional) de Lentidão a inimigos e reduzem o dano deles em 15% contra seus aliados (exceto você). Tempo de Recarga: 25s.",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade",
        "Cura",
        "Escudo"
       ],
       "classes": [
        "Tank",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [],
       "cg": {
        "categoria": "gatilho da substituição automática — \"efeito de imobilização\" (categoria pura)",
        "inclui": [
         "Aéreo",
         "Berserk",
         "Encantamento",
         "Fuga Forçada",
         "Provocação",
         "Enraizamento",
         "Sono",
         "Estase",
         "Atordoamento",
         "Supressão"
        ],
        "naoInclui": "",
        "obs": "Yorick é tratado como exceção e conta como se não tivesse imobilização, mesmo tendo uma no W (Procissão Sombria) (vale também para o Pós-choque)."
       },
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/GlacialAugment/GlacialAugment.png",
       "riotId": 8351
      },
      {
       "id": "livro-de-feiticos-deslacrado",
       "nome": "Livro de Feitiços Deslacrado",
       "descricao": "Troque um dos seus Feitiços de Invocador equipados por um novo de uso único. Cada troca de Feitiço de Invocador reduz permanentemente seu Tempo de Recarga em 25s (Tempo de Recarga inicial de 270s). Sua primeira troca fica disponível aos 6min. Feitiços de Invocador só podem ser trocados fora de combate. Depois de usar um Feitiço de Invocador que já foi trocado, você precisa trocar mais 3 vezes antes que ele possa ser selecionado novamente. O dano de Golpear aumenta após duas trocas de Feitiço de Invocador.",
       "atributos": [],
       "classes": [
        "Mago",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [
        "O tempo de recarga da troca é fixo — não é reduzido por Aceleração de Feitiço de Invocador.",
        "Não existe prazo pros feitiços trocados — eles ficam disponíveis indefinidamente até serem usados.",
        "Selecionar o Golpear numa troca não concede acesso aos itens exclusivos de selva; trocar o Golpear por outro feitiço também não bloqueia o acesso a esses itens."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/UnsealedSpellbook/UnsealedSpellbook.png",
       "riotId": 8360
      },
      {
       "id": "primeiro-ataque",
       "nome": "Primeiro Ataque",
       "descricao": "Ataques ou Habilidades contra um Campeão inimigo em até 0.25s depois de entrar em combate contra um Campeão concedem 10 de ouro e Primeiro Ataque por 3s. Durante esse período, você causa 7% de dano adicional a Campeões e recebe 50% (35% para Campeões de ataque à distância) do dano adicional causado como ouro. Tempo de Recarga: 25s - 15s.",
       "atributos": [
        "Ouro"
       ],
       "classes": [
        "Mago",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [
        "Dano do tipo \"proc\", marcado como indireto — não aciona efeitos de feitiço, e não herda a marcação de dano da fonte original (diferente de modificadores de dano comuns).",
        "\"Iniciar combate\" inclui efeitos que causam 0 de dano.",
        "O bônus de dano funciona em qualquer tipo de dano, incluindo Dano Verdadeiro.",
        "Ao contrário do Golpe Desleal, o próprio golpe que inicia o combate TAMBÉM recebe o bônus de dano.",
        "Dispara um projétil pra cada instância de dano causada por instância de conjuração enquanto ativo — esse projétil leva 0.4s fixos pra chegar."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/FirstStrike/FirstStrike.png",
       "riotId": 8369
      }
     ]
    },
    {
     "nome": "Slot 1",
     "tipo": "slot",
     "runas": [
      {
       "id": "flashtracao-hextec",
       "nome": "Flashtração Hextec",
       "descricao": "Enquanto o Flash estiver em Tempo de Recarga, ele é substituído pelo Flash Hextec. Flash Hextec: Canalize por 2s para se teletransportar para um novo local. Tempo de Recarga: 20s. Entra em Tempo de Recarga por 10s quando você entra em combate contra um Campeão.",
       "atributos": [],
       "classes": [
        "Assassino",
        "Mago"
       ],
       "adaptativa": "",
       "notas": [
        "O Flash Hextec fica desabilitado enquanto o usuário estiver ancorado, enraizado ou impedido de conjurar.",
        "Se o Flash sair da recarga enquanto o Flash Hextec está sendo canalizado, ainda dá pra completar a conjuração (perdendo o Flash Hextec), e ela ainda entra em recarga.",
        "Não considera o arremesso do Pinstouro (planta da selva) como \"entrar em combate\"."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/HextechFlashtraption/HextechFlashtraption.png",
       "riotId": 8306
      },
      {
       "id": "calcados-magicos",
       "nome": "Calçados Mágicos",
       "descricao": "Recebe Botas Levemente Mágicas gratuitamente aos 12 min, mas não é possível comprar botas antes disso. Cada eliminação acelera o recebimento das botas em 45s. O item Botas Levemente Mágicas concede a você 10 de Velocidade de Movimento adicional.",
       "atributos": [
        "Velocidade de Movimento"
       ],
       "classes": [
        "Suporte",
        "Mago"
       ],
       "adaptativa": "",
       "notas": [
        "Se as botas forem vendidas, dá pra recomprar normalmente na loja."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/MagicalFootwear/MagicalFootwear.png",
       "riotId": 8304
      },
      {
       "id": "reembolso",
       "nome": "Reembolso",
       "descricao": "Recebe 7.5% do ouro de volta ao comprar itens Lendários.",
       "atributos": [
        "Ouro"
       ],
       "classes": [
        "Atirador",
        "Lutador"
       ],
       "adaptativa": "",
       "notas": [
        "Itens do Guardião (Lâmina, Martelo, Berrante e Orbe do Guardião) não contam como itens Lendários pra esse reembolso."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/CashBack/CashBack2.png",
       "riotId": 8321
      }
     ]
    },
    {
     "nome": "Slot 2",
     "tipo": "slot",
     "runas": [
      {
       "id": "tonico-triplo",
       "nome": "Tônico Triplo",
       "descricao": "Concede Elixires gratuitos conforme você sobe de nível: - Nível 3: Elixir da Avareza — +5 de Dano Verdadeiro ao atingir tropas por 60s; ao expirar, concede 60 de ouro - Nível 6: Elixir da Força — +15 de Dano de Ataque (AD) adaptável ou 25 de Poder de Habilidade (AP) adaptável por 60s - Nível 9: Elixir da Habilidade — concede 1 ponto de habilidade adicional",
       "atributos": [
        "Dano de Ataque",
        "Poder de Habilidade",
        "Ouro"
       ],
       "classes": [
        "Mago",
        "Atirador"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/PerfectTiming/AlchemistCabinet.png",
       "riotId": 8313
      },
      {
       "id": "tonico-de-distorcao-no-tempo",
       "nome": "Tônico de Distorção no Tempo",
       "descricao": "Consumir uma poção concede 40% da restauração de Vida do item imediatamente.",
       "atributos": [
        "Cura"
       ],
       "classes": [
        "Lutador",
        "Mago"
       ],
       "adaptativa": "",
       "notas": [
        "A cura imediata é um adicional: a poção continua curando o total normal ao longo da duração. Só vale para poções (Poção de Vida: 48; Poção com Refil: 40) — biscoito não conta.",
        "Se consumíveis estiverem empilhados, a restauração instantânea do próximo só se aplica depois que a duração do atual terminar."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/TimeWarpTonic/TimeWarpTonic.png",
       "riotId": 8352
      },
      {
       "id": "entrega-de-biscoitos",
       "nome": "Entrega de Biscoitos",
       "descricao": "Recebe um Biscoito total da determinação eterna a cada 2min, até o minuto 6. Biscoitos restauram 20 + 2% da sua Vida máxima. A cura aumenta em até 100% com base na Vida perdida. Consumir ou vender um Biscoito aumenta permanentemente sua Vida máxima em 30.",
       "atributos": [
        "Vida Máxima",
        "Cura"
       ],
       "classes": [
        "Mago",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [
        "A vida concedida conta como Vida bônus (importa pra efeitos que escalam com vida bônus).",
        "Desfazer a venda de um biscoito remove essa vida bônus de novo.",
        "Não aumenta a vida ATUAL, só a máxima."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/BiscuitDelivery/BiscuitDelivery.png",
       "riotId": 8345
      }
     ]
    },
    {
     "nome": "Slot 3",
     "tipo": "slot",
     "runas": [
      {
       "id": "perspicacia-cosmica",
       "nome": "Perspicácia Cósmica",
       "descricao": "+18 de Aceleração de Feitiço de Invocador. +10 de Aceleração de Item.",
       "atributos": [
        "Aceleração de Feitiço de Invocador",
        "Aceleração de Item"
       ],
       "classes": [
        "Tank",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/CosmicInsight/CosmicInsight.png",
       "riotId": 8347
      },
      {
       "id": "velocidade-de-aproximacao",
       "nome": "Velocidade de Aproximação",
       "descricao": "Recebe 7.5% de Velocidade de Movimento em direção a Campeões inimigos próximos que estiverem com movimento debilitado. Esse bônus aumenta para 15% de Velocidade de Movimento em direção a Campeões inimigos cujo movimento você debilitou. Alcance de ativação do CG de aliados: 1000.",
       "atributos": [
        "Velocidade de Movimento"
       ],
       "classes": [
        "Tank",
        "Suporte"
       ],
       "adaptativa": "",
       "notas": [
        "Alvos válidos precisam estar dentro de um ângulo de 180° na direção em que o usuário está virado.",
        "O bônus de velocidade é concedido mesmo que o usuário esteja parado."
       ],
       "cg": {
        "categoria": "\"imobilizado, ancorado ou lento\"",
        "inclui": [
         "Aéreo",
         "Berserk",
         "Encantamento",
         "Fuga Forçada",
         "Provocação",
         "Enraizamento",
         "Sono",
         "Estase",
         "Atordoamento",
         "Supressão",
         "Ancoragem",
         "Lentidão",
         "Sonolência"
        ],
        "naoInclui": "",
        "obs": ""
       },
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/ApproachVelocity/ApproachVelocity.png",
       "riotId": 8410
      },
      {
       "id": "quebra-galho",
       "nome": "Quebra-galho",
       "descricao": "A cada atributo diferente recebido de itens, recebe um acúmulo de Quebra-galho. Cada acúmulo concede 1 Aceleração de Habilidade. Recebe 8 ou 20 de Força Adaptativa adicional com 5 e 10 acúmulos, respectivamente.",
       "atributos": [
        "Aceleração de Habilidade",
        "Dano de Ataque",
        "Poder de Habilidade"
       ],
       "classes": [
        "Mago",
        "Tank",
        "Suporte"
       ],
       "adaptativa": "com 5 acúmulos: 4.8 de Dano de Ataque ou 8 de Poder de Habilidade — com 10 acúmulos: 12.0 de Dano de Ataque ou 20 de Poder de Habilidade. Nunca as duas coisas juntas.",
       "notas": [
        "Nem todo efeito que concede um atributo conta como \"diferente\" pra gerar acúmulo — efeitos de itens como o Sinal de Sterak ou a Flechatroz de Yun Tal contam; já efeitos como a Fome da Fome Eterna NÃO contam.",
        "Atributos elegíveis incluem: Dano de Ataque, Alcance de Ataque, Velocidade de Ataque, Aceleração de Habilidade, Poder de Habilidade, Armadura, Penetração de Armadura percentual, Chance de Crítico, Dano Crítico, Geração de Ouro, Poder de Cura/Escudo, Vida, Regeneração de Vida base, Roubo de Vida, Letalidade, Penetração Mágica fixa e percentual, Resistência Mágica, Mana e Regeneração de Mana base (lista não exaustiva)."
       ],
       "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/JackOfAllTrades/JackofAllTrades2.png",
       "riotId": 8316
      }
     ]
    }
   ],
   "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7203_Whimsy.png",
   "riotId": 8300,
   "cor": "#30a8a8"
  }
 ],
 "fragmentos": [
  {
   "nome": "Slot 1",
   "runas": [
    {
     "id": "forca-adaptativa",
     "nome": "Força Adaptativa",
     "descricao": "+9 de Força Adaptativa.",
     "atributos": [
      "Dano de Ataque",
      "Poder de Habilidade"
     ],
     "classes": [
      "Tank",
      "Lutador",
      "Assassino",
      "Mago",
      "Atirador",
      "Suporte"
     ],
     "adaptativa": "5.4 de Dano de Ataque ou 9 de Poder de Habilidade — nunca as duas coisas juntas.",
     "notas": [],
     "riotId": 5008,
     "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsAdaptiveForceIcon.png"
    },
    {
     "id": "velocidade-de-ataque",
     "nome": "Velocidade de Ataque",
     "descricao": "+10% de Velocidade de Ataque.",
     "atributos": [
      "Velocidade de Ataque"
     ],
     "classes": [
      "Atirador"
     ],
     "adaptativa": "",
     "notas": [],
     "riotId": 5005,
     "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsAttackSpeedIcon.png"
    },
    {
     "id": "aceleracao-de-habilidade",
     "nome": "Aceleração de Habilidade",
     "descricao": "+8 de Aceleração de Habilidade.",
     "atributos": [
      "Aceleração de Habilidade"
     ],
     "classes": [
      "Mago",
      "Lutador"
     ],
     "adaptativa": "",
     "notas": [],
     "riotId": 5007,
     "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsCDRScalingIcon.png"
    }
   ]
  },
  {
   "nome": "Slot 2",
   "runas": [
    {
     "id": "forca-adaptativa",
     "nome": "Força Adaptativa",
     "descricao": "+9 de Força Adaptativa.",
     "atributos": [
      "Dano de Ataque",
      "Poder de Habilidade"
     ],
     "classes": [
      "Tank",
      "Lutador",
      "Assassino",
      "Mago",
      "Atirador",
      "Suporte"
     ],
     "adaptativa": "5.4 de Dano de Ataque ou 9 de Poder de Habilidade — nunca as duas coisas juntas.",
     "notas": [],
     "riotId": 5008,
     "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsAdaptiveForceIcon.png"
    },
    {
     "id": "velocidade-de-movimento",
     "nome": "Velocidade de Movimento",
     "descricao": "+2,5% de Velocidade de Movimento.",
     "atributos": [
      "Velocidade de Movimento"
     ],
     "classes": [
      "Assassino",
      "Suporte",
      "Mago"
     ],
     "adaptativa": "",
     "notas": [],
     "riotId": 5010,
     "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsMovementSpeedIcon.png"
    },
    {
     "id": "escalamento-de-vida",
     "nome": "Escalamento de Vida",
     "descricao": "+10-180 de Vida (com base no nível).",
     "atributos": [
      "Vida Máxima"
     ],
     "classes": [
      "Tank",
      "Lutador"
     ],
     "adaptativa": "",
     "notas": [],
     "riotId": 5001,
     "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsHealthPlusIcon.png"
    }
   ]
  },
  {
   "nome": "Slot 3",
   "runas": [
    {
     "id": "vida",
     "nome": "Vida",
     "descricao": "+65 de Vida.",
     "atributos": [
      "Vida Máxima"
     ],
     "classes": [
      "Tank",
      "Lutador",
      "Suporte"
     ],
     "adaptativa": "",
     "notas": [],
     "riotId": 5011,
     "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsHealthScalingIcon.png"
    },
    {
     "id": "tenacidade-e-resistencia-a-lentidao",
     "nome": "Tenacidade e Resistência a Lentidão",
     "descricao": "+15% de Tenacidade e Resistência a Lentidão.",
     "atributos": [
      "Tenacidade",
      "Resistência a Lentidão"
     ],
     "classes": [
      "Tank",
      "Lutador",
      "Atirador"
     ],
     "adaptativa": "",
     "notas": [],
     "riotId": 5013,
     "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsTenacityIcon.png"
    },
    {
     "id": "escalamento-de-vida",
     "nome": "Escalamento de Vida",
     "descricao": "+10-180 de Vida (com base no nível).",
     "atributos": [
      "Vida Máxima"
     ],
     "classes": [
      "Tank",
      "Lutador"
     ],
     "adaptativa": "",
     "notas": [],
     "riotId": 5001,
     "iconUrl": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsHealthPlusIcon.png"
    }
   ]
  }
 ],
 "substituicoes": [
  {
   "de": "Caminhar Sobre as Águas",
   "para": "Chamuscar",
   "quando": "em modos sem rio"
  },
  {
   "de": "Caminhar Sobre as Águas",
   "para": "Tempestade Crescente",
   "quando": "em A Lenda do Rei Poro"
  },
  {
   "de": "Demolir",
   "para": "Fonte da Vida",
   "quando": "em modos sem estruturas ou com estruturas que não podem ser alvo"
  },
  {
   "de": "Demolir",
   "para": "Fonte da Vida",
   "quando": "na Lua Sangrenta"
  },
  {
   "de": "Sentinela Profunda",
   "para": "Lembranças Aterrorizantes",
   "quando": "em modos sem sentinelas"
  },
  {
   "de": "Sentinela Profunda",
   "para": "Lembranças Aterrorizantes",
   "quando": "no Fiddlesticks"
  },
  {
   "de": "Sexto Sentido",
   "para": "Lembranças Aterrorizantes",
   "quando": "em modos sem sentinelas"
  },
  {
   "de": "Faixa de Fluxo de Mana",
   "para": "Arcanista do Axioma",
   "quando": "em campeões sem mana, no URF e no URFeA na Neve"
  },
  {
   "de": "Faixa de Fluxo de Mana",
   "para": "Manto de Nimbus",
   "quando": "na Ambessa"
  },
  {
   "de": "Presença de Espírito",
   "para": "Triunfo",
   "quando": "em campeões sem mana nem energia, no URF e no URFeA na Neve"
  },
  {
   "de": "Pós-choque",
   "para": "Aperto dos Mortos-Vivos",
   "quando": "em campeões sem efeito de imobilização e no Yorick"
  },
  {
   "de": "Pós-choque",
   "para": "Guardião",
   "quando": "na Yuumi"
  },
  {
   "de": "Aprimoramento Glacial",
   "para": "Primeiro Ataque",
   "quando": "em campeões sem efeito de imobilização e no Yorick"
  },
  {
   "de": "Flashtração Hextec",
   "para": "Reembolso",
   "quando": "em campeões que não equipam Flash"
  },
  {
   "de": "Caça Suprema",
   "para": "Caça Incansável",
   "quando": "em Bel'Veth"
  },
  {
   "de": "Caça Suprema",
   "para": "Caçador de Tesouros",
   "quando": "em Samira"
  },
  {
   "de": "Arcanista do Axioma",
   "para": "Manto de Nimbus",
   "quando": "em Elise, Jayce, Nidalee e Zoe"
  },
  {
   "de": "Livro de Feitiços Deslacrado",
   "para": "Primeiro Ataque",
   "quando": "no URF e no Livro Supremo de Ultimates"
  },
  {
   "de": "Livro de Feitiços Deslacrado",
   "para": "Aprimoramento Glacial",
   "quando": "na Lua Sangrenta e em A Lenda do Rei Poro"
  },
  {
   "de": "Entrega de Biscoitos",
   "para": "Tônico de Distorção no Tempo",
   "quando": "no ARAM e no Confronto"
  },
  {
   "de": "Tônico Triplo",
   "para": "Tônico de Distorção no Tempo",
   "quando": "no Confronto"
  },
  {
   "de": "Perspicácia Cósmica",
   "para": "Velocidade de Aproximação",
   "quando": "no URFeA na Neve"
  },
  {
   "de": "Manto de Nimbus",
   "para": "Arcanista do Axioma",
   "quando": "no URFeA na Neve"
  },
  {
   "de": "Fonte da Vida",
   "para": "Demolir",
   "quando": "no Corki"
  }
 ]
};
