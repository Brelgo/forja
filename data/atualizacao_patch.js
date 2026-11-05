// Gerado por data/robo/aplicar_patch.py (o robô de patch, F13-T74). Não editar à mão:
// o que mudou na fonte de 16.21.1 para 16.22.1 e passou na regra de segurança (docs/robo_de_patch.md).
window.ATUALIZACAO_PATCH = {
 "de": "16.21.1",
 "para": "16.22.1",
 "gerado": "2026-11-05T20:41:35Z",
 "catalogo": {
  "patch": "16.21.1",
  "sha256": "931b0eefc328e4f93b4e6bc4ed26f36b2f37a593dedb2bac752544a97cd3da32"
 },
 "fonte": {
  "wiki": {
   "de": 4088750,
   "para": 4092074
  },
  "ddragon": {
   "de": "16.21.1",
   "para": "16.22.1"
  }
 },
 "itens": {
  "doran-s-bow": {
   "campos": {
    "attributes": [
     {
      "raw": "+7 de Dano de Ataque",
      "value": 7,
      "unit": "flat",
      "stat": "Dano de Ataque",
      "scaling": null
     },
     {
      "raw": "+15% de Velocidade de Ataque",
      "value": 15,
      "unit": "percent",
      "stat": "Velocidade de Ataque",
      "scaling": null
     },
     {
      "raw": "+1,5% de Vampirismo Universal",
      "value": 1.5,
      "unit": "percent",
      "stat": "Vampirismo Universal",
      "scaling": null
     }
    ]
   },
   "mudou": [
    {
     "campo": "Dano de Ataque",
     "de": 8,
     "para": 7,
     "fonte": "wiki"
    }
   ],
   "contaVelha": [
    "costAnalysis",
    "itemClass"
   ],
   "base": {
    "attributes": [
     {
      "raw": "+8 de Dano de Ataque",
      "value": 8,
      "unit": "flat",
      "stat": "Dano de Ataque",
      "scaling": null
     },
     {
      "raw": "+15% de Velocidade de Ataque",
      "value": 15,
      "unit": "percent",
      "stat": "Velocidade de Ataque",
      "scaling": null
     },
     {
      "raw": "+1,5% de Vampirismo Universal",
      "value": 1.5,
      "unit": "percent",
      "stat": "Vampirismo Universal",
      "scaling": null
     }
    ]
   }
  },
  "overlord-s-bloodmail": {
   "campos": {
    "attributes": [
     {
      "raw": "+40 de Dano de Ataque",
      "value": 40,
      "unit": "flat",
      "stat": "Dano de Ataque",
      "scaling": null
     },
     {
      "raw": "+550 de Vida",
      "value": 550,
      "unit": "flat",
      "stat": "Vida",
      "scaling": null
     }
    ]
   },
   "mudou": [
    {
     "campo": "Dano de Ataque",
     "de": 30,
     "para": 40,
     "fonte": "wiki"
    }
   ],
   "contaVelha": [
    "costAnalysis",
    "itemClass",
    "masterwork",
    "abilities",
    "apexNumeric"
   ],
   "base": {
    "attributes": [
     {
      "raw": "+30 de Dano de Ataque",
      "value": 30,
      "unit": "flat",
      "stat": "Dano de Ataque",
      "scaling": null
     },
     {
      "raw": "+550 de Vida",
      "value": 550,
      "unit": "flat",
      "stat": "Vida",
      "scaling": null
     }
    ]
   }
  }
 },
 "aConferir": [
  {
   "slug": "bloodletter-s-curse",
   "item": "Maldição Sanguinária",
   "campo": "efeito Vile Decay",
   "porque": "mudou na wiki: o texto",
   "antes": "Dealing {{as|magic damage}} to an enemy champion with a [[champion ability]] applies a stack of ''Vile Decay'' to them for 6 seconds, stacking up to 4 times and up to once per basic attack or ability per {{tip|cast instance}} every {{fd|0.3}} seconds. Each stack inflicts {{as|{{fd|7.5}}% magic resistance reduction}}, up to {{as|30%|mr}} at 4 stacks.",
   "depois": "Dealing {{as|magic damage}} to an enemy champion with a [[champion ability]] applies a stack of ''Vile Decay'' to them for 6 seconds, stacking up to 4 times. Each stack inflicts {{as|{{fd|7.5}}% magic resistance reduction}}, up to {{as|30%|mr}} at 4 stacks."
  },
  {
   "slug": "overlord-s-bloodmail",
   "item": "Armadura Sangrenta do Suserano",
   "campo": "efeito Retribution",
   "porque": "mudou na wiki: o texto",
   "antes": "Gain {{as|'''bonus''' attack damage}} equal to {{pp|0 to 12 by 1|0 to 70|key=%|key1=%|type='''missing''' health|color=health}} of your {{as|'''total''' attack damage}} from other sources.",
   "depois": "Gain {{as|'''bonus''' attack damage}} equal to {{pp|0 to 10 by 1|0 to 70|key=%|key1=%|type='''missing''' health|color=health}} of your {{as|'''total''' attack damage}} from other sources."
  }
 ],
 "novos": []
};
