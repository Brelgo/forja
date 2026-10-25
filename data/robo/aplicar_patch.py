"""O robô de patch, parte 2 (F13-T74): a regra de segurança.

Compara a foto da fonte do patch do catálogo (a "antiga") com a do patch novo e
decide, campo a campo, item a item:

  - APLICA quando a fonte que o catálogo seguia mudou e o catálogo estava igual
    a ela — prova de que o catálogo seguia a fonte; o valor novo vai para a camada;
  - NADA quando a fonte que o catálogo segue não mudou (a outra pode ter mudado:
    o Atma segue o Data Dragon, e a wiki mudar não mexe nele);
  - A CONFERIR no resto: o catálogo não seguia a fonte, as fontes que ele seguia
    divergem agora, o texto de um efeito mudou, o grupo mudou, o item saiu.

O catálogo (data/Catalogo_Itens_LoL.md, do Capítulo 1) nunca é tocado: o que o
robô aplica vai para data/atualizacao_patch.js, que o app soma por cima do
catalog.js (parte 3). Conta que depende de regra do Capítulo 1 (análise de custo,
eficiência, soma por núcleo, Passiva do Ornn) não é refeita: fica marcada como
"conta do patch anterior". Só se refaz o que tem fórmula no próprio dado — o
custo de combinação (preço − componentes) e o Reembolso (a porcentagem do campo).

Uso:  python data/robo/aplicar_patch.py                # do patch do catálogo à foto mais nova
      python data/robo/aplicar_patch.py --para 16.22.1
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)
from ler_fonte import ATRIBUTOS, BAIXADO, EFEITOS_COM_NOME, ler_catalogo, ler_foto, modos_da_fonte, num, resolver, revisao_do_capitulo1  # noqa: E402

CAMADA = os.path.join(RAIZ, "data", "atualizacao_patch.js")
CATALOGO_JS = os.path.join(RAIZ, "data", "catalog.js")
AUSENTE = "(sem o atributo)"
# 4ª rodada: o mesmo atributo em duas unidades tem nomes diferentes na tela ("Letalidade" é
# a penetração de armadura plana; "Regeneração de Vida (a cada 5s)", a regeneração plana) —
# a troca de unidade se vê pela família da chave da wiki, não pelo nome
FAMILIA = {"msflat": "ms", "mpenflat": "mpen", "hp5flat": "hp5", "lethality": "armpen"}
CHAVES_DE_MODO = ("classic sr 5v5", "aram", "mayhem")      # as que modos_da_fonte lê
# campos da wiki que o Capítulo 1 usa e o robô não refaz (4ª rodada): mudou, a conferir
OUTROS_DA_WIKI = {"type": "o tier", "tier": "o tier", "req": "a condição", "sell": "o valor de venda", "sellratio": "o valor de venda"}


def numero(v):
    """Número de verdade: o `true` do Lua vira True, e True é int em Python (4ª rodada)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def rotulo(k):
    return "%s (%s)" % ATRIBUTOS[k] if ATRIBUTOS[k][1] == "percent" else ATRIBUTOS[k][0]


def modos_dd(d):
    mapas = (d or {}).get("maps") or {}
    return sorted((["Summoner's Rift"] if mapas.get("11") else []) + (["ARAM", "ARAM: Mayhem"] if mapas.get("12") else []))


# ---------------------------------------------------------------- o que cada lado diz
def da_fonte(f, d, nome_por_id):
    """O que a fonte diz de um item, no formato do catálogo. f: wiki (resolvida); d: Data Dragon."""
    f = f or {}
    gold = (d or {}).get("gold") or {}
    efeitos = {k: e for k, e in (f.get("effects") or {}).items()}
    return {
        "preco_wiki": num(f.get("buy")) if numero(f.get("buy")) else None,
        "preco_dd": gold.get("total") if gold.get("purchasable") else None,
        "receita_wiki": sorted(x for x in (f.get("recipe") or []) if isinstance(x, str)),
        "receita_dd": sorted(nome_por_id.get(x, "?" + x) for x in ((d or {}).get("from") or [])) if d else None,
        "atributos": {k: num(v) for k, v in (f.get("stats") or {}).items() if k in ATRIBUTOS and numero(v)},
        "spec": (f.get("stats") or {}).get("spec"),        # o atributo em texto livre (a Abatedora)
        "modos": sorted(modos_da_fonte(f.get("modes")) or []) if isinstance(f.get("modes"), dict) else None,
        "chaves_modo": sorted(k for k in f["modes"] if k in CHAVES_DE_MODO) if isinstance(f.get("modes"), dict) else None,
        # 3ª rodada: o catálogo segue também os mapas do Data Dragon (212 de 225 batem)
        "modos_dd": modos_dd(d) if d else None,
        "outros": {k: f.get(k) for k in OUTROS_DA_WIKI},
        "nome": (d or {}).get("name"),
        "efeitos": efeitos,
        "grupo": [f.get("itemlimit"), f.get("itemlimit2"), f.get("limit")],
    }


def do_catalogo(it):
    attrs = {(a.get("stat"), a.get("unit")): num(a.get("value")) for a in (it.get("attributes") or []) if isinstance(a, dict)}
    return {
        "preco": it.get("priceGold"),
        "receita": sorted(c["nameEn"] for c in (it.get("components") or []) for _ in range(int(c.get("qty") or 1))),
        "atributos": {k: attrs.get(par) for k, par in ATRIBUTOS.items()},
        "modos": sorted(it.get("gameModes") or []),
        "nome": it.get("namePt"),
    }


def decidir(cat, fontes):
    """fontes: [(nome, antes, depois)]. Devolve None (nada), ("aplica", valor, de_onde) ou ("confere", porque)."""
    mudaram = [x for x in fontes if x[1] != x[2]]
    if not mudaram:
        return None
    seguidas = [x for x in fontes if x[1] is not None and x[1] == cat]
    if not seguidas:
        return ("confere", "o catálogo não seguia a fonte antiga (%s)" % ", ".join("%s: %s" % (n, json.dumps(a, ensure_ascii=False)) for n, a, _ in fontes))
    mudadas = [x for x in seguidas if x[1] != x[2]]
    if not mudadas:
        return None                       # a fonte que o catálogo segue não mudou
    if len(mudadas) < len(seguidas):
        firmes = ", ".join(n for n, a, b in seguidas if a == b)
        return ("confere", "as fontes que o catálogo seguia divergem agora: %s mudou, %s não" % (", ".join(n for n, _, _ in mudadas), firmes))
    novos = {json.dumps(b, ensure_ascii=False, sort_keys=True) for _, _, b in mudadas}
    if len(novos) > 1:
        return ("confere", "as fontes dizem valores novos diferentes: %s" % "; ".join("%s %s" % (n, json.dumps(b, ensure_ascii=False)) for n, _, b in mudadas))
    # a fonte que "não tem mais" o dado não é um valor novo: o item saiu, a página
    # mudou de forma ou a leitura falhou — nunca se aplica (revisão da T74)
    if mudadas[0][2] is None or mudadas[0][2] == []:
        return ("confere", "a fonte não tem mais o dado (%s)" % " e ".join(n for n, _, _ in mudadas))
    return ("aplica", mudadas[0][2], " e ".join(n for n, _, _ in mudadas))


# ---------------------------------------------------------------- números como o catálogo escreve
def fmt_num(n):
    """3000 → "3.000"; 262.5 → "262,5"; 3237.5 → "3.237,5"."""
    n = round(n, 2)
    inteiro = int(n) if float(n).is_integer() else None
    if inteiro is not None:
        return "{:,}".format(inteiro).replace(",", ".")
    s = "{:,.2f}".format(n).rstrip("0").rstrip(".")
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def raw_atributo(valor, stat, unidade):
    return "+%s%s de %s" % (fmt_num(valor), "%" if unidade == "percent" else "", stat)


# ---------------------------------------------------------------- a regra
def preco_do_capitulo1(it):
    """O preço tem nota do Capítulo 1 ("não comprável", "gratuito", "aprimoramento
    gratuito; valor de venda…"): o número e a nota andam juntos — é do Capítulo 1."""
    return bool((it.get("priceNote") or "").strip())


def salto(antes, depois):
    """Número que triplica ou cai a um terço: no dia de patch a wiki passa por edições
    no meio do caminho (o Capítulo 1 viu "Quebra-Bastião com 1038 de Letalidade" em
    21/10/2026) — vai para a conferir, não se aplica."""
    if not numero(antes) or not numero(depois):
        return False
    if antes == depois:
        return False
    if antes == 0 or depois == 0:
        return True          # 3ª rodada: cair a zero (ou sair dele) é o salto maior — o 0 é o "espaço reservado" típico
    r = depois / antes
    return r >= 3 or r <= 1 / 3


def limites_dos_atributos(catalogo):
    """O menor e o maior valor positivo de cada atributo (nome e unidade) no catálogo: o
    atributo que ENTRA num item não tem "antes" para medir salto — fora da faixa, a conferir."""
    lim = {}
    for it in catalogo["items"]:
        for x in it.get("attributes") or []:
            if isinstance(x, dict) and numero(x.get("value")) and x["value"] > 0:
                k = (x.get("stat"), x.get("unit"))
                piso, teto = lim.get(k, (x["value"], x["value"]))
                lim[k] = (min(piso, x["value"]), max(teto, x["value"]))
    return lim


def fora_da_faixa(valor, chave, limites):
    """Por que o atributo que entra é suspeito ("" = não é). 4ª rodada: o teto só olhava para
    cima — o 0, o negativo e a fração (0,45 no lugar de 45%) entravam sozinhos."""
    piso, teto = limites.get(ATRIBUTOS[chave], (None, None))
    if valor <= 0:
        return "atributo que entra com %s" % fmt_num(valor)
    if teto is None:
        return "atributo que entra com %s, e nenhum item do catálogo tem este" % fmt_num(valor)
    if valor > teto:
        return "atributo que entra com %s, acima do maior do catálogo (%s)" % (fmt_num(valor), fmt_num(teto))
    if valor < piso:
        return "atributo que entra com %s, abaixo do menor do catálogo (%s)" % (fmt_num(valor), fmt_num(piso))
    return ""


def longe_da_faixa(valor, chave, limites):
    """O atributo que MUDA para bem longe da faixa do catálogo ("" = não é). 5ª rodada: o dígito
    a mais na frente (55 → 155) não chega a triplicar, e a faixa só valia para o que entra. Com
    folga de 50%: o reforço do item que já é o maior (o Sanguinário, 80 → 85) não para."""
    piso, teto = limites.get(ATRIBUTOS[chave], (None, None))
    if teto is None or not numero(valor):
        return ""
    if valor > 1.5 * teto:
        return "o atributo vai a %s, bem acima do maior do catálogo (%s)" % (fmt_num(valor), fmt_num(teto))
    if 0 < valor < piso / 1.5:
        return "o atributo vai a %s, bem abaixo do menor do catálogo (%s)" % (fmt_num(valor), fmt_num(piso))
    return ""


def textos_do_item(it):
    """(campo, texto) de cada texto do Capítulo 1 que pode fazer conta com um número do item."""
    for x in it.get("abilities") or []:
        if isinstance(x, dict):
            yield "abilities", "%s %s" % (x.get("mechanics") or "", x.get("description") or "")
    for k in ("apex", "notes", "aramNotes", "mayhemNotes"):
        if isinstance(it.get(k), str):
            yield k, it[k]


def textos_que_citam(it, velhos=(), do_item=False, ouro=False):
    """Os textos do item que fazem conta com um número que mudou: o atributo ("13,75 só com os
    550 de Vida do item"), o preço ("2.250g ÷ 2.300g"), o custo de combinação, o Reembolso, o
    preço de um componente. 4ª rodada: só o atributo, e só "<n> de". 5ª rodada: qualquer número
    antigo citado sozinho ("55 + 15 + 3N"), o "do próprio item", e — quando o valor em ouro dos
    atributos muda (`ouro`) — toda conta de ouro ("÷", "385g"). Marcar demais é leve."""
    formas = set()
    for v in velhos:
        if numero(v) and v != 0:
            formas.add(fmt_num(v))
            if float(v).is_integer():
                formas.add(str(int(v)))
    padroes = [r"(?<![\d.,])%s(?!\d|[.,]\d)" % re.escape(f) for f in formas]
    if do_item:
        padroes.append(r"\bdo (?:próprio )?item\b")
    if ouro:
        padroes.append(r"÷|\d\s*g\b")
    out = []
    for campo, texto in textos_do_item(it):
        if campo not in out and any(re.search(x, texto) for x in padroes):
            out.append(campo)
    return out


def assentada(meta, conferido=None):
    """A foto do patch novo só se aplica quando o robô VIU a revisão dela com pelo menos 24 h
    de idade E pelo menos 24 h depois da 1ª foto do patch. 3ª rodada: só a idade da revisão
    deixava passar a edição feita antes de o Data Dragon trocar o patch. 4ª rodada: a idade
    contava até agora, não até a leitura — a foto de dia de patch que o leitor não conseguiu
    refazer (texto quebrado, sem rede) envelhecia no disco e passava. "Visto" é a hora da foto
    ou a da última leitura que achou a wiki nesta mesma revisão (fonte/_baixado/conferido.json,
    que o ler_fonte grava a cada leitura boa)."""
    def data(x):
        return datetime.datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    try:
        revisao = data(meta["wiki"]["revisao_de"])
        primeira = data(meta.get("primeira_foto") or meta["lido_em"])
        visto = data(meta["lido_em"])
        c = conferido or {}
        # 5ª rodada: a leitura casa com a foto pelo CONTEÚDO (sha256), não pelo revid — uma
        # revisão nova de texto igual (desfazer, revisão nula de proteção) travava a espera; e a
        # idade conta da revisão que a leitura viu, que é a mais nova
        if c.get("patch") == meta.get("patch") and c.get("sha256") == meta["wiki"]["sha256"]:
            visto = max(visto, data(c["em"]))
            if c.get("revisao_de"):
                revisao = max(revisao, data(c["revisao_de"]))
    except (KeyError, ValueError, TypeError):
        return False
    dia = datetime.timedelta(hours=24)
    return (visto - revisao) >= dia and (visto - primeira) >= dia


def referencias_de_preco(catalogo):
    """Os itens que dão o valor em ouro de cada atributo (meta.statPrices: "Espada Longa
    (350g ÷ 10)"): mudou um deles, a análise de custo e o núcleo de todo item ficam velhos."""
    nomes = {i["namePt"]: i["slug"] for i in catalogo["items"]}
    out = {}
    for s in (catalogo.get("meta") or {}).get("statPrices") or []:
        nome = (s.get("reference") or "").split(" (")[0].strip()
        if nome in nomes:
            out[nomes[nome]] = nome
    return out


def regra(catalogo, antiga, nova):
    """antiga, nova: (wiki como veio, extrato do Data Dragon, meta). Devolve a camada (dict).

    Revisão da T74 (a revisão adversarial achou, e um cético reproduziu): a fonte
    que "não tem mais" o dado nunca é aplicada; o item que sai do Data Dragon ou de
    todos os modos, ou que tem referência "=>" sem destino, vai inteiro para a
    conferir; receita e nome em português são do Capítulo 1 (o texto dele cita os
    dois); o custo de combinação só se refaz com o preço do item resolvido e
    conferido contra o "base" do Data Dragon."""
    w0, dd0, m0 = antiga
    w1, dd1, m1 = nova
    w0r, _ = resolver(w0)
    w1r, faltou1 = resolver(w1)
    sem_destino = {}
    for x in faltou1:
        n, _, resto = x.partition(":")
        sem_destino.setdefault(n.strip(), []).append(resto.strip())
    itens = catalogo["items"]
    nome_por_id = {str(i["id"]).split(" ")[0]: i["nameEn"] for i in itens}
    id_para_nome1 = {str(v.get("id")): k for k, v in w1r.items()}
    camada = {"itens": {}, "aConferir": [], "novos": [], "nada": 0}
    mudancas_de_preco = {}
    preco_em_aberto = set()          # o preço mudou em alguma fonte e não foi aplicado
    inteiros = set()                 # itens mandados inteiros para a conferir: nada deles entra na camada
    limites = limites_dos_atributos(catalogo)

    def confere(it, campo, porque, **extra):
        camada["aConferir"].append(dict({"slug": it["slug"], "item": it["namePt"], "campo": campo, "porque": porque}, **extra))

    def entra(it):
        return camada["itens"].setdefault(it["slug"], {"campos": {}, "mudou": [], "contaVelha": []})

    for it in itens:
        nome = it.get("wikiName") or it.get("nameEn")
        id_c = str(it["id"]).split(" ")[0]
        f0 = w0r.get(nome)
        if f0 is None:
            continue                      # sem par na foto antiga: o leitor já diz no relatório dele
        f1 = w1r.get(nome)
        if f1 is None:
            outro = id_para_nome1.get(str(f0.get("id")))
            confere(it, "item", "o nome em inglês mudou na wiki (agora %r)" % outro if outro else "o item saiu da wiki")
            inteiros.add(it["slug"])
            continue
        # o item inteiro para a conferir: referência sem destino, saiu do Data Dragon, saiu de todos os modos
        if nome in sem_destino:
            confere(it, "item", "referência \"=>\" sem destino na wiki: %s" % "; ".join(sem_destino[nome]))
            inteiros.add(it["slug"])
            continue
        d0, d1 = dd0["data"].get(id_c), dd1["data"].get(id_c)
        if d0 is not None and d1 is None:
            confere(it, "item", "o item saiu do Data Dragon da Summoner's Rift e do ARAM (ou mudou de id)")
            inteiros.add(it["slug"])
            continue
        a, b, c = da_fonte(f0, d0, nome_por_id), da_fonte(f1, d1, nome_por_id), do_catalogo(it)
        if a["modos"] and not b["modos"]:
            confere(it, "item", "a wiki tirou o item de todos os modos")
            inteiros.add(it["slug"])
            continue
        novos_campos, mudou = {}, []
        # Salto num campo: a revisão pode estar no meio de uma edição — o item todo espera.
        # 4ª rodada: o sinal se mede na FONTE (antes → depois), em todo campo e antes de
        # decidir; venha por qualquer porta (o preço que salta numa fonte só, o atributo que
        # o catálogo não seguia, o valor que o robô não lê), ele segura o item inteiro
        suspeito = []

        def suspeita(campo, porque, **extra):
            suspeito.append(campo)
            confere(it, campo, porque + ": a wiki pode estar no meio de uma edição", **extra)

        for fonte, x0, x1 in (("wiki", a["preco_wiki"], b["preco_wiki"]), ("Data Dragon", a["preco_dd"], b["preco_dd"])):
            if salto(x0, x1):
                suspeita("preço", "salto grande no preço (%s: %s → %s)" % (fonte, x0, x1), catalogo=c["preco"])
                break
        if "preço" not in suspeito and f1.get("buy") is not None and f0.get("buy") != f1.get("buy") and not numero(f1.get("buy")):
            suspeita("preço", "a wiki escreve o preço de um jeito que o robô não lê (%r)" % (f1.get("buy"),))
        st0, st1 = f0.get("stats") or {}, f1.get("stats") or {}
        ilegiveis = sorted(k for k, v in st1.items() if k != "spec" and (k not in ATRIBUTOS or not numero(v)) and st0.get(k) != v)
        if ilegiveis:
            suspeita("atributos", "a wiki tem atributo que o robô não lê (%s)" % ", ".join("%s = %r" % (k, st1[k]) for k in ilegiveis))
        fam = lambda k: FAMILIA.get(k, k)
        trocas = ({fam(k) for k in a["atributos"] if k not in b["atributos"]} & {fam(k) for k in b["atributos"] if k not in a["atributos"]})
        for k in sorted(set(a["atributos"]) | set(b["atributos"])):
            v0, v1 = a["atributos"].get(k), b["atributos"].get(k)
            if fam(k) in trocas:
                continue
            if salto(v0, v1):
                suspeita(rotulo(k), "salto grande (%s → %s)" % (fmt_num(v0), fmt_num(v1)), catalogo=c["atributos"].get(k))
            elif v0 is None and v1 is not None and fora_da_faixa(v1, k, limites):
                suspeita(rotulo(k), fora_da_faixa(v1, k, limites), catalogo=c["atributos"].get(k))
            elif v0 is not None and v1 is not None and v0 != v1 and longe_da_faixa(v1, k, limites):
                suspeita(rotulo(k), longe_da_faixa(v1, k, limites), catalogo=c["atributos"].get(k))

        # preço: a wiki e o Data Dragon (o catálogo segue um deles — o Atma, o Data Dragon).
        # O item não comprável tem preço do Capítulo 1 (0 e a nota): nunca se aplica.
        mudou_preco = a["preco_wiki"] != b["preco_wiki"] or a["preco_dd"] != b["preco_dd"] or f0.get("buy") != f1.get("buy")
        if preco_do_capitulo1(it):
            if mudou_preco:
                confere(it, "preço", "o catálogo tem nota no preço (%s): o preço é do Capítulo 1%s" % (
                    it.get("priceNote"), "; o item não se compra" if "não comprável" in (it.get("priceNote") or "") else ""), catalogo=c["preco"])
                preco_em_aberto.add(it["slug"])
        elif "preço" in suspeito:
            preco_em_aberto.add(it["slug"])
        else:
            r = decidir(c["preco"], [("wiki", a["preco_wiki"], b["preco_wiki"]), ("Data Dragon", a["preco_dd"], b["preco_dd"])])
            if r and r[0] == "aplica":
                novos_campos["priceGold"] = r[1]
                mudou.append({"campo": "preço", "de": c["preco"], "para": r[1], "fonte": r[2]})
            elif r:
                confere(it, "preço", r[1], catalogo=c["preco"])
                preco_em_aberto.add(it["slug"])

        # receita: é do Capítulo 1 — ela muda também o "Vira componente de" dos outros itens
        if a["receita_wiki"] != b["receita_wiki"] or a["receita_dd"] != b["receita_dd"]:
            confere(it, "receita", "mudou na fonte (wiki %s → %s; Data Dragon %s → %s) — o Capítulo 1 refaz a receita e o \"Vira componente de\"" % (
                json.dumps(a["receita_wiki"], ensure_ascii=False), json.dumps(b["receita_wiki"], ensure_ascii=False),
                json.dumps(a["receita_dd"], ensure_ascii=False), json.dumps(b["receita_dd"], ensure_ascii=False)), catalogo=c["receita"])

        # atributos, um a um (só os que o robô sabe nomear). Não ter o atributo também é
        # um valor: o que a wiki acrescenta e o catálogo também não tinha, entra. Mas o que
        # o robô não lê (chave nova, valor que não é número) e a tabela que sumiu inteira
        # vão para a conferir — nunca viram "a fonte não tem"
        attrs_mudados = {}
        val = lambda d, k: AUSENTE if d.get(k) is None else d.get(k)
        if st0 and not st1:
            confere(it, "atributos", "a wiki tirou a tabela de atributos do item")
        elif not ilegiveis:
            # 3ª rodada: uma chave que sai e outra do mesmo atributo que entra é troca de unidade
            # (plano ↔ percentual: "msflat = 25" vira "ms = 25") — não é "sai um, entra outro"
            if trocas:
                confere(it, "atributos", "a unidade mudou (plano ↔ percentual) em %s — a conferir" % ", ".join(
                    sorted({ATRIBUTOS[k][0] for k in set(a["atributos"]) | set(b["atributos"]) if fam(k) in trocas})))
            for k in sorted(set(a["atributos"]) | set(b["atributos"])):
                if fam(k) in trocas or rotulo(k) in suspeito:
                    continue
                r = decidir(val(c["atributos"], k), [("wiki", val(a["atributos"], k), val(b["atributos"], k))])
                if r and r[0] == "aplica":
                    attrs_mudados[k] = None if r[1] == AUSENTE else r[1]
                    mudou.append({"campo": rotulo(k), "de": c["atributos"].get(k), "para": attrs_mudados[k], "fonte": r[2]})
                elif r:
                    confere(it, rotulo(k), r[1], catalogo=c["atributos"].get(k))
        # 4ª rodada: o atributo em texto livre da tabela (stats.spec: "+3 [[health]] [[on-hit]]",
        # a Vida ao contato da Abatedora) é do Capítulo 1 — mudou, a conferir
        if a["spec"] != b["spec"]:
            confere(it, "atributos", "o atributo em texto livre da wiki (stats.spec) mudou (%r → %r): é do Capítulo 1" % (a["spec"], b["spec"]))

        # modos (a wiki). Chave de modo que some, entra ou muda de nome não é "saiu do modo":
        # a wiki mudou a forma da tabela (ou um editor errou a linha) — a conferir. 4ª rodada:
        # só as chaves que o robô lê (o Nexus Blitz e a Arena saírem não desliga a conferência),
        # e o Data Dragon conta também quando as chaves mudam
        if a["chaves_modo"] != b["chaves_modo"]:
            if a["modos"] != b["modos"] or a["modos_dd"] != b["modos_dd"]:
                confere(it, "modos", "a wiki mudou as chaves de modo (%s → %s)" % (a["chaves_modo"], b["chaves_modo"]), catalogo=c["modos"])
        else:
            r = decidir(c["modos"], [("wiki", a["modos"], b["modos"]), ("Data Dragon", a["modos_dd"], b["modos_dd"])])
            if r and r[0] == "aplica":
                novos_campos["gameModes"] = r[1]
                mudou.append({"campo": "modos", "de": c["modos"], "para": r[1], "fonte": r[2]})
            elif r:
                confere(it, "modos", r[1], catalogo=c["modos"])
        # o nome em português: o texto do Capítulo 1 o cita ("Limitado a 1 Tiara Sussurrante")
        if a["nome"] != b["nome"]:
            confere(it, "nome", "o Data Dragon trocou o nome (%r → %r) — o texto do Capítulo 1 cita nomes, como no \"Limitado a 1 …\"" % (a["nome"], b["nome"]), catalogo=c["nome"])

        # o que é texto do Capítulo 1: sempre a conferir
        for k in sorted(set(a["efeitos"]) | set(b["efeitos"])):
            e0, e1 = a["efeitos"].get(k), b["efeitos"].get(k)
            if e0 == e1:
                continue
            nome_ef = ((e1 or e0) or {}).get("name") if isinstance(e1 or e0, dict) else None
            rot = "efeito %s" % (nome_ef or k)
            if e0 is None:
                confere(it, rot, "efeito novo na wiki")
            elif e1 is None:
                confere(it, rot, "o efeito saiu da wiki")
            else:
                diff = sorted(x for x in set(e0) | set(e1) if e0.get(x) != e1.get(x)) if isinstance(e0, dict) and isinstance(e1, dict) else ["texto"]
                confere(it, rot, "mudou na wiki: %s" % ", ".join("o texto" if x == "description" else x for x in diff),
                        antes=e0.get("description") if isinstance(e0, dict) else e0, depois=e1.get("description") if isinstance(e1, dict) else e1)
        if a["grupo"] != b["grupo"]:
            confere(it, "grupo/limite", "mudou na wiki", antes=a["grupo"], depois=b["grupo"])
        for k, uso in OUTROS_DA_WIKI.items():
            if a["outros"][k] != b["outros"][k]:
                confere(it, k, "mudou na wiki (%s → %s): é do Capítulo 1 (%s)" % (
                    json.dumps(a["outros"][k], ensure_ascii=False), json.dumps(b["outros"][k], ensure_ascii=False), uso))

        if suspeito:
            # 4ª rodada: o aviso sai sempre (antes, só quando havia outro campo a aplicar)
            confere(it, "item", "o item espera inteiro: sinal de edição pela metade em %s" % ", ".join(dict.fromkeys(suspeito)))
            inteiros.add(it["slug"])
            continue
        if not novos_campos and not attrs_mudados:
            camada["nada"] += 1
            continue
        e = entra(it)
        e["mudou"].extend(mudou)
        preco = novos_campos.get("priceGold", it.get("priceGold"))
        if "priceGold" in novos_campos:
            e["campos"]["priceGold"] = preco
            mudancas_de_preco[it["nameEn"]] = (it.get("priceGold"), preco)
        if "gameModes" in novos_campos:
            e["campos"]["gameModes"] = novos_campos["gameModes"]
            e["contaVelha"].extend(k for k in ("aramNotes", "mayhemNotes") if it.get(k))   # 5ª rodada: "Item desativado em ARAM."
        if attrs_mudados:
            lista = copy.deepcopy(it.get("attributes") or [])
            for k, v in attrs_mudados.items():
                stat, unidade = ATRIBUTOS[k]
                achou = [x for x in lista if isinstance(x, dict) and x.get("stat") == stat and x.get("unit") == unidade]
                if v is None:
                    lista = [x for x in lista if x not in achou]
                elif achou:
                    achou[0]["value"] = v
                    achou[0]["raw"] = raw_atributo(v, stat, unidade)
                else:
                    lista.append({"raw": raw_atributo(v, stat, unidade), "value": v, "unit": unidade, "stat": stat, "scaling": None})
            e["campos"]["attributes"] = lista
            e["contaVelha"].extend(["costAnalysis", "itemClass"] + (["masterwork"] if it.get("masterwork") else []))
            e["contaVelha"].extend(textos_que_citam(it, [c["atributos"].get(k) for k in attrs_mudados], do_item=True))   # 4ª rodada
            if any((v is None) != (c["atributos"].get(k) is None) for k, v in attrs_mudados.items()):
                e["contaVelha"].append("attributeCategory")   # atributo que entra ou sai muda a categoria
        if "priceGold" in novos_campos and "costAnalysis" not in e["contaVelha"]:
            e["contaVelha"].append("costAnalysis")
        if "priceGold" in novos_campos:
            e["contaVelha"].extend(textos_que_citam(it, [it.get("priceGold")]))   # 5ª rodada: "Eficiência … sobre 2.300g"
        if it.get("apexNumeric") and ("priceGold" in novos_campos or attrs_mudados):
            e["contaVelha"].append("apexNumeric")   # a eficiência no Ápice divide pelo preço e soma os atributos

    # o que se refaz pela fórmula do próprio dado: o preço novo dos componentes nos
    # itens que os usam, o custo de combinação e o Reembolso
    for it in itens:
        if it["slug"] in inteiros:
            # 4ª rodada: o item que espera não recebe campo nenhum, mas a conta dele que depende
            # de OUTRO item aplicado (o preço de um componente) fica marcada
            if any(x.get("nameEn") in mudancas_de_preco for x in it.get("components") or []):
                e = entra(it)
                e["contaVelha"] = sorted(set(e["contaVelha"]) | {"components"} | ({"combineCost"} if it.get("combineCost") is not None else set())
                                         | set(textos_que_citam(it, [mudancas_de_preco[x["nameEn"]][0] for x in it.get("components") or [] if x.get("nameEn") in mudancas_de_preco])))
            continue
        e = camada["itens"].get(it["slug"])
        comps = copy.deepcopy(e["campos"]["components"] if e is not None and "components" in e["campos"] else (it.get("components") or []))
        mexeu_comp = False
        for comp in comps:
            if comp.get("nameEn") in mudancas_de_preco:
                comp["priceGold"] = mudancas_de_preco[comp["nameEn"]][1]
                mexeu_comp = True
        preco_mudou = e is not None and "priceGold" in e["campos"]
        if not (mexeu_comp or preco_mudou):
            continue
        e = entra(it)
        if mexeu_comp:
            e["campos"]["components"] = comps
            e["contaVelha"].extend(textos_que_citam(it, [mudancas_de_preco[x["nameEn"]][0] for x in comps if x.get("nameEn") in mudancas_de_preco]))
            e["mudou"].append({"campo": "preço de componente", "de": None, "para": None, "fonte": "a regra",
                               "nota": ", ".join("%s %s→%s" % (n, mudancas_de_preco[n][0], mudancas_de_preco[n][1])
                                                 for n in sorted({x["nameEn"] for x in comps if x.get("nameEn") in mudancas_de_preco}))})
        preco = e["campos"].get("priceGold", it.get("priceGold"))
        if it.get("combineCost") is not None and comps:
            id_c = str(it["id"]).split(" ")[0]
            base0 = ((dd0["data"].get(id_c) or {}).get("gold") or {}).get("base")
            base1 = ((dd1["data"].get(id_c) or {}).get("gold") or {}).get("base")
            antes = (it.get("priceGold") or 0) - sum((x.get("priceGold") or 0) * int(x.get("qty") or 1) for x in (it.get("components") or []))
            novo = preco - sum((x.get("priceGold") or 0) * int(x.get("qty") or 1) for x in comps) if preco is not None else None
            if it["slug"] in preco_em_aberto or antes != it["combineCost"] or novo is None or (base0 == it["combineCost"] and base1 is None):
                e["contaVelha"].append("combineCost")
            elif base0 == it["combineCost"] and base1 is not None and base1 != novo:
                confere(it, "custo de combinação", "a conta dá %s e o Data Dragon diz %s" % (novo, base1), catalogo=it["combineCost"])
                e["contaVelha"].append("combineCost")
            else:
                e["campos"]["combineCost"] = novo
                if novo != it["combineCost"]:
                    e["contaVelha"].extend(textos_que_citam(it, [it["combineCost"]]))
        cb = it.get("cashback")
        if cb and "priceGold" in e["campos"]:
            pct = cb.get("percent")
            velho = it.get("priceGold") or 0
            if pct is not None and round(velho * pct / 100, 2) == round(cb.get("refundGold") or 0, 2):
                ref = round(preco * pct / 100, 2)
                e["campos"]["cashback"] = dict(cb, refundGold=num(ref), netGold=num(round(preco - ref, 2)),
                                               raw="%s%% de %sg = %sg (líquido: %sg)" % (fmt_num(pct), fmt_num(preco), fmt_num(ref), fmt_num(preco - ref)))
                e["contaVelha"].extend(textos_que_citam(it, [cb.get("refundGold"), cb.get("netGold")]))
            else:
                e["contaVelha"].append("cashback")
        e["contaVelha"] = sorted(set(e["contaVelha"]))

    # o item de referência do valor em ouro mudou (meta.statPrices): a análise de custo e o
    # núcleo de todo item com atributo ficam velhos — a camada diz isso item a item
    refs = referencias_de_preco(catalogo)
    mudaram = sorted(refs[s] for s, e in camada["itens"].items() if s in refs and ("priceGold" in e["campos"] or "attributes" in e["campos"]))
    if mudaram:
        camada["statPricesVelhos"] = mudaram
        for it in itens:
            # 3ª rodada: os Elixires não têm atributo, e a conta deles é pelo valor em ouro.
            # 4ª rodada: o item que espera inteiro também fica marcado (campo dele não entra, a
            # marca sim), e os fragmentos do Aumento de Atributo (atributo × valor em ouro) também
            marca = ({"costAnalysis", "itemClass"} | ({"apexNumeric"} if it.get("apexNumeric") else set())) if it.get("costAnalysis") else set()
            if it.get("fragments"):
                marca.add("fragments")
            if marca:
                marca |= set(textos_que_citam(it, ouro=True))   # 5ª rodada: "Dano de Ataque 11 (385g)", "2.250g ÷ 2.300g"
                e = entra(it)
                e["contaVelha"] = sorted(set(e["contaVelha"]) | marca)

    # itens novos no jogo (Summoner's Rift ou ARAM): são do Capítulo 1. 4ª rodada: "novo" é por
    # modo, não por nome — o item que VOLTA (a wiki já tinha a entrada, sem SR nem ARAM) também
    # entra; e o que só o Data Dragon traz (a wiki ainda sem a entrada), também
    nomes_cat = {i.get("wikiName") or i.get("nameEn") for i in itens}
    ids_listados = set()
    for n in sorted(w1r):
        f = w1r[n]
        if n in nomes_cat or not isinstance(f, dict):
            continue
        modos = modos_da_fonte(f.get("modes")) if isinstance(f.get("modes"), dict) else []
        f0 = w0r.get(n)
        antes = (modos_da_fonte(f0.get("modes")) if isinstance(f0, dict) and isinstance(f0.get("modes"), dict) else None) or []
        if modos and not antes:
            camada["novos"].append(dict({"nome": n, "id": f.get("id"), "tipo": f.get("type"), "modos": modos, "preco": f.get("buy")},
                                        **({"volta": True} if f0 is not None else {})))
            ids_listados.add(str(f.get("id")))
    nomes_pt = {i.get("namePt") for i in itens}
    for k in sorted(set(dd1["data"]) - set(dd0["data"]) - set(nome_por_id) - ids_listados):
        d = dd1["data"][k]
        if d.get("name") in nomes_pt or (len(k) == 6 and k[2:] in nome_por_id):
            continue      # 5ª rodada: a variante (22xxxx do ARAM, 32xxxx, 66xxxx da Arena, 77xxxx do Mayhem) não é item novo
        camada["novos"].append({"nome": d.get("name"), "id": k, "tipo": None, "modos": modos_dd(d),
                                "preco": (d.get("gold") or {}).get("total"), "fonte": "só o Data Dragon"})
    # 4ª rodada: cada campo da camada leva o valor do catálogo de que nasceu — o app só o põe
    # por cima se o catálogo ainda disser isso (o Capítulo 1 pode ter mexido no item depois)
    por_slug = {i["slug"]: i for i in itens}
    for slug, e in camada["itens"].items():
        e["base"] = {k: copy.deepcopy(por_slug[slug].get(k)) for k in e["campos"]}
    # "sem mudança" no fim, depois das marcas de conta velha (que entram em itens sem mudança própria)
    camada["nada"] = sum(1 for i in itens if i["slug"] not in camada["itens"] and i["slug"] not in inteiros)
    return camada


# ---------------------------------------------------------------- saída
def sha_do_texto(b):
    """O sha256 do conteúdo, com o fim de linha normalizado: o mesmo commit é CRLF no Windows
    do Leo e LF no GitHub (5ª rodada: a camada válida virava "de outro catálogo")."""
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def sha_do_catalogo():
    with open(CATALOGO_JS, "rb") as f:
        return sha_do_texto(f.read())


def camada_no_disco(caminho=CAMADA):
    try:
        t = open(caminho, encoding="utf-8").read()
        return json.loads(t[t.index("{"): t.rindex("}") + 1])
    except (OSError, ValueError):
        return None


def camada_ainda_vale(velha, de, sha):
    """A camada no disco nasceu deste catálogo? 4ª rodada: o catálogo subia de patch (ou o
    Capítulo 1 mexia nele) num dia em que a foto mais nova não tinha assentado, e a camada de
    outro catálogo ficava por cima dele — com listas inteiras copiadas do catálogo velho."""
    return bool(velha) and velha.get("de") == de and (velha.get("catalogo") or {}).get("sha256") == sha


def ler_conferido():
    try:
        return json.load(open(os.path.join(BAIXADO, "conferido.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None


def escrever_camada(camada, de, para, m0, m1, caminho=CAMADA):
    rev = lambda m: ((m or {}).get("wiki") or {}).get("revid")
    ver = lambda m: ((m or {}).get("ddragon") or {}).get("versao")
    corpo = {
        "de": de, "para": para,
        "gerado": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # 4ª rodada: o catálogo de que a camada nasceu — com outro catálogo, ela não vale
        "catalogo": {"patch": de, "sha256": sha_do_catalogo()},
        "fonte": {"wiki": {"de": rev(m0), "para": rev(m1)}, "ddragon": {"de": ver(m0), "para": ver(m1)}},
        "itens": camada["itens"], "aConferir": camada["aConferir"], "novos": camada["novos"],
    }
    if camada.get("statPricesVelhos"):
        corpo["statPricesVelhos"] = camada["statPricesVelhos"]   # o valor em ouro dos atributos é do patch anterior
    # F13-T78: o robô roda todo dia no GitHub; a camada igual (fora o "gerado") não se regrava —
    # nem vira um commit só de data
    velha = camada_no_disco(caminho)
    sem_data = lambda c: {k: v for k, v in c.items() if k != "gerado"}
    if velha is not None and sem_data(velha) == json.loads(json.dumps(sem_data(corpo), ensure_ascii=False)):
        corpo["gerado"] = velha.get("gerado", corpo["gerado"])
        return corpo
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("// Gerado por data/robo/aplicar_patch.py (o robô de patch, F13-T74). Não editar à mão:\n")
        f.write("// o que mudou na fonte de %s para %s e passou na regra de segurança (docs/robo_de_patch.md).\n" % (de, para))
        f.write("window.ATUALIZACAO_PATCH = ")
        json.dump(corpo, f, ensure_ascii=False, indent=1)
        f.write(";\n")
    return corpo


def relatorio(corpo, nada, caminho):
    cel = lambda x: "—" if x is None else (json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x)
    L = ["# Robô de patch — o que mudou de %s para %s" % (corpo["de"], corpo["para"]), "",
         "Gerado por `data/robo/aplicar_patch.py` em %s. Wiki: revisão %s → %s · Data Dragon %s → %s." % (
             corpo["gerado"], corpo["fonte"]["wiki"]["de"], corpo["fonte"]["wiki"]["para"], corpo["fonte"]["ddragon"]["de"], corpo["fonte"]["ddragon"]["para"]), ""]
    aplicados = sum(len(e["mudou"]) for e in corpo["itens"].values())
    com_campo = sum(1 for e in corpo["itens"].values() if e["mudou"])
    so_marca = len(corpo["itens"]) - com_campo      # só a marca de conta do patch anterior
    L.append("**%d mudança%s aplicada%s** em %d ite%s (camada `data/atualizacao_patch.js`)%s · **%d a conferir** · **%d ite%s novo%s no jogo** · %d itens sem mudança." % (
        aplicados, "" if aplicados == 1 else "s", "" if aplicados == 1 else "s", com_campo, "m" if com_campo == 1 else "ns",
        " · %d ite%s só com conta do patch anterior" % (so_marca, "m" if so_marca == 1 else "ns") if so_marca else "",
        len(corpo["aConferir"]), len(corpo["novos"]), "m" if len(corpo["novos"]) == 1 else "ns", "" if len(corpo["novos"]) == 1 else "s", nada))
    L.append("")
    if corpo["itens"]:
        L += ["## Aplicado pelo robô", "", "| Item | Campo | Antes | Agora | Fonte |", "|---|---|---|---|---|"]
        for slug, e in corpo["itens"].items():
            for m in e["mudou"]:
                L.append("| %s | %s | %s | %s | %s |" % (slug, m["campo"], cel(m.get("de")) if "nota" not in m else m["nota"], cel(m.get("para")) if "nota" not in m else "", m["fonte"]))
            if e["contaVelha"]:
                L.append("| %s | conta do patch anterior | %s | — | o Capítulo 1 refaz |" % (slug, ", ".join(e["contaVelha"])))
        L.append("")
    if corpo["aConferir"]:
        L += ["## A conferir (o Capítulo 1 decide)", "", "| Item | Campo | Por quê |", "|---|---|---|"]
        for x in corpo["aConferir"]:
            L.append("| %s | %s | %s |" % (x["item"], x["campo"], x["porque"]))
        L.append("")
    if corpo["novos"]:
        L += ["## Itens novos no jogo (entram pelo Capítulo 1)", "", "| Nome (wiki) | Id | Tipo | Modos | Preço |", "|---|---|---|---|---|"]
        for x in corpo["novos"]:
            L.append("| %s | %s | %s | %s | %s |" % (x["nome"], x["id"], cel(x["tipo"]), ", ".join(x["modos"]), cel(x["preco"])))
        L.append("")
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def fotos():
    pasta = os.path.join(AQUI, "fonte")
    chave = lambda v: tuple(int(x) if x.isdigit() else 0 for x in v.split("."))
    return sorted((x for x in os.listdir(pasta) if x[:1].isdigit() and os.path.isdir(os.path.join(pasta, x))), key=chave)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--para", help="o patch novo (padrão: a foto mais nova em data/robo/fonte)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    catalogo = ler_catalogo()
    de = catalogo["meta"]["patch"]
    para = a.para or fotos()[-1]
    vazia = {"itens": {}, "aConferir": [], "novos": []}
    if not os.path.exists(os.path.join(AQUI, "fonte", de, "meta.json")):
        escrever_camada(vazia, de, de, None, None)
        sys.exit("sem a foto base do %s (o patch do catálogo): rode o ler_fonte, que a faz · a camada ficou vazia" % de)
    antiga, nova = ler_foto(de), ler_foto(para)
    if para == de:
        # o catálogo já é deste patch: a camada fica vazia (e a de um patch velho sai)
        escrever_camada(vazia, de, para, antiga[2], nova[2])
        print("o catálogo já é do %s: nada a aplicar · camada vazia em data/atualizacao_patch.js" % de)
        return
    # 4ª rodada: a base tem de ser a revisão que o Capítulo 1 registrou para o patch do catálogo
    declarada = revisao_do_capitulo1(patch=de)
    if declarada is None:
        # 5ª rodada: sem a revisão registrada, a base pode ser uma foto do dia, de depois da
        # leitura do Capítulo 1 — e o que mudou entre as duas some da camada sem aviso
        escrever_camada(vazia, de, de, antiga[2], antiga[2])
        sys.exit("o Catalogo_Itens_LoL.md não registra (ou registra mais de uma) a revisão do Module:ItemData/data na reconciliação do %s: "
                 "sem ela a base não se confere · a camada ficou vazia" % de)
    if antiga[2]["wiki"]["revid"] != declarada:
        escrever_camada(vazia, de, de, antiga[2], antiga[2])
        sys.exit("a foto base do %s é da revisão %s, e o Capítulo 1 registrou a %s: rode o ler_fonte (ele refaz a base) · a camada ficou vazia"
                 % (de, antiga[2]["wiki"]["revid"], declarada))
    if not assentada(nova[2], ler_conferido()):
        # dia de patch: a wiki ainda está sendo editada — o robô tenta de novo amanhã (revisão
        # da T74: uma foto no meio da edição seria aplicada). A camada de antes fica se nasceu
        # deste catálogo; se não, sai (4ª rodada)
        espera = "a revisão %s (de %s) do %s ainda não foi vista assentada (24 h de idade e 24 h depois da 1ª foto do patch): o robô espera" % (
            nova[2]["wiki"]["revid"], nova[2]["wiki"]["revisao_de"], para)
        if camada_ainda_vale(camada_no_disco(), de, sha_do_catalogo()):
            print(espera + "; a camada não mudou")
        else:
            escrever_camada(vazia, de, de, antiga[2], antiga[2])
            print(espera + "; a camada de antes era de outro catálogo e ficou vazia")
        return
    camada = regra(catalogo, antiga, nova)
    corpo = escrever_camada(camada, de, para, antiga[2], nova[2])
    relatorio(corpo, camada["nada"], os.path.join(AQUI, "mudancas_%s_%s.md" % (de, para)))
    print("de %s para %s · %d itens com mudança aplicada · %d a conferir · %d novos · camada em data/atualizacao_patch.js"
          % (de, para, len(corpo["itens"]), len(corpo["aConferir"]), len(corpo["novos"])))


if __name__ == "__main__":
    main()
