"""O robô dos cards (F13-T95): a prévia da build publicada no Discord.

Plano aprovado pelo Leo em 31/10/2026 (o robô novo a cada 30 min, "ok"; o desenho, a Bigorna).
F13-T98 (Leo, 01/11/2026: "os usuários gostaram mais do conceito 1"): o desenho passa a ser a Ficha
da build — o retrato, as runas, a ordem das habilidades, os iniciais, o Core, a bota e os situacionais.
Para cada build publicada, uma página estática em b/<id>/ com as etiquetas Open Graph (o que o
Discord lê para montar a prévia) e a imagem do card, b/<id>/card.jpg, fotografada do molde
data/robo/card.html num Chrome sem janela. Quem abre a página vai direto para #build/<id>, a build
no app. A build que saiu do servidor perde a página (o 404.html da raiz manda o link para o app,
que diz que ela não existe mais).

Só lê o servidor, com a chave pública (data/servidor.js), como o site. Só escreve em b/.
Refaz uma página só quando a build, o molde, o catálogo, as runas ou este script mudam (a assinatura fica
na própria página).

Uso:  python data/robo/cards.py                    (lê o servidor e atualiza b/)
      python data/robo/cards.py --json x.json      (as builds de um arquivo, no lugar do servidor)
      python data/robo/cards.py --saida pasta      (escreve em outra pasta, para testar)
      python data/robo/cards.py --so 70e0d5,f8b39b (só estas; não apaga nada)
Precisa de: Chrome instalado e `pip install websocket-client`.
"""
import argparse
import base64
import hashlib
import html
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import websocket

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
MOLDE = os.path.join(AQUI, "card.html")
SITE = "https://brelgo.github.io/forja/"
UA = "MontadorDeItens-robo-dos-cards/0.1 (https://brelgo.github.io/forja/)"
# o que o card mostra (e a assinatura acompanha): a Ficha mostra as runas e a ordem das habilidades
CAMPOS = ("id", "nome", "descricao", "campeao", "modo", "rota", "patch", "autor", "caixas", "runas", "habilidades")
ID_OK = re.compile(r"^[0-9a-f]{6}$")
ESPERA_MOLDE = 30   # segundos para o molde abrir no Chrome
ORCAMENTO = 14 * 60   # segundos de fotos por rodada: o resto fica para a próxima (o Actions corta o job em 20 min)
CHROMES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]


def ler_texto(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


def servidor():
    t = ler_texto(os.path.join(RAIZ, "data", "servidor.js"))
    url = re.search(r'url:\s*"([^"]+)"', t).group(1)
    chave = re.search(r'anonKey:\s*"([^"]+)"', t).group(1)
    return url, chave


def buscar_publicas():
    """Todas as builds, de página em página (o servidor corta em 1000 por pedido): só para quando
    uma página vem vazia. Qualquer resposta torta interrompe a rodada — e nada é apagado."""
    url, chave = servidor()
    lista = []
    while True:
        pedido = urllib.request.Request(
            "%s/rest/v1/builds_publicas?select=%s&order=id&limit=1000&offset=%d" % (url, ",".join(CAMPOS), len(lista)),
            headers={"apikey": chave, "Authorization": "Bearer " + chave, "User-Agent": UA})
        with urllib.request.urlopen(pedido, timeout=60) as r:
            parte = json.loads(r.read().decode("utf-8"))
        if not isinstance(parte, list):
            raise RuntimeError(("o servidor não devolveu uma lista: %r" % (parte,))[:200])
        if not parte:
            return lista
        lista += parte
        if len(lista) > 200000:
            raise RuntimeError("mais de 200 mil builds: o robô parou por segurança")


def base_da_assinatura():
    """O que, mudando, refaz todos os cards: o molde, o catálogo, as runas (a Ficha mostra os ícones
    delas, F13-T98) e este script."""
    h = hashlib.sha256()
    for c in (MOLDE, os.path.join(RAIZ, "data", "catalog.js"), os.path.join(RAIZ, "data", "runas.js"), os.path.abspath(__file__)):
        h.update(ler_texto(c).encode("utf-8"))
    return h.hexdigest()


def assinatura(build, base):
    dados = json.dumps({k: build.get(k) for k in CAMPOS}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((base + dados).encode("utf-8")).hexdigest()[:24]


def assinatura_gravada(pasta):
    try:
        t = ler_texto(os.path.join(pasta, "index.html"))
    except OSError:
        return None
    m = re.search(r'<meta name="forja:assinatura" content="([^"]*)">', t)
    return m.group(1) if m else None


def cortar(t, n):
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def pagina(build, info, ass, versao="", site=SITE):
    """A página b/<id>/index.html: as etiquetas da prévia e o caminho para a build no app. A versão
    (o ?v= da imagem) vem dos bytes do card.jpg: imagem nova, endereço novo — o Discord guarda a
    imagem pelo endereço."""
    i = build["id"]
    nome = cortar(build.get("nome") or "Build sem nome", 100)
    autor = cortar(build.get("autor"), 60)
    desc = cortar(info.get("quem"), 200)
    if autor:
        desc += (" · " if desc else "") + "por " + autor
    if cortar(build.get("descricao"), 200):
        desc += (" — " if desc else "") + cortar(build.get("descricao"), 200)
    desc = cortar(desc or "Uma build publicada na Forja, o montador de itens.", 200)
    e = lambda s: html.escape(s, quote=True)
    url = site + "b/" + i + "/"
    imagem = url + "card.jpg" + ("?v=" + versao if versao else "")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(nome)} · Forja</title>
<!-- Gerada pelo robô dos cards (data/robo/cards.py, F13-T95): não editar à mão. -->
<meta name="forja:assinatura" content="{e(ass)}">
<meta name="robots" content="noindex">
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#ff7a1e">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Forja · Montador de Itens de LoL">
<meta property="og:title" content="{e(nome)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(imagem)}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="O card da build {e(nome)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{e(url)}">
<meta http-equiv="refresh" content="0; url=../../#build/{i}">
<script>location.replace("../../#build/{i}");</script>
</head>
<body style="margin:0;padding:32px;background:#100d0b;color:#d8cbb6;font-family:Georgia,serif">
<p><a style="color:#ffd27a" href="../../#build/{i}">Abrir a build “{e(nome)}” na Forja</a></p>
</body>
</html>
"""


# ---------------------------------------------------------------- o Chrome sem janela
def achar_chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for c in CHROMES:
        if os.path.exists(c):
            return c
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if shutil.which(n):
            return shutil.which(n)
    sys.exit("Não achei o Chrome (ponha o caminho na variável CHROME).")


class Fotografo:
    def __init__(self):
        s = socket.socket(); s.bind(("127.0.0.1", 0)); porta = s.getsockname()[1]; s.close()
        self.perfil = tempfile.mkdtemp(prefix="cards-chrome-")
        args = [achar_chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--no-first-run",
                "--no-default-browser-check", "--force-device-scale-factor=1", "--window-size=1200,630",
                "--remote-debugging-port=%d" % porta, "--user-data-dir=" + self.perfil, "about:blank"]
        if sys.platform.startswith("linux"):
            args.insert(1, "--no-sandbox")   # o runner do GitHub não deixa o Chrome montar a caixa de areia
        self.ws = None
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # deu errado daqui em diante: o Chrome não fica órfão (com a porta aberta e o perfil no disco)
        try:
            alvo = None
            for _ in range(100):
                try:
                    with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % porta, timeout=2) as r:
                        alvo = next((t for t in json.loads(r.read()) if t.get("type") == "page"), None)
                    if alvo:
                        break
                except OSError:
                    pass
                time.sleep(0.2)
            if not alvo:
                raise RuntimeError("o Chrome não abriu a porta de depuração")
            # o desenho tem prazo de 15 s por coisa da rede (a arte, a splash, as fontes, os ícones)
            self.ws = websocket.create_connection(alvo["webSocketDebuggerUrl"], suppress_origin=True, timeout=120)
            self.n = 0
            self.envia("Emulation.setDeviceMetricsOverride", {"width": 1200, "height": 630, "deviceScaleFactor": 1, "mobile": False})
            self.envia("Page.enable")
            self.envia("Page.navigate", {"url": pathlib.Path(MOLDE).as_uri()})
            fim = time.time() + ESPERA_MOLDE
            while not self.js("typeof window.desenhar === 'function' && typeof CATALOG === 'object'"):
                if time.time() > fim:
                    raise RuntimeError("o molde não carregou (data/robo/card.html)")
                time.sleep(0.2)
        except BaseException:
            self.fechar()
            raise

    def envia(self, metodo, params=None):
        self.n += 1
        meu = self.n
        self.ws.send(json.dumps({"id": meu, "method": metodo, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == meu:
                if "error" in m:
                    raise RuntimeError("%s: %s" % (metodo, m["error"]))
                return m.get("result", {})

    def js(self, expr, esperar=False):
        r = self.envia("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": esperar})
        if r.get("exceptionDetails"):
            raise RuntimeError("erro no molde: %s" % r["exceptionDetails"].get("exception", {}).get("description", r["exceptionDetails"]))
        return r.get("result", {}).get("value")

    def card(self, build):
        info = self.js("desenhar(%s)" % json.dumps(build), esperar=True)
        foto = self.envia("Page.captureScreenshot", {"format": "jpeg", "quality": 88,
                                                     "clip": {"x": 0, "y": 0, "width": 1200, "height": 630, "scale": 1}})["data"]
        return info, base64.b64decode(foto)

    def fechar(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        shutil.rmtree(self.perfil, ignore_errors=True)


# ---------------------------------------------------------------- a rodada
def falta_algo(build, info):
    """A foto saiu sem uma peça da rede: um ícone, a arte do campeão, as fontes do molde ou o que o
    molde anota em "faltou" (as habilidades do campeão para a ordem, o retrato)."""
    return bool(info.get("quebradas") or (build.get("campeao") and not info.get("arte")) or not info.get("fontes")
                or info.get("faltou"))


def rodar(builds, saida, so=None, apagar=True, orcamento=ORCAMENTO):
    os.makedirs(saida, exist_ok=True)
    base = base_da_assinatura()
    builds = [b for b in builds if isinstance(b, dict) and ID_OK.match(str(b.get("id") or ""))]
    if so:
        builds = [b for b in builds if b["id"] in so]
    contas = {"novas": [], "refeitas": [], "iguais": 0, "incompletas": [], "falhas": [], "adiadas": [], "apagadas": []}
    inicio = time.time()
    fila = []
    for b in builds:
        ass = assinatura(b, base)
        if assinatura_gravada(os.path.join(saida, b["id"])) == ass:
            contas["iguais"] += 1
        else:
            fila.append((b, ass))
    if fila:
        foto = Fotografo()
        try:
            for k, (b, ass) in enumerate(fila):
                # a rede pendurada faz cada foto esperar os prazos: passou do orçamento, o que falta fica
                # para a próxima rodada e o que ficou pronto vai para o commit
                if time.time() - inicio > orcamento:
                    contas["adiadas"] = [x["id"] for x, _ in fila[k:]]
                    break
                pasta = os.path.join(saida, b["id"])
                # cada build por si: a que quebrar (um dado torto, a rede pendurada) fica de fora desta
                # rodada e as outras seguem; o Chrome é reaberto, que a conversa com ele pode ter parado no meio
                try:
                    info, jpg = foto.card(b)
                    if falta_algo(b, info):
                        if not info.get("fontes"):
                            # a falha da fonte fica gravada na página (a folha e cada rosto são pedidos uma
                            # vez só): a segunda tentativa vai num Chrome novo
                            foto.fechar()
                            foto = Fotografo()
                        info, jpg = foto.card(b)      # uma segunda tentativa: a rede piscou
                except Exception as erro:
                    contas["falhas"].append("%s (%s: %s)" % (b["id"], type(erro).__name__, str(erro)[:120]))
                    foto.fechar()
                    foto = Fotografo()
                    continue
                incompleta = falta_algo(b, info)
                tinha_card = os.path.exists(os.path.join(pasta, "card.jpg"))
                os.makedirs(pasta, exist_ok=True)
                if incompleta:
                    contas["incompletas"].append(b["id"])
                if not (incompleta and tinha_card):   # a incompleta não troca o card que já estava
                    with open(os.path.join(pasta, "card.jpg"), "wb") as f:
                        f.write(jpg)
                    contas["refeitas" if tinha_card else "novas"].append(b["id"])
                with open(os.path.join(pasta, "card.jpg"), "rb") as f:
                    versao = hashlib.sha256(f.read()).hexdigest()[:10]
                # a página sempre (os textos da build como ela está); a incompleta grava outra
                # assinatura, para a próxima rodada tentar a foto de novo
                with open(os.path.join(pasta, "index.html"), "w", encoding="utf-8", newline="\n") as f:
                    f.write(pagina(b, info, ("incompleta-" if incompleta else "") + ass, versao))
        finally:
            foto.fechar()
    if apagar and not so:
        ids = {b["id"] for b in builds}
        velhas = [d for d in os.listdir(saida) if ID_OK.match(d) and os.path.isdir(os.path.join(saida, d)) and d not in ids]
        if velhas and not ids:
            print("aviso: o servidor respondeu sem nenhuma build — nada foi apagado")
        else:
            for d in velhas:
                shutil.rmtree(os.path.join(saida, d))
                contas["apagadas"].append(d)
    return contas


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", help="as builds de um arquivo, no lugar do servidor")
    ap.add_argument("--saida", default=os.path.join(RAIZ, "b"), help="a pasta das páginas (padrão: b/ na raiz)")
    ap.add_argument("--so", help="só estes ids (separados por vírgula); não apaga nada")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.json:
        with open(a.json, encoding="utf-8") as f:
            builds = json.load(f)
    else:
        builds = buscar_publicas()
    so = set(a.so.split(",")) if a.so else None
    c = rodar(builds, a.saida, so)
    print("cards: %d novos · %d refeitos · %d iguais · %d apagados · incompletos: %s · falhas: %d · adiados: %d" % (
        len(c["novas"]), len(c["refeitas"]), c["iguais"], len(c["apagadas"]), ", ".join(c["incompletas"]) or "nenhum", len(c["falhas"]), len(c["adiadas"])))
    for k in ("novas", "refeitas", "apagadas", "falhas", "adiadas"):
        if c[k]:
            print("  %s: %s" % (k, ", ".join(c[k])))
    # no Actions, o aviso aparece no resumo da rodada (a rodada segue verde: o resto foi gravado)
    if os.environ.get("GITHUB_ACTIONS"):
        for f in c["falhas"]:
            print("::warning title=Card não feito::%s" % f)
        if c["adiadas"]:
            print("::warning title=Cards para a próxima rodada::%d builds (a rodada passou do tempo)" % len(c["adiadas"]))
        if c["incompletas"]:
            print("::warning title=Cards incompletos::%s (sem a arte, um ícone, as fontes, o retrato ou as habilidades; a próxima rodada tenta de novo)" % ", ".join(c["incompletas"]))


if __name__ == "__main__":
    main()
