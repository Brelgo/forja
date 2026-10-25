"""O robô de patch, parte 1 (F13-T73): o leitor.

Lê a fonte do Capítulo 1 no patch do dia e diz o que ela tem de diferente do
catálogo — sem mexer em nada. Plano aprovado pelo Leo em 16/10/2026 (CHECKPOINT,
seção 4): o robô guarda a foto da fonte de cada patch e, nas próximas partes,
aplica sozinho só o que mudou na fonte e que o catálogo tinha igual à fonte
antiga; o resto vira "a conferir".

Fontes (as mesmas do Capítulo 1, docs/projeto/Regras_de_Fonte.md de lá):
  - Data Dragon: versions.json (o patch do dia) e o item.json em pt_BR;
  - wiki do LoL: o Module:ItemData/data, pela API (a página HTML recusa robô).

Saída:
  - data/robo/fonte/<patch>/wiki_itemdata.json  a tabela da wiki como veio (lida, sem resolver)
  - data/robo/fonte/<patch>/meta.json           de onde, quando, qual revisão e o hash
  - data/robo/relatorio_<patch>.md              fonte × catálogo, campo a campo

Uso:  python data/robo/ler_fonte.py            (baixa de novo)
      python data/robo/ler_fonte.py --offline  (usa o que já está em data/robo/fonte/_baixado)
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)
from lua_tabela import ErroLua, ler_modulo  # noqa: E402

UA = "MontadorDeItens-robo/0.1 (https://brelgo.github.io/montador_de_itens_lol/)"
URL_VERSOES = "https://ddragon.leagueoflegends.com/api/versions.json"
URL_WIKI = ("https://wiki.leagueoflegends.com/en-us/api.php?action=query&prop=revisions"
            "&titles=Module:ItemData/data&rvprop=content|ids|timestamp&rvslots=main&format=json&formatversion=2")
URL_ITEM = "https://ddragon.leagueoflegends.com/cdn/{patch}/data/pt_BR/item.json"
URL_WIKI_REVISAO = ("https://wiki.leagueoflegends.com/en-us/api.php?action=query&prop=revisions"
                    "&revids={revid}&rvprop=content|ids|timestamp&rvslots=main&format=json&formatversion=2")
CATALOGO_MD = os.path.join(RAIZ, "data", "Catalogo_Itens_LoL.md")
BAIXADO = os.path.join(AQUI, "fonte", "_baixado")

# O nome de cada atributo da wiki no catálogo, com a unidade — é o esquema do
# Capítulo 1 (docs/esquema_catalog.md), não dado de item. "spec" é texto livre.
ATRIBUTOS = {
    "ad": ("Dano de Ataque", "flat"), "ah": ("Aceleração de Habilidade", "flat"), "ap": ("Poder de Habilidade", "flat"),
    "armor": ("Armadura", "flat"), "mr": ("Resistência Mágica", "flat"), "hp": ("Vida", "flat"), "mana": ("Mana", "flat"),
    "as": ("Velocidade de Ataque", "percent"), "crit": ("Chance de Acerto Crítico", "percent"),
    "critdamage": ("Dano de Acerto Crítico", "percent"), "lethality": ("Letalidade", "flat"),
    "msflat": ("Velocidade de Movimento", "flat"), "ms": ("Velocidade de Movimento", "percent"),
    "mp5": ("Regeneração de Mana base", "percent"), "hp5": ("Regeneração de Vida base", "percent"),
    "hp5flat": ("Regeneração de Vida (a cada 5s)", "flat"), "hsp": ("Poder de Cura e Escudo", "percent"),
    "omnivamp": ("Vampirismo Universal", "percent"), "lifesteal": ("Roubo de Vida", "percent"),
    "gp10": ("ouro a cada 10s", "flat"), "tenacity": ("Tenacidade", "percent"),
    "mpenflat": ("Penetração Mágica", "flat"), "mpen": ("Penetração Mágica", "percent"),
    "armpen": ("Penetração de Armadura", "percent"),
}
EFEITOS_COM_NOME = ("pass", "pass2", "pass3", "pass4", "act")


# ---------------------------------------------------------------- baixar
def baixar(url, nome, offline):
    """Lê do que já foi baixado (--offline) ou da internet — sem gravar nada ainda:
    quem grava é ler_fontes, depois que as três fontes chegaram (revisão da T74: um
    item.json que ainda não saiu deixava _baixado com o versions.json novo e o item.json velho)."""
    if offline:
        with open(os.path.join(BAIXADO, nome), "rb") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except OSError as e:          # HTTPError e URLError são OSError
        sys.exit("não deu para baixar %s (%s): %s — nada foi gravado" % (nome, url, e))


def ler_fontes(offline):
    brutos = {}
    brutos["versions.json"] = baixar(URL_VERSOES, "versions.json", offline)
    patch = json.loads(brutos["versions.json"])[0]
    brutos["itemdata_api.json"] = baixar(URL_WIKI, "itemdata_api.json", offline)
    brutos["item_pt_BR.json"] = baixar(URL_ITEM.format(patch=patch), "item_pt_BR.json", offline)
    api = json.loads(brutos["itemdata_api.json"])
    pagina = api["query"]["pages"][0]
    rev = pagina["revisions"][0]
    lua = rev["slots"]["main"]["content"]
    avisos = []
    wiki = ler_modulo(lua, avisos)
    ddragon = json.loads(brutos["item_pt_BR.json"])
    if ddragon.get("version") != patch:
        sys.exit("o item.json é do %s, e o patch do dia é o %s: nada foi gravado" % (ddragon.get("version"), patch))
    if not offline:
        os.makedirs(BAIXADO, exist_ok=True)
        for nome, dado in brutos.items():
            with open(os.path.join(BAIXADO, nome), "wb") as f:
                f.write(dado)
    meta = {
        "patch": patch,
        "lido_em": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "wiki": {"pagina": pagina["title"], "revid": rev["revid"], "revisao_de": rev["timestamp"],
                 "sha256": hashlib.sha256(lua.encode("utf-8")).hexdigest(), "itens": len(wiki)},
        "ddragon": {"versao": ddragon.get("version"), "itens": len(ddragon.get("data", {}))},
        "avisos_do_leitor": avisos,
    }
    return patch, wiki, ddragon, meta, lua


def extrato_ddragon(ddragon):
    """Os itens da Summoner's Rift (11) e do ARAM (12) — o escopo do catálogo —, com
    o que o robô compara: nome, preço, receita e os dois mapas."""
    out = {}
    for k, v in ddragon.get("data", {}).items():
        mapas = v.get("maps") or {}
        if mapas.get("11") or mapas.get("12"):
            out[k] = {"name": v.get("name"), "gold": v.get("gold"), "from": v.get("from", []),
                      "maps": {m: bool(mapas.get(m)) for m in ("11", "12")}}
    return {"version": ddragon.get("version"), "data": out}


def ler_foto(patch):
    """A foto guardada de um patch: (wiki como veio, extrato do Data Dragon, meta)."""
    pasta = os.path.join(AQUI, "fonte", patch)
    ler = lambda n: json.load(open(os.path.join(pasta, n), encoding="utf-8"))
    return ler("wiki_itemdata.json"), ler("ddragon_itens.json"), ler("meta.json")


def contar_por_fora(lua):
    """Quantas entradas de 1º nível o texto tem, sem o leitor: a conta tem de bater.
    Revisão da T74: era uma regex de 4 espaços, e um tab ou um espaço dentro do colchete
    travava o robô com "leitura pela metade" falso. Agora varre o texto pelas chaves
    (pulando texto entre aspas, texto longo e comentários) e conta as entradas
    `[ "Nome" ] = {` na profundidade 1 — a formatação não importa."""
    i, n, prof, nomes = 0, len(lua), 0, set()
    while i < n:
        if lua.startswith("--", i):
            m = re.match(r"--\[(=*)\[", lua[i:i + 40])
            if m:
                fim = lua.find("]" + m.group(1) + "]", i + len(m.group(0)))
                i = n if fim < 0 else fim + len(m.group(1)) + 2
            else:
                fim = lua.find("\n", i)
                i = n if fim < 0 else fim + 1
            continue
        c = lua[i]
        if c in "\"'":
            j = i + 1
            while j < n and lua[j] != c:
                j += 2 if lua[j] == "\\" else 1
            i = j + 1
            continue
        if c == "[":
            m = re.match(r"\[(=*)\[", lua[i:i + 40])
            if m:
                fim = lua.find("]" + m.group(1) + "]", i + len(m.group(0)))
                i = n if fim < 0 else fim + len(m.group(1)) + 2
                continue
        if c == "{":
            m = re.search(r'\[\s*"([^"]*)"\s*\]\s*=\s*$', lua[max(0, i - 300):i]) if prof == 1 else None
            if m:
                nomes.add(m.group(1))   # 3ª rodada: nomes distintos — uma entrada colada duas vezes é Lua válido (vale a última, e o leitor avisa)
            prof += 1
        elif c == "}":
            prof -= 1
        i += 1
    return len(nomes)


# ---------------------------------------------------------------- resolver "=>"
def resolver(wiki):
    """A wiki escreve "=>Outro Item" para "igual ao Outro Item" — no campo inteiro
    (type, modes) ou num atributo só (stats.hp). Devolve uma cópia resolvida e a
    lista do que não deu para resolver."""
    faltou = []

    def valor(nome_item, caminho, v, vistos):
        if isinstance(v, str) and v.startswith("=>"):
            alvo = v[2:].strip()
            if alvo not in wiki or (alvo, caminho) in vistos:
                faltou.append("%s: %s = %r" % (nome_item, ".".join(caminho), v))
                return v
            x = wiki[alvo]
            for k in caminho:
                x = x.get(k) if isinstance(x, dict) else None
            if x is None:      # o destino não tem o campo: avisa, não vira "nada" calado
                faltou.append("%s: %s = %r (o %s não tem o campo)" % (nome_item, ".".join(caminho), v, alvo))
                return v
            return valor(alvo, caminho, x, vistos | {(alvo, caminho)})
        if isinstance(v, dict):
            return {k: valor(nome_item, caminho + (k,), vv, vistos) for k, vv in v.items()}
        return v

    return {n: {k: valor(n, (k,), v, {(n, (k,))}) for k, v in item.items()} for n, item in wiki.items()}, faltou


# ---------------------------------------------------------------- comparar
def ler_catalogo():
    t = open(os.path.join(RAIZ, "data", "catalog.js"), encoding="utf-8").read()
    return json.loads(t[t.index("{"): t.rindex("}") + 1])


def num(v):
    return int(v) if isinstance(v, float) and v.is_integer() else v


def modos_da_fonte(m):
    if not isinstance(m, dict):
        return None
    out = []
    if m.get("classic sr 5v5"):
        out.append("Summoner's Rift")
    if m.get("aram"):
        out.append("ARAM")
    # Mayhem: a wiki só marca quando difere do ARAM (10 itens); sem a marca, segue o ARAM
    if m.get("mayhem", m.get("aram")):
        out.append("ARAM: Mayhem")
    return out


def efeitos_da_fonte(item):
    ef = item.get("effects") or {}
    return sorted({e["name"].strip() for k, e in ef.items()
                   if k in EFEITOS_COM_NOME and isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"].strip()})


def grupos_do_catalogo(cond):
    return sorted(set(re.findall(r"Limitado a 1 item do grupo [^(.;]+\(([^)]+)\)", cond or "")))


def nao_compravel(it, d):
    """Item que não se compra (concedido por runa, missão…): o catálogo dá 0 e diz
    por quê; a wiki não dá preço; o Data Dragon dá um valor com purchasable false."""
    return (it.get("priceGold") in (0, None) and "não comprável" in (it.get("priceNote") or "")) or (d is not None and d.get("gold", {}).get("purchasable") is False)


def comparar(catalogo, wiki_r, ddragon):
    dd = ddragon.get("data", {})
    dif = {k: [] for k in ("id", "preco", "receita", "atributos", "modos", "efeitos", "grupo", "ddragon")}
    dividida = []                 # a wiki diverge, o catálogo bate com o Data Dragon (o Capítulo 1 seguiu o Data Dragon)
    conta = {k: 0 for k in dif}
    so_no_catalogo = []           # atributo que a fonte não traz em "stats" (vem de efeito, por exemplo)
    sem_par = []
    nome_por_id = {str(i["id"]).split(" ")[0]: i["nameEn"] for i in catalogo["items"]}
    for it in catalogo["items"]:
        nome = it.get("wikiName") or it.get("nameEn")
        f = wiki_r.get(nome)
        rotulo = "%s (%s)" % (it["namePt"], nome)
        if f is None:
            sem_par.append(rotulo)
            continue
        id_c = str(it["id"]).split(" ")[0]
        d = dd.get(id_c)
        # id: a wiki dá às variantes de ARAM o id 22xxxx; o catálogo, o do Data Dragon (e às vezes anota o da wiki)
        conta["id"] += 1
        id_f = f.get("id")
        if not (str(id_f) == id_c or (isinstance(id_f, int) and id_c.isdigit() and id_f == 220000 + int(id_c)) or str(id_f) in str(it["id"])):
            dif["id"].append((rotulo, it["id"], id_f))
        # preço
        conta["preco"] += 1
        if num(f.get("buy")) != it.get("priceGold") and not (f.get("buy") in (None, 0) and nao_compravel(it, d)):
            if d is not None and d.get("gold", {}).get("purchasable") and d["gold"].get("total") == it.get("priceGold"):
                dividida.append(("preço", rotulo, it.get("priceGold"), f.get("buy")))
            else:
                dif["preco"].append((rotulo, it.get("priceGold"), f.get("buy")))
        # receita
        rec_f = sorted(f.get("recipe") or [])
        rec_c = sorted(c["nameEn"] for c in (it.get("components") or []) for _ in range(int(c.get("qty") or 1)))
        if rec_f or rec_c:
            conta["receita"] += 1
            if rec_f != rec_c:
                rec_d = sorted(nome_por_id.get(x, "?" + x) for x in ((d or {}).get("from") or []))
                if rec_d == rec_c:
                    dividida.append(("receita", rotulo, rec_c, rec_f))
                else:
                    dif["receita"].append((rotulo, rec_c, rec_f))
        # atributos
        attrs = {(a.get("stat"), a.get("unit")): a.get("value") for a in (it.get("attributes") or []) if isinstance(a, dict)}
        usados = set()
        for chave, v in (f.get("stats") or {}).items():
            if chave == "spec":
                continue
            conta["atributos"] += 1
            par = ATRIBUTOS.get(chave)
            if not par:
                dif["atributos"].append((rotulo, "—", "%s = %r (atributo que o robô ainda não conhece)" % (chave, v)))
                continue
            usados.add(par)
            if num(attrs.get(par)) != num(v):
                dif["atributos"].append((rotulo, "%s %s" % (par[0], attrs.get(par, "—")), "%s %r" % (par[0], v)))
        for par, v in attrs.items():
            if par not in usados and par in ATRIBUTOS.values():
                dif["atributos"].append((rotulo, "%s %s" % (par[0], v), "%s —" % par[0]))
            elif par not in usados:
                so_no_catalogo.append("%s: %s %s" % (rotulo, par[0], v))
        # modos
        mf = modos_da_fonte(f.get("modes"))
        if mf is not None:
            conta["modos"] += 1
            if sorted(mf) != sorted(it.get("gameModes") or []):
                dif["modos"].append((rotulo, it.get("gameModes"), mf))
        # efeitos com nome: o efeito sem nome em português ("—") leva no catálogo um
        # rótulo ("passiva", "transformação", "Active"); conta só se a wiki tiver o nome
        ef_f = efeitos_da_fonte(f)
        ef_c = sorted({(a.get("nameEn") or "").strip() for a in (it.get("abilities") or [])
                       if (a.get("nameEn") or "").strip() and a.get("type") != "consumir"
                       and (not re.fullmatch(r"[—–-]+", (a.get("name") or "").strip()) or (a.get("nameEn") or "").strip() in ef_f)})
        if ef_f or ef_c:
            conta["efeitos"] += 1
            if ef_f != ef_c:
                dif["efeitos"].append((rotulo, ef_c, ef_f))
        # grupo "Limitado a 1": o da wiki tem de estar escrito na condição do catálogo
        # (o padrão é "do grupo X (EN)"; os Elixires dizem "1 efeito de Elixir por vez")
        gr_f = sorted({f[k] for k in ("itemlimit", "itemlimit2") if isinstance(f.get(k), str)})
        gr_c = grupos_do_catalogo(it.get("condition"))
        if gr_f or gr_c:
            conta["grupo"] += 1
            cond = it.get("condition") or ""
            if any(not re.search(r"\b%s\b" % re.escape(g), cond) for g in gr_f) or any(g not in gr_f for g in gr_c):
                dif["grupo"].append((rotulo, gr_c or cond[:60], gr_f))
        # Data Dragon: o item existe, o preço (de quem se compra) e o nome em português
        conta["ddragon"] += 1
        if d is None:
            dif["ddragon"].append((rotulo, "id %s" % it["id"], "não está no item.json"))
        else:
            if d.get("gold", {}).get("purchasable") and d["gold"].get("total") != it.get("priceGold"):
                dif["ddragon"].append((rotulo, "preço %s" % it.get("priceGold"), "preço %s" % d["gold"].get("total")))
            if d.get("name") != it["namePt"]:
                dif["ddragon"].append((rotulo, "nome %s" % it["namePt"], "nome %s" % d.get("name")))
    return dif, conta, so_no_catalogo, sem_par, dividida


# ---------------------------------------------------------------- relatório
TITULOS = {
    "id": "Id", "preco": "Preço (buy)", "receita": "Receita (recipe)", "atributos": "Atributos (stats)",
    "modos": "Modos (modes)", "efeitos": "Efeitos com nome (pass/act)", "grupo": "Grupo \"Limitado a 1\" (itemlimit)",
    "ddragon": "Data Dragon (id, preço e nome pt_BR)",
}


def relatorio(meta, catalogo, wiki, dif, conta, so_no_catalogo, sem_par, faltou, por_fora, dividida):
    cat_ids = {str(it["id"]).split(" ")[0] for it in catalogo["items"]}
    cat_nomes = {it.get("wikiName") or it.get("nameEn") for it in catalogo["items"]}
    fora = sorted(n for n in wiki if n not in cat_nomes)
    L = []
    L.append("# Robô de patch — fonte × catálogo, patch %s" % meta["patch"])
    L.append("")
    L.append("Gerado por `data/robo/ler_fonte.py` em %s. **Só leitura**: nada do catálogo foi tocado." % meta["lido_em"])
    L.append("")
    L.append("| Fonte | O que foi lido |")
    L.append("|---|---|")
    L.append("| Data Dragon | patch do dia **%s** · `item.json` pt_BR com %d itens |" % (meta["patch"], meta["ddragon"]["itens"]))
    L.append("| Wiki `%s` | revisão %s de %s · %d itens lidos (%d entradas contadas por fora) |"
             % (meta["wiki"]["pagina"], meta["wiki"]["revid"], meta["wiki"]["revisao_de"], meta["wiki"]["itens"], por_fora))
    L.append("| Catálogo | `data/catalog.js`, patch %s · %d itens |" % (catalogo["meta"]["patch"], len(catalogo["items"])))
    L.append("")
    total = sum(len(v) for v in dif.values())
    L.append("**%s a conferir.** %d itens do catálogo casados com a wiki (%d sem par); %d em que a wiki diverge e o catálogo segue o Data Dragon." % (
        "Nenhuma diferença" if not total else "%d diferença%s" % (total, "" if total == 1 else "s"),
        len(catalogo["items"]) - len(sem_par), len(sem_par), len(dividida)))
    L.append("")
    L.append("| Campo | Itens comparados | A conferir |")
    L.append("|---|---:|---:|")
    for k in dif:
        L.append("| %s | %d | %d |" % (TITULOS[k], conta[k], len(dif[k])))
    L.append("")
    cel = lambda x: json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x
    for k, linhas in dif.items():
        if not linhas:
            continue
        L.append("## A conferir — %s" % TITULOS[k])
        L.append("")
        L.append("| Item | Catálogo | Fonte |")
        L.append("|---|---|---|")
        for rot, c, f in linhas:
            L.append("| %s | %s | %s |" % (rot, cel(c), cel(f)))
        L.append("")
    if dividida:
        L.append("## Fonte dividida — o catálogo segue o Data Dragon")
        L.append("")
        L.append("A wiki diz outra coisa, e o Data Dragon do patch bate com o catálogo: foi o que o Capítulo 1 escolheu (pendências A1 e A2 em `docs/pendencias_capitulo1.md`). Não é erro do catálogo; o robô nunca troca esses campos sozinho.")
        L.append("")
        L.append("| Campo | Item | Catálogo (= Data Dragon) | Wiki |")
        L.append("|---|---|---|---|")
        for campo, rot, c, f in dividida:
            L.append("| %s | %s | %s | %s |" % (campo, rot, cel(c), cel(f)))
        L.append("")
    if sem_par:
        L.append("## Itens do catálogo sem par na wiki")
        L.append("")
        L.extend("- %s" % x for x in sem_par)
        L.append("")
    L.append("## O que o robô não compara (e por quê)")
    L.append("")
    L.append("- **Atributos que só o catálogo tem** (%d): não estão nos números da tabela `stats` da wiki — vêm do texto do efeito ou do texto livre `stats.spec` (a Vida ao contato da Abatedora); o robô vê a mudança pelo texto (do efeito ou do `spec`) e a manda para a conferir, na parte 2." % len(so_no_catalogo))
    L.extend("  - %s" % x for x in so_no_catalogo)
    L.append("- **Texto curado** (Mecânica, Ápice, Passiva do Ornn, notas, interações): é de pessoa; o robô só marca \"a conferir\".")
    L.append("- **%d itens da wiki fora do catálogo** (Arena, Nexus Blitz, torres, tropas, os removidos…): o escopo são os 225 do Capítulo 1." % len(fora))
    L.append("")
    if meta["avisos_do_leitor"] or faltou:
        L.append("## Avisos do leitor")
        L.append("")
        L.extend("- %s" % x for x in meta["avisos_do_leitor"])
        L.extend("- referência \"=>\" sem destino: %s" % x for x in faltou)
        L.append("")
    return "\n".join(L)


def acao_da_base(existe, rev_da_base, declarada, offline):
    """O que fazer com a foto base (a do patch do catálogo): "ok", "criar", "refazer" ou
    "avisar". Ela tem de ser a revisão que o Capítulo 1 registrou no catálogo (3ª rodada da
    revisão: o robô fotografa o patch novo todo dia, e quando o catálogo subia a foto do dia
    virava base — de outra revisão; e o catálogo num patch nunca fotografado ficava sem base)."""
    if not declarada:
        return "avisar" if existe else "ok"      # 5ª rodada: sem a revisão registrada, a base não se confere — avisa
    if existe and rev_da_base == declarada:
        return "ok"
    if offline:
        return "avisar" if existe else "ok"
    return "refazer" if existe else "criar"


def base_confere(pagina, wiki, lua, catalogo):
    """A revisão que vai virar base é mesmo o módulo, lido inteiro, com os itens do catálogo?
    ("" = é). 4ª rodada: um número trocado no .md (o Capítulo 1 cita revisões de várias
    páginas lado a lado) virava base de outra página — ou derrubava o robô todo dia."""
    if (pagina or {}).get("title") != "Module:ItemData/data":
        return "é da página %r, não do Module:ItemData/data" % (pagina or {}).get("title")
    if contar_por_fora(lua) != len(wiki):
        return "foi lida pela metade (%d de %d entradas)" % (len(wiki), contar_por_fora(lua))
    nomes = {i.get("wikiName") or i.get("nameEn") for i in catalogo["items"]}
    if len(nomes & set(wiki)) < 0.95 * len(nomes):
        return "casa só %d dos %d itens do catálogo" % (len(nomes & set(wiki)), len(nomes))
    return ""


def garantir_base(catalogo, offline):
    """A foto base fica certa — ou o robô avisa e segue: a foto do patch novo ainda se faz, e o
    aplicar_patch se recusa a aplicar com a base errada (4ª rodada: antes, parava tudo)."""
    patch = catalogo["meta"]["patch"]
    pasta = os.path.join(AQUI, "fonte", patch)
    caminho = os.path.join(pasta, "meta.json")
    existe = os.path.exists(caminho)
    rev = json.load(open(caminho, encoding="utf-8"))["wiki"]["revid"] if existe else None
    declarada = revisao_do_capitulo1(patch=patch)
    acao = acao_da_base(existe, rev, declarada, offline)
    if acao == "avisar" and not declarada:
        print("atenção: o Catalogo_Itens_LoL.md não registra (ou registra mais de uma) a revisão do Module:ItemData/data na reconciliação do %s — "
              "a base (revisão %s) não se confere, e o aplicar_patch não aplica nada até isso se resolver" % (patch, rev))
    elif acao == "avisar":
        print("atenção: a foto base do %s é da revisão %s, e o Capítulo 1 registrou a %s (sem rede, não refaço)" % (patch, rev, declarada))
    if acao not in ("criar", "refazer"):
        return
    try:
        pagina, revisao, lua, wiki, avisos = ler_revisao(declarada)
    except (ErroLua, KeyError, IndexError, TypeError, ValueError) as e:
        print("atenção: a revisão %s que o Capítulo 1 registrou para o %s não se lê como o módulo (%s: %s) — a base não foi %s"
              % (declarada, patch, type(e).__name__, e, "refeita" if existe else "feita"))
        return
    problema = base_confere(pagina, wiki, lua, catalogo)
    if problema:
        print("atenção: a revisão %s que o Capítulo 1 registrou para o %s %s — a base não foi %s (confira o número no Catalogo_Itens_LoL.md)"
              % (declarada, patch, problema, "refeita" if existe else "feita"))
        return
    ddragon = json.loads(baixar(URL_ITEM.format(patch=patch), "item_pt_BR.json", False))
    if ddragon.get("version") != patch:
        print("atenção: o item.json do %s não veio (veio o %s) — a base não foi %s" % (patch, ddragon.get("version"), "refeita" if existe else "feita"))
        return
    agora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {"patch": patch, "lido_em": agora, "primeira_foto": agora,
            "wiki": {"pagina": pagina["title"], "revid": revisao["revid"], "revisao_de": revisao["timestamp"],
                     "sha256": hashlib.sha256(lua.encode("utf-8")).hexdigest(), "itens": len(wiki)},
            "ddragon": {"versao": ddragon.get("version"), "itens": len(ddragon.get("data", {}))},
            "avisos_do_leitor": avisos + ["a base é a revisão %s, a que o Capítulo 1 registrou no catálogo" % declarada]}
    gravar_foto(pasta, wiki, ddragon, meta, base=True)
    print("a foto base do %s foi %s da revisão %s, a que o Capítulo 1 registrou" % (patch, "refeita" if acao == "refazer" else "feita", declarada))


def escrever_relatorio(patch, meta, wiki, catalogo, extrato, por_fora):
    wiki_r, faltou = resolver(wiki)
    dif, conta, so_no_catalogo, sem_par, dividida = comparar(catalogo, wiki_r, extrato)
    texto = relatorio(meta, catalogo, wiki, dif, conta, so_no_catalogo, sem_par, faltou, por_fora, dividida)
    with open(os.path.join(AQUI, "relatorio_%s.md" % patch), "w", encoding="utf-8", newline="\n") as f:
        f.write(texto + "\n")
    total = sum(len(v) for v in dif.values())
    print("patch %s · wiki rev %s · %d itens lidos · %d a conferir · %d com a fonte dividida · relatório em data/robo/relatorio_%s.md"
          % (patch, meta["wiki"]["revid"], len(wiki), total, len(dividida), patch))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="usa os arquivos já baixados em data/robo/fonte/_baixado")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    catalogo = ler_catalogo()

    # 1. a base: a foto do patch do catálogo, da revisão que o Capítulo 1 registrou
    garantir_base(catalogo, a.offline)

    # 2. a fonte de hoje
    patch, wiki, ddragon, meta, lua = ler_fontes(a.offline)
    por_fora = contar_por_fora(lua)
    if por_fora != len(wiki):
        sys.exit("o leitor leu %d itens e o texto tem %d entradas: leitura pela metade, nada gravado" % (len(wiki), por_fora))
    pasta = os.path.join(AQUI, "fonte", patch)

    if patch == catalogo["meta"]["patch"]:
        # A foto do patch do catálogo é a BASE da regra e não se regrava (revisão da T74: uma
        # wiki que mudasse antes do Data Dragon trocar o patch apagava a mudança). O relatório
        # dele sai da própria base: diz o que a foto diz, contra o catálogo de agora.
        aviso = foto_e_base(pasta, patch, patch, meta)
        if aviso:
            print(aviso)
        if os.path.exists(os.path.join(pasta, "meta.json")):
            w0, dd0, m0 = ler_foto(patch)
            escrever_relatorio(patch, m0, w0, catalogo, dd0, m0["wiki"]["itens"])
            return
        gravar_foto(pasta, wiki, ddragon, meta, base=True)   # sem a revisão do Capítulo 1 registrada (ou sem rede)
        escrever_relatorio(patch, meta, wiki, catalogo, extrato_ddragon(ddragon), por_fora)
        return

    # 3. um patch mais novo: a foto se refaz enquanto a wiki se completa (nem se regrava se nada mudou)
    if foto_igual(pasta, meta):
        print("a foto do %s já é desta revisão da wiki e deste Data Dragon: nada a regravar" % patch)
        meta_da_foto = json.load(open(os.path.join(pasta, "meta.json"), encoding="utf-8"))
    else:
        gravar_foto(pasta, wiki, ddragon, meta)
        meta_da_foto = meta
    # F13-T78: o relatório diz a hora da foto, não a de hoje — sem foto nova ele não muda (o robô
    # roda todo dia no GitHub, e um commit só de data seria barulho)
    escrever_relatorio(patch, meta_da_foto, wiki, catalogo, extrato_ddragon(ddragon), por_fora)
    if not a.offline:
        gravar_conferido(meta)      # a leitura de hoje viu a wiki nesta revisão (a espera de 24 h conta até aqui)


def gravar_conferido(meta):
    """A última leitura boa que achou a wiki nesta revisão (fica em _baixado, fora do git): a
    espera de 24 h do aplicar_patch conta até ela, e não até a hora em que ele roda (4ª rodada)."""
    os.makedirs(BAIXADO, exist_ok=True)
    with open(os.path.join(BAIXADO, "conferido.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"patch": meta["patch"], "revid": meta["wiki"]["revid"], "revisao_de": meta["wiki"]["revisao_de"],
                   "sha256": meta["wiki"]["sha256"], "em": meta["lido_em"]}, f, ensure_ascii=False, indent=1)
        f.write("\n")


def revisao_do_capitulo1(caminho=CATALOGO_MD, patch=None):
    """A revisão do Module:ItemData/data que o Capítulo 1 usou para pôr o catálogo no `patch`
    (padrão: o do catálogo): a da seção "# Ajustes — reconciliação do patch 16.21.1 (…)" — a
    última, se houver duas. 4ª rodada: era a última citação do arquivo inteiro (um Ajuste fora
    de patch virava a base). 5ª rodada: o parágrafo com "`versions.json` = P" também não serve —
    a frase aparece nos Ajustes de sessão ("Patch conferido no início da sessão"), e a Fonte pode
    ficar noutro parágrafo da seção. Nenhuma revisão na seção, ou duas diferentes: None (o robô
    avisa e não aplica)."""
    if patch is None:
        patch = ler_catalogo()["meta"]["patch"]
    try:
        texto = open(caminho, encoding="utf-8").read()
    except OSError:
        return None
    secao, dentro = None, False
    for linha in texto.splitlines():
        if linha.startswith("# "):
            dentro = bool(re.match(r"# Ajustes\s*[—–-]\s*reconciliação do patch %s(?!\.?\d)" % re.escape(patch), linha))
            if dentro:
                secao = []
            continue
        if dentro:
            secao.append(linha)
    if secao is None:
        return None
    achadas = {int(x) for x in re.findall(r"`Module:ItemData/data` \(revisão (\d+)\)", "\n".join(secao))}
    return achadas.pop() if len(achadas) == 1 else None


def ler_revisao(revid):
    """Uma revisão antiga do módulo (a que o Capítulo 1 usou), para a foto base nascer dela."""
    api = json.loads(baixar(URL_WIKI_REVISAO.format(revid=revid), "itemdata_rev_%s.json" % revid, False))
    pagina = api["query"]["pages"][0]
    rev = pagina["revisions"][0]
    lua = rev["slots"]["main"]["content"]
    avisos = []
    return pagina, rev, lua, ler_modulo(lua, avisos), avisos


def foto_e_base(pasta, patch, patch_do_catalogo, meta):
    """Devolve o aviso (texto) quando a foto existente é a base e não pode ser regravada; senão ""."""
    caminho = os.path.join(pasta, "meta.json")
    if patch != patch_do_catalogo or not os.path.exists(caminho):
        return ""
    velha = json.load(open(caminho, encoding="utf-8"))
    if velha["wiki"]["revid"] == meta["wiki"]["revid"]:
        return ""
    return ("a foto do %s é a base da regra (wiki revisão %s) e não foi regravada; a wiki já está na revisão %s — "
            "o que mudou entra quando o Data Dragon trocar o patch" % (patch, velha["wiki"]["revid"], meta["wiki"]["revid"]))


def foto_igual(pasta, meta):
    """A foto guardada já é desta revisão da wiki e deste Data Dragon (regravar só mudaria a data)."""
    caminho = os.path.join(pasta, "meta.json")
    if not os.path.exists(caminho):
        return False
    velha = json.load(open(caminho, encoding="utf-8"))
    return velha["wiki"]["sha256"] == meta["wiki"]["sha256"] and velha["ddragon"]["versao"] == meta["ddragon"]["versao"]


def gravar_foto(pasta, wiki, ddragon, meta, base=False):
    """Grava a foto. A data da primeira foto do patch fica (a espera de 24 h do
    aplicar_patch conta dela); a base refeita começa de novo."""
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "meta.json")
    if not base and os.path.exists(caminho):
        meta["primeira_foto"] = json.load(open(caminho, encoding="utf-8")).get("primeira_foto") or meta.get("lido_em")
    else:
        meta.setdefault("primeira_foto", meta.get("lido_em"))
    with open(os.path.join(pasta, "wiki_itemdata.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(wiki, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(pasta, "meta.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
        f.write("\n")
    # do Data Dragon, só o que o robô compara: a foto fica pequena e a conta se refaz sem rede
    with open(os.path.join(pasta, "ddragon_itens.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(extrato_ddragon(ddragon), f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
