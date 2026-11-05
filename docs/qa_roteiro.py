#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Roteiro de QA do Montador de Itens — os caminhos de sempre, percorridos a cada mudança.

    python docs/qa_roteiro.py            # o app desta pasta
    python docs/qa_roteiro.py --site     # o que está no ar, no GitHub Pages
    python docs/qa_roteiro.py -k marcador   # só as checagens com essa palavra

Por que ele existe: em 20/09/2026 dois bugs foram parar no ar e quem achou foi o
Leo — a aba Públicas vazia e os marcadores mudos. Nenhum dos dois era difícil de
pegar: bastava abrir o app e percorrer o de sempre. O roteiro faz isso com
clique de verdade (CDP), porque evento sintético já passou com bug no drag e no
duplo clique.

Ele não substitui o olho: mede o que dá para medir e cala sobre o resto.
Captura de tela e aprovado continuam por fora.

Precisa de: Chrome instalado e `pip install websocket-client`.
"""
import argparse
import atexit
import base64
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

import websocket

# O console do Windows nasce em cp1252 e engasga no primeiro acento do relatório.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://brelgo.github.io/forja/"   # o site virou "forja" em 30/10/2026 (o endereço montador_de_itens_lol só redireciona)
CHROMES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
]
# O Leo abre o app nestas três, nesta ordem de prioridade (20/09/2026). A quarta
# é um piso: notebook comum, conferido mas sem prioridade.
# Celular NÃO é alvo (Leo, 21/09/2026: "não tenho a intenção de fazer para o
# celular") — o app é ferramenta de mesa, e 375px nem entra na conta.
RESOLUCOES = [(2560, 1440), (1920, 1080), (1600, 900), (1280, 800)]
# F13-T99: a entrada da loja sorteia a região a cada visita; ?entrada=<regiao> força uma. A marca é um
# elemento que só o desenho daquela região gera (prova que ela foi montada e desenhada).
REGIOES_ENTRADA = ["freljord", "noxus", "shurima"]
NOME_REGIAO = {"freljord": "Freljord", "noxus": "Noxus", "shurima": "Shurima"}
MARCA_REGIAO = {"freljord": "en-pinheiros", "noxus": "en-torres", "shurima": "en-ruinas"}

VERDE, VERMELHO, AMARELO, CINZA, FIM = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m"


# ---------------------------------------------------------------- resultado
class Placar:
    def __init__(self):
        self.linhas = []

    def conta(self, grupo, nome, ok, detalhe="", pulou=False):
        self.linhas.append((grupo, nome, ok, detalhe, pulou))
        marca = (AMARELO + "–" + FIM) if pulou else ((VERDE + "ok" + FIM) if ok else (VERMELHO + "FALHOU" + FIM))
        print("  %-6s %-44s %s%s%s" % (marca, nome, CINZA, detalhe, FIM))

    @property
    def falhas(self):
        return [l for l in self.linhas if not l[2] and not l[4]]

    def resumo(self):
        passou = sum(1 for l in self.linhas if l[2] and not l[4])
        pulou = sum(1 for l in self.linhas if l[4])
        print("\n" + "=" * 78)
        if self.falhas:
            print("%sFALHOU: %d de %d%s" % (VERMELHO, len(self.falhas), len(self.linhas), FIM))
            for g, n, _, d, _ in self.falhas:
                print("  %s · %s — %s" % (g, n, d))
        else:
            print("%s%d checagens, nenhuma falha%s%s" % (VERDE, passou, (", %d pulada(s)" % pulou) if pulou else "", FIM))
        return 1 if self.falhas else 0


# ---------------------------------------------------------------- servidor
# F13-T95: páginas que o roteiro serve sem gravar no disco (a b/<id>/ que o robô dos cards gera)
PAGINAS_EXTRAS = {}


class Servidor:
    """Serve a pasta do projeto numa porta livre, só para o roteiro. Como o GitHub Pages, o
    endereço que não existe recebe o 404.html da raiz (F13-T95)."""

    def __init__(self):
        import http.server
        s = socket.socket(); s.bind(("127.0.0.1", 0)); self.porta = s.getsockname()[1]; s.close()

        class Mudo(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **k):
                super().__init__(*a, directory=RAIZ, **k)

            def log_message(self, *a, **k):
                pass                      # o relatório é o que importa, não o log

            def handle_one_request(self):
                try:
                    super().handle_one_request()
                except ConnectionError:
                    self.close_connection = True   # o Chrome corta conexão à vontade

            def _manda(self, codigo, corpo):
                self.send_response(codigo)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(corpo)

            def do_GET(self):
                if self.path.startswith("/__pendura"):
                    time.sleep(6)         # F13-T95: o prazo do molde contra quem não responde
                    return self._manda(204, b"")
                extra = PAGINAS_EXTRAS.get(self.path.split("?")[0].split("#")[0])
                if extra is not None:
                    return self._manda(200, extra.encode("utf-8"))
                return super().do_GET()

            def send_error(self, code, message=None, explain=None):
                pagina = os.path.join(RAIZ, "404.html")
                if code == 404 and self.command == "GET" and os.path.exists(pagina):
                    with open(pagina, "rb") as f:
                        return self._manda(404, f.read())
                return super().send_error(code, message, explain)

        handler = Mudo
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", self.porta), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d/" % self.porta

    def parar(self):
        self.httpd.shutdown()


TIPOS = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml",
         ".mp3": "audio/mpeg", ".woff2": "font/woff2", ".ico": "image/x-icon", ".txt": "text/plain; charset=utf-8"}


def pages_falso(url):
    """F13-T95: o GitHub Pages de mentira para https://brelgo.github.io/forja/… — os arquivos desta
    pasta, as páginas de PAGINAS_EXTRAS e, no que não existe, o 404.html da raiz com status 404
    (como o Pages faz). Com ele, a aba roda o app no endereço do site sem sair do disco."""
    from urllib.parse import urlsplit, unquote
    caminho = "/" + unquote(urlsplit(url).path).lstrip("/")      # o Pages junta as barras do começo
    if caminho in PAGINAS_EXTRAS:
        return 200, PAGINAS_EXTRAS[caminho].encode("utf-8"), TIPOS[".html"]
    if caminho.startswith("/forja/"):
        rel = caminho[len("/forja/"):]
        if rel == "" or rel.endswith("/"):
            rel += "index.html"
        partes = rel.split("/")
        arq = os.path.join(RAIZ, *partes)
        if ".." not in partes and os.path.isfile(arq):
            with open(arq, "rb") as f:
                return 200, f.read(), TIPOS.get(os.path.splitext(arq)[1].lower(), "application/octet-stream")
    with open(os.path.join(RAIZ, "404.html"), "rb") as f:
        return 404, f.read(), TIPOS[".html"]


def ligar_site_falso(r):
    """A aba passa a buscar https://brelgo.github.io/… no pages_falso (CDP Fetch)."""
    r.site_falso = pages_falso
    r.envia("Fetch.enable", {"patterns": [{"urlPattern": "https://brelgo.github.io/*", "requestStage": "Request"}]})


# ---------------------------------------------------------------- navegador
class Sessao:
    def __init__(self, url):
        chrome = next((c for c in CHROMES if os.path.exists(c)), None)
        if not chrome:
            sys.exit("Não achei o Chrome. Ajuste CHROMES no topo do arquivo.")
        s = socket.socket(); s.bind(("127.0.0.1", 0)); porta = s.getsockname()[1]; s.close()
        self.porta = porta
        import tempfile
        # perfil próprio: dois Chromes no mesmo user-data-dir e o segundo não sobe
        perfil = tempfile.mkdtemp(prefix="qa-montador-")
        self.proc = subprocess.Popen(
            [chrome, "--headless=new", "--mute-audio", "--remote-debugging-port=%d" % porta, "--user-data-dir=" + perfil,
             "--window-size=1920,1080", "--no-first-run", "--hide-scrollbars", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        atexit.register(self.fechar)
        alvo = None
        for _ in range(80):
            try:
                alvo = [t for t in json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % porta))
                        if t["type"] == "page"][0]
                break
            except Exception:
                time.sleep(0.25)
        if not alvo:
            sys.exit("O Chrome não respondeu na porta de depuração.")
        self.ws = websocket.create_connection(alvo["webSocketDebuggerUrl"], suppress_origin=True)
        self.ws.settimeout(90)
        self._id = 0
        self.erros = []
        self.rede = []
        self.dialogos = []
        self.site_falso = None   # F13-T95: ligar_site_falso
        self.envia("Page.enable"); self.envia("Runtime.enable"); self.envia("Log.enable")
        self._barra_eventos()
        self.url = url

    # F13-T56: o roteiro não conta impressão, visualização nem cópia no servidor de
    # verdade. Antes, cada rodada (perfil novo, memória limpa) registrava uma
    # "impressao" por build da aba Públicas no Supabase do Leo. O registrar_evento
    # responde "ok" sem sair da página, em toda carga e em toda aba.
    BARREIRA = r"""(() => { const f = window.fetch; window.__eventosBarrados = 0;
      window.fetch = function (u, ...a) {
        if (String(u && u.url || u).includes('/rpc/registrar_evento')) { window.__eventosBarrados++;
          return Promise.resolve(new Response('null', { status: 200, headers: { 'Content-Type': 'application/json' } })); }
        return f.call(this, u, ...a); };
      try { if (sessionStorage.getItem('qa.dicas') !== '1') localStorage.setItem('dicas.desligadas', '1'); } catch (e) {} })();"""

    def _barra_eventos(self):
        self.envia("Page.addScriptToEvaluateOnNewDocument", {"source": Sessao.BARREIRA})

    def fechar(self):
        try: self.proc.kill()
        except Exception: pass

    def nova_aba(self):
        """Uma segunda aba no MESMO Chrome — mesmo perfil, mesmo localStorage, e o
        evento "storage" chega de uma para a outra (F13-T35, duas abas abertas)."""
        req = urllib.request.Request("http://127.0.0.1:%d/json/new?about:blank" % self.porta, method="PUT")
        alvo = json.load(urllib.request.urlopen(req))
        outra = object.__new__(Sessao)
        outra.proc = None
        outra.porta = self.porta
        outra.ws = websocket.create_connection(alvo["webSocketDebuggerUrl"], suppress_origin=True)
        outra.ws.settimeout(90)
        outra._id = 0; outra.erros = []; outra.rede = []; outra.dialogos = []
        outra.envia("Page.enable"); outra.envia("Runtime.enable"); outra.envia("Log.enable")
        outra._barra_eventos()
        outra.url = self.url
        outra.alvo_id = alvo["id"]
        return outra

    def fechar_aba(self):
        """Fecha a aba de verdade (não só a conexão): aberta, ela continua ouvindo o
        localStorage e reage aos grupos seguintes do roteiro."""
        try: self.ws.close()
        except Exception: pass
        try: urllib.request.urlopen("http://127.0.0.1:%d/json/close/%s" % (self.porta, self.alvo_id)).read()
        except Exception: pass

    def envia(self, metodo, params=None):
        self._id += 1
        meu = self._id   # F13-T95: o _anota também manda comandos (e sobe o _id) enquanto este espera
        self.ws.send(json.dumps({"id": meu, "method": metodo, "params": params or {}}))
        while True:
            try:
                msg = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException:
                # Acontece de verdade: com a lista pública cheia, o renderizador
                # some por mais de um minuto. Vira falha legível, não pilha.
                raise RuntimeError("o navegador parou de responder em %s" % metodo)
            if msg.get("id") == meu:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})
            self._anota(msg)

    def _anota(self, msg):
        if msg.get("method") == "Fetch.requestPaused":
            # F13-T95: o pedido ao site responde aqui (o GitHub Pages de mentira); o resto segue
            p = msg["params"]
            self._id += 1
            if self.site_falso:
                resposta = self.site_falso(p["request"]["url"])
                if resposta is None:
                    return        # o pedido fica parado: um servidor que não responde
                st, corpo, tipo = resposta
                self.ws.send(json.dumps({"id": self._id, "method": "Fetch.fulfillRequest", "params": {
                    "requestId": p["requestId"], "responseCode": st, "responseHeaders": [{"name": "Content-Type", "value": tipo}],
                    "body": base64.b64encode(corpo).decode("ascii")}}))
            else:
                self.ws.send(json.dumps({"id": self._id, "method": "Fetch.continueRequest", "params": {"requestId": p["requestId"]}}))
            return
        if msg.get("method") == "Page.javascriptDialogOpening":
            # Um diálogo nativo (confirm, alert, "sair sem salvar?") trava a
            # página inteira até alguém responder: o roteiro via só "o navegador
            # parou de responder". Agora ele anota qual foi e aceita.
            d = msg["params"]
            self.dialogos.append("%s: %s" % (d.get("type"), (d.get("message") or "")[:80]))
            self._id += 1
            self.ws.send(json.dumps({"id": self._id, "method": "Page.handleJavaScriptDialog",
                                     "params": {"accept": True}}))
            return
        if msg.get("method") == "Runtime.exceptionThrown":
            self.erros.append((msg["params"]["exceptionDetails"].get("text") or "")[:160])
        elif msg.get("method") == "Log.entryAdded":
            e = msg["params"]["entry"]
            if e.get("level") == "error":
                # 404 de arquivo é bug de publicação: o Pages é case-sensitive.
                alvo = e.get("url") or ""
                self.rede.append("%s %s" % (e.get("text", "")[:80], alvo))

    def js(self, expr):
        r = self.envia("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in r:
            # "Uncaught" sozinho não diz nada: a mensagem de verdade mora em exception.description
            d = r["exceptionDetails"]
            desc = ((d.get("exception") or {}).get("description") or d.get("text") or "erro no JS").split(chr(10))[0]
            raise RuntimeError(desc + " :: " + expr[:80])
        return r["result"].get("value")

    def abrir(self, caminho=""):
        self.envia("Page.navigate", {"url": self.url + caminho})
        fim = time.time() + 30
        while time.time() < fim:
            try:
                msg = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException:
                raise RuntimeError("a página não carregou: %s" % (self.url + caminho)[:90])
            self._anota(msg)
            if msg.get("method") == "Page.loadEventFired":
                return
        raise RuntimeError("a página não terminou de carregar")

    def caixa(self, seletor):
        # Rolar só quando precisa: um scrollIntoView à toa fecha menu ancorado
        # (que escuta scroll de propósito) e o clique seguinte cai no vazio.
        return self.js("""(() => { const e = document.querySelector(%s); if (!e) return null;
          let r = e.getBoundingClientRect();
          if (r.top < 4 || r.bottom > innerHeight - 4 || r.left < 4 || r.right > innerWidth - 4) {
            e.scrollIntoView({block:'center'}); r = e.getBoundingClientRect();
          }
          if (r.width < 1 || r.height < 1) return 'invisivel';
          return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)]; })()""" % json.dumps(seletor))

    def hover(self, seletor):
        p = self.caixa(seletor)
        if not isinstance(p, list):
            raise RuntimeError("não achei (ou tem tamanho zero): " + seletor)
        self.envia("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": p[0], "y": p[1]})
        time.sleep(0.25)
        return p

    def clicar(self, seletor, espera=0.4, na_hora=False):
        """Clique de verdade. O mouseMoved antes não é enfeite: sem ele, controle
        que só existe no hover tem tamanho zero e o clique cai no vazio.
        F13-T73: antes de medir, espera acabar a animação finita no caminho do
        elemento (ele ou quem o contém). O painel que acaba de abrir desenrola
        (modal-unroll, 0,25 s) e o hover mede, espera 0,25 s e clica: o botão já
        estava em outro lugar e o clique caía no painel — o "Usar esta aba" do grupo
        "duas abas" falhava um roteiro sim, outro não (o diário da aba mostrou).
        `na_hora`: o teste que precisa do clique já (no meio da conferência da trava)."""
        if not na_hora:
            self.js("""(async () => { const el = document.querySelector(%s); if (!el) return 0;
              const correndo = () => document.getAnimations().some(a => a.playState === 'running' && a.effect && a.effect.target
                && a.effect.target.contains && a.effect.target.contains(el) && a.effect.getTiming().iterations !== Infinity);
              const fim = Date.now() + 2000;
              while (Date.now() < fim && correndo()) await new Promise(r => setTimeout(r, 30));
              return 1; })()""" % json.dumps(seletor))
        p = self.hover(seletor)
        for tipo in ("mousePressed", "mouseReleased"):
            self.envia("Input.dispatchMouseEvent",
                       {"type": tipo, "x": p[0], "y": p[1], "button": "left", "clickCount": 1})
        time.sleep(espera)

    def tela(self, largura, altura):
        self.envia("Emulation.setDeviceMetricsOverride",
                   {"width": largura, "height": altura, "deviceScaleFactor": 1, "mobile": False})
        time.sleep(0.6)

    def tela_normal(self):
        self.envia("Emulation.clearDeviceMetricsOverride")

    def captura(self, destino, altura=900):
        dados = self.envia("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                           "clip": {"x": 0, "y": 0, "width": 1920, "height": altura, "scale": 1}})["data"]
        with open(destino, "wb") as f:
            f.write(base64.b64decode(dados))

    # ------- atalhos do app
    def entrar(self):
        # F13-T69: espera a trava das abas decidir antes de entrar. Enquanto confere,
        # a página fica parada (é a proteção) e, desde a F13-T68, sem o véu escuro na
        # frente — um clique nessa hora não faria nada, sem nada na tela dizer por quê.
        fim = time.time() + 6
        while time.time() < fim and self.js("typeof decidido !== 'undefined' && !decidido"):
            time.sleep(0.1)
        self.js("document.getElementById('entrar').click(); document.documentElement.style.scrollBehavior='auto'")
        # F13-T97: a entrada é o posto de troca do Freljord, que abre animado (~2,1 s; 0,85 s com
        # menos movimento) — espera ela fechar de fato, em vez do 1,8 s fixo da placa antiga
        fim = time.time() + 5
        while time.time() < fim and not self.js("(() => { const e = document.getElementById('entrada'); return !e || e.classList.contains('fechada'); })()"):
            time.sleep(0.1)

    def limpar_memoria(self):
        self.js("localStorage.clear()")
        self.abrir()
        time.sleep(0.8)

    def nova_build(self):
        self.js("switchTab('build'); showBuildScreen('lista')")
        time.sleep(0.5)
        self.js("document.getElementById('new-build').click()")
        time.sleep(1.2)
        self.js("showBuildScreen('forja')")
        time.sleep(0.8)


# ---------------------------------------------------------------- 1. arquivos
def checar_arquivos(p):
    """O que dá para conferir sem abrir o navegador. O Pages é case-sensitive e
    não perdoa nome com uma letra diferente."""
    print("\n%sARQUIVOS%s" % (AMARELO, FIM))
    idx = open(os.path.join(RAIZ, "index.html"), encoding="utf-8").read()

    p.conta("arquivos", ".nojekyll existe", os.path.exists(os.path.join(RAIZ, ".nojekyll")))

    absolutos = re.findall(r'(?:src|href)="(/[^/][^"]*)"', idx)
    p.conta("arquivos", "nenhum caminho absoluto", not absolutos, ", ".join(absolutos[:3]))

    # todo assets/... citado no HTML e no CSS existe, com a mesma caixa de letra
    # Trecho montado em JS (`${...}`) ou com curinga não é arquivo: fica de fora.
    citados = sorted({c for c in re.findall(r'["\'\(](assets/[^"\'\)\s]+)', idx)
                      if "${" not in c and "*" not in c})
    faltando = [c for c in citados if not _existe_exato(c)]
    p.conta("arquivos", "assets citados existem (caixa exata)", not faltando,
            "%d citados; faltam: %s" % (len(citados), ", ".join(faltando[:3]) or "nenhum"))

    # áudio: o mapa vive no index.html e os arquivos na pasta do Leo
    mapa = re.search(r"const SOM_ARQUIVOS = (\{.*?\n\});", idx, re.S)
    if mapa:
        arquivos = sorted({v for lista in json.loads(mapa.group(1)).values() for v in lista})
        sumidos = [a for a in arquivos if not _existe_exato("assets/audio/" + a)]
        p.conta("arquivos", "áudio do mapa existe em assets/audio", not sumidos,
                "%d arquivos; sumiram: %s" % (len(arquivos), ", ".join(sumidos[:3]) or "nenhum"))
    else:
        p.conta("arquivos", "áudio do mapa existe em assets/audio", False, "não achei SOM_ARQUIVOS no index.html")

    # cards de região: o data/regioes.js aponta, a pasta tem de ter
    reg = os.path.join(RAIZ, "data", "regioes.js")
    if os.path.exists(reg):
        corpo = open(reg, encoding="utf-8").read()
        bloco = corpo.split("medidas:", 1)[1].split("variantes:", 1)[0]
        cards = ["assets/regioes/cards/%s.jpg" % n for n in re.findall(r'"([^"]+)":\s*\[', bloco)]
        sumidos = [c for c in cards if not _existe_exato(c)]
        p.conta("arquivos", "cards de região existem", not sumidos,
                "%d cards; sumiram: %s" % (len(cards), ", ".join(sumidos[:2]) or "nenhum"))

    # F13-T61: o data/mudancas.js é o que o gerar_mudancas.py gera agora — esquecer
    # de rodar o gerador depois de trocar o catálogo deixaria a regra de
    # desatualizada lendo o registro velho (e o app caindo na regra antiga)
    import subprocess, tempfile
    tmp = os.path.join(tempfile.gettempdir(), "qa_mudancas_%d.js" % os.getpid())
    try:
        subprocess.run([sys.executable, os.path.join(RAIZ, "data", "gerar_mudancas.py"), tmp], capture_output=True, check=True)
        igual = open(tmp, "rb").read() == open(os.path.join(RAIZ, "data", "mudancas.js"), "rb").read()
        det = "igual ao que o gerar_mudancas.py gera" if igual else "diferente: rode python data/gerar_mudancas.py"
    except Exception as e:
        igual, det = False, "%s: %s" % (type(e).__name__, str(e)[:90])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    p.conta("arquivos", "o registro de mudanças está em dia com o catálogo", igual, det)

    # F13-T87: o supabase.sql é o banco inteiro na forma de hoje — colar de novo não
    # pode derrubar as Públicas (antes: view sem runas/habilidades/rota, grant por
    # coluna faltando, um segundo publicar_build). Confere o arquivo contra a página.
    sql = open(os.path.join(RAIZ, "docs", "servidor", "supabase.sql"), encoding="utf-8").read()
    furos = sql_cobre_a_pagina(sql, idx)
    p.conta("arquivos", "o supabase.sql cobre o que a página manda e lê", not furos, "; ".join(furos[:4]) or "funções, view e grant")

    # F13-T88: o limite de 5 por IP mora no registrar_evento do supabase.sql — some se
    # alguém recriar a função sem ele (e as duas tabelas não podem abrir para o público)
    reg = re.search(r"create or replace function public\.registrar_evento\(.*?end \$\$;", sql, re.S)
    corpo = reg.group(0) if reg else ""
    faltam = [x for x, ok in (("cf-connecting-ip", "cf-connecting-ip" in corpo), ("eventos_por_ip", "eventos_por_ip" in corpo),
                              ("o teto 5", re.search(r"if v_n > 5 then return;", corpo) is not None),
                              ("o sal do dia", "sal_do_dia" in corpo),
                              ("o revoke das tabelas", re.search(r"revoke all on public\.sal_do_dia, public\.eventos_por_ip from anon, authenticated;", sql) is not None))
              if not ok]
    p.conta("arquivos", "o supabase.sql tem o limite de 5 por IP no registrar_evento", not faltam, "falta: " + ", ".join(faltam) if faltam else "cf-connecting-ip, teto 5, sal do dia, tabelas fechadas")


def sql_cobre_a_pagina(sql, idx):
    """O que falta no SQL para a página funcionar: cada função chamada criada uma vez
    só e com todos os parâmetros que a página manda; a builds_publicas com todas as
    colunas da tabela menos o hash; e o grant por coluna com as mesmas."""
    furos = []
    sem_coment = re.sub(r"--[^\n]*", "", sql)
    chamadas = {"publicar_build": set(re.findall(r"\b(p_\w+):", (re.search(r"const params = \{(.*?)\n    \};", idx, re.S) or [None, ""])[1]))}
    for f, corpo in re.findall(r'Servidor\.rpc\("(\w+)", \{([^}]*)\}', idx):
        chamadas.setdefault(f, set()).update(re.findall(r"\b(p_\w+):", corpo))
    for f, pars in sorted(chamadas.items()):
        criadas = re.findall(r"create or replace function public\.%s\((.*?)\)\s*returns" % f, sem_coment, re.S)
        if len(criadas) != 1:
            furos.append("%s criada %d vezes" % (f, len(criadas)))
            continue
        falta = sorted(pars - set(re.findall(r"\b(p_\w+)\s", criadas[0])))
        if falta:
            furos.append("%s sem %s" % (f, ", ".join(falta)))
    tab = re.search(r"create table if not exists public\.builds \((.*?)\n\);", sem_coment, re.S)
    colunas = set(re.findall(r"^\s+(\w+)\s+(?:text|jsonb|integer|timestamptz)\b", tab.group(1), re.M)) if tab else set()
    colunas |= set(re.findall(r"alter table public\.builds add column if not exists (\w+)", sem_coment))
    publicas = colunas - {"segredo_hash"}
    view = re.search(r"create view public\.builds_publicas.*?from public\.builds b;", sem_coment, re.S)
    na_view = set(re.findall(r"\bb\.(\w+)", view.group(0))) if view else set()
    # o que a página publica tem de voltar pela view (p_runas → runas, p_rota → rota…)
    publicas |= {x[2:] for x in chamadas.get("publicar_build", set())} - {"segredo", "id"}
    if not view or publicas - na_view or "segredo_hash" in na_view:
        furos.append("builds_publicas sem %s" % (", ".join(sorted(publicas - na_view)) or "a view"))
    grant = re.search(r"grant select \(([^)]*)\)\s+on public\.builds to anon", sem_coment)
    no_grant = {c.strip() for c in grant.group(1).split(",")} if grant else set()
    if na_view - no_grant or "segredo_hash" in no_grant:
        furos.append("grant por coluna sem %s" % ", ".join(sorted(na_view - no_grant)))
    return furos


def _existe_exato(rel):
    """os.path.exists mente no Windows: 'Assets/X.PNG' passa. Aqui cada pedaço do
    caminho é conferido contra o que a pasta realmente tem."""
    atual = RAIZ
    for pedaco in rel.split("?")[0].split("#")[0].split("/"):
        if not pedaco:
            continue
        try:
            nomes = os.listdir(atual)
        except (NotADirectoryError, FileNotFoundError):
            return False
        if pedaco not in nomes:
            return False
        atual = os.path.join(atual, pedaco)
    return True


# ---------------------------------------------------------------- 2. o app
def checar_fundacao(s, p):
    print("\n%sFUNDAÇÃO%s" % (AMARELO, FIM))
    s.limpar_memoria()
    n = s.js("CATALOG.items.length")
    p.conta("fundação", "225 itens no catálogo", n == 225, "vieram %s" % n)
    # Contadas pela estrutura e conferidas contra o número que o gerador anotou:
    # foi um leitor calado que deixou 4 runas de fora em 18/09/2026.
    r = s.js("""(() => { const n = RUNAS.trilhas.reduce((a, t) =>
        a + t.slots.reduce((b, sl) => b + sl.runas.length, 0), 0);
      return { contadas: n, meta: RUNAS.meta.runas,
               frag: RUNAS.fragmentos.reduce((a, g) => a + g.runas.length, 0),
               metaFrag: RUNAS.meta.fragmentos }; })()""")
    p.conta("fundação", "runas contadas batem com o gerador",
            r["contadas"] == r["meta"] and r["frag"] == r["metaFrag"],
            "%s runas (gerador diz %s), %s fragmentos (diz %s)"
            % (r["contadas"], r["meta"], r["frag"], r["metaFrag"]))
    patch = s.js("CATALOG.meta && CATALOG.meta.patch")
    p.conta("fundação", "o catálogo diz de que patch é", bool(patch), "patch %s" % patch)
    # F13-T54 (Leo, 19/10/2026): a placa de entrada diz que é hobby e como falar
    # com o autor — escrito, à vista, e a placa inteira cabe na tela.
    # F13-T97: a placa é a de madeira do posto de troca (título na madeira, o resto no pergaminho
    # pregado nela, a nota na etiqueta de baixo); F13-T99: ou a chapa de ferro de Noxus, ou a tábua com o
    # papiro de Shurima — as três com as mesmas classes. Cada canal tem o nome e o ID na mesma linha; a
    # letra conta como aparece (a computada vezes a escala do palco e da câmera): rótulos ≥ 10 px,
    # nota e IDs ≥ 12 px nas quatro resoluções.
    le = """(() => { const pl = document.querySelector('.entrada-placa'), t = pl ? pl.innerText.replace(/\\s+/g, ' ') : '';
      const grupo = pl && pl.parentElement, nota = document.querySelector('.entrada-nota');
      const ids = [...document.querySelectorAll('.entrada-contato .ea-id')].map(b => b.textContent + ':' + getComputedStyle(b).userSelect);
      const dentro = e => { if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight; };
      const canais = [...document.querySelectorAll('.entrada-contato .ea-canal')].map(c => { const n = c.querySelector('.ea-nome'), i = c.querySelector('.ea-id');
        if (!n || !i) return false; const a = n.getBoundingClientRect(), b = i.getBoundingClientRect();
        return a.top < b.bottom && b.top < a.bottom && a.right <= b.left + 1 && c.scrollWidth <= c.clientWidth + 1; });
      const esc = e => { let m = new DOMMatrix(); for (let x = e; x; x = x.parentElement) { const tr = getComputedStyle(x).transform; if (tr && tr !== 'none') m = new DOMMatrix(tr).multiply(m); }
        return Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)); };
      const px = sel => Math.min(...[...document.querySelectorAll(sel)].map(e => parseFloat(getComputedStyle(e).fontSize) * esc(e)));
      const estouros = ['.entrada-titulo', '.entrada-hobby', '.entrada-contato', '.entrada-contato .ea-canal', '.entrada-nota']
        .flatMap(sel => [...document.querySelectorAll(sel)]).map(e => e.scrollWidth - e.clientWidth);
      return { linha: canais.length === 2 && canais.every(Boolean), hobby: t.includes('Este é um projeto feito por hobby sem fins lucrativos.'),
               lol: /League of Legends Brelgo#RPG/i.test(t), discord: /Discord brelgo/i.test(t), ids,
               cabe: dentro(pl) && dentro(grupo) && dentro(nota), estouro: pl ? Math.max(...estouros) : null,
               letra: { rotulos: +px('.entrada-contato .ea-rot, .entrada-contato .ea-nome').toFixed(1), nota: +px('.entrada-nota').toFixed(1), ids: +px('.entrada-contato .ea-id').toFixed(1) } }; })()"""
    # F13-T99: a placa é a de cada região (a entrada sorteia uma por visita): a conta vale para as três,
    # cada uma forçada pelo ?entrada=
    ruins = []
    for rg in REGIOES_ENTRADA:
        s.tela_normal()
        s.abrir("?entrada=" + rg)
        time.sleep(0.8)
        if s.js("document.getElementById('entrada').dataset.regiao") != rg:
            ruins.append("%s: a região forçada não montou" % rg)
            continue
        for w, h in RESOLUCOES:
            s.tela(w, h)
            r = s.js(le)
            if not (r["hobby"] and r["lol"] and r["discord"] and r["cabe"] and r["estouro"] <= 1 and r["linha"]
                    and r["ids"] == ["Brelgo#RPG:all", "brelgo:all"]
                    and r["letra"]["rotulos"] >= 10 and r["letra"]["nota"] >= 12 and r["letra"]["ids"] >= 12):
                ruins.append("%s %dx%d %s" % (rg, w, h, r))
    s.tela_normal()
    # F13-T57 (Leo, 19/10/2026): "Bem Vindo(a)!", "Meus Contatos" e a atualização do
    # projeto ao lado do patch — e o número não fica para trás do último commit de
    # tarefa (com o index.html mexido, uma tarefa está em andamento: tem de estar à frente)
    pl = s.js("""(() => ({ regiao: document.getElementById('entrada').dataset.regiao, titulo: document.querySelector('.entrada-titulo').textContent.trim(),
      rot: document.querySelector('.entrada-contato .ea-rot').textContent.trim(),
      nota: document.querySelector('.entrada-nota').textContent.replace(/\\s+/g, ' ').trim(),
      at: typeof ATUALIZACAO === 'string' ? ATUALIZACAO : null, patch: CATALOG.meta.patch }))()""")
    try:
        log = subprocess.run(["git", "log", "--format=%s", "-n", "400"], cwd=RAIZ, capture_output=True).stdout.decode("utf-8", "replace")
        # a amostra de uma tarefa ("F13-T112 (amostra): …") não mexe no index.html: não conta como a tarefa feita
        ultima = max([int(n) for n in re.findall(r"^F13-T(\d+)\b(?!\s*\(amostra\))", log, re.M)] or [0])
        mexido = bool(subprocess.run(["git", "status", "--porcelain", "index.html"], cwd=RAIZ, capture_output=True).stdout.strip())
    except Exception:
        ultima, mexido = None, False
    fase, _, tarefa = (pl["at"] or "").partition(".")
    em_dia = ultima is None or (fase == "13" and tarefa.isdigit() and (int(tarefa) > ultima if mexido else int(tarefa) >= ultima))
    p.conta("fundação", "a placa dá as boas-vindas, com a atualização do projeto e o patch",
            pl["titulo"] == "Bem Vindo(a)!" and pl["rot"] == "Meus Contatos"
            and pl["nota"] == "League of Legends · Atualização %s · patch %s" % (pl["at"], pl["patch"]) and em_dia,
            "%s; último commit de tarefa F13-T%s%s" % (pl, ultima, " (index.html mexido: a atualização tem de estar à frente)" if mexido else ""))
    p.conta("fundação", "a placa de entrada diz o hobby e o contato do autor", not ruins,
            "; ".join(ruins) or "hobby, Brelgo#RPG e brelgo à vista em %d resoluções nas %d regiões; um clique seleciona o ID inteiro" % (len(RESOLUCOES), len(REGIOES_ENTRADA)))
    s.entrar()
    p.conta("fundação", "entrar na loja não gera erro", not s.erros, "; ".join(s.erros[:2]))


def checar_catalogo(s, p):
    print("\n%sCATÁLOGO%s" % (AMARELO, FIM))
    n = s.js("document.querySelectorAll('#grid .card').length")
    p.conta("catálogo", "225 cards desenhados", n == 225, "vieram %s" % n)

    s.js("""(() => { const c = document.getElementById('search-input'); c.value = 'doran';
            c.dispatchEvent(new Event('input', {bubbles: true})); })()""")
    time.sleep(0.6)
    achados = s.js("document.querySelectorAll('#grid .card').length")
    p.conta("catálogo", "a busca filtra", 0 < achados < 225, "'doran' → %s itens" % achados)
    s.js("""(() => { const c = document.getElementById('search-input'); c.value = '';
            c.dispatchEvent(new Event('input', {bubbles: true})); })()""")
    time.sleep(0.6)

    s.clicar(".class-tab[data-classe='AD']", 0.8)
    estado = s.js("""(() => { const o = document.getElementById('oficina');
      const e = document.querySelector('.estandarte');
      return { display: getComputedStyle(o).display, faixa: e ? Math.round(e.getBoundingClientRect().width) : 0,
               corpo: [...document.body.classList].filter(c => c.startsWith('nucleo')) }; })()""")
    # A regressão de 18–20/09: a .oficina deixou de ser grid e o estandarte
    # engoliu a largura toda em toda aba de núcleo.
    p.conta("catálogo", "aba de núcleo vira oficina com estandarte",
            estado["display"] == "grid" and estado["faixa"] == 46,
            "display %s, faixa %spx" % (estado["display"], estado["faixa"]))

    s.clicar(".class-tab[data-classe='']", 0.8)
    p.conta("catálogo", "aba Todos volta a ser uma coluna só de grade",
            s.js("getComputedStyle(document.getElementById('oficina')).display") == "block")

    # F13-T9: o Ápice não pode apagar número do item. A Tocha perdia os +80 de PdH
    # (o texto diz "+20% de PdH"), a Couraça Protoplasmática ia de 600 para 241
    # de Vida, e o Elixir da Força somava as duas alternativas de um "ou". E o
    # caminho antigo: o Lacre Sombrio continua indo de 15 para 55 no Ápice.
    # F13-T21: desde o Capítulo 1 de 23/09 o Ápice vem em números (apexNumeric):
    # o total no máximo substitui, o "a mais" soma. A Couraça chega a 841,18 de
    # Vida no nível 13 (a leitura humilde da T9 deixava os 600), a Tocha mantém
    # os +80 e ganha o multiplicador de +20%, e o Atma — o caso que provou que
    # o texto não bastava — chega a 50% de crítico, não 30%.
    ap = s.js("""(() => { const pega = (n) => CATALOG.items.find(i => i.namePt === n);
      const le = (n) => { const it = pega(n); state.applyApex = true;
        const r = effectiveAttributes(it, { itemId: it.slug }).map(a => a.raw); state.applyApex = false; return r; };
      return { tocha: le('Tocha de Chamas Negras'), couraca: le('Couraça Protoplasmática'),
               elixir: le('Elixir da Força'), lacre: le('Lacre Sombrio'), atma: le('Acerto de Contas de Atma') }; })()""")
    p.conta("catálogo", "Ápice não apaga número do item (Tocha +80 e +20%)",
            "+80 de Poder de Habilidade" in ap["tocha"] and "+20% de Poder de Habilidade" in ap["tocha"],
            "Tocha %s" % ap["tocha"][:3])
    p.conta("catálogo", "Ápice usa o total do catálogo (Couraça 841,18; Atma 50%)",
            "+841,18 de Vida" in ap["couraca"] and "+50% de Chance de Acerto Crítico" in ap["atma"],
            "Couraça %s | Atma %s" % (ap["couraca"][:1], [x for x in ap["atma"] if "Crítico" in x]))
    p.conta("catálogo", "Ápice não soma as duas pontas de um \"ou\"", ap["elixir"] == [], str(ap["elixir"]))
    p.conta("catálogo", "Ápice ainda sobe o que é máximo (Lacre 15 → 55)",
            "+55 de Poder de Habilidade" in ap["lacre"], str(ap["lacre"][:1]))

    # F13-T15 (Leo, 23/09: eficiência "com a passiva"): duas regras que valem
    # para o catálogo inteiro. O desconto do Reembolso nunca piora um item — a
    # base antiga derrubava o Limite da Razão de 119% para 91% —, e a caixa com
    # um item só mostra a mesma eficiência da ficha dele, com e sem Reembolso.
    ef = s.js("""(() => { const piora = [], dif = [];
      CATALOG.items.forEach(it => { const val = (on) => { state.applyCashback = on; return [itemEfficiency(it), goldEfficiency([{ itemId: it.slug }]).pct]; };
        const [off, cxOff] = val(false), [on, cxOn] = val(true);
        if (hasCashback(it) && off !== null && on !== null && on < off - 0.05) piora.push(it.namePt);
        if ((off !== null && cxOff !== null && Math.abs(off - cxOff) > 0.06) || (on !== null && cxOn !== null && Math.abs(on - cxOn) > 0.06)) dif.push(it.namePt); });
      state.applyCashback = false; return { piora, dif }; })()""")
    p.conta("catálogo", "o Reembolso nunca piora a eficiência de um item", not ef["piora"],
            ("pioram: " + ", ".join(ef["piora"][:4])) if ef["piora"] else "nenhum dos 225")
    p.conta("catálogo", "caixa de um item só = eficiência da ficha dele", not ef["dif"],
            ("diferem: " + ", ".join(ef["dif"][:4])) if ef["dif"] else "os 225, com e sem Reembolso")
    # F13-T20: o valor em ouro vem pronto do Capítulo 1 (goldValueBase). O
    # contorno da T15 (efficiencyBase × preço) errava por arredondamento em 16
    # itens — o Limite da Razão valia 3.331,72g em vez de 3.331,67g.
    vo = s.js("""(() => { const dif = [], com = [];
      CATALOG.items.forEach(it => { const b = it.costAnalysis && it.costAnalysis.goldValueBase;
        if (typeof b !== 'number') return; com.push(it);
        if (Math.abs(valorEmOuro(it) - b) > 0.001) dif.push(it.namePt + ' ' + valorEmOuro(it).toFixed(2) + '≠' + b); });
      return { n: com.length, dif }; })()""")
    p.conta("catálogo", "valor em ouro = o do catálogo, sem conta por fora", vo["n"] > 200 and not vo["dif"],
            ("diferem: " + "; ".join(vo["dif"][:3])) if vo["dif"] else "%d itens com Valor de Ouro (base)" % vo["n"])
    # F13-T22: o Ápice e o Mestre Forjador mudam o valor em ouro, com os números
    # do catálogo. O Atma no ápice vale 3.866,67g (133,33%); forjado, qualquer
    # Lendário elegível ganha os 1.000g do bônus. E a caixa com um item só
    # continua igual à ficha dele com o Ápice ligado.
    mx = s.js("""(() => { const atma = CATALOG.items.find(i => i.namePt === 'Acerto de Contas de Atma');
      state.applyApex = true; const efAtma = itemEfficiency(atma);
      const dif = [];
      CATALOG.items.forEach(it => { const f = itemEfficiency(it), c = goldEfficiency([{ itemId: it.slug }]).pct;
        if (f !== null && c !== null && Math.abs(f - c) > 0.06) dif.push(it.namePt); });
      state.applyApex = false;
      const alvo = CATALOG.items.find(i => mfEligible(i) && typeof i.costAnalysis.goldValueBase === 'number');
      const antes = build.masterwork; build.masterwork = true;
      const ouro = goldEfficiency([{ itemId: alvo.slug, mf: true }]).gold;
      build.masterwork = antes;
      return { efAtma, dif, alvo: alvo.namePt, ouro, base: alvo.costAnalysis.goldValueBase, bonus: alvo.masterwork.bonusGold }; })()""")
    p.conta("catálogo", "o Ápice muda a eficiência (Atma 133,33%)", abs((mx["efAtma"] or 0) - 133.33) < 0.01,
            "Atma no ápice: %s%%" % mx["efAtma"])
    p.conta("catálogo", "o Mestre Forjador soma o bônus ao item forjado",
            abs(mx["ouro"] - (mx["base"] + (mx["bonus"] or 0))) < 0.01 and (mx["bonus"] or 0) > 0,
            "%s: %sg + %sg = %sg" % (mx["alvo"], mx["base"], mx["bonus"], mx["ouro"]))
    p.conta("catálogo", "caixa de um item só = ficha, também no Ápice", not mx["dif"],
            ("diferem: " + ", ".join(mx["dif"][:4])) if mx["dif"] else "os 225")
    # F13-T29 (bug nº 46, achado pelo Leo): no modo Ícones o mouse fazia os
    # ícones do AD sumirem. A reação do núcleo não entra ali (F11-T5), mas o AD
    # anima o próprio card, e a variante 5 apagava a superfície por 235 ms. O
    # sorteio escolhe a 5 uma vez em cinco: a checagem olha se QUALQUER variante
    # foi acionada, e mede a opacidade da superfície logo depois do mouse entrar.
    def passar_mouse_nos_ad(modo, n=6):
        s.clicar('.view-btn[data-view="%s"]' % modo, 0.8)
        s.js("document.querySelector('#grid').scrollIntoView({block: 'start'}); window.scrollBy(0, -40); 'ok'")
        time.sleep(0.4)
        idx = s.js("""[...document.querySelectorAll('#grid .card')].map((c, i) => [c, i])
          .filter(([c]) => c.classList.contains('fx-ad') && c.getBoundingClientRect().top > 0
                           && c.getBoundingClientRect().bottom < innerHeight).slice(0, %d).map(([, i]) => i)""" % n)
        vistos = []
        for i in idx:
            c = s.js("(() => { const r = document.querySelectorAll('#grid .card')[%d].getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; })()" % i)
            s.envia("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": c[0], "y": c[1]})
            time.sleep(0.06)
            vistos.append(s.js("""(() => { const c = document.querySelectorAll('#grid .card')[%d];
              return { variante: [1,2,3,4,5].filter(v => c.classList.contains('a' + v))[0] || 0,
                       op: Number(getComputedStyle(c.querySelector('.card-surface')).opacity) }; })()""" % i))
            s.envia("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": 3, "y": 3})
            time.sleep(0.3)
        return vistos
    ic = passar_mouse_nos_ad("icons")
    p.conta("catálogo", "Ícones: o mouse não aciona o golpe do AD (nem apaga o ícone)",
            len(ic) >= 4 and all(v["variante"] == 0 and v["op"] > 0.99 for v in ic),
            "%d ícones AD; variantes %s; menor opacidade %.2f" % (len(ic), [v["variante"] for v in ic], min([v["op"] for v in ic] or [0])))
    cd = passar_mouse_nos_ad("cards", 4)
    p.conta("catálogo", "Cards: o golpe do AD continua (caminho antigo)", len(cd) >= 3 and all(v["variante"] > 0 for v in cd),
            "%d cards AD; variantes %s" % (len(cd), [v["variante"] for v in cd]))

    # F13-T43 (nºs 24, 32 e 33): o número que a tela mostra é o mesmo que o
    # filtro, o cabeçalho do grupo, o seletor e a soma usam. O pior dado: a Joia
    # da Ruína (99,995%) e o Cetro Vampírico (99,98%), que aparecem "100,0%";
    # Sapatos Enfeitiçados, com Penetração Mágica plana e em %; o Arco do Axioma
    # (2.543,75g com Reembolso) e a Força da Trindade (3.083,03g).
    n43 = s.js("""(() => {
      const it = n => CATALOG.items.find(i => i.namePt === n);
      const joia = it('Joia da Ruína'), cetro = it('Cetro Vampírico');
      const antes = { eff: new Set(state.efficiency), sort: state.sort, cash: state.applyCashback };
      state.efficiency = new Set(['100-119']);
      const noFiltro = [joia, cetro].map(x => itemMatchesFilters(x));
      const naTela = [joia, cetro].map(x => fmtEff(itemEfficiency(x)));
      state.efficiency = antes.eff;
      state.sort = 'eff-desc';
      const grupo = [joia, cetro].map(x => groupLabelFn(CATALOG.items)(x));
      state.sort = antes.sort;
      const opt = [...document.querySelectorAll('#sort-attr-select option')].find(o => o.value === 'Penetração Mágica');
      const comPen = CATALOG.items.filter(x => (x.attributes || []).some(a => a.stat === 'Penetração Mágica')).length;
      state.applyCashback = true;
      const arco = it('Arco do Axioma'), forca = it('Força da Trindade');
      const precos = [arco, forca].map(x => fmtG(effectivePrice(x)));
      const caixa = catTotal({ items: [{ itemId: arco.slug }, { itemId: forca.slug }], kind: 'comum' });
      const soma = [arco, forca].reduce((t, x) => t + effectivePrice(x), 0);
      state.applyCashback = antes.cash;
      return { noFiltro, naTela, grupo, curto: [fmtEff(106.1), fmtEff(100), fmtEff(1450 / 2500 * 100)], opt: opt ? opt.textContent : null, comPen, precos, caixa: fmtG(caixa), soma: fmtG(soma),
               netArco: arco.cashback.netGold, netForca: forca.cashback.netGold };
    })()""")
    # (Leo, 17/10/2026: a eficiência nunca arredonda para cima) 99,995% e 99,98%
    # saem 99,9%, ficam fora de "100% a 119%" e no grupo que vai até 99
    import re as _re
    faixas = [tuple(int(x) for x in _re.findall(r"\d+", g)[:2]) for g in n43["grupo"]]
    p.conta("catálogo", "eficiência que a tela mostra é a do filtro e a do grupo",
            n43["naTela"] == ["99,9%", "99,9%"] and n43["noFiltro"] == [False, False]
            and all(len(f) == 2 and f[0] <= 99 <= f[1] for f in faixas)
            and n43["curto"] == ["106,1%", "100,0%", "58,0%"],
            "na tela %s · no filtro 100–119%% %s · grupo %s · 106,1, 100 e 1450÷2500 (57,99999…): %s" % (n43["naTela"], n43["noFiltro"], n43["grupo"], n43["curto"]))
    p.conta("catálogo", "o seletor de atributo conta itens",
            n43["opt"] == "Penetração Mágica (%d itens)" % n43["comPen"], "%s · itens com o atributo: %d" % (n43["opt"], n43["comPen"]))
    # F13-T43b (nº 25, opção A do Leo): ordenar por um atributo com pontos e %
    # misturados nunca compara os dois — primeiro os pontos, depois a %, cada
    # grupo diz qual é, e o card mostra todos os valores do item
    t25 = s.js("""(() => { const antes = { sort: state.sort, attr: state.sortAttr, stats: new Set(state.stats) };
      const ordem = (stat, sort) => { state.sort = sort; state.sortAttr = stat; state.stats = new Set([stat]);
        const { list } = getFilteredSorted(); const g = groupLabelFn(list);
        return list.map(it => ({ nome: it.namePt, vs: statValores(it, stat), grupo: g(it) })); };
      const pen = ordem('Penetração Mágica', 'attr-desc'), vm = ordem('Velocidade de Movimento', 'attr-asc'), ph = ordem('Poder de Habilidade', 'attr-desc');
      state.sort = 'attr-desc'; state.sortAttr = 'Penetração Mágica'; state.stats = new Set(['Penetração Mágica']); render();
      const card = [...document.querySelectorAll('.card')].find(c => c.querySelector('.card-name') && c.querySelector('.card-name').textContent.startsWith('Sapatos Enfeitiçados'));
      const linha = card && card.querySelector('.card-sortstat') ? card.querySelector('.card-sortstat').textContent : '';
      state.sort = antes.sort; state.sortAttr = antes.attr; state.stats = antes.stats; render();
      return { pen, vm, ph, linha }; })()""")

    def partes_ok(lst, desc):
        parte = [0 if any(not v["pct"] for v in x["vs"]) else 1 for x in lst]
        valor = [next((v["v"] for v in x["vs"] if not v["pct"]), x["vs"][0]["v"]) for x in lst]
        if parte != sorted(parte):
            return False
        for i in range(1, len(lst)):
            if parte[i] == parte[i - 1] and ((valor[i] > valor[i - 1]) if desc else (valor[i] < valor[i - 1])):
                return False
        return all((" em pontos" in x["grupo"]) == (p_ == 0) and (" em %" in x["grupo"]) == (p_ == 1) for x, p_ in zip(lst, parte))
    p.conta("catálogo", "ordenar por atributo não mistura pontos com %",
            partes_ok(t25["pen"], True) and partes_ok(t25["vm"], False) and all(" em " not in x["grupo"] for x in t25["ph"])
            and "+20" in t25["linha"] and "+8%" in t25["linha"],
            "Penetração: %s · card dos Sapatos Enfeitiçados: %r" % ([(x["nome"], x["grupo"].split(":")[0]) for x in t25["pen"]][:8], t25["linha"]))
    p.conta("catálogo", "preço com Reembolso com as casas do catálogo",
            n43["precos"] == ["2.543,75g", "3.083,03g"] and n43["caixa"] == n43["soma"] == "5.626,78g",
            "preços %s (catálogo: %s e %s) · caixa %s · soma %s" % (n43["precos"], n43["netArco"], n43["netForca"], n43["caixa"], n43["soma"]))


def checar_ficha(s, p):
    """F13-T55 (Leo, 19/10/2026: "os jogadores lembram dos itens pela imagem e não
    pelo nome"): a receita em árvore com a troca para a conta de somar, o "Vira
    componente de" por ícone e o "Exibir detalhes". As peças são contadas por fora,
    direto do catalog.js (components × qty), e a tela tem de bater com a conta."""
    print("\n%sFICHA DO ITEM%s" % (AMARELO, FIM))
    s.js("localStorage.removeItem('ficha.vista'); 'ok'")
    s.abrir(); time.sleep(0.8); s.entrar()
    conta_fora = """const porEn = {}; CATALOG.items.forEach(i => porEn[i.nameEn] = i);
      const filhos = (it) => (it.components || []).flatMap(c => Array(c.qty || 1).fill(porEn[c.nameEn] || null));
      const conta = (it, n) => { const f = n < 5 ? filhos(it) : []; if (!f.length) return { nos: 1, folhas: 1, juntar: 0, compostos: 0 };
        return f.reduce((a, k) => { if (!k) return { nos: a.nos + 1, folhas: a.folhas + 1, juntar: a.juntar, compostos: a.compostos };
          const b = conta(k, n + 1); return { nos: a.nos + b.nos, folhas: a.folhas + b.folhas, juntar: a.juntar + b.juntar, compostos: a.compostos + b.compostos }; },
          { nos: 1, folhas: 0, juntar: it.combineCost ? 1 : 0, compostos: 1 }); };"""
    # a de mais peças do catálogo (Dança da Morte no 16.21.1), com duas peças iguais na receita
    r = s.js("""(() => { %s
      const alvo = CATALOG.items.filter(i => (i.components || []).length).map(i => ({ i, c: conta(i, 0) })).sort((a, b) => b.c.folhas - a.c.folhas)[0];
      openModal(alvo.i.slug); const m = document.getElementById('modal');
      return { nome: alvo.i.namePt, quer: alvo.c, tela: { nos: m.querySelectorAll('.rt .rt-no').length, folhas: m.querySelectorAll('.rt .rt-no.folha, .rt .rt-no.fora').length,
               juntar: m.querySelectorAll('.rt .rt-juntar').length, raiz: (m.querySelector('.rt .rt-no.raiz b') || {}).textContent,
               conta: (m.querySelector('.rt-conta') || {}).textContent || '', preco: fmtG(alvo.i.priceGold), arvore: getComputedStyle(m.querySelector('.rt')).display !== 'none' } }; })()""" % conta_fora)
    t, quer = r["tela"], r["quer"]
    p.conta("ficha", "a receita em árvore: as peças da tela batem com o catálogo",
            t["arvore"] and t["raiz"] == r["nome"] and t["nos"] == quer["nos"] and t["folhas"] == quer["folhas"] and t["juntar"] == quer["juntar"]
            and t["conta"].endswith(" para juntar = %s · o clique numa peça abre a ficha dela." % t["preco"]),
            "%s: %d nós, %d na ponta, %d galhos com ouro de juntar; conta: %s" % (r["nome"], t["nos"], t["folhas"], t["juntar"], t["conta"][:70]))
    # o clique numa peça abre a ficha dela (clique de verdade, depois do pergaminho desenrolar:
    # no meio da animação a peça ainda está mudando de lugar)
    time.sleep(0.8)
    s.clicar("#modal .rt .rt-no.folha", 1.0)
    aberta = s.js("(document.querySelector('#modal h2') || {}).textContent")
    p.conta("ficha", "o clique numa peça abre a ficha dela", aberta and aberta != r["nome"], "abriu: %s" % aberta)

    # a troca para a conta de somar, lembrada depois de recarregar
    s.js("openModal(%s); 'ok'" % json.dumps(s.js("(CATALOG.items.find(i => i.namePt === %s) || {}).slug" % json.dumps(r["nome"]))))
    time.sleep(0.8)
    s.clicar('#modal [data-receita="soma"]', 0.5)
    soma = s.js("""(() => { const m = document.getElementById('modal'), linhas = [...m.querySelectorAll('.rs .rs-linha')];
      return { rt: getComputedStyle(m.querySelector('.rt')).display, rs: getComputedStyle(m.querySelector('.rs')).display, n: linhas.length,
               raizUltima: linhas.length > 0 && linhas[linhas.length - 1].classList.contains('raiz') }; })()""")
    s.js("closeModal(); 'ok'")
    s.abrir(); time.sleep(0.8); s.entrar()
    lembrou = s.js("""(() => { openModal(CATALOG.items.find(i => (i.components || []).length > 1).slug); const m = document.getElementById('modal');
      return getComputedStyle(m.querySelector('.rs')).display !== 'none' && m.querySelector('[data-receita="soma"]').classList.contains('ativo'); })()""")
    p.conta("ficha", "a troca para a conta de somar (e o app lembra)",
            soma["rt"] == "none" and soma["rs"] != "none" and soma["n"] >= 2 and soma["raizUltima"] and lembrou,
            "%s; lembrou depois de recarregar: %s" % (soma, lembrou))
    s.js("document.querySelector('#modal [data-receita=\"arvore\"]').click(); closeModal(); 'ok'")

    # "Vira componente de" por ícone, por etapa, do mais barato ao mais caro; o nome no hover
    vira = s.js("""(() => { const it = CATALOG.items.slice().sort((a, b) => (b.buildsIntoIds || []).length - (a.buildsIntoIds || []).length)[0];
      openModal(it.slug); const m = document.getElementById('modal');
      const grupos = [...m.querySelectorAll('.vira-grupo')].map(g => [...g.querySelectorAll('.vira-item')].map(b => byId[b.dataset.goto]));
      const ordem = grupos.every(g => g.every((x, i) => !i || (g[i - 1].priceGold || 0) <= (x.priceGold || 0)) && g.every(x => x.tier === g[0].tier));
      const etapas = grupos.map(g => TIER_ORDER.indexOf(g[0].tier)); const etapasOk = etapas.every((x, i) => !i || etapas[i - 1] < x);
      const nomes = [...m.querySelectorAll('.vira-item')].every(b => b.title === byId[b.dataset.goto].namePt && b.querySelector('img'));
      return { nome: it.namePt, quer: it.buildsIntoIds.length, tela: m.querySelectorAll('.vira-item').length, ordem, etapasOk, nomes,
               chips: m.querySelectorAll('.vira .recipe-chip:not(.unlinked)').length }; })()""")
    time.sleep(0.8)
    s.clicar("#modal .vira-item", 1.0)
    vira_abre = s.js("(document.querySelector('#modal h2') || {}).textContent")
    p.conta("ficha", "o “Vira componente de” por ícone, por etapa",
            vira["tela"] == vira["quer"] and vira["ordem"] and vira["etapasOk"] and vira["nomes"] and vira["chips"] == 0 and vira_abre != vira["nome"],
            "%s: %d de %d ícones; o clique abriu %s" % (vira["nome"], vira["tela"], vira["quer"], vira_abre))

    # Exibir detalhes: fechado no padrão (com memória limpa), abre no clique, e o app lembra
    s.js("closeModal(); localStorage.removeItem('ficha.vista'); 'ok'")
    s.abrir(); time.sleep(0.8); s.entrar()
    vis = """(() => { const m = document.getElementById('modal');
      const sec = (t) => [...m.querySelectorAll('.modal-section-title')].find(e => e.textContent.trim().startsWith(t));
      const ve = (t) => { const e = sec(t); return !!e && e.getClientRects().length > 0; };
      const algum = (sel) => [...m.querySelectorAll(sel)].some(e => e.getClientRects().length > 0);
      return { atributos: ve('Atributos'), receita: ve('Do que é feito'), custo: ve('Análise de custo'), tags: ve('Categoria de Atributo'), ornn: ve('Passiva do Ornn'),
               habilidade: algum('.ability-desc'), mecanica: algum('.ability-mech'), nota: algum('.modal-note'),
               botao: (m.querySelector('.ficha-detalhes-btn') || {}).textContent }; })()"""
    # Leo, 23/10/2026: no Resumido a habilidade fica no texto curto; o "Exibir detalhes" expande
    # para a versão completa (a Mecânica) e as notas do item — o alvo tem as duas
    alvo = s.js("""CATALOG.items.find(i => i.tier === 'Lendário' && i.costAnalysis && (i.components || []).length && i.masterwork && i.attributeCategory && i.attributeCategory.length
      && (i.abilities || []).some(a => a.mechanics) && i.notes).slug""")
    s.js("openModal(%s); 'ok'" % json.dumps(alvo)); time.sleep(0.8)
    antes = s.js(vis)
    s.clicar("#modal .ficha-detalhes-btn", 0.5)
    depois = s.js(vis)
    s.js("closeModal(); 'ok'")
    s.abrir(); time.sleep(0.8); s.entrar()
    s.js("openModal(%s); 'ok'" % json.dumps(alvo)); time.sleep(0.8)
    lembra = s.js(vis)
    p.conta("ficha", "o Exibir detalhes: resumido no padrão (habilidade no texto curto), o resto no clique (e o app lembra)",
            antes["atributos"] and antes["receita"] and antes["habilidade"] and not antes["custo"] and not antes["tags"] and not antes["ornn"]
            and not antes["mecanica"] and not antes["nota"] and antes["botao"] == "Exibir detalhes"
            and depois["custo"] and depois["tags"] and depois["ornn"] and depois["mecanica"] and depois["nota"] and depois["habilidade"] and depois["botao"] == "Ocultar detalhes"
            and lembra["custo"] and lembra["mecanica"] and lembra["botao"] == "Ocultar detalhes",
            "antes %s · depois %s · recarregado %s" % (antes, depois, lembra))
    s.js("document.querySelector('#modal .ficha-detalhes-btn').click(); closeModal(); 'ok'")

    # nas 225 fichas: item sem receita não mostra a seção; a árvore nunca passa da largura da ficha
    todas = s.js("""(() => { %s const ruins = [], semSecao = [];
      CATALOG.items.forEach(i => { openModal(i.slug); const m = document.getElementById('modal'), rt = m.querySelector('.rt');
        const tem = !!m.querySelector('.receita');
        if (tem !== filhos(i).length > 0) semSecao.push(i.namePt);
        if (rt && rt.scrollWidth > rt.clientWidth + 1) ruins.push(i.namePt + ' (' + rt.scrollWidth + '/' + rt.clientWidth + ')'); });
      closeModal(); return { ruins, semSecao, n: CATALOG.items.length }; })()""" % conta_fora)
    p.conta("ficha", "nas 225 fichas a árvore cabe, e só quem tem receita mostra a seção",
            not todas["ruins"] and not todas["semSecao"], "%d fichas; estouram: %s; seção errada: %s" % (todas["n"], todas["ruins"][:3] or "nenhuma", todas["semSecao"][:3] or "nenhuma"))


def checar_calculadora(s, p):
    """F13-T42 (bugs nºs 23 e 31): o "Puxar da build ativa" usa os itens que a
    build de fato compra — sem as caixas Opcionais e, na Escolha 1, só o padrão —
    e não apaga a vida digitada quando os itens não dão vida."""
    print("\n%sCALCULADORA%s" % (AMARELO, FIM))
    s.nova_build()
    garantir_build_editavel(s)
    puxa = """(() => { document.getElementById('calc-from-build').click(); return { hp: calc.hp, armor: calc.armor, mr: calc.mr }; })()"""
    r = s.js("""(() => { const it = n => CATALOG.items.find(i => i.namePt === n);
      const ent = n => ({ itemId: it(n).slug, note: '' });
      const pr = it('Presságio de Randuin'), es = it('Armadura de Espinhos'), wa = it('Armadura de Warmog');
      const v = (x, st) => (x.attributes || []).filter(a => a.stat === st && a.unit === 'flat').reduce((t, a) => t + a.value, 0);
      build.cats = [
        { id: 'cat-c1', name: 'Escolha', desc: '', kind: 'escolha', span: 2, cols: 1, rows: 2, items: [ent('Presságio de Randuin'), ent('Armadura de Espinhos')] },
        { id: 'cat-c2', name: 'Se precisar', desc: '', kind: 'opcional', span: 2, cols: 6, rows: 1, items: [ent('Armadura de Warmog')] },
      ];
      gravarBuild(); renderBuildAll();
      return { esperado: { hp: v(pr, 'Vida'), armor: v(pr, 'Armadura') }, comTudo: { hp: v(pr, 'Vida') + v(es, 'Vida') + v(wa, 'Vida'), armor: v(pr, 'Armadura') + v(es, 'Armadura') + v(wa, 'Armadura') } }; })()""")
    s.js("switchTab('calc')")
    time.sleep(0.6)
    veio = s.js(puxa)
    p.conta("calculadora", "Puxar da build ativa: sem Opcionais e só o padrão da Escolha 1",
            veio["hp"] == r["esperado"]["hp"] and veio["armor"] == r["esperado"]["armor"] and r["esperado"] != r["comTudo"],
            "veio vida %s / armadura %s · o padrão dá %s / %s · somando tudo daria %s / %s" % (
                veio["hp"], veio["armor"], r["esperado"]["hp"], r["esperado"]["armor"], r["comTudo"]["hp"], r["comTudo"]["armor"]))
    # a revisão da T42: o painel "Atributos da build" da forja somava as
    # Opcionais, e a Calculadora deixou de somar — os dois contam a mesma build
    painel = s.js("""(() => { switchTab('build'); showBuildScreen('forja'); renderBuildTotals();
      const t = document.querySelector('#build-totals .bt-title'), l = document.querySelector('#build-totals .cs-list');
      return { titulo: t ? t.textContent : '', lista: l ? l.textContent : '' }; })()""")
    s.js("switchTab('calc')")
    time.sleep(0.4)
    p.conta("calculadora", "o painel Atributos da build conta a mesma build",
            "1 item" in painel["titulo"] and ("+%d" % r["esperado"]["hp"]) in painel["lista"]
            and ("+%d" % r["comTudo"]["hp"]) not in painel["lista"], "%s · %s" % (painel["titulo"], painel["lista"][:80]))
    s.js("""(() => { const it = CATALOG.items.find(i => i.namePt === 'Cota de Malha');
      build.cats = [{ id: 'cat-c1', name: 'Núcleo', desc: '', kind: 'comum', span: 2, cols: 6, rows: 1, items: [{ itemId: it.slug, note: '' }] }];
      gravarBuild(); calc.hp = 2000; renderCalc(); return 'ok'; })()""")
    veio = s.js(puxa)
    p.conta("calculadora", "Puxar da build ativa: itens sem vida não apagam a vida digitada",
            veio["hp"] == 2000 and veio["armor"] > 0, "vida %s (era 2000) · armadura %s" % (veio["hp"], veio["armor"]))
    # F13-T93 (achado no roteiro do controle remoto): cada tecla redesenha a calculadora, e o focus() punha
    # o cursor no começo do campo de número — "12" digitado tecla a tecla virava "21"
    s.clicar("#calc-hp", 0.2)
    s.js("(() => { document.getElementById('calc-hp').select(); return 1; })()")
    for ch in "125":
        for tipo in ("keyDown", "keyUp"):
            s.envia("Input.dispatchKeyEvent", {"type": tipo, "key": ch, "code": "Digit" + ch, "text": ch if tipo == "keyDown" else "",
                                               "windowsVirtualKeyCode": ord(ch), "nativeVirtualKeyCode": ord(ch)})
        time.sleep(0.12)
    dig = s.js("({ valor: document.getElementById('calc-hp').value, hp: calc.hp, foco: document.activeElement && document.activeElement.id })")
    p.conta("calculadora", "digitar a vida tecla a tecla: \"125\" fica 125 (o redesenho de cada tecla deixa o cursor no fim)",
            dig["valor"] == "125" and dig["hp"] == 125 and dig["foco"] == "calc-hp", "%s" % dig)
    s.js("switchTab('build')")
    s.nova_build()


def checar_som(s, p):
    """F13-T46 e T48 (Leo: "os sons estão muito altos"; "estou tendo que deixar o
    volume no mínimo"): cada arquivo toca com o redutor medido em
    data/ganho_sons.js, o controle segue a curva v² (a metade dá ¼), o padrão é
    50%, o volume gravado antes passa ao novo uma vez, e o hover dos cards do
    Catálogo toca 60% mais baixo. O Chrome do roteiro roda mudo (--mute-audio)."""
    print("\n%sSOM%s" % (AMARELO, FIM))

    def recarregar(prepara):
        s.js(prepara)
        s.js("location.reload()")
        time.sleep(2.0)
        s.entrar()
        return s.js("({ vol: Som.estado.volume, gravado: localStorage.getItem('som.volume'), marca: localStorage.getItem('som.padrao') })")

    novo = recarregar("localStorage.removeItem('som.volume'); localStorage.removeItem('som.padrao'); 'ok'")
    antigo = recarregar("localStorage.setItem('som.volume', '0.05'); localStorage.setItem('som.padrao', '2'); 'ok'")
    depois = recarregar("'ok'")
    escolheu = recarregar("localStorage.setItem('som.volume', '0.3'); localStorage.setItem('som.padrao', '3'); 'ok'")
    p.conta("som", "volume padrão 50% (e o volume gravado antes passa ao novo uma vez)",
            novo["vol"] == 0.5 and antigo["vol"] == 0.5 and antigo["gravado"] == "0.5" and depois["vol"] == 0.5 and escolheu["vol"] == 0.3,
            "sem nada gravado %s · com o volume de antes (0,05) %s (gravou %s) · recarregando %s · escolhido depois 0,3 %s" % (
                novo["vol"], antigo["vol"], antigo["gravado"], depois["vol"], escolheu["vol"]))
    s.js("Som.setVolume(0.5); 'ok'")
    r = s.js("""(() => { window.__vols = []; const orig = HTMLMediaElement.prototype.play;
      HTMLMediaElement.prototype.play = function () { window.__vols.push([decodeURIComponent(this.src.split('/').pop()), this.volume]); return orig.call(this); };
      const it = CATALOG.items.find(i => i.itemClass && i.itemClass.core === 'AD' && /^Lendário/.test(i.tier));
      Som.play('catalog:hover', { item: it });
      Som.play('catalog:click', { item: it });
      Som.play('build:open');
      HTMLMediaElement.prototype.play = orig;
      const todos = [...new Set(Object.values(Som.ARQUIVOS).flat())];
      const G = window.GANHO_SONS || {};
      return { vols: window.__vols, G, semGanho: todos.filter(f => typeof G[f] !== 'number'),
               foraDaFaixa: todos.filter(f => !(G[f] > 0 && G[f] <= 1)), baixados: todos.filter(f => G[f] < 1).length, total: todos.length }; })()""")
    esperado = {"ui_catalog_mod_hover_": 0.25 * 0.4, "ui_shop_click_": 0.25, "build_open": 0.25}
    ok_vol = len(r["vols"]) == 3 and all(
        any(f.startswith(k) and abs(v - e * r["G"][f]) < 1e-6 for k, e in esperado.items()) for f, v in r["vols"])
    p.conta("som", "cada som toca na altura medida (curva v² e redutor por arquivo)",
            ok_vol and not r["semGanho"] and not r["foraDaFaixa"] and r["baixados"] > 0,
            "tocados %s · %d arquivos, %d com redutor · sem ganho: %s" % (
                [(f, round(v, 4), r["G"].get(f)) for f, v in r["vols"]], r["total"], r["baixados"], r["semGanho"][:3]))


def checar_falta_publicar(s, p):
    """F13-T45 (nºs 50 e 53): na janela "Falta pouco para publicar", o campo do
    nome sumia na primeira letra (com o foco dentro), e escolher de novo o mesmo
    marcador (ou uma tecla que não muda o texto) carimbava a "Última atualização"."""
    print("\n%sFALTA POUCO PARA PUBLICAR%s" % (AMARELO, FIM))
    s.nova_build()
    s.js("""(() => { if (build.editing) document.getElementById('edit-switch').click();
      build.desc = ''; build.markers = []; build.cats[3].items = [{ itemId: 'long-sword', note: '' }]; gravarBuild();
      showBuildScreen('lista'); biSelected = build.id; renderBuildIndex(); return 'ok'; })()""")
    time.sleep(0.5)
    s.clicar('#bi-detail [data-act="publish"]', 0.8)
    aberta = s.js("!document.getElementById('pub-falta').hidden")
    s.clicar("#pf-nome", 0.2)
    s.envia("Input.insertText", {"text": "T"})
    time.sleep(0.4)
    r = s.js("({ grupo: !document.getElementById('pf-nome-g').hidden, foco: document.activeElement && document.activeElement.id })")
    s.envia("Input.insertText", {"text": "ítulo"})
    time.sleep(0.3)
    nome = s.js("(library.builds.find(b => b.id === biSelected) || {}).name")
    p.conta("falta publicar", "o campo do nome fica na tela enquanto se digita",
            aberta and r["grupo"] and r["foco"] == "pf-nome" and nome == "Título",
            "janela %s · grupo visível %s · foco em %s · nome gravado %r" % (aberta, r["grupo"], r["foco"], nome))
    d = s.js("""(async () => { const b = () => library.builds.find(x => x.id === biSelected);
      const m = { t: 'tag', id: MARCADORES[0].id };
      markerDono = donoDoPopup(); markerSlot = 0; setMarker(0, m); markerDono = null;
      const t1 = b().updatedAt; await new Promise(r => setTimeout(r, 30));
      markerDono = donoDoPopup(); markerSlot = 0; setMarker(0, m); markerDono = null;
      const t2 = b().updatedAt; await new Promise(r => setTimeout(r, 30));
      gravarNaBuild('name', b().name);
      const t3 = b().updatedAt; await new Promise(r => setTimeout(r, 30));
      markerDono = donoDoPopup(); markerSlot = 1; setMarker(1, { t: 'tag', id: MARCADORES[1].id }); markerDono = null;
      const t4 = b().updatedAt;
      return { mesmoMarcador: t2 === t1, mesmoNome: t3 === t1, outroMarcador: t4 > t1 }; })()""")
    s.clicar("#pf-close", 0.3)
    p.conta("falta publicar", "a data só muda quando a build muda",
            d["mesmoMarcador"] and d["mesmoNome"] and d["outroMarcador"], "%s" % d)
    # a revisão da T45: com o nome padrão o campo abre vazio, e um espaço ali
    # gravava nome vazio (a build ficava sem nome na lista) e carimbava a data
    s.nova_build()
    s.js("""(() => { if (build.editing) document.getElementById('edit-switch').click();
      build.desc = ''; build.markers = []; build.cats[3].items = [{ itemId: 'long-sword', note: '' }]; gravarBuild();
      showBuildScreen('lista'); biSelected = build.id; renderBuildIndex(); return 'ok'; })()""")
    time.sleep(0.5)
    antes = s.js("(() => { const b = library.builds.find(x => x.id === biSelected); return { nome: b.name, data: b.updatedAt }; })()")
    s.clicar('#bi-detail [data-act="publish"]', 0.8)
    s.clicar("#pf-nome", 0.2)
    s.envia("Input.insertText", {"text": " "})
    time.sleep(0.4)
    espaco = s.js("(() => { const b = library.builds.find(x => x.id === biSelected); return { nome: b.name, data: b.updatedAt }; })()")
    s.envia("Input.insertText", {"text": "X"})
    time.sleep(0.3)
    s.js("(() => { const c = document.getElementById('pf-nome'); c.value = ''; c.dispatchEvent(new Event('input', { bubbles: true })); return 'ok'; })()")
    time.sleep(0.3)
    apagou = s.js("(library.builds.find(x => x.id === biSelected) || {}).name")
    s.clicar("#pf-close", 0.3)
    p.conta("falta publicar", "campo do nome vazio não apaga o nome da build",
            antes["nome"] and espaco["nome"] == antes["nome"] and espaco["data"] == antes["data"] and apagou == antes["nome"],
            "nome %r · depois de um espaço %r (data igual %s) · depois de apagar %r" % (antes["nome"], espaco["nome"], espaco["data"] == antes["data"], apagou))


def checar_forja(s, p):
    print("\n%sFORJA%s" % (AMARELO, FIM))
    s.nova_build()
    caixas = s.js("build.cats.length")
    p.conta("forja", "nova build nasce com as 8 caixas sugeridas", caixas == 8, "vieram %s" % caixas)

    s.js("build.cats[1].items.push({ itemId: CATALOG.items[0].slug, note: '' }); renderBuildAll()")
    time.sleep(0.5)
    p.conta("forja", "item entra na caixa", s.js("build.cats[1].items.length") == 1)

    # A build nasce em leitura: é o padrão do Leo, "o jogador vê os itens, não os
    # atributos". Os dois lados da regra são conferidos, leitura e edição.
    atributos = """(() => { const t = document.querySelector('.build-totals.show');
      return t ? getComputedStyle(t).display !== 'none' : false; })()"""
    p.conta("forja", "modo leitura esconde os atributos", not s.js(atributos),
            "editando = %s" % s.js("document.body.classList.contains('editando')"))
    s.clicar("#edit-switch", 0.8)
    p.conta("forja", "o Editar liga", s.js("document.body.classList.contains('editando')"))
    p.conta("forja", "e com ele os atributos voltam", s.js(atributos))

    # F13-T3: os dois verbos que estavam escondidos no balão. Como só existem no
    # hover, o mouse passa antes — senão o clique cai num retângulo invisível.
    s.hover(".item-tile")
    p.conta("forja", "os botões do molde aparecem no hover",
            s.js("""(() => { const f = document.querySelector('.item-tile .tile-acoes');
              return !!f && Number(getComputedStyle(f).opacity) > .9
                     && getComputedStyle(f).pointerEvents === 'auto'; })()"""))
    s.clicar(".item-tile .ta-nota", 0.6)
    p.conta("forja", "o ✎ abre a observação",
            s.js("document.getElementById('note-editor').classList.contains('show')"))
    s.js("closeNoteEditor(false)")
    time.sleep(0.4)
    antes = s.js("build.cats[1].items.length")
    s.hover(".item-tile")
    s.clicar(".item-tile .ta-x", 0.6)
    p.conta("forja", "o ✕ tira o item da caixa", s.js("build.cats[1].items.length") == antes - 1,
            "de %s para %s" % (antes, s.js("build.cats[1].items.length")))

    # F13-T7: dois ✕ em 150 ms tiravam o item errado (achado da caçada de bugs).
    # A saída espera a animação; a posição mudava no meio. Pedir A e B tem de
    # deixar o C.
    fim = s.js("""(async () => { const c = build.cats[1]; c.items = [];
      CATALOG.items.filter(i => i.tier === 'Lendário').slice(0, 3).forEach(it => c.items.push({ itemId: it.slug, note: '' }));
      renderBuildAll(); await new Promise(r => setTimeout(r, 400));
      const c3 = c.items[2].itemId;
      removeItemFromCategory(c.id, 0); await new Promise(r => setTimeout(r, 150));
      removeItemFromCategory(c.id, 1); await new Promise(r => setTimeout(r, 900));
      return { sobrou: c.items.map(i => i.itemId), esperado: [c3] }; })()""")
    p.conta("forja", "dois ✕ seguidos tiram os dois pedidos", fim["sobrou"] == fim["esperado"],
            "sobrou %s" % fim["sobrou"])

    # F13-T4: o tipo da caixa deixou de ser um botão que dá a volta olímpica.
    s.clicar(".build-cat:nth-of-type(2) .cat-kind", 0.6)
    menu = s.js("""(() => { const m = document.getElementById('kind-menu');
      if (!m || !m.classList.contains('show')) return null;
      const r = m.getBoundingClientRect();
      return { opcoes: [...m.querySelectorAll('button')].map(b => b.dataset.kind),
               marcado: (m.querySelector('[aria-checked="true"]') || {}).dataset,
               cabe: r.left >= 0 && r.top >= 0 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1 }; })()""")
    p.conta("forja", "o tipo da caixa abre um menu com os quatro",
            bool(menu) and menu["opcoes"] == ["comum", "prioridade", "opcional", "escolha"] and menu["cabe"],
            "%s" % (menu or "não abriu"))
    s.clicar('#kind-menu [data-kind="opcional"]', 0.7)
    p.conta("forja", "escolher no menu troca o tipo e fecha",
            s.js("build.cats[1].kind") == "opcional"
            and not s.js("document.getElementById('kind-menu').classList.contains('show')"),
            "ficou %s" % s.js("build.cats[1].kind"))
    s.js("build.cats[1].kind = 'comum'; renderBuild()")


def checar_marcadores(s, p):
    """O bug de 20/09: o diálogo abria, a escolha não gravava. Todo passo aqui é
    clique de verdade, e o × só existe no hover."""
    print("\n%sMARCADORES%s" % (AMARELO, FIM))
    # Leo, 23/10/2026: marcador só se escolhe com o Editar ligado
    garantir_build_editavel(s)
    s.clicar("#build-marks .mark-slot[data-i='0']")
    p.conta("marcadores", "o diálogo abre", not s.js("document.getElementById('marker-dialog').hidden"))
    s.clicar("#md-tags .md-cell")
    primeiro = s.js("JSON.stringify(build.markers)")
    p.conta("marcadores", "escolher grava na build", s.js("build.markers.length") == 1, primeiro)

    s.clicar("#build-marks .mark-slot[data-i='1']")
    s.clicar("#md-tags .md-cell:nth-child(3)")
    p.conta("marcadores", "o segundo espaço também", s.js("build.markers.length") == 2)

    s.clicar("#build-marks .mark-slot[data-i='0']")
    s.clicar("#md-tags .md-cell:nth-child(5)")
    p.conta("marcadores", "trocar um já preenchido",
            s.js("JSON.stringify(build.markers)") != primeiro and s.js("build.markers.length") == 2)

    s.hover("#build-marks .mark-slot[data-i='1']")
    s.clicar("#build-marks .mark-slot[data-i='1'] .mark-x")
    p.conta("marcadores", "o × tira", s.js("build.markers.length") == 1)

    # F13-T47 (nº 59; Leo, 17/10/2026): o mesmo marcador não repete. O que já
    # está noutro espaço fica apagado no diálogo, não entra por setMarker, e uma
    # lista com repetido (de antes) conta sem ele — não libera publicar.
    rep = s.js("""(() => { const A = { t: 'tag', id: MARCADORES[0].id }, B = { t: 'tag', id: MARCADORES[1].id }, C = { t: 'tag', id: MARCADORES[2].id };
      const norm = normMarkers([A, A, B]).length;
      build.markers = [A, B]; renderBuildAll();
      openMarkerDialog(0);
      const cel = (m) => [...document.querySelectorAll('#md-tags .md-cell')].find(c => c.dataset.m === JSON.stringify(m));
      const dialogo = { B: cel(B) && cel(B).disabled, A: cel(A) && !cel(A).disabled, C: cel(C) && !cel(C).disabled };
      closeMarkerDialog();
      setMarker(0, B);
      const depois = JSON.stringify(build.markers) === JSON.stringify([A, B]);
      const d = buildResumo(build); d.markers = normMarkers([A, A, B]);
      const falta = faltaParaPublicar(d).some(f => f.includes('marcador'));
      build.markers = []; renderBuildAll();
      return { norm, dialogo, depois, falta }; })()""")
    p.conta("marcadores", "o mesmo marcador não repete",
            rep["norm"] == 2 and rep["dialogo"]["B"] and rep["dialogo"]["A"] and rep["dialogo"]["C"] and rep["depois"] and rep["falta"],
            "%s" % rep)


def checar_visualizacao(s, p):
    """Leo, 23/10/2026: com a build aberta sem o Editar dava para trocar campeão,
    modo, nome, marcadores e Mestre Forjador — e saveBuild, sem o Editar, grava
    na hora. A aba Runas também mudava a página (o nº 29 era isso numa pública).
    Clique de verdade onde há clique; o change forçado cobre o teclado e quem
    tirar o disabled pelo inspetor."""
    print("\n%sVISUALIZAÇÃO SÓ LÊ%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes();
      const t = RUNAS.trilhas[0];
      build.champion = { key: '103', id: 'Ahri', name: 'Ahri' }; build.mode = ''; build.masterwork = false;
      build.markers = [{ t: 'tag', id: MARCADORES[0].id }];
      build.runas = normRunas({ primaria: t.id, assinatura: t.slots[0].runas[0].id });
      rascunho.sujo = false; gravarBuild(); ligarEdicao(false);
      switchTab('build'); showBuildScreen('forja'); renderBuildAll(); return 'ok'; })()""")
    time.sleep(0.8)
    antes = s.js("assinaturaDaBuild(build)")

    s.clicar("#build-champ-btn", 0.6)
    aberto_clique = not s.js("document.getElementById('champ-menu').hidden")
    forcado = s.js("""(() => { const b = document.getElementById('build-champ-btn'), dis = b.disabled;
      b.disabled = false; b.click(); const abriu = !document.getElementById('champ-menu').hidden;
      document.querySelector('#champ-list .champ-row.todos').click();
      renderBuildAll(); return { dis, abriu, champ: build.champion && build.champion.key }; })()""")
    p.conta("visualização", "sem o Editar o campeão não troca",
            forcado["dis"] and not aberto_clique and not forcado["abriu"] and forcado["champ"] == "103",
            "clique abriu o menu" if aberto_clique else "%s" % forcado)

    modo = s.js("""(() => { const sel = document.getElementById('build-mode'), dis = sel.disabled;
      const outro = [...sel.options].find(o => o.value !== sel.value);
      sel.disabled = false; sel.value = outro.value; sel.dispatchEvent(new Event('change', { bubbles: true }));
      const r = { dis, modo: build.mode, tela: sel.value }; renderBuildAll(); return r; })()""")
    p.conta("visualização", "nem o modo de jogo", modo["dis"] and modo["modo"] == "" and modo["tela"] == "", "%s" % modo)

    nome = s.js("""(() => { const i = document.getElementById('build-name-input'), ro = i.readOnly, era = build.name;
      i.value = 'Nome trocado'; i.dispatchEvent(new Event('change', { bubbles: true }));
      return { ro, mudou: build.name !== era, tela: i.value === era }; })()""")
    p.conta("visualização", "nem o nome", nome["ro"] and not nome["mudou"] and nome["tela"], "%s" % nome)

    s.clicar("#build-marks .mark-slot.cheio", 0.6)
    marcas = s.js("""(() => ({ dialogo: !document.getElementById('marker-dialog').hidden,
      vazios: [...document.querySelectorAll('#build-marks .mark-slot:not(.cheio)')].filter(e => getComputedStyle(e).display !== 'none').length,
      n: build.markers.length }))()""")
    if marcas["dialogo"]:
        s.js("closeMarkerDialog(); 'ok'")
    p.conta("visualização", "nem os marcadores", not marcas["dialogo"] and marcas["vazios"] == 0 and marcas["n"] == 1, "%s" % marcas)

    s.clicar("#mf-switch", 0.5)
    mf = s.js("""(() => { const c = document.getElementById('mf-toggle'), dis = c.disabled, clique = build.masterwork;
      c.disabled = false; c.click(); const r = { dis, clique, forcado: build.masterwork, tela: c.checked }; renderBuildAll(); return r; })()""")
    p.conta("visualização", "nem o Mestre Forjador", mf["dis"] and not mf["clique"] and not mf["forcado"] and not mf["tela"], "%s" % mf)
    p.conta("visualização", "a build saiu igual", s.js("assinaturaDaBuild(build)") == antes)

    # A aba Runas: a faixa leva à página da build, que aparece e não muda
    rotulo = s.js("(document.getElementById('build-runas-abrir') || {}).textContent || ''")
    s.clicar("#build-runas-abrir", 0.9)
    runas_antes = s.js("JSON.stringify(build.runas)")
    r = s.js("""(() => { const tela = document.getElementById('view-runas');
      const so = tela.classList.contains('so-leitura'), dona = document.getElementById('runas-dona').textContent;
      const lp = document.querySelector('#runas-corpo [data-limpar]');
      const alvo = [...document.querySelectorAll('#runas-corpo [data-escolher]')].find(e => !e.classList.contains('escolhida'));
      if (alvo) alvo.click();
      const tr = [...document.querySelectorAll('#runas-trilhas [data-trilha]')].find(b => !b.classList.contains('ativa'));
      if (tr) tr.click();
      return { so, dona, limpar: !!lp && getComputedStyle(lp).display === 'none', alvo: !!alvo, montar: runasEstado.modo }; })()""")
    p.conta("visualização", "sem o Editar a aba Runas mostra a página e não muda",
            "ver" in rotulo and r["so"] and "só para ver" in r["dona"] and r["limpar"] and r["alvo"] and r["montar"] == "montar"
            and s.js("JSON.stringify(build.runas)") == runas_antes, "faixa “%s” · %s" % (rotulo.strip(), r))

    # O caminho de sempre continua: Ligar Editar ali mesmo, e a runa entra
    s.clicar("#rd-ligar", 0.6)
    ligada = s.js("""(() => { const so = document.getElementById('view-runas').classList.contains('so-leitura');
      const alvo = [...document.querySelectorAll('#runas-corpo [data-escolher]')].find(e => !e.classList.contains('escolhida'));
      if (alvo) alvo.click();
      return { editando: build.editing, so, sujo: rascunho.sujo }; })()""")
    p.conta("visualização", "o Ligar Editar da aba Runas libera a página",
            ligada["editando"] and not ligada["so"] and ligada["sujo"] and s.js("JSON.stringify(build.runas)") != runas_antes, "%s" % ligada)

    # E com o Editar, a barra volta a mexer: campeão pelo menu e modo pelo seletor
    s.js("switchTab('build'); showBuildScreen('forja'); 'ok'")
    time.sleep(0.6)
    s.clicar("#build-champ-btn", 0.8)
    abriu = not s.js("document.getElementById('champ-menu').hidden")
    if abriu:
        s.clicar("#champ-list .champ-row.todos", 0.6)
    ed = s.js("""(() => { const sel = document.getElementById('build-mode');
      const outro = [...sel.options].find(o => o.value !== sel.value);
      sel.value = outro.value; sel.dispatchEvent(new Event('change', { bubbles: true }));
      return { champ: build.champion, modo: build.mode, quer: outro.value, dis: sel.disabled }; })()""")
    p.conta("visualização", "com o Editar campeão e modo trocam como antes",
            abriu and ed["champ"] is None and ed["modo"] == ed["quer"] and not ed["dis"], "menu %s · %s" % ("abriu" if abriu else "não abriu", ed))
    s.js("descartarAlteracoes(); 'ok'")
    time.sleep(0.5)

    # A tela de um jogador (Leo, 23/10/2026): retratos e nomes colados. As três
    # colunas eram fixas e encolhiam junto com o menu (janela estreita, zoom
    # alto). Em 1920 continuam três; com o menu apertado, perde coluna.
    colunas_js = """(async () => { const m = document.getElementById('champ-menu');
      if (m.hidden) document.getElementById('build-champ-btn').click();
      await new Promise(r => setTimeout(r, 300));
      const rows = [...document.querySelectorAll('#champ-list .champ-row:not(.todos)')].filter(r => !r.hidden).slice(0, 24);
      const r = { cols: new Set(rows.map(e => e.offsetLeft)).size, menor: Math.min(...rows.map(e => e.getBoundingClientRect().width)) };
      document.getElementById('champ-menu').hidden = true; return r; })()"""
    s.tela(1920, 1080)
    largo = s.js(colunas_js)
    s.tela(420, 800)
    estreito = s.js(colunas_js)
    s.tela_normal()
    time.sleep(0.4)
    p.conta("visualização", "o seletor de campeão não espreme os nomes",
            largo["cols"] == 3 and estreito["menor"] >= 130,
            "1920: %d colunas · menu de 380 px: %d colunas, a menor com %d px" % (largo["cols"], estreito["cols"], estreito["menor"]))

    # F13-T63 (a print de um jogador, 23/10/2026: retratos e nomes empilhados): a linha
    # tem overflow: hidden, então pode encolher a zero. O Firefox mede a lista de
    # campeões pela altura máxima — aqui a altura fica fixa, que é o que ele faz. E o
    # menu de troca de build, com 25 builds (só na memória), encolhia em qualquer navegador.
    aperto = s.js("""(async () => { const espera = (ms) => new Promise(r => setTimeout(r, ms));
      const linhas = (sel) => [...document.querySelectorAll(sel)].filter(x => !x.hidden && x.getClientRects().length);
      const cortadas = (sel) => linhas(sel).filter(x => x.scrollHeight > x.clientHeight + 1).length;
      const st = document.createElement('style'); st.textContent = '.champ-list { height: 380px !important; }'; document.head.appendChild(st);
      if (document.getElementById('champ-menu').hidden) document.getElementById('build-champ-btn').click();
      await espera(400);
      const champ = { cortadas: cortadas('#champ-list .champ-row'), menor: Math.min(...linhas('#champ-list .champ-row').map(x => Math.round(x.getBoundingClientRect().height))) };
      document.getElementById('champ-menu').hidden = true; st.remove();
      library.builds.push(...Array.from({ length: 25 }, (_, i) => ({ id: 'qa-lista-' + i, name: 'Lista ' + (i + 1), cats: [], seq: 1, mode: '' })));
      document.getElementById('build-switch-btn').click(); await espera(400);
      const troca = { n: linhas('#build-switch-list .champ-row').length, cortadas: cortadas('#build-switch-list .champ-row') };
      document.getElementById('build-switch-menu').hidden = true;
      library.builds = library.builds.filter(b => !String(b.id).startsWith('qa-lista-')); renderLibrary();
      return { champ, troca }; })()""")
    p.conta("visualização", "as listas com rolagem não espremem as linhas",
            aperto["champ"]["cortadas"] == 0 and aperto["champ"]["menor"] >= 30 and aperto["troca"]["n"] >= 25 and aperto["troca"]["cortadas"] == 0,
            "campeões medidos como no Firefox: menor linha %d px, %d cortadas · troca de build com %d: %d cortadas"
            % (aperto["champ"]["menor"], aperto["champ"]["cortadas"], aperto["troca"]["n"], aperto["troca"]["cortadas"]))


def _tecla(s, nome):
    """Tecla de verdade (CDP), no elemento com o foco. O Enter leva o "\\r" para o
    navegador gerar o clique num botão, como acontece com a tecla."""
    codigos = {"Escape": 27, "Enter": 13, "Tab": 9}
    extra = {"text": "\r", "unmodifiedText": "\r"} if nome == "Enter" else {}
    s.envia("Input.dispatchKeyEvent", dict({"type": "keyDown", "key": nome, "code": nome, "windowsVirtualKeyCode": codigos[nome]}, **extra))
    s.envia("Input.dispatchKeyEvent", {"type": "keyUp", "key": nome, "code": nome, "windowsVirtualKeyCode": codigos[nome]})
    time.sleep(0.4)


def checar_teclado(s, p):
    """F13-T64: o Esc de um diálogo da forja largava a caixa escolhida (nº 22); o
    Enter no coração da lista abria a build (nº 43); o coração da visualização de
    uma pública acendia só a cópia de passagem (nº 44). Teclas de verdade (CDP)."""
    print("\n%sTECLADO E O CORAÇÃO%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); ligarEdicao(true);
      build.cats[1].items = [{ itemId: 'long-sword', note: '' }]; build.cats[3].items = [{ itemId: 'stat-bonus', note: '' }];
      switchTab('build'); showBuildScreen('forja'); renderBuildAll(); return 'ok'; })()""")
    time.sleep(0.6)
    escolhe = "(() => { build.selectedCatId = build.cats[1].id; renderBuild(); return build.selectedCatId; })()"
    sel1 = '.build-cat[data-cat-id="%s"]' % s.js("build.cats[1].id")
    sel3 = '.build-cat[data-cat-id="%s"]' % s.js("build.cats[3].id")
    # cada diálogo: abre por clique, o Esc fecha ele, e a caixa escolhida fica
    dialogos = [
        ("observação", lambda: (s.hover(sel1 + " .item-tile"), s.clicar(sel1 + " .item-tile .ta-nota", 0.6)), "document.getElementById('note-editor').classList.contains('show')"),
        ("marcador", lambda: s.clicar("#build-marks .mark-slot", 0.6), "!document.getElementById('marker-dialog').hidden"),
        ("tipo da caixa", lambda: s.clicar(sel1 + " .cat-kind", 0.6), "document.getElementById('kind-menu').classList.contains('show')"),
        ("fragmento", lambda: s.clicar(sel3 + " .item-tile .item-icon", 0.8), "!document.getElementById('escolher-fragmento').hidden"),
        ("campeão", lambda: s.clicar("#build-champ-btn", 0.8), "!document.getElementById('champ-menu').hidden"),
        ("troca de build", lambda: s.clicar("#build-switch-btn", 0.8), "!document.getElementById('build-switch-menu').hidden"),
    ]
    ruins = []
    for nome, abre, aberto in dialogos:
        s.js("window.scrollTo(0, 0); 'ok'")
        s.js(escolhe)
        time.sleep(0.3)
        abre()
        abriu = s.js(aberto)
        # se o clique que abriu o diálogo caiu fora da caixa e a largou, ela volta (sem redesenhar, que fecharia o menu)
        largou_no_clique = s.js("(() => { const l = !build.selectedCatId; if (l) build.selectedCatId = build.cats[1].id; return l; })()")
        _tecla(s, "Escape")
        r = s.js("({ aberto: %s, caixa: build.selectedCatId })" % aberto)
        if not abriu or r["aberto"] or not r["caixa"]:
            ruins.append("%s (abriu %s, fechou %s, caixa %s)" % (nome, abriu, not r["aberto"], bool(r["caixa"])))
    s.js(escolhe)
    s.js("document.activeElement && document.activeElement.blur(); 'ok'")
    _tecla(s, "Escape")
    largou = s.js("build.selectedCatId") is None
    p.conta("teclado", "o Esc de um diálogo da forja fecha o diálogo e a caixa escolhida fica",
            not ruins and largou, "; ".join(ruins) if ruins else "observação, marcador, tipo da caixa, fragmento, campeão e troca de build; sem diálogo, o Esc ainda larga a caixa")

    # nº 43: com o foco no coração, o Enter favorita; com o foco na linha, abre
    s.js("descartarAlteracoes(); ligarEdicao(false); switchTab('build'); showBuildScreen('lista'); document.querySelector('.bi-tab[data-view=\"minhas\"]').click(); 'ok'")
    time.sleep(0.6)
    alvo = s.js("build.id")
    s.js("document.querySelector('#bi-rows .bi-row[data-id=\"%s\"] [data-fav]').focus(); 'ok'" % alvo)
    antes = s.js("!!(library.builds.find(b => b.id === %s) || {}).fav" % json.dumps(alvo))
    _tecla(s, "Enter")
    depois = s.js("({ fav: !!(library.builds.find(b => b.id === %s) || {}).fav, tela: buildScreen })" % json.dumps(alvo))
    s.js("document.querySelector('#bi-rows .bi-row[data-id=\"%s\"]').focus(); 'ok'" % alvo)
    _tecla(s, "Enter")
    abriu = s.js("buildScreen")
    p.conta("teclado", "Enter no coração favorita; Enter na linha abre a build",
            depois["fav"] != antes and depois["tela"] == "lista" and abriu == "forja", "coração: %s → %s, ficou na %s; na linha abriu a %s" % (antes, depois["fav"], depois["tela"], abriu))
    s.js("(() => { const b = library.builds.find(x => x.id === %s); if (b && b.fav) { b.fav = false; if (b.id === build.id) build.fav = false; gravarBiblioteca(); } return 1; })()" % json.dumps(alvo))

    # nº 44: o coração da visualização de uma pública favorita a pública de origem
    s.js("""(() => { localStorage.removeItem('publicacao.favoritos');
      publicas.lista = [{ id: 'qf0001', nome: 'Pública para ver', descricao: 'x', campeao: null, modo: '', marcadores: [], versao: 1,
        atualizado_em: new Date().toISOString(), patch: CATALOG.meta.patch, autor: '', engajamentos: 0, pop_dia: 0, popular_semana: false, dias_no_top: 0,
        layout: null, runas: null, habilidades: null, caixas: [{ name: 'Core', kind: 'comum', items: [{ itemId: 'long-sword' }] }] }];
      // recém-carregada: a aba Públicas não vai buscar a lista de verdade por cima desta
      publicas.favs = []; publicas.erro = null; publicas.carregadoEm = Date.now();
      abrirPublicaTemporaria(publicaResumo(publicas.lista[0])); return 'ok'; })()""")
    time.sleep(0.8)
    s.js("showBuildScreen('lista'); document.querySelector('.bi-tab[data-view=\"minhas\"]').click(); 'ok'")
    time.sleep(0.6)
    s.clicar('#bi-rows .bi-row[data-id="tmp:qf0001"] [data-fav]', 0.6)
    fav = s.js("""(() => { const linha = document.querySelector('#bi-rows .bi-row[data-id="tmp:qf0001"] [data-fav]');
      return { favs: favoritosIds(), acesa: !!linha && linha.classList.contains('on') }; })()""")
    s.js("document.querySelector('.bi-tab[data-view=\"publicas\"]').click(); 'ok'")
    time.sleep(0.6)
    nas_publicas = s.js("(() => { const c = document.querySelector('#bi-rows .bi-row[data-id=\"pub:qf0001\"] [data-fav]'); return !!c && c.classList.contains('on'); })()")
    p.conta("teclado", "o coração da visualização de uma pública favorita a pública",
            fav["favs"] == ["qf0001"] and fav["acesa"] and nas_publicas, "%s; nas Públicas acesa: %s" % (fav, nas_publicas))
    s.js("""(() => { localStorage.removeItem('publicacao.favoritos'); publicas.lista = []; publicas.carregadoEm = 0;
      document.querySelector('.bi-tab[data-view="minhas"]').click(); fecharBuild && build.temp && fecharBuild(); return 'ok'; })()""")
    time.sleep(0.5)


def checar_redesenho(s, p):
    """F13-T65: o que ficava na tela sem ser verdade, ou mudava sem nada mudar.
    nº 18: a grade de habilidades com os ícones do campeão anterior; nº 30: a
    descrição e o layout importados invisíveis até sair e voltar; nº 52: um clique
    parado no canto da caixa gravava a grade e sujava o rascunho."""
    print("\n%sREDESENHO%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); ligarEdicao(true);
      build.habilidades = normHabilidades(['Q', 'W', 'E', 'Q']); setBuildChampion({ key: '103', id: 'Ahri', name: 'Ahri' });
      switchTab('build'); showBuildScreen('forja'); return 'ok'; })()""")
    arte = "document.querySelectorAll('#build-habs .bh-letra img').length"
    fim = time.time() + 8
    while time.time() < fim and not s.js(arte):
        time.sleep(0.4)
    if not s.js(arte):
        p.conta("redesenho", "tirar o campeão tira os ícones dele da grade", False, "", pulou=True)
    else:
        s.clicar("#build-champ-btn", 0.8)
        s.clicar("#champ-list .champ-row.todos", 0.8)
        sem = s.js("({ campeao: build.champion, icones: %s })" % arte)
        # e trocar para outra build sem campeão (a lista de builds, o caminho do relato)
        s.js("(() => { setBuildChampion({ key: '103', id: 'Ahri', name: 'Ahri' }); salvarAgora(); return 1; })()")
        fim = time.time() + 6
        while time.time() < fim and not s.js(arte):
            time.sleep(0.4)
        com = s.js(arte)
        outra = s.js("(() => { const b = library.builds.find(x => x.id !== build.id && !x.temp && !x.champion); return b ? b.id : null; })()")
        if not outra:
            s.js("(() => { const id = build.id; createNewBuild('Sem campeão'); const nova = build.id; activateBuild(id); return nova; })()")
            outra = s.js("(() => { const b = library.builds.find(x => x.id !== build.id && !x.temp && !x.champion); return b ? b.id : null; })()")
        s.js("ligarEdicao(false); activateBuild(%s); ligarEdicao(true); renderBuildAll(); 'ok'" % json.dumps(outra))
        time.sleep(0.6)
        troca = s.js(arte)
        p.conta("redesenho", "tirar o campeão (ou trocar para uma build sem ele) tira os ícones da grade",
                sem["campeao"] is None and sem["icones"] == 0 and com > 0 and troca == 0,
                "sem campeão: %s ícones · com a Ahri: %s · na build sem campeão: %s" % (sem["icones"], com, troca))

    # nº 30: importar com DESCRIÇÃO e LAYOUT (sem campeão nem Passiva do Ornn) mostra os dois na hora
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); switchTab('build'); showBuildScreen('forja');
      document.getElementById('io-panel').classList.add('show');
      document.getElementById('import-text').value = ['BUILD: Importada com descrição', 'DESCRIÇÃO: Uma descrição que tem de aparecer', 'LAYOUT: Trilha por fases', '', '[COMUM] Core', '- Espada Longa'].join(String.fromCharCode(10));
      return 'ok'; })()""")
    s.clicar("#import-btn", 1.0)
    imp = s.js("""({ nome: build.name, desc: document.getElementById('build-desc').value, layout: document.getElementById('build-layout').value,
      quer: layoutValido('trilha'), gravado: build.layout })""")
    p.conta("redesenho", "a descrição e o layout importados aparecem na hora",
            imp["nome"] == "Importada com descrição" and imp["desc"] == "Uma descrição que tem de aparecer" and imp["layout"] == imp["gravado"] == "trilha",
            "%s" % imp)

    # nº 52: o clique parado no canto não grava; arrastar continua gravando
    s.js("""(() => { if (!build.editing) ligarEdicao(true); if (rascunho.sujo) salvarAgora();
      const c = build.cats[0]; c.kind = 'comum'; c.cols = 3; c.rows = 0;
      c.items = ['long-sword', 'dagger', 'boots', 'cloth-armor', 'amplifying-tome'].map(i => ({ itemId: i, note: '' }));
      salvarAgora(); renderBuild(); window.scrollTo(0, 0); return 'ok'; })()""")
    time.sleep(0.5)
    canto = '.build-cat[data-cat-id="%s"] .cat-resize' % s.js("build.cats[0].id")
    s.clicar(canto, 0.5)
    parado = s.js("({ sujo: rascunho.sujo, cols: build.cats[0].cols, rows: build.cats[0].rows })")
    p0 = s.hover(canto)
    for tipo, x in (("mousePressed", p0[0]), ("mouseMoved", p0[0] + 95), ("mouseReleased", p0[0] + 95)):
        s.envia("Input.dispatchMouseEvent", {"type": tipo, "x": x, "y": p0[1], "button": "left", "buttons": 1 if tipo != "mouseReleased" else 0, "clickCount": 1})
        time.sleep(0.15)
    time.sleep(0.4)
    arrastado = s.js("({ sujo: rascunho.sujo, cols: build.cats[0].cols })")
    p.conta("redesenho", "clicar no canto sem arrastar não grava a grade (arrastar grava)",
            not parado["sujo"] and parado["cols"] == 3 and parado["rows"] == 0 and arrastado["sujo"] and arrastado["cols"] == 4,
            "parado %s · arrastado %s" % (parado, arrastado))
    s.js("descartarAlteracoes(); 'ok'")


def checar_importacao(s, p):
    """F13-T66: três furos da importação. nº 54: linha com colchete virava caixa
    (link de markdown, "[Dica]" de texto de IA); nº 55: o Arsenal.json nascia com
    uma grade e voltava com outra depois do F5; nº 56: régua abaixo do BUILD:
    seguida de um BUILD: repetido criava uma build fantasma. Pelo botão de verdade."""
    print("\n%sIMPORTAÇÃO%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    importa = lambda texto: s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); switchTab('build'); showBuildScreen('forja');
      document.getElementById('io-panel').classList.add('show'); document.getElementById('import-text').value = %s; return 'ok'; })()""" % json.dumps(texto))
    importa("\n".join(["BUILD: Texto de IA", "[Guia completo](https://exemplo.com/guia)", "[COMUM] Início", "- Espada Longa",
                       "[Dica] comprar o Gume cedo", "- Gume do Infinito", "[ESCOLHA] Botas", "- Botas"]))
    s.clicar("#import-btn", 1.0)
    caixas = s.js("build.cats.map(c => [c.name, c.kind, c.items.map(e => byId[e.itemId].namePt)])")
    p.conta("importação", "colchete que não é tipo de caixa é texto (e ESCOLHA sem o 1 vale)",
            caixas == [["Início", "comum", ["Espada Longa", "Gume do Infinito"]], ["Botas", "escolha", ["Botas"]]], "%s" % caixas)

    # nº 55: o Arsenal.json com um bloco de 2 itens tem a mesma grade antes e depois do F5
    arsenal = {"title": "Arsenal de teste", "associatedMaps": [], "associatedChampions": [],
               "blocks": [{"type": "Início", "items": [{"id": "1036", "count": 1}, {"id": "1001", "count": 1}]}]}
    importa(json.dumps(arsenal))
    s.clicar("#import-btn", 1.0)
    antes = s.js("({ id: build.id, cols: catCols(build.cats[0]), rows: catRows(build.cats[0]), n: build.cats[0].items.length })")
    s.js("salvarAgora(); 'ok'")
    s.abrir(); time.sleep(0.8); s.entrar()
    depois = s.js("(() => { const b = library.builds.find(x => x.id === %s); return b ? { cols: catCols(b.cats[0]), rows: catRows(b.cats[0]) } : null; })()" % json.dumps(antes["id"]))
    # 6 colunas, como a caixa do texto importado sem grade (Leo, 17/10/2026, escolha B)
    p.conta("importação", "o Arsenal.json tem a mesma grade antes e depois do F5",
            antes["n"] == 2 and depois and antes["cols"] == depois["cols"] == 6 and antes["rows"] == depois["rows"], "antes %s · depois do F5 %s" % (antes, depois))

    # nº 56: a régua abaixo do título com o cabeçalho depois é enfeite; a do lote exportado separa
    partes = s.js("""(() => { const N = String.fromCharCode(10), R = '='.repeat(40);
      const mao = dividirBuilds(['BUILD: Jinx', '=====', 'MODO: ARAM', 'BUILD: Jinx (ARAM)', '[COMUM] Core', '- Gume do Infinito'].join(N)).map(textToBuild);
      const lote = dividirBuilds(['BUILD: Sem caixa', 'MODO: ARAM', '', R, '', 'BUILD: Com caixa', '[COMUM] Core', '- Espada Longa'].join(N)).map(textToBuild);
      return { mao: mao.map(r => [r.name, r.mode, r.cats.length]), lote: lote.map(r => [r.name, r.cats.length]) }; })()""")
    p.conta("importação", "BUILD: repetido depois de régua e cabeçalho só renomeia; o lote exportado ainda separa",
            partes["mao"] == [["Jinx (ARAM)", "ARAM", 1]] and partes["lote"] == [["Sem caixa", 0], ["Com caixa", 1]], "%s" % partes)


def checar_lote_e_ornn(s, p):
    """F13-T67. nº 51: excluir a visualização de uma pública pelo lote perguntava
    "As publicadas também saem do site" e dizia "1 build(s) excluída(s)" — a
    visualização só fecha. nº 58: a Passiva do Ornn na alternativa de baixo de uma
    Escolha 1 aparecia na nota da soma, e nada somava."""
    print("\n%sLOTE E A PASSIVA DO ORNN%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); ligarEdicao(false);
      window.__perguntas = []; window.__confirmOrig = window.__confirmOrig || window.confirm;
      window.confirm = (t) => { window.__perguntas.push(String(t)); return true; };
      createNewBuild('Para excluir no lote'); gravarBuild();
      publicas.lista = [{ id: 'ql0001', nome: 'Pública só para ver', descricao: 'x', campeao: null, modo: '', marcadores: [], versao: 1,
        atualizado_em: new Date().toISOString(), patch: CATALOG.meta.patch, autor: '', engajamentos: 0, pop_dia: 0, popular_semana: false, dias_no_top: 0,
        layout: null, runas: null, habilidades: null, caixas: [{ name: 'Core', kind: 'comum', items: [{ itemId: 'long-sword' }] }] }];
      publicas.favs = []; publicas.erro = null; publicas.carregadoEm = Date.now();
      return 'ok'; })()""")
    lote = lambda ids: (s.js("showBuildScreen('lista'); document.querySelector('.bi-tab[data-view=\"minhas\"]').click(); 'ok'"), time.sleep(0.5),
                        s.clicar("#bi-lote", 0.4), [s.clicar('.bi-row[data-id="%s"]' % i, 0.3) for i in ids],
                        s.clicar("#bl-excluir", 1.0), time.sleep(0.6))
    # só a visualização
    s.js("abrirPublicaTemporaria(publicaResumo(publicas.lista[0])); 'ok'"); time.sleep(0.8)
    lote(["tmp:ql0001"])
    so = s.js("({ pergunta: window.__perguntas.pop() || '', msg: document.getElementById('bl-msg').textContent, existe: library.builds.some(b => b.id === 'tmp:ql0001') })")
    s.clicar("#bl-sair", 0.3)
    # a visualização e uma build sua, não publicada
    s.js("abrirPublicaTemporaria(publicaResumo(publicas.lista[0])); 'ok'"); time.sleep(0.8)
    propria = s.js("(library.builds.find(b => b.name === 'Para excluir no lote') || {}).id")
    lote(["tmp:ql0001", propria])
    mista = s.js("({ pergunta: window.__perguntas.pop() || '', msg: document.getElementById('bl-msg').textContent })")
    s.clicar("#bl-sair", 0.3)
    s.js("window.confirm = window.__confirmOrig; publicas.lista = []; publicas.carregadoEm = 0; 'ok'")
    p.conta("lote e ornn", "excluir uma visualização pelo lote diz que fecha (e só fala do site quando há publicada)",
            so["pergunta"].startswith("Fechar 1 visualização de pública?") and "a pública continua no site" in so["pergunta"] and "saem do site" not in so["pergunta"]
            and so["msg"] == "1 visualização fechada." and not so["existe"]
            and mista["pergunta"].startswith("Excluir 1 build(s)?") and "E fechar 1 visualização" in mista["pergunta"]
            and "saem do site" not in mista["pergunta"] and "Isso não dá pra desfazer." in mista["pergunta"]
            and mista["msg"] == "1 build(s) excluída(s) e 1 visualização fechada.",
            "só a visualização: %r → %r · com uma build sua: %r" % (so["pergunta"][:60], so["msg"], mista["msg"]))

    # nº 58: a forja na alternativa de baixo de uma Escolha 1 é avisada fora da soma
    garantir_build_editavel(s)
    r = s.js("""(() => { const por = (n) => CATALOG.items.find(i => i.namePt === n).slug;
      build.masterwork = true;
      build.cats[2].kind = 'escolha'; build.cats[2].items = [{ itemId: por('Presságio de Randuin'), note: '' }, { itemId: por('Armadura de Espinhos'), note: '' }];
      renderBuildAll();
      setForged(build.cats[2].id, 1); const embaixo = document.getElementById('build-totals').textContent;
      setForged(build.cats[2].id, 0); const padrao = document.getElementById('build-totals').textContent;
      return { embaixo, padrao }; })()""")
    s.js("descartarAlteracoes(); 'ok'")
    p.conta("lote e ornn", "a Passiva do Ornn na alternativa de baixo é avisada fora da soma",
            "Armadura de Espinhos — fora da soma" in r["embaixo"] and "Presságio de Randuin" in r["padrao"] and "fora da soma" not in r["padrao"],
            "embaixo: …%s… · no padrão: …%s…" % (r["embaixo"][r["embaixo"].find("Passiva"):][:80], r["padrao"][r["padrao"].find("Passiva"):][:50]))


def checar_conferencia(s, p):
    """F13-T68 (Leo, 20/10/2026: "acho bem mais prático ser um ícone no canto inferior
    da tela ao invés de um pop up imenso"): enquanto confere a trava, a aba fica
    parada, mas o aviso é um ícone discreto no canto inferior — e só se passar de
    meio segundo. O "Aberto em outra aba" segue no centro (grupo "duas abas")."""
    print("\n%sCONFERÊNCIA DAS ABAS%s" % (AMARELO, FIM))
    r = s.js("""(async () => { virarEspectadora('conferindo');
      const v = document.getElementById('aba-dona'); const antes = getComputedStyle(v).opacity;
      await new Promise(r => setTimeout(r, 900));
      const rc = v.getBoundingClientRect();
      const out = { antes, depois: getComputedStyle(v).opacity, w: Math.round(rc.width), h: Math.round(rc.height),
        direita: Math.round(innerWidth - rc.right), baixo: Math.round(innerHeight - rc.bottom), fundo: getComputedStyle(v).backgroundColor,
        parada: [...document.body.children].some(e => e !== v && e.inert), titulo: v.querySelector('.md-panel').title,
        leitor: (document.getElementById('aba-dona-titulo') || {}).textContent };
      assumirVez();
      out.voltou = ![...document.body.children].some(e => e.inert) && !document.getElementById('aba-dona');
      return out; })()""")
    p.conta("conferência", "a conferência das abas é um ícone no canto inferior, só se demorar",
            r["antes"] == "0" and r["depois"] == "1" and r["w"] <= 48 and r["h"] <= 48 and 10 <= r["direita"] <= 30 and 10 <= r["baixo"] <= 30
            and r["fundo"] in ("rgba(0, 0, 0, 0)", "transparent") and r["parada"] and "Conferindo" in r["titulo"]
            and r["leitor"] == "Conferindo as abas" and r["voltou"], "%s" % r)


def checar_rota(s, p):
    """F13-T69 (Leo, 24/10/2026: a rota num seletor da barra da build): o seletor
    (só fora do ARAM, só com o Editar), e a rota em todo caminho — disco, texto,
    link, lote, cópias e publicação (com a volta sem ela enquanto o servidor não
    tiver a coluna: docs/servidor/rota.sql)."""
    print("\n%sROTA%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); ligarEdicao(false); build.mode = ''; renderBuildAll(); return 'ok'; })()""")
    muda = """(() => { const sel = document.getElementById('build-rota'); sel.value = %s; sel.dispatchEvent(new Event('change', { bubbles: true })); return build.rota; })()"""
    sem_editar = s.js(muda % json.dumps("top"))
    tranca = s.js("document.getElementById('build-rota').disabled")
    s.js("ligarEdicao(true); 'ok'")
    com_editar = s.js(muda % json.dumps("top"))
    s.js("salvarAgora(); 'ok'")
    aram = s.js("(() => { build.mode = 'ARAM'; renderBuildAll(); const h = document.getElementById('rota-pick').hidden; build.mode = ''; renderBuildAll(); return h; })()")
    alvo = s.js("build.id")
    s.abrir(); time.sleep(0.8); s.entrar()
    disco = s.js("(library.builds.find(b => b.id === %s) || {}).rota" % json.dumps(alvo))
    p.conta("rota", "o seletor: só com o Editar, some no ARAM, e a rota fica gravada",
            sem_editar == "" and tranca and com_editar == "top" and aram and disco == "top",
            "sem Editar %r (trancado %s) · com Editar %r · some no ARAM %s · depois do F5 %r" % (sem_editar, tranca, com_editar, aram, disco))

    # texto, link e lote: a rota vai e volta; no ARAM o texto não a escreve
    ida = s.js("""(() => { activateBuild(%s); const b = library.builds.find(x => x.id === build.id), N = String.fromCharCode(10);
      const texto = textoDaBuild(buildResumo(b));
      const volta = textToBuild(texto).rota;
      const apelido = textToBuild(['BUILD: x', 'ROTA: jungle', '[COMUM] Core', '- Espada Longa'].join(N)).rota;
      const lk = linkParaBuild('#' + buildParaLink(b).split('#')[1]).rota;
      const lote = dividirBuilds(loteParaTexto([b.id])).map(textToBuild)[0].rota;
      const aram = textoDaBuild(Object.assign(buildResumo(b), { mode: 'ARAM' })).includes('ROTA:');
      return { linha: texto.split(N).find(l => l.startsWith('ROTA:')) || '', volta, apelido, lk, lote, aram }; })()""" % json.dumps(alvo))
    p.conta("rota", "a rota vai e volta no texto, no link e no lote (e o ARAM não a escreve)",
            ida["linha"] == "ROTA: Top" and ida["volta"] == ida["lk"] == ida["lote"] == "top" and ida["apelido"] == "selva" and not ida["aram"], "%s" % ida)
    # F13-T71: a chave "r" do link é das runas — com as duas na build, a página
    # apagava a rota (a ida e volta acima é de uma build sem runas e passava)
    ambas = s.js("""(() => { const b = library.builds.find(x => x.id === build.id), t = RUNAS.trilhas[0];
      const runas = normRunas({ primaria: t.id, assinatura: t.slots[0].runas[0].id, slots: ['', '', ''] });
      const l = buildParaLink(Object.assign({}, b, { id: 'qa-link-71', rota: 'selva', runas }));
      const volta = linkParaBuild(l.slice(l.indexOf('#')));
      // o link que a T69 gerou: sem runas, a rota ia como texto na "r"
      const velho = '#b=' + b64urlEncode(JSON.stringify({ v: 1, n: 'Link da T69', m: '', d: '', r: 'meio', c: null, k: [], cats: [{ n: 'Core', k: 'comum', i: ['long-sword'] }] }));
      return { rota: volta.rota, runa: volta.runas.assinatura === runas.assinatura, velho: (linkParaBuild(velho) || {}).rota }; })()""")
    p.conta("rota", "o link leva a rota junto com as runas (e o link da T69 ainda abre com a rota)",
            ambas == {"rota": "selva", "runa": True, "velho": "meio"}, "%s" % ambas)

    # importar pelo botão, duplicar e copiar uma pública levam a rota
    s.js("""(() => { switchTab('build'); showBuildScreen('forja'); document.getElementById('io-panel').classList.add('show');
      document.getElementById('import-text').value = ['BUILD: Importada com rota', 'ROTA: Suporte', '[COMUM] Core', '- Espada Longa'].join(String.fromCharCode(10)); return 'ok'; })()""")
    time.sleep(1.0)   # a forja acabou de abrir e ainda se arruma: medido antes disso, o clique cai ao lado do botão
    s.clicar("#import-btn", 1.0)
    copias = s.js("""(() => { const imp = build.rota; duplicateBuild(build.id); const dup = build.rota;
      publicas.lista = [{ id: 'qr0001', nome: 'Pública com rota', descricao: 'x', campeao: null, modo: '', marcadores: [], versao: 1,
        atualizado_em: new Date().toISOString(), patch: CATALOG.meta.patch, autor: '', engajamentos: 0, pop_dia: 0, popular_semana: false, dias_no_top: 0,
        layout: null, runas: null, habilidades: null, rota: 'meio', caixas: [{ name: 'Core', kind: 'comum', items: [{ itemId: 'long-sword' }] }] }];
      publicas.favs = []; publicas.erro = null; publicas.carregadoEm = Date.now();
      const d = publicaResumo(publicas.lista[0]); copiarPublica(d); const copia = build.rota;
      publicas.lista = []; publicas.carregadoEm = 0;
      return { imp, dup, resumo: d.rota, copia }; })()""")
    p.conta("rota", "importar, duplicar e copiar uma pública levam a rota",
            copias == {"imp": "suporte", "dup": "suporte", "resumo": "meio", "copia": "meio"}, "%s" % copias)

    # publicar manda p_rota; servidor sem a coluna recusa — publica de novo sem ela, com as runas
    pub = s.js("""(async () => { const pedidos = []; window.__fetchOrigR = window.fetch;
      window.fetch = function (u, o) { const t = String(u);
        if (t.includes('publicar_build')) { const corpo = JSON.parse(o.body); pedidos.push(Object.keys(corpo).sort().join(','));
          // como o PostgREST: a mensagem lista os parâmetros que chegaram
          if ('p_rota' in corpo) return Promise.resolve(new Response(JSON.stringify({ message: 'Could not find the function public.publicar_build(' + Object.keys(corpo).sort().join(', ') + ') in the schema cache' }), { status: 404, headers: { 'Content-Type': 'application/json' } }));
          return Promise.resolve(new Response(JSON.stringify({ id: 'qr9999', versao: 1 }), { status: 200, headers: { 'Content-Type': 'application/json' } })); }
        if (t.includes('/rpc/') || t.includes('/rest/')) return Promise.resolve(new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }));
        return window.__fetchOrigR.call(this, u, o); };
      const N = String.fromCharCode(10);
      build.desc = 'para publicar'; build.markers = MARCADORES.slice(0, 3).map(m => ({ t: 'tag', id: m.id })); salvarAgora();
      await publicarBuild(build.id); await new Promise(r => setTimeout(r, 400)); fecharPub();
      window.fetch = window.__fetchOrigR;
      const b = library.builds.find(x => x.id === build.id);
      const r = { pedidos, pubId: b && b.pubId };
      if (b) { b.pubId = null; b.pubVersao = 0; b.pubEm = 0; b.pubAssinatura = ''; if (build.id === b.id) { build.pubId = null; } gravarBiblioteca(); }
      return r; })()""")
    p.conta("rota", "publicar manda a rota; sem a coluna no servidor, publica sem ela (com as runas)",
            len(pub["pedidos"]) == 2 and "p_rota" in pub["pedidos"][0] and "p_rota" not in pub["pedidos"][1] and "p_runas" in pub["pedidos"][1] and pub["pubId"] == "qr9999",
            "%s" % pub)
    s.js("descartarAlteracoes && rascunho.sujo && descartarAlteracoes(); 'ok'")


def checar_filtro_rota(s, p):
    """F13-T75 (Leo, 24/10/2026: "implementar a rota no sistema de busca, acho bom
    colocar em baixo dos marcadores padrão"): no "Filtrar por marcador", a seção
    Rota logo abaixo dos marcadores padrão; vale em Minhas e em Públicas; a build
    de rota "Qualquer" e a de ARAM (sem rota) não entram no filtro de uma rota."""
    print("\n%sFILTRO DE ROTA%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); ligarEdicao(false);
      const base = library.builds.find(b => !b.temp);
      const mk = (id, nome, mode, rota) => Object.assign(JSON.parse(JSON.stringify(base)), { id, name: nome, mode, rota, pubId: null, updatedAt: Date.now() });
      library.builds = library.builds.filter(b => !String(b.id).startsWith('qa-ro-'));
      library.builds.push(mk('qa-ro-top', 'QA rota Top', "Summoner's Rift", 'top'), mk('qa-ro-selva', 'QA rota Selva', "Summoner's Rift", 'selva'),
        mk('qa-ro-qualquer', 'QA rota Qualquer', "Summoner's Rift", ''), mk('qa-ro-aram', 'QA rota ARAM', 'ARAM', 'selva'));
      gravarBiblioteca(); biFilter.marker = null; biFilter.champ = null; biFilter.rota = null;
      switchTab('build'); showBuildScreen('lista'); document.getElementById('bi-search').value = 'QA rota'; renderBuildIndex(); refletirFiltro(); return 1; })()""")
    time.sleep(0.6)
    NA_TELA = "[...document.querySelectorAll('#bi-rows .bi-row')].map(r => r.dataset.pub || r.dataset.id).filter(x => /^qa-ro-|^qr7/.test(x)).sort()"
    s.clicar("#bi-filter", 0.4)
    menu = s.js("""(() => { const r = document.getElementById('bf-rotas'); if (!r) return null; const rot = r.previousElementSibling;
      return { rotulo: rot && rot.textContent, antes: rot && rot.previousElementSibling && rot.previousElementSibling.id,
               chips: [...r.querySelectorAll('.bf-rota')].map(b => b.getAttribute('aria-label') + (b.querySelector('img') && b.querySelector('img').naturalWidth > 0 ? '' : ' (sem ícone)')) }; })()""")
    todas = s.js(NA_TELA)
    sel = '#bf-rotas .bf-rota[data-rota="%s"]'
    tem_selva = s.js("!!document.querySelector(%s)" % json.dumps(sel % "selva"))
    if tem_selva:
        s.clicar(sel % "selva", 0.4)
    selva = {"tela": s.js(NA_TELA), "botao": s.js("document.getElementById('bi-filter').textContent")}
    if tem_selva:
        s.clicar(sel % "selva", 0.4)             # de novo: solta
    solto = s.js(NA_TELA)
    p.conta("filtro de rota", "no filtro, a Rota (os cinco ícones, com o nome) vem logo abaixo dos marcadores padrão; em Minhas, a Selva mostra só a da Selva (nem a \"Qualquer\", nem a de ARAM) e o segundo clique solta",
            menu == {"rotulo": "Rota", "antes": "bf-tags", "chips": ["Top", "Selva", "Meio", "Atirador", "Suporte"]}
            and todas == ["qa-ro-aram", "qa-ro-qualquer", "qa-ro-selva", "qa-ro-top"] and selva["tela"] == ["qa-ro-selva"]
            and selva["botao"] == "Filtro: Selva" and solto == todas,
            "menu %s · todas %s · Selva %s · solto %s" % (menu, todas, selva, solto))

    # públicas: a lista de mentira (sem tocar no servidor); a de ARAM e a sem rota ficam de fora
    s.js("""(() => { const pub = (id, nome, modo, rota) => ({ id, nome, descricao: 'x', campeao: null, modo, marcadores: [], versao: 1,
        atualizado_em: new Date().toISOString(), patch: CATALOG.meta.patch, autor: '', engajamentos: 0, pop_dia: 0, popular_semana: false, dias_no_top: 0,
        layout: null, runas: null, habilidades: null, rota, caixas: [{ name: 'Core', kind: 'comum', items: [{ itemId: 'long-sword' }] }] });
      publicas.lista = [pub('qr7001', 'QA rota pub Meio', "Summoner's Rift", 'meio'), pub('qr7002', 'QA rota pub sem rota', "Summoner's Rift", ''),
        pub('qr7003', 'QA rota pub ARAM', 'ARAM', 'meio'), pub('qr7004', 'QA rota pub Meio 2', '', 'meio')];
      publicas.favs = []; publicas.erro = null; publicas.carregadoEm = Date.now(); return 1; })()""")
    s.envia("Input.dispatchMouseEvent", {"type": "mousePressed", "x": 5, "y": 5, "button": "left", "clickCount": 1})
    s.envia("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": 5, "y": 5, "button": "left", "clickCount": 1})
    time.sleep(0.3)
    s.clicar('.bi-tab[data-view="publicas"]', 0.6)
    s.js("(() => { publicas.carregadoEm = Date.now(); renderBuildIndex(); return 1; })()"); time.sleep(0.4)
    pub_todas = s.js(NA_TELA)
    s.clicar("#bi-filter", 0.4)
    if s.js("!!document.querySelector(%s)" % json.dumps(sel % "meio")):
        s.clicar(sel % "meio", 0.4)
    pub_meio = s.js(NA_TELA)
    s.clicar("#bf-clear", 0.4)
    limpo = {"tela": s.js(NA_TELA), "rota": s.js("biFilter.rota"), "botao": s.js("document.getElementById('bi-filter').textContent")}
    p.conta("filtro de rota", "em Públicas, a Meio mostra as duas da Meio (não a de ARAM, não a sem rota); \"Limpar filtro\" solta a rota",
            pub_todas == ["qr7001", "qr7002", "qr7003", "qr7004"] and pub_meio == ["qr7001", "qr7004"]
            and limpo == {"tela": pub_todas, "rota": None, "botao": "Filtrar por marcador"},
            "todas %s · Meio %s · limpo %s" % (pub_todas, pub_meio, limpo))
    s.js("""(() => { publicas.lista = []; publicas.carregadoEm = 0; library.builds = library.builds.filter(b => !String(b.id).startsWith('qa-ro-'));
      gravarBiblioteca(); document.getElementById('bi-search').value = ''; return 1; })()""")
    s.clicar('.bi-tab[data-view="minhas"]', 0.4)
    # o menu cabe na janela nas resoluções do Leo (alinhado pela esquerda do botão, passava 60 px em 1600 e 1280)
    cabe = {}
    for w, h in ((2560, 1440), (1920, 1080), (1600, 900), (1280, 800)):
        s.tela(w, h)
        s.js("document.getElementById('bi-filter-menu').hidden = true; 1")
        s.clicar("#bi-filter", 0.4)
        cabe[w] = s.js("(() => { const m = document.getElementById('bi-filter-menu').getBoundingClientRect(); return Math.round(m.left) >= 0 && Math.round(m.right) <= window.innerWidth && document.documentElement.scrollWidth <= window.innerWidth; })()")
        s.clicar("#bi-filter", 0.3)
    s.tela_normal()
    p.conta("filtro de rota", "o menu do filtro cabe na janela em 2560, 1920, 1600 e 1280 (sem rolagem lateral)", all(cabe.values()), "%s" % cabe)


def checar_cadeado(s, p):
    """F13-T70 (Leo, 15/10 e 24/10/2026): o cadeado impede o item trancado nas
    caixas que contam (Comum, Prioridade e o padrão da Escolha 1); a Opcional e as
    alternativas aceitam. Lido do catálogo: a rota (Selva, Meio, a linha do Atlas),
    o grupo "Limitado a 1", a runa exigida e o "Substitui as Botas"."""
    print("\n%sCADEADO%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    dado = s.js("""(() => { const t = travas(), conta = (r) => Object.values(t.rota).filter(x => x === r).length;
      return { selva: conta('selva'), meio: conta('meio'), suporte: conta('suporte'), runas: Object.keys(t.runa).length,
               grupos: new Set(Object.values(t.grupos).flat()).size, sub: Object.entries(t.substitui).map(([a, b]) => byId[a].namePt + '>' + byId[b].namePt) }; })()""")
    p.conta("cadeado", "o cadeado lê do catálogo a rota, os grupos, as runas e a substituição",
            dado["selva"] == 3 and dado["meio"] == 7 and dado["suporte"] == 8 and dado["runas"] == 5 and dado["grupos"] == 24
            and dado["sub"] == ["Botas Levemente Mágicas>Botas"], "%s" % dado)

    # cenário: rota Top; caixas Comum (0), Prioridade (1), Opcional (2), Escolha 1 (3)
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); ligarEdicao(true);
      const por = (n) => CATALOG.items.find(i => i.namePt === n).slug;
      build.mode = "Summoner's Rift"; build.rota = 'top'; build.runas = normRunas(null);
      // a build aberta pode ter vindo de outro grupo com menos caixas (uma importada, por exemplo)
      while (build.cats.length < 4) build.cats.push({ id: 'cat-qa-' + build.cats.length + '-' + Date.now(), name: 'Caixa', desc: '', kind: 'comum', span: 2, cols: 3, rows: 0, items: [] });
      build.cats = build.cats.slice(0, 4);
      ['comum', 'prioridade', 'opcional', 'escolha'].forEach((k, i) => { build.cats[i].kind = k; build.cats[i].items = []; });
      build.cats[0].items = [{ itemId: por('Hidra Raivosa'), note: '' }];
      build.cats[3].items = [{ itemId: por('Gume do Infinito'), note: '' }];
      build.selectedCatId = build.cats[1].id; build.pickerQuery = ''; switchTab('build'); showBuildScreen('forja'); renderBuildAll();
      window.__por = por; return 'ok'; })()""")
    time.sleep(0.8)
    def poe_pela_bandeja(nome, caixa):
        s.js("""(() => { build.selectedCatId = build.cats[%d].id; build.pickerQuery = %s; document.getElementById('picker-search').value = %s; renderBuildAll(); return 1; })()"""
             % (caixa, json.dumps(nome), json.dumps(nome)))
        time.sleep(0.3)
        sel = '#picker-list .picker-row[data-item-id="%s"]' % s.js("__por(%s)" % json.dumps(nome))
        trancada = s.js("(() => { const r = document.querySelector(%s); return r ? r.classList.contains('trancado') : null; })()" % json.dumps(sel))
        antes = s.js("build.cats[%d].items.length" % caixa)
        s.clicar(sel, 0.5)
        depois = s.js("build.cats[%d].items.length" % caixa)
        aviso = s.js("document.getElementById('edit-hint').textContent")
        return {"trancada": trancada, "entrou": depois > antes, "aviso": aviso}
    selva_prio = poe_pela_bandeja("Cria de Andabrisas", 1)
    selva_opc = poe_pela_bandeja("Cria de Andabrisas", 2)
    p.conta("cadeado", "fora da Selva, o item de selva não entra na caixa que conta (a Opcional aceita)",
            selva_prio["trancada"] and not selva_prio["entrou"] and "só na rota Selva" in selva_prio["aviso"]
            and selva_opc["trancada"] is False and selva_opc["entrou"], "Prioridade %s · Opcional %s" % (selva_prio, selva_opc))
    hidra = poe_pela_bandeja("Hidra Titânica", 1)
    alternativa = poe_pela_bandeja("Hidra Titânica", 3)
    sobe = s.js("""(() => { const c = build.cats[3]; const ultimo = c.items[c.items.length - 1].itemId; moveItem(c.id, c.items.length - 1, c.id, 0);
      return { subiu: c.items[0].itemId === ultimo }; })()""")
    # F13-T76 (Leo, 24/10/2026): a Escolha 1 é exceção do cadeado — a alternativa entra e pode virar a padrão
    p.conta("cadeado", "o grupo “Limitado a 1”: a segunda Hidra não conta junto; na Escolha 1 (exceção do cadeado) ela entra e pode subir a padrão",
            hidra["trancada"] and not hidra["entrou"] and "grupo Hidra" in hidra["aviso"] and "Hidra Raivosa" in hidra["aviso"]
            and alternativa["entrou"] and alternativa["trancada"] is False and sobe["subiu"], "Prioridade %s · alternativa %s · subir %s" % (hidra, alternativa, sobe))

    # a runa: Botas Levemente Mágicas pedem Calçados Mágicos; com a runa, as Botas comuns ficam trancadas
    sem_runa = poe_pela_bandeja("Botas Levemente Mágicas", 1)
    s.js("""(() => { const id = 'calcados-magicos'; let tr, si;
      RUNAS.trilhas.forEach(t => t.slots.forEach((sl, i) => { if (sl.runas.some(r => r.id === id)) { tr = t.id; si = i; } }));
      const slots = ['', '', '']; slots[si - 1] = id;
      build.runas = normRunas({ primaria: tr, assinatura: '', slots }); renderBuildAll(); return [tr, si]; })()""")
    com_runa = poe_pela_bandeja("Botas Levemente Mágicas", 1)
    botas = poe_pela_bandeja("Botas", 0)
    p.conta("cadeado", "a runa: as Botas Levemente Mágicas pedem a Calçados Mágicos; com ela, as Botas ficam trancadas",
            sem_runa["trancada"] and not sem_runa["entrou"] and "pede a runa Calçados Mágicos" in sem_runa["aviso"]
            and com_runa["entrou"] and botas["trancada"] and not botas["entrou"] and "Botas Levemente Mágicas vem no lugar" in botas["aviso"],
            "sem a runa %s · com a runa %s · Botas %s" % (sem_runa, com_runa, botas))

    # o que já está na build: trocar a rota tranca o item de selva que estava numa caixa que conta
    marca = s.js("""(() => { build.rota = ''; build.cats[0].items.push({ itemId: __por('Filhote de Garrabrasa'), note: '' }); renderBuildAll();
      const livre = !!document.querySelector('.build-cat[data-cat-id="' + build.cats[0].id + '"] .item-tile.trancado');
      build.rota = 'meio'; renderBuildAll();
      const t = [...document.querySelectorAll('.build-cat[data-cat-id="' + build.cats[0].id + '"] .item-tile.trancado')];
      return { livre, trancados: t.map(x => byId[build.cats[0].items[Number(x.dataset.index)].itemId].namePt), motivo: t[0] && t[0].dataset.cadeado }; })()""")
    p.conta("cadeado", "o item que já estava na build ganha o cadeado quando a rota muda",
            not marca["livre"] and marca["trancados"] == ["Filhote de Garrabrasa"] and "só na rota Selva" in (marca["motivo"] or ""), "%s" % marca)

    # a loja: o card trancado e o clique que não entra
    s.js("""(() => { build.cats[0].items = build.cats[0].items.filter(e => e.itemId !== __por('Filhote de Garrabrasa')); build.selectedCatId = build.cats[1].id;
      renderBuildAll(); switchTab('catalog'); document.getElementById('search-input').value = 'Broto de Esmagamusgo';
      document.getElementById('search-input').dispatchEvent(new Event('input', { bubbles: true })); return 1; })()""")
    time.sleep(0.8)
    card = '#grid .card[data-slug="%s"]' % s.js("__por('Broto de Esmagamusgo')")
    trancado = s.js("(() => { const c = document.querySelector(%s); return c ? c.classList.contains('trancado') : null; })()" % json.dumps(card))
    antes = s.js("build.cats[1].items.length")
    s.clicar(card + " .card-name, " + card, 0.8)
    loja = s.js("({ entrou: build.cats[1].items.length > %d, aviso: (document.getElementById('catalog-mode-hint') || {}).textContent || '' })" % antes)
    p.conta("cadeado", "na loja, o card trancado mostra o cadeado e o clique não entra",
            trancado and not loja["entrou"] and "só na rota Selva" in loja["aviso"], "card trancado %s · %s" % (trancado, loja))
    s.js("""(() => { document.getElementById('search-input').value = ''; document.getElementById('search-input').dispatchEvent(new Event('input', { bubbles: true }));
      descartarAlteracoes(); return 1; })()""")


def checar_reembolso_e_topo(s, p):
    """F13-T71: a runa Reembolso na página da build liga o Reembolso dos preços
    (e abrir uma build sem ela, ou tirá-la, desliga) — só na troca de build ou
    da runa: mexer à mão, para comparar, vale até a próxima. E os níveis 19 e 20
    do Udyr (a missão do Topo, pela ficha do Capítulo 1.1) só com a rota Top."""
    print("\n%sREEMBOLSO E TOPO%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); ligarEdicao(true);
      const id = 'reembolso'; let tr, si;
      RUNAS.trilhas.forEach(t => t.slots.forEach((sl, i) => { if (sl.runas.some(r => r.id === id)) { tr = t.id; si = i; } }));
      const slots = ['', '', '']; slots[si - 1] = id;
      window.__comReembolso = () => normRunas({ primaria: tr, assinatura: '', slots });
      build.runas = normRunas(null); gravarPagina(); salvarAgora();
      const cb = document.querySelector('input[data-rune="cashback"]'); if (cb.checked) cb.click();
      switchTab('build'); showBuildScreen('forja'); return 'ok'; })()""")
    time.sleep(0.8)
    ESTADO = """(() => ({ on: !!state.applyCashback, loja: document.querySelector('input[data-rune="cashback"]').checked,
      faixa: document.getElementById('cashback-banner').classList.contains('show'), forja: document.getElementById('cb-toggle').checked,
      icone: !!document.querySelector('#cb-switch img.sw-runa:not([hidden])') }))()"""
    LIGADO = {"on": True, "loja": True, "faixa": True, "forja": True}
    DESLIGADO = {"on": False, "loja": False, "faixa": False, "forja": False}
    def estado():
        e = s.js(ESTADO)
        return e, {k: e[k] for k in LIGADO}
    def pagina(com):
        s.js("(() => { build.runas = %s; gravarPagina(); return 1; })()" % ("__comReembolso()" if com else "normRunas(null)"))
        time.sleep(0.3)

    pagina(True)
    liga, liga4 = estado()
    s.clicar("#cb-switch", 0.4)                     # à mão: desliga para comparar
    s.js("renderBuildAll(); 1"); time.sleep(0.2)    # qualquer outro redesenho (item, caixa, campeão)
    _, mao4 = estado()
    p.conta("reembolso", "a runa liga o Reembolso (loja, faixa e forja, com o ícone); desligar à mão vale até a próxima troca",
            liga4 == LIGADO and liga["icone"] and mao4 == DESLIGADO, "com a runa %s · à mão, depois de redesenhar %s" % (liga, mao4))

    s.clicar("#cb-switch", 0.4)
    pagina(False)
    tira, tira4 = estado()
    s.clicar("#cb-switch", 0.4)                     # o caminho de sempre: sem a runa, ligar à mão
    s.js("renderBuildAll(); 1"); time.sleep(0.2)
    _, velho4 = estado()
    s.clicar("#cb-switch", 0.4)
    p.conta("reembolso", "tirar a runa desliga; sem a runa, ligar à mão continua valendo",
            tira4 == DESLIGADO and not tira["icone"] and velho4 == LIGADO, "sem a runa %s · à mão %s" % (tira, velho4))

    # trocar de build: a outra com a runa liga (mesmo desligado à mão aqui); voltar a uma sem, desliga
    pagina(True); s.js("salvarAgora(); 1")
    a = s.js("build.id")
    s.clicar("#cb-switch", 0.4)
    s.js("""(() => { build.desc = 'a original'; build.mode = "Summoner's Rift"; build.rota = 'meio'; salvarAgora(); return 1; })()""")
    s.clicar("#dup-build", 1.0)                     # o Duplicar da forja, como na mão
    _, dup4 = estado()
    b = s.js("build.id")
    # a forja redesenhada com a cópia: antes ela ficava com a descrição e a rota em branco
    tela = s.js("({ outra: build.id !== %s, desc: document.getElementById('build-desc').value, rota: document.getElementById('build-rota').value })" % json.dumps(a))
    p.conta("reembolso", "duplicar na forja mostra a cópia inteira (descrição e rota na tela)",
            tela == {"outra": True, "desc": "a original", "rota": "meio"}, "%s" % tela)
    # desligado à mão na cópia, a troca direta para a original (as duas com a runa) liga de novo
    s.clicar("#cb-switch", 0.4)
    s.js("activateBuild(%s); 1" % json.dumps(a)); time.sleep(0.4)
    _, volta4 = estado()
    s.js("activateBuild(%s); 1" % json.dumps(b)); time.sleep(0.4)
    s.js("(() => { ligarEdicao(true); build.runas = normRunas(null); gravarPagina(); salvarAgora(); return 1; })()"); time.sleep(0.3)
    s.js("activateBuild(%s); 1" % json.dumps(a)); time.sleep(0.4)
    s.js("activateBuild(%s); 1" % json.dumps(b)); time.sleep(0.4)
    _, outra4 = estado()
    p.conta("reembolso", "trocar de build sincroniza: a cópia com a runa liga; desligada à mão, a original com a runa liga de novo; a sem desliga",
            dup4 == LIGADO and volta4 == LIGADO and outra4 == DESLIGADO, "cópia %s · a original %s · a sem %s" % (dup4, volta4, outra4))
    s.js("""(() => { activateBuild(%s); ligarEdicao(true); build.runas = normRunas(null); gravarPagina(); salvarAgora();
      const cb = document.querySelector('input[data-rune="cashback"]'); if (cb.checked) cb.click(); return 1; })()""" % json.dumps(a))
    time.sleep(0.4)

    # Udyr: 18 pontos em Q/W/E (6 cada) e o R nos níveis 19 e 20 — só com a rota Top
    seq = ["Q" if n in (1, 3, 5, 7, 9, 11) else "W" if n in (2, 4, 6, 8, 10, 12) else "E" for n in range(1, 19)]
    s.js("""(() => { build.mode = "Summoner's Rift"; build.rota = ''; build.champion = { key: '77', id: 'Udyr', name: 'Udyr' };
      build.habilidades = normHabilidades(%s); renderBuildAll(); return 1; })()""" % json.dumps(seq))
    time.sleep(0.4)
    COLUNAS = "document.querySelectorAll('#build-habs .bh-niv').length"
    sem_rota = s.js(COLUNAS)
    s.js("""(() => { const sel = document.getElementById('build-rota'); sel.value = 'top'; sel.dispatchEvent(new Event('change', { bubbles: true })); return 1; })()""")
    time.sleep(0.4)
    top = s.js(COLUNAS)
    tem19 = s.js("!!document.querySelector(\".bh-cel[data-hab='R'][data-nivel='19']\")")
    if tem19:
        s.clicar(".bh-cel[data-hab='R'][data-nivel='19']", 0.3)
        s.clicar(".bh-cel[data-hab='R'][data-nivel='20']", 0.3)
    u = s.js("""(() => { const g = document.querySelector('#build-habs .bh-grade').getBoundingClientRect();
      const n = [...document.querySelectorAll('#build-habs .bh-niv')], c20 = document.querySelector(".bh-cel[data-hab='R'][data-nivel='20']");
      return { h: (build.habilidades || []).slice(18).join(''), aviso: document.querySelector('#build-habs .bh-aviso').textContent,
               linha: n.length === 20 && Math.round(n[0].getBoundingClientRect().top) === Math.round(n[19].getBoundingClientRect().top),
               cabe: !!c20 && c20.getBoundingClientRect().right <= g.right + 1,
               nota: [...document.querySelectorAll('#build-habs .bh-nota')].some(x => x.textContent.includes('até o nível 20')) }; })()""")
    p.conta("topo", "o Udyr da rota Top: a grade vai ao 20 e o R entra no 19 e no 20 (sem rota, 18 colunas)",
            sem_rota == 18 and top == 20 and u["h"] == "RR" and "20/20 níveis" in u["aviso"] and u["linha"] and u["cabe"] and u["nota"],
            "colunas sem rota %s · na Top %s · %s" % (sem_rota, top, u))

    s.js("""(() => { const sel = document.getElementById('build-rota'); sel.value = 'meio'; sel.dispatchEvent(new Event('change', { bubbles: true })); return 1; })()""")
    time.sleep(0.4)
    meio = s.js("""(() => { const c = document.querySelector(".bh-cel[data-hab='R'][data-nivel='19']");
      return { colunas: document.querySelectorAll('#build-habs .bh-niv').length, h: build.habilidades.slice(18).join(''),
               vermelho: !!c && c.classList.contains('invalida'), motivo: c ? c.title : '' }; })()""")
    s.js("""(() => { build.champion = { key: '86', id: 'Garen', name: 'Garen' }; build.rota = 'top'; build.habilidades = normHabilidades(%s); renderBuildAll(); return 1; })()""" % json.dumps(seq))
    time.sleep(0.3)
    garen = s.js(COLUNAS)
    p.conta("topo", "fora da Top o ponto do 19 e do 20 fica, em vermelho e com o motivo; o Garen na Top segue com 18",
            meio["colunas"] == 20 and meio["h"] == "RR" and meio["vermelho"] and "rota Top" in meio["motivo"] and garen == 18,
            "na Meio %s · Garen na Top %s colunas" % (meio, garen))

    # o formato: 18 casas quando o 19 e o 20 estão vazios (a build de sempre grava igual); texto e link levam os 20
    f = s.js("""(() => { const h20 = normHabilidades(%s.concat(['R', 'R']));
      build.champion = { key: '77', id: 'Udyr', name: 'Udyr' }; build.habilidades = h20; salvarAgora();
      const b = library.builds.find(x => x.id === build.id);
      const texto = textoDaBuild(buildResumo(b)), volta = normHabilidades(textToBuild(texto).habilidades);
      const l = buildParaLink(b), lk = linkParaBuild(l.slice(l.indexOf('#'))).habilidades;
      return { vazio: normHabilidades(null).length, dezoito: normHabilidades(%s).length, vinte: h20.length,
               texto: volta.join('') === h20.join(''), link: lk.join('') === h20.join('') }; })()""" % (json.dumps(seq), json.dumps(seq)))
    p.conta("topo", "18 casas sem ponto no 19 e no 20; com eles, texto e link levam os 20",
            f == {"vazio": 18, "dezoito": 18, "vinte": 20, "texto": True, "link": True}, "%s" % f)
    s.js("(() => { build.habilidades = normHabilidades(null); build.champion = null; build.rota = ''; salvarAgora(); return 1; })()")


def checar_aviso(s, p):
    """F13-T72 (Leo, 15/10/2026: "como o sistema de lentidão, que sempre prioriza
    o valor mais alto, e o Feridas Dolorosas"): o efeito que não acumula — a
    passiva (ou ativa) única de mesmo nome e as etiquetas Lentidão e Anti-Cura.
    Não tranca: o item entra, e o selo e o recado dizem com o que não acumula. O
    par que já divide um grupo "Limitado a 1" fica só com o cadeado."""
    print("\n%sAVISO%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    dado = s.js("""(() => { const por = (n) => CATALOG.items.find(i => i.namePt === n).slug;
      const caso = (item, outros) => motivoDoAviso(byId[por(item)], { contam: outros.map(n => ({ itemId: por(n), note: '' })), runas: new Set(), rota: '' });
      let pares = 0; const itens = new Set();
      CATALOG.items.forEach(a => CATALOG.items.forEach(b => {
        if (a.slug >= b.slug || !motivoDoAviso(a, { contam: [{ itemId: b.slug }], runas: new Set(), rota: '' })) return;
        pares++; itens.add(a.slug); itens.add(b.slug); }));
      return { pares, itens: itens.size, passiva: caso('Morellonomicon', ['Lembrete Mortal']), etiqueta: caso('Morellonomicon', ['Serrespada Quimiopunk']),
               lentidao: caso('Cetro de Cristal de Rylai', ['Presságio de Randuin']), grupo: caso('Hidra Raivosa', ['Hidra Titânica']) + caso('Manamune', ['Muramana']),
               nada: caso('Gume do Infinito', ['Morellonomicon']), copia: caso('Orbe do Oblívio', ['Orbe do Oblívio']),
               // F13-T76 (Leo, 25/10/2026): só entre itens do mesmo tier — o Fulgor ainda vira Trindade
               tier: caso('Força da Trindade', ['Fulgor']) + caso('Morellonomicon', ['Orbe do Oblívio']),
               trava: { fulgor: motivoDoCadeado(byId['sheen'], { contam: [{ itemId: 'trinity-force' }], runas: new Set(), rota: '' }),
                        lich: motivoDoCadeado(byId['trinity-force'], { contam: [{ itemId: 'lich-bane' }], runas: new Set(), rota: '' }) } }; })()""")
    p.conta("aviso", "o aviso lê do catálogo: passiva única de mesmo nome (e a cópia repetida), Lentidão e Anti-Cura; o par do mesmo grupo fica com o cadeado; entre tiers diferentes, nem aviso nem cadeado (o Fulgor ainda vira Trindade)",
            dado["pares"] == 54 and dado["itens"] == 26
            and dado["passiva"] == "a passiva única Feridas Dolorosas não acumula com Lembrete Mortal — vale uma só"
            and dado["tier"] == "" and dado["trava"]["fulgor"] == "" and "Lâmina Arcana" in dado["trava"]["lich"]
            and dado["etiqueta"] == "o efeito Anti-Cura não soma com Serrespada Quimiopunk — vale o mais forte"
            and dado["lentidao"].startswith("o efeito Lentidão não soma com Presságio de Randuin") and dado["grupo"] == "" and dado["nada"] == ""
            and dado["copia"] == "a passiva única Feridas Dolorosas não acumula com Orbe do Oblívio — vale uma só", "%s" % dado)

    # cenário: caixas Comum (0), Prioridade (1), Opcional (2), Escolha 1 (3); Morellonomicon na Prioridade
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); ligarEdicao(true);
      const por = (n) => CATALOG.items.find(i => i.namePt === n).slug; window.__por = por;
      build.mode = "Summoner's Rift"; build.rota = ''; build.runas = normRunas(null);
      while (build.cats.length < 4) build.cats.push({ id: 'cat-qa-' + build.cats.length + '-' + Date.now(), name: 'Caixa', desc: '', kind: 'comum', span: 2, cols: 3, rows: 0, items: [] });
      build.cats = build.cats.slice(0, 4);
      ['comum', 'prioridade', 'opcional', 'escolha'].forEach((k, i) => { build.cats[i].kind = k; build.cats[i].items = []; });
      build.cats[1].items = [{ itemId: por('Morellonomicon'), note: '' }];
      build.cats[3].items = [{ itemId: por('Gume do Infinito'), note: '' }];
      build.selectedCatId = build.cats[0].id; build.pickerQuery = ''; switchTab('build'); showBuildScreen('forja'); renderBuildAll(); return 'ok'; })()""")
    time.sleep(0.8)
    def pela_bandeja(nome, caixa):
        s.js("""(() => { build.selectedCatId = build.cats[%d].id; build.pickerQuery = %s; document.getElementById('picker-search').value = %s; renderBuildAll(); return 1; })()"""
             % (caixa, json.dumps(nome), json.dumps(nome)))
        time.sleep(0.3)
        sel = '#picker-list .picker-row[data-item-id="%s"]' % s.js("__por(%s)" % json.dumps(nome))
        marca = s.js("(() => { const r = document.querySelector(%s); return r ? { aviso: r.classList.contains('nao-soma'), titulo: r.title } : null; })()" % json.dumps(sel))
        antes = s.js("build.cats[%d].items.length" % caixa)
        s.js("document.getElementById('edit-hint').textContent = ''; 1")
        s.clicar(sel, 0.5)
        return {"marca": marca, "entrou": s.js("build.cats[%d].items.length" % caixa) > antes, "recado": s.js("document.getElementById('edit-hint').textContent")}
    opc = pela_bandeja("Lembrete Mortal", 2)        # na Opcional é alternativa: nem selo, nem recado
    comum = pela_bandeja("Lembrete Mortal", 0)      # F13-T76: do mesmo tier do Morellonomicon (os dois Lendários)
    p.conta("aviso", "na bandeja: o selo para a caixa que conta, o item entra e o recado diz com o que não acumula (na Opcional, nada)",
            opc["marca"] and not opc["marca"]["aviso"] and opc["entrou"] and "Aviso" not in opc["recado"]
            and comum["marca"]["aviso"] and "Feridas Dolorosas" in comum["marca"]["titulo"] and comum["entrou"]
            and "entrou. Aviso: a passiva única Feridas Dolorosas" in comum["recado"] and "Morellonomicon" in comum["recado"],
            "Opcional %s · Comum %s" % (opc, comum))

    # no molde: os dois que contam com o selo e o motivo no balão; o da Opcional e a alternativa da Escolha 1 sem
    s.js("(() => { build.cats[3].items.push({ itemId: __por('Lembrete Mortal'), note: '' }); renderBuildAll(); return 1; })()")
    time.sleep(0.4)
    molde = s.js("""(() => { const nomes = (i) => [...document.querySelectorAll('.build-cat[data-cat-id="' + build.cats[i].id + '"] .item-tile.nao-soma')]
        .map(t => byId[build.cats[i].items[Number(t.dataset.index)].itemId].namePt);
      return { comum: nomes(0), prioridade: nomes(1), opcional: nomes(2), escolha: nomes(3) }; })()""")
    s.js("document.getElementById('build-canvas').scrollIntoView({ block: 'start' }); 1"); time.sleep(0.3)
    s.hover('.build-cat[data-cat-id="%s"] .item-tile.nao-soma .item-icon' % s.js("build.cats[1].id")); time.sleep(0.6)
    balao = s.js("(() => { const a = document.querySelector('#item-tooltip .tt-aviso'); return a ? a.textContent : ''; })()")
    s.envia("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": 5, "y": 5}); time.sleep(0.3)
    p.conta("aviso", "no molde: o selo nos dois que contam (não na Opcional nem na alternativa da Escolha 1) e o motivo no balão",
            molde == {"comum": ["Lembrete Mortal"], "prioridade": ["Morellonomicon"], "opcional": [], "escolha": []}
            and balao.startswith("Aviso: a passiva única Feridas Dolorosas") and "Lembrete Mortal" in balao, "%s · balão %r" % (molde, balao))

    # na loja: o card com o selo; o clique entra e o recado da loja explica
    s.js("""(() => { build.cats[0].items = []; build.cats[1].items = [{ itemId: __por('Presságio de Randuin'), note: '' }]; build.selectedCatId = build.cats[0].id;
      renderBuildAll(); switchTab('catalog'); document.getElementById('search-input').value = 'Rylai';
      document.getElementById('search-input').dispatchEvent(new Event('input', { bubbles: true })); return 1; })()""")
    time.sleep(0.8)
    card = '#grid .card[data-slug="%s"]' % s.js("__por('Cetro de Cristal de Rylai')")
    selo = s.js("(() => { const c = document.querySelector(%s); return c ? c.classList.contains('nao-soma') : null; })()" % json.dumps(card))
    busca = "(() => { const b = document.getElementById('search-input'); b.value = %s; b.dispatchEvent(new Event('input', { bubbles: true })); return 1; })()"
    # a loja aberta acompanha a build sem redesenhar a busca: o Presságio entra e o card da Zeke ganha o selo
    s.js("(() => { build.cats[1].items = []; renderBuildAll(); return 1; })()")
    s.js(busca % json.dumps("Converg")); time.sleep(0.6)
    ZEKE = "(() => { const c = document.querySelector('#grid .card[data-slug=\"' + __por('Convergência de Zeke') + '\"]'); return c ? c.classList.contains('nao-soma') : null; })()"
    zeke_antes = s.js(ZEKE)
    s.js("(() => { build.cats[1].items = [{ itemId: __por('Presságio de Randuin'), note: '' }]; renderBuildAll(); return 1; })()"); time.sleep(0.3)
    zeke_depois = s.js(ZEKE)
    s.js(busca % json.dumps("Zhonya")); time.sleep(0.6)   # sem nada em comum com o Presságio: sem selo
    zhonya = s.js("(() => { const c = document.querySelector('#grid .card[data-slug=\"' + __por('Ampulheta de Zhonya') + '\"]'); return c ? c.classList.contains('nao-soma') : null; })()")
    s.js(busca % json.dumps("Rylai")); time.sleep(0.6)
    s.clicar(card + " .card-name, " + card, 0.8)
    loja = s.js("({ entrou: build.cats[0].items.some(e => e.itemId === __por('Cetro de Cristal de Rylai')), recado: (document.getElementById('catalog-mode-hint') || {}).textContent || '' })")
    p.conta("aviso", "na loja: o card com o selo, também quando a build muda com a loja aberta (a Zhonya, sem nada em comum, sem); o clique entra e o recado diz Lentidão",
            zeke_antes is False and zeke_depois and selo and zhonya is False and loja["entrou"] and "entrou. Aviso: o efeito Lentidão não soma com Presságio de Randuin" in loja["recado"] and "Lentidão" in loja["recado"],
            "Zeke antes %s, depois %s · selo %s · Zhonya %s · %s" % (zeke_antes, zeke_depois, selo, zhonya, loja))
    s.js("""(() => { document.getElementById('search-input').value = ''; document.getElementById('search-input').dispatchEvent(new Event('input', { bubbles: true }));
      descartarAlteracoes(); return 1; })()""")


def checar_passiva_do_ornn(s, p):
    """F13-T60 (Leo, 23/10/2026): o "Mestre Forjador" virou "Passiva do Ornn" na
    tela, e a placa MF virou "Ornn". O formato de texto continua escrevendo
    MESTRE FORJADOR: — escolha do Leo; é o que o formato_de_importacao.md ensina.
    Varre o HTML inteiro (menos script e style: o código pode falar do formato),
    os title e os placeholder, com o item forjado na forja, o balão aberto e a
    ficha de um elegível aberta."""
    print("\n%sPASSIVA DO ORNN%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    slug = s.js("""(() => { const eleg = CATALOG.items.find(i => i.masterwork && i.masterwork.eligible === true);
      build.cats[3].items = [{ itemId: eleg.slug, note: '', mf: true }]; build.masterwork = true;
      switchTab('build'); showBuildScreen('forja'); renderBuildAll(); return eleg.slug; })()""")
    time.sleep(0.6)
    varre = """(() => { const c = document.body.cloneNode(true); c.querySelectorAll('script, style').forEach(e => e.remove());
      const t = [c.textContent]; document.querySelectorAll('[title], [placeholder]').forEach(e => t.push(e.title || '', e.placeholder || ''));
      const tudo = t.join(' '); const i = tudo.search(/mestre\\s+forjador/i);
      return { velho: i < 0 ? '' : tudo.slice(Math.max(0, i - 40), i + 30), visivel: document.body.innerText.includes('Passiva do Ornn') }; })()"""
    s.hover('.build-cat[data-cat-id="%s"] .item-tile' % s.js("build.cats[3].id"))
    forja = s.js(varre)
    placa = s.js("(document.querySelector('.item-tile.mf .mf-badge') || {}).textContent || ''")
    # F13-T55: a seção da Passiva do Ornn fica atrás do "Exibir detalhes" — a ficha é olhada com ele aberto
    s.js("switchTab('catalog'); fichaEstado.detalhes = true; openModal(%s); 'ok'" % json.dumps(slug))
    time.sleep(0.8)
    ficha = s.js(varre)
    s.js("fichaEstado.detalhes = false; closeModal(); 'ok'")
    texto = s.js("buildToText()")
    s.js("descartarAlteracoes(); 'ok'")
    time.sleep(0.4)
    p.conta("passiva do Ornn", "nenhum texto do app diz mais “Mestre Forjador”",
            not forja["velho"] and not ficha["velho"] and forja["visivel"] and ficha["visivel"] and placa == "Ornn",
            "forja (com o balão) e ficha à vista com “Passiva do Ornn”; placa “%s”" % placa if not (forja["velho"] or ficha["velho"])
            else "ainda: …%s…" % (forja["velho"] or ficha["velho"]))
    p.conta("passiva do Ornn", "o formato de texto continua com MESTRE FORJADOR:", "MESTRE FORJADOR:" in texto,
            "escolha do Leo, 23/10/2026")


def garantir_build_editavel(s):
    """Runas, habilidades e texto são da build ativa, e a grade de habilidades só
    existe com o Editar ligado. Rodando um grupo sozinho (-k), nada disso existe
    ainda — então o roteiro monta o cenário antes de cobrar."""
    # F13-T53: o primeiro acesso nasce sem build — sem uma na bigorna, cria
    if not s.js("typeof build !== 'undefined' && !!build && !!build.id"):
        s.nova_build()
    else:
        s.js("switchTab('build'); showBuildScreen('forja')")
        time.sleep(0.5)
    if not s.js("document.body.classList.contains('editando')"):
        s.clicar("#edit-switch", 0.8)


def checar_runas(s, p):
    print("\n%sRUNAS%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("switchTab('runas')")
    time.sleep(0.8)
    s.js("""(() => { const b = document.querySelector('.runas-modo[data-modo=\"montar\"]');
            if (b) b.click(); })()""")
    time.sleep(0.8)
    # A página só oferece runas depois da trilha primária escolhida, e as da
    # secundária só depois da secundária. Então: trilha, escolhe o que aparecer,
    # secundária, escolhe o que aparecer de novo.
    s.clicar("#runas-trilhas [data-trilha]", 0.6)
    fim = time.time() + 40
    while time.time() < fim:
        # Uma escolha por fileira: toda opção carrega data-escolher, então clicar
        # sempre na primeira "não escolhida" só ficaria trocando a mesma vaga.
        acao = s.js("""(() => {
          for (const sec of document.querySelectorAll('#runas-corpo .runas-slot')) {
            if (sec.querySelector('[data-secundaria]')) {
              if (!sec.querySelector('[data-secundaria].ativa')) {
                sec.querySelector('[data-secundaria]').click();
                return 'secundaria';
              }
              continue;
            }
            if (sec.querySelector('.escolhida')) continue;
            const b = sec.querySelector('[data-escolher]:not(.bloqueada)');
            if (b) { b.click(); return 'runa'; }
          }
          return ''; })()""")
        if not acao:
            break
        time.sleep(0.25)
    cheias = s.js("""(() => { const p = paginaDaBuild();
      return (p.assinatura ? 1 : 0) + p.slots.filter(Boolean).length
           + p.secundarios.filter(Boolean).length + p.fragmentos.filter(Boolean).length; })()""")
    p.conta("runas", "a página fecha em 9 de 9", cheias == 9, "%s de 9" % cheias)
    # F13-T18: o app não aplica as trocas automáticas, só avisa — e a tela diz isso.
    # No Resumido, que é onde as linhas "Vira…" aparecem (em Ícones o card não
    # tem texto, e a legenda some junto de propósito).
    s.js("document.querySelector('.runas-vista[data-vista=resumido]').click(); 'ok'")
    time.sleep(0.4)
    rodape_montar = s.js("""(() => { const r = document.querySelector('#runas-corpo .runas-rodape');
      return !!r && getComputedStyle(r).display !== 'none' && r.textContent.includes('O app só avisa'); })()""")
    p.conta("runas", "a faixa aparece na forja",
            s.js("""(() => { switchTab('build'); showBuildScreen('forja');
              const f = document.querySelector('.build-runas');
              return !!f && !f.hidden && getComputedStyle(f).display !== 'none'; })()"""))
    # F13-T17: o bloco "Controle de grupo válido" do markdown sumia no leitor,
    # calado — a ficha do Golpe Desleal nunca mostrou a lista.
    s.js("switchTab('runas'); 'ok'")
    time.sleep(0.6)
    s.js("""(() => { const b = document.querySelector('.runas-modo[data-modo="ler"]'); if (b) b.click(); })()""")
    time.sleep(0.5)
    s.js("document.querySelector('.runas-vista[data-vista=completo]').click(); 'ok'")
    time.sleep(0.4)
    s.js("""(() => { const t = [...document.querySelectorAll('#runas-trilhas [data-trilha]')]
      .find(b => b.dataset.trilha === 'dominacao'); if (t) t.click(); })()""")
    time.sleep(0.6)
    cg = s.js("""(() => { const a = [...document.querySelectorAll('article.runa')].find(e => e.title === 'Golpe Desleal');
      const c = a && a.querySelector('.cg');
      return { visivel: !!c && getComputedStyle(c).display !== 'none', texto: c ? c.textContent : '' }; })()""")
    p.conta("runas", "a ficha mostra o controle de grupo válido",
            cg["visivel"] and "Inclui" in cg["texto"] and "Cripple" in cg["texto"],
            "Golpe Desleal, modo Completo" if cg["visivel"] else "o bloco não aparece")
    rodape_ler = s.js("""(() => { const r = document.querySelector('#runas-corpo .runas-rodape');
      return !!r && getComputedStyle(r).display !== 'none' && r.textContent.includes('O app só avisa'); })()""")
    p.conta("runas", "a tela diz que as trocas “Vira…” são só aviso", rodape_montar and rodape_ler,
            "no Ler e no Montar" if rodape_montar and rodape_ler
            else "falta no " + " e no ".join(n for n, ok in (("Montar", rodape_montar), ("Ler", rodape_ler)) if not ok))


def checar_fragmento(s, p):
    """F13-T23: o Atributo adicional guarda o fragmento escolhido (entry.frag)."""
    print("\n%sFRAGMENTO DO ATRIBUTO ADICIONAL%s" % (AMARELO, FIM))
    s.nova_build()
    if not s.js("document.body.classList.contains('editando')"):
        s.clicar("#edit-switch", 0.8)
    s.js("""(() => { const c = build.cats[3]; c.items = [{ itemId: 'stat-bonus', note: '' }, { itemId: 'stat-bonus', note: 'segundo' }];
      switchTab('build'); showBuildScreen('forja'); renderBuildAll(); return 'ok'; })()""")
    time.sleep(0.8)
    sel = s.js("'.build-cat[data-cat-id=\"' + build.cats[3].id + '\"] .item-tile'")
    s.clicar(sel + " .item-icon", 0.8)
    n = s.js("document.getElementById('escolher-fragmento').hidden ? 0 : document.querySelectorAll('#fr-lista [data-frag]').length")
    p.conta("fragmento", "clicar no ícone abre a escolha dos fragmentos", n > 30, "%s fragmentos na lista" % n)
    if n:
        s.clicar('#fr-lista [data-frag="Ouro · Vida"]', 0.8)
    s.js("(() => { build.cats[3].items[1].frag = 'Prata · Swiftness'; renderBuildAll(); return 'ok'; })()")
    t = s.js("""(() => { const cx = build.cats[3]; return { f: cx.items.map(e => e.frag || null),
      attrs: sumAttributes(cx.items).map(x => x.stat + '|' + x.unit + '|' + x.value), ouro: goldEfficiency(cx.items).gold }; })()""")
    p.conta("fragmento", "o fragmento entra nos atributos e no ouro",
            t["f"] == ["Ouro · Vida", "Prata · Swiftness"] and "Vida|flat|375" in t["attrs"] and "Velocidade de Ataque|percent|10" in t["attrs"]
            and abs(t["ouro"] - 1650) < 0.01, "%s · %sg" % (t["attrs"], t["ouro"]))
    # Os caminhos que listam os campos da entrada um a um: texto, lote, link e servidor.
    s.js("gravarBuild(); 'ok'")
    v = s.js("""(() => { const quer = JSON.stringify(['Ouro · Vida', 'Prata · Swiftness']);
      const deTexto = (txt) => JSON.stringify(textToBuild(txt).cats.flatMap(c => c.items).filter(e => e.itemId === 'stat-bonus').map(e => e.frag || null));
      const b = library.builds.find(x => x.id === build.id);
      const lk = linkParaBuild('#' + buildParaLink(b).split('#')[1]);
      const sv = caixasDoServidor(caixasParaServidor(build.cats), []);
      const so = (cats) => JSON.stringify(cats.flatMap(c => c.items).filter(e => e.itemId === 'stat-bonus').map(e => e.frag || null));
      return { texto: deTexto(buildToText()) === quer, lote: deTexto(loteParaTexto([build.id]).split(String.fromCharCode(10) + String.fromCharCode(10) + '=====')[0]) === quer,
               link: so(lk.cats) === quer, servidor: so(sv) === quer }; })()""")
    p.conta("fragmento", "o fragmento viaja no texto, no lote, no link e na publicação", all(v.values()),
            ", ".join(k for k, ok in v.items() if not ok) or "os quatro")


def checar_habilidades(s, p):
    print("\n%sHABILIDADES%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    # O nível 1 já ficou inalcançável uma vez, por causa do rótulo transbordando.
    s.clicar(".bh-cel[data-hab='Q'][data-nivel='1']")
    p.conta("habilidades", "nível 1 aceita clique", (s.js("build.habilidades[0]") or "") == "Q",
            "ficou %r" % s.js("build.habilidades[0]"))
    s.clicar(".bh-cel[data-hab='R'][data-nivel='5']")
    p.conta("habilidades", "supremo recusado no nível 5", (s.js("build.habilidades[4]") or "") != "R")
    s.clicar(".bh-cel[data-hab='R'][data-nivel='6']")
    p.conta("habilidades", "supremo aceito no nível 6", (s.js("build.habilidades[5]") or "") == "R")

    # F13-T8: duplicar perdia runas, habilidades e Mestre Forjador (caçada de bugs).
    antes = s.js("""(() => { build.masterwork = true; gravarBuild();
      return { hab: build.habilidades.map(x => x || '-').join(''), runas: JSON.stringify(build.runas), id: build.id }; })()""")
    s.js("duplicateBuild(build.id)")
    time.sleep(0.6)
    depois = s.js("({ hab: build.habilidades.map(x => x || '-').join(''), runas: JSON.stringify(build.runas), id: build.id, mf: !!build.masterwork })")
    p.conta("habilidades", "duplicar leva habilidades, runas e Mestre Forjador",
            depois["id"] != antes["id"] and depois["hab"] == antes["hab"] and depois["runas"] == antes["runas"] and depois["mf"],
            "habilidades %s" % depois["hab"])

    # F13-T58: as regras de pontos do Capítulo 1.1 (data/habilidades.js) — a geral
    # para todos e as fichas dos campeões de exceção; cliques de verdade na grade
    s.js("switchTab('build'); showBuildScreen('forja'); 'ok'")
    time.sleep(0.4)
    def grade(seq, champ=None):
        s.js("""(() => { build.champion = %s; build.habilidades = normHabilidades(%s); renderHabilidades(); return 'ok'; })()"""
             % (json.dumps(champ), json.dumps(seq)))
        time.sleep(0.2)
    def marca(L, n):
        s.clicar(".bh-cel[data-hab='%s'][data-nivel='%d']" % (L, n), 0.2)
    em = lambda n: s.js("build.habilidades[%d]" % (n - 1))
    vazio = [None] * 18
    udyr = {"key": "77", "id": "Udyr", "name": "Udyr"}
    jayce = {"key": "126", "id": "Jayce", "name": "Jayce"}
    azir = {"key": "268", "id": "Azir", "name": "Azir"}
    # a regra geral: rank 2 só no nível 3; no nível 8 ninguém está no rank 5 (o 5º ponto, só no 9)
    grade(vazio)
    for n in (1, 2, 3, 5, 7, 8, 9):
        marca("Q", n)
    geral = {n: em(n) for n in (1, 2, 3, 5, 7, 8, 9)}
    p.conta("habilidades", "a regra de nível vale para todos (rank 2 no 3; o 5º ponto só no 9)",
            geral[1] == "Q" and geral[2] != "Q" and geral[3] == "Q" and geral[8] != "Q" and geral[9] == "Q", "%s" % geral)
    # o supremo como o jogo: o 1º ponto a partir do 6 (pode atrasar), o 2º só a partir do 11
    grade(vazio)
    for n in (7, 10, 12):
        marca("R", n)
    sup = {n: em(n) for n in (7, 10, 12)}
    p.conta("habilidades", "o supremo pode atrasar, como no jogo (R no 7; o 2º só a partir do 11)",
            sup[7] == "R" and sup[10] != "R" and sup[12] == "R", "%s" % sup)
    # as fichas: Udyr com 6 ranks e o R desde o nível 1; Jayce com o R sozinho; Azir com o W antes
    grade(vazio, udyr)
    for n in (1, 3, 5, 7, 9, 11):
        marca("Q", n)
    marca("R", 2)
    u = s.js("({ q: build.habilidades.filter(x => x === 'Q').length, r2: build.habilidades[1], nota: !!document.querySelector('.build-habs .bh-nota') })")
    grade(vazio, jayce)
    marca("R", 6)
    j = s.js("""(() => ({ auto: document.querySelector(".bh-cel[data-hab='R'][data-nivel='1']").classList.contains('auto'), r6: build.habilidades[5] }))()""")
    grade(vazio, azir)
    marca("Q", 2)                       # sem o W antes: o Azir não aceita (o nível 2 já seria o mínimo do Q)
    sem_w = em(2)
    marca("W", 1); marca("Q", 2)
    a = {n: em(n) for n in (1, 2)}
    a["Q no 2 sem W"] = sem_w
    if sem_w == "Q":
        a[2] = "aceitou sem o W"
    p.conta("habilidades", "as exceções do Capítulo 1.1 valem (Udyr, Jayce, Azir)",
            u["q"] == 6 and u["r2"] == "R" and u["nota"] and j["auto"] and j["r6"] != "R" and a[1] == "W" and a[2] == "Q",
            "Udyr %s; Jayce %s; Azir %s" % (u, j, a))
    # um ponto que já estava fora da regra não some: fica em vermelho, com o motivo
    grade(["Q", "Q"] + [None] * 16)
    f = s.js("""(() => { const c = document.querySelector(".bh-cel[data-hab='Q'][data-nivel='2']");
      return { fica: build.habilidades[1] === 'Q', vermelho: c.classList.contains('invalida'), motivo: c.title,
               nota: !!document.querySelector('.build-habs .bh-nota.erro') }; })()""")
    p.conta("habilidades", "ponto fora da regra fica, em vermelho e com o motivo", f["fica"] and f["vermelho"] and f["nota"] and "nível 3" in f["motivo"], "%s" % f)
    # a importação (e toda cópia) não corta mais o 6º rank nem o R fora do 6/11/16
    n = s.js("""(() => { const h = normHabilidades(['Q','W','Q','E','Q','W','R','W','Q','W','Q','E','Q','E','E','R','E','W']);
      return { q: h.filter(x => x === 'Q').length, r7: h[6] }; })()""")
    p.conta("habilidades", "importar e copiar não cortam pontos (6º rank, R no 7)", n["q"] == 6 and n["r7"] == "R", "%s" % n)
    s.js("descartarAlteracoes(); 'ok'")
    time.sleep(0.3)


def checar_texto(s, p):
    """Exportar e reimportar tem de devolver a mesma build — é como o Leo move
    build entre máquinas e como uma IA gera build para ele."""
    print("\n%sTEXTO%s" % (AMARELO, FIM))
    # sempre uma build nova, com as 8 caixas: herdar a do grupo anterior fazia o
    # teste depender da ordem (rodando só -k texto, não havia caixa nem item)
    s.nova_build()
    garantir_build_editavel(s)
    # F13-T12: a comparação antiga contava as CHAVES do objeto de runas — sempre
    # 6 — e não via runa sumindo. Agora compara o conteúdo, com a pior página:
    # Slot 1 da primária vazio e fragmento do Slot 1 vazio. Era exatamente aí
    # que a ida e volta perdia runas (a escrita espremia os vazios e a leitura
    # confiava na posição).
    s.js("""(() => { const t = RUNAS.trilhas[0], t2 = RUNAS.trilhas[1];
      const F = RUNAS.fragmentos;
      // itens: texto sem item é recusado pelo importador, e aí não há ida e volta
      if (!build.cats.some(c => c.items.length))
        build.cats[3].items = CATALOG.items.filter(i => i.tier === 'Lendário').slice(0, 3).map(it => ({ itemId: it.slug, note: '' }));
      build.runas = normRunas({ primaria: t.id, assinatura: t.slots[0].runas[0].id,
        slots: ['', t.slots[2].runas[0].id, t.slots[3].runas[0].id],
        secundaria: t2.id, secundarios: [t2.slots[1].runas[0].id, t2.slots[3].runas[0].id],
        fragmentos: ['', F[1].runas[0].id, F[2].runas[0].id] });
      gravarBuild(); return 'ok'; })()""")
    RETRATO = """(() => JSON.stringify({ itens: build.cats.flatMap(c => c.items.map(i => i.itemId)),
      marcadores: build.markers, habilidades: build.habilidades, runas: normRunas(build.runas) }))()"""
    antes = s.js(RETRATO)
    id_antes = s.js("build.id")
    texto = s.js("buildToText()")
    s.js("switchTab('build'); showBuildScreen('lista'); document.getElementById('toggle-io').classList.add('active')")
    time.sleep(0.4)
    s.js("document.getElementById('import-text').value = %s" % json.dumps(texto))
    s.js("document.getElementById('import-btn').click()")
    time.sleep(1.4)
    depois = s.js(RETRATO)
    importou = s.js("build.id") != id_antes
    if not importou:
        det = "a importação NÃO criou build nova: comparar seria comparar a build com ela mesma"
    elif antes == depois:
        det = "itens, marcadores, habilidades e runas iguais"
    else:
        a, d = json.loads(antes), json.loads(depois)
        det = "; ".join("%s: %s → %s" % (k, json.dumps(a[k], ensure_ascii=False)[:90], json.dumps(d[k], ensure_ascii=False)[:90])
                        for k in a if a[k] != d[k])
    p.conta("texto", "exportar e reimportar devolve a mesma build", importou and antes == depois, det)

    # F13-T38 (bug nº 35): a linha RUNAS só saía com runa na primária. Com a
    # trilha escolhida e sem runa, o texto ia só com RUNAS 2 e FRAGMENTOS, e na
    # volta a secundária sumia junto (o normRunas não guarda secundária sem
    # primária) — sem aviso. O pior dado: primária sem runa com a secundária
    # cheia; só a trilha; a secundária escolhida sem runa.
    r38 = s.js("""(() => { const t = RUNAS.trilhas[0], t2 = RUNAS.trilhas[1], F = RUNAS.fragmentos;
      const it = CATALOG.items.find(i => i.tier === 'Lendário').namePt;
      const volta = (pg) => { const linhas = linhasDeRunas(pg);
        const r = textToBuild(['BUILD: T38', ...linhas, '[COMUM] Núcleo', '- ' + it].join(String.fromCharCode(10)));
        return { ok: JSON.stringify(normRunas(pg)) === JSON.stringify(normRunas(r.runas)) && !r.unknown.length,
                 linhas: linhas.join(' ¦ '), unknown: r.unknown }; };
      return {
        semRuna: volta({ primaria: t.id, secundaria: t2.id, secundarios: [t2.slots[1].runas[0].id, t2.slots[3].runas[0].id],
                         fragmentos: [F[0].runas[0].id, F[1].runas[0].id, F[2].runas[0].id] }),
        soTrilha: volta({ primaria: t.id }),
        secSemRuna: volta({ primaria: t.id, assinatura: t.slots[0].runas[0].id, secundaria: t2.id }),
      }; })()""")
    p.conta("texto", "primária sem runa não leva a secundária junto", r38["semRuna"]["ok"], r38["semRuna"]["linhas"][:150])
    p.conta("texto", "trilha escolhida sem runa volta no texto",
            r38["soTrilha"]["ok"] and r38["secSemRuna"]["ok"],
            "só a trilha: %s · secundária sem runa: %s" % (r38["soTrilha"]["linhas"][:60], r38["secSemRuna"]["linhas"][:90]))
    # a revisão da T38: o link também perdia a trilha sem runa (só levava a
    # página com alguma runa escolhida) — o texto e o link levam a mesma página
    lk = s.js("""(() => { const t = RUNAS.trilhas[0], t2 = RUNAS.trilhas[1];
      const vai = (pg) => { const b = { ...build, id: 'lk38', isActive: false, runas: normRunas(pg) };
        const url = buildParaLink(b); const volta = linkParaBuild(url.slice(url.indexOf('#b=')));
        return JSON.stringify(normRunas(pg)) === JSON.stringify(normRunas(volta && volta.runas)); };
      return { soTrilha: vai({ primaria: t.id }), comSec: vai({ primaria: t.id, secundaria: t2.id }) }; })()""")
    p.conta("texto", "o link leva a trilha escolhida sem runa", lk["soTrilha"] and lk["comSec"], "%s" % lk)

    # F13-T36 (bugs nºs 17 e 28): a descrição e a observação têm várias linhas,
    # e o texto é uma linha por campo. A observação saía com a quebra crua (a
    # segunda linha sumia, ou virava descrição da caixa com "#", ou item com
    # "-"); a descrição voltava partida em qualquer "/" ("poke/sustain"). O pior
    # dado: barras coladas, barra solta, barra dupla, link, e linhas que parecem
    # cabeçalho do formato.
    DESC = "Build de poke/sustain para a rota do meio (3/0, AD/AP)" + chr(10) + "Contra tanque: AD / AP no fim // ou não" + chr(10) + "https://exemplo.com/a/b"
    NOTA = "segurar até os 20 min" + chr(10) + "#1 contra tanque" + chr(10) + "- não vender / nunca" + chr(10) + "= marco falso" + chr(10) + "[COMUM] caixa falsa"
    s.js("""(() => { const c = build.cats.find(x => x.items.length); build.desc = %s; c.items[0].note = %s; c.desc = 'desc da caixa';
      window.__qaCaixa = build.cats.indexOf(c); gravarBuild(); return 'ok'; })()""" % (json.dumps(DESC), json.dumps(NOTA)))
    texto36 = s.js("buildToText()")
    id36 = s.js("build.id")
    s.js("switchTab('build'); showBuildScreen('lista'); document.getElementById('toggle-io').classList.add('active')")
    time.sleep(0.4)
    s.js("document.getElementById('import-text').value = %s" % json.dumps(texto36))
    s.js("document.getElementById('import-btn').click()")
    time.sleep(1.4)
    r36 = s.js("""(() => { const c = build.cats[window.__qaCaixa] || {}; return { nova: build.id !== %s, desc: build.desc, nota: (c.items && c.items[0] || {}).note,
      caixa: c.desc, caixas: build.cats.length, msg: document.getElementById('io-msg').textContent }; })()""" % json.dumps(id36))
    p.conta("texto", "descrição e observação de várias linhas voltam iguais (Copiar esta build → Importar)",
            r36["nova"] and r36["desc"] == DESC and r36["nota"] == NOTA and r36["caixa"] == "desc da caixa" and "não encontr" not in r36["msg"].lower(),
            "nova %s · descrição %s · observação %s · caixa %s · aviso: %s" % (r36["nova"], "igual" if r36["desc"] == DESC else json.dumps(r36["desc"], ensure_ascii=False)[:90],
            "igual" if r36["nota"] == NOTA else json.dumps(r36["nota"], ensure_ascii=False)[:90], r36["caixa"], r36["msg"][:60] or "—"))
    # o texto de várias builds (Selecionar → Copiar como texto) é outro escritor
    lote36 = s.js("""(() => { const r = textToBuild(loteParaTexto([build.id])); const c = r.cats[window.__qaCaixa] || {};
      return { desc: r.desc, nota: (c.items && c.items[0] || {}).note, unknown: r.unknown }; })()""")
    p.conta("texto", "o texto de várias builds leva a descrição e a observação inteiras",
            lote36["desc"] == DESC and lote36["nota"] == NOTA and not lote36["unknown"],
            "descrição %s · observação %s · não encontrei %s" % ("igual" if lote36["desc"] == DESC else json.dumps(lote36["desc"], ensure_ascii=False)[:80],
            "igual" if lote36["nota"] == NOTA else json.dumps(lote36["nota"], ensure_ascii=False)[:80], lote36["unknown"]))
    # texto escrito à mão (ou por IA, pelo docs/formato_de_importacao.md): " / " separa, "/" colado é barra
    mao = s.js("""(() => { const r = textToBuild(%s); return { desc: r.desc, nota: (r.cats[0].items[0] || {}).note }; })()""" % json.dumps(chr(10).join([
        "BUILD: t", "DESCRIÇÃO: Crítico puro. / / A Coletora primeiro contra poke/sustain", "[COMUM] Core | 3x1", "- Abatedora * AD/AP ¶ segurar até 3/0"])))
    p.conta("texto", "texto escrito à mão: \" / \" separa a descrição e \" ¶ \" a observação; \"/\" colado é barra",
            mao["desc"] == "Crítico puro." + chr(10) + "A Coletora primeiro contra poke/sustain" and mao["nota"] == "AD/AP" + chr(10) + "segurar até 3/0",
            "descrição %s · observação %s" % (json.dumps(mao["desc"], ensure_ascii=False), json.dumps(mao["nota"], ensure_ascii=False)))
    # texto exportado antes da T36 (a observação saía crua): " / " e " // " na observação são barra, como eram
    velho36 = s.js("""(() => { const n = CATALOG.items.filter(i => i.tier === 'Lendário').slice(0, 3).map(i => i.namePt);
      const r = textToBuild(['BUILD: velho', '[COMUM] Core | 3x1', '- ' + n[0] + ' * AD / AP', '- ' + n[1] + ' * 3 / 0 no lane', '- ' + n[2] + ' * a // b'].join(String.fromCharCode(10)));
      return { notas: r.cats[0].items.map(i => i.note), unknown: r.unknown }; })()""")
    p.conta("texto", "texto exportado antes: a barra na observação continua barra",
            velho36["notas"] == ["AD / AP", "3 / 0 no lane", "a // b"] and not velho36["unknown"], "%s" % velho36)
    # quebras que chegam por fora (U+2028 colado, \r, observação só de espaço, nome da build com quebra) não derrubam item, caixa nem descrição
    fora = s.js("""(() => { const c = build.cats.find(x => x.items.length >= 2) || build.cats.find(x => x.items.length); const guarda = JSON.stringify({ n: build.name, d: build.desc, c });
      const L = String.fromCharCode(0x2028), P = String.fromCharCode(0x2029), R = String.fromCharCode(13), N = String.fromCharCode(10);
      build.name = 'Jinx' + N + '- ' + CATALOG.items[0].namePt; build.desc = 'x' + P + 'y' + R + 'z';
      c.items[0].note = ' ' + N + ' '; if (c.items[1]) c.items[1].note = 'a' + L + 'b'; c.name = 'Core' + L + 'falsa' + R + 'x';
      const i = build.cats.indexOf(c); const r = textToBuild(buildToText()); const rc = r.cats[i] || {};
      const res = { nome: r.name, desc: r.desc, caixas: r.cats.length, esperado: build.cats.length, itens: (rc.items || []).length, itensAntes: c.items.length,
        nota1: rc.items && rc.items[1] ? rc.items[1].note : null, tem2: !!c.items[1], caixa: rc.name, unknown: r.unknown };
      const g = JSON.parse(guarda); build.name = g.n; build.desc = g.d; Object.assign(c, g.c); return res; })()""")
    p.conta("texto", "quebras que chegam por fora não derrubam item, caixa nem descrição",
            fora["nome"].startswith("Jinx - ") and fora["desc"] == "x" + chr(10) + "y" + chr(10) + "z" and fora["caixas"] == fora["esperado"]
            and fora["itens"] == fora["itensAntes"] and (not fora["tem2"] or fora["nota1"] == "a" + chr(10) + "b") and fora["caixa"] == "Core falsa x" and not fora["unknown"],
            "%s" % fora)
    # fragmento e modo que chegam de fora (link #b= ou pública montados à mão) não
    # desmontam a linha: o fragmento sai do catálogo, e o modo só se for um modo de verdade
    ff = s.js("""(() => { const c = build.cats.find(x => x.items.length); const N = String.fromCharCode(10);
      const comFrag = CATALOG.items.find(i => temFragmentos(i)); const guarda = JSON.stringify(c.items);
      c.items[0].note = 'nota'; c.items[0].frag = 'x' + N + '- ' + CATALOG.items[1].namePt;
      c.items.push({ itemId: comFrag.slug, note: '', frag: 'Prata · X] * y [z' });
      const i = build.cats.indexOf(c); const r = textToBuild(buildToText()); const rc = r.cats[i] || { items: [] };
      const res = { itens: rc.items.length, esperado: c.items.length, nota0: (rc.items[0] || {}).note, notaFrag: (rc.items[rc.items.length - 1] || {}).note, unknown: r.unknown };
      c.items = JSON.parse(guarda);
      const salvo = library.builds.find(b => !b.temp && b.id !== build.id); const modo = salvo.mode;   // outra: a aberta é lida da memória viva
      salvo.mode = 'ARAM' + N + '[OPCIONAL] Injetada' + N + '- ' + CATALOG.items[1].namePt;
      const rl = textToBuild(loteParaTexto([salvo.id])); salvo.mode = modo;
      res.caixasLote = rl.cats.length; res.caixasEsperadas = salvo.cats.length; return res; })()""")
    p.conta("texto", "fragmento e modo que chegam de fora não desmontam a linha",
            ff["itens"] == ff["esperado"] and ff["nota0"] == "nota" and ff["notaFrag"] == "" and not ff["unknown"] and ff["caixasLote"] == ff["caixasEsperadas"],
            "%s" % ff)
    # texto antigo com U+2028 no meio de uma linha (colado na descrição da caixa ou no marco): a linha fica inteira
    u28 = s.js("""(() => { const L = String.fromCharCode(0x2028), N = String.fromCharCode(10);
      const r = textToBuild(['BUILD:' + L + 'Jinx', '[COMUM] Core | 3x1', '# contra AD' + L + 'AP no fim', '= ~14min' + L + '6.500g', '- ' + CATALOG.items[1].namePt].join(N));
      return { nome: r.name, desc: (r.cats[0] || {}).desc, marco: (r.cats[0] || {}).marco, itens: ((r.cats[0] || {}).items || []).length }; })()""")
    p.conta("texto", "texto antigo com uma quebra invisível no meio da linha fica inteiro",
            u28["nome"] == "Jinx" and u28["desc"] == "contra AD AP no fim" and u28["marco"] == "~14min 6.500g" and u28["itens"] == 1, "%s" % u28)
    # F13-T37 (bug nº 19): o texto de várias builds (Selecionar → Copiar como texto)
    # voltava como UMA build, com o nome da última, todas as caixas empilhadas, a
    # régua virando marco — e sem runas, fragmentos, habilidades nem Mestre
    # Forjador, que o lote nem escrevia. Três builds diferentes, pelo botão de verdade.
    RETRATO37 = """(b => JSON.stringify({ nome: b.name, modo: b.mode, desc: b.desc, layout: layoutValido(b.layout), mf: !!b.masterwork,
      camp: b.champion ? b.champion.key : null, marc: normMarkers(b.markers), runas: normRunas(b.runas), hab: normHabilidades(b.habilidades),
      caixas: (b.cats || []).map(c => ({ n: c.name, d: c.desc || '', m: c.marco || '', k: c.kind, w: catCols(c), h: catRows(c),
        i: c.items.map(e => [e.itemId, e.note || '', !!e.mf, e.frag || '']) })) }))"""
    texto37 = s.js("""(async () => { await Campeoes.carregar();
      const t = RUNAS.trilhas[0], t2 = RUNAS.trilhas[1], F = RUNAS.fragmentos;
      const lend = CATALOG.items.filter(i => i.tier === 'Lendário' && mfEligible(i)).slice(0, 2);
      const champs = [Campeoes.porNome('Jinx'), Campeoes.porNome('Ahri'), null];
      const ids = [];
      ['Lote A', 'Lote B', 'Lote C'].forEach((nome, k) => {
        createNewBuild(nome, [{ id: 'cat-qa37-' + k, name: 'Core ' + k, desc: 'caixa ' + k, marco: '~' + (k + 14) + 'min', kind: 'comum', span: 2, cols: 3, rows: 1,
          items: lend.map((it, j) => ({ itemId: it.slug, note: 'nota ' + k + j, ...(j === 0 && k !== 2 ? { mf: true } : {}) })) }],
          k === 1 ? 'ARAM' : "Summoner's Rift", champs[k], [{ t: 'hab', letter: 'Q' }]);
        build.desc = 'descrição ' + k; build.layout = k === 0 ? 'arvore' : 'tabuleiro'; build.masterwork = k !== 2;
        build.runas = normRunas({ primaria: t.id, assinatura: t.slots[0].runas[k % t.slots[0].runas.length].id,
          slots: [t.slots[1].runas[0].id, t.slots[2].runas[0].id, t.slots[3].runas[0].id],
          secundaria: t2.id, secundarios: [t2.slots[1].runas[0].id, t2.slots[2].runas[0].id], fragmentos: [F[0].runas[0].id, F[1].runas[0].id, F[2].runas[0].id] });
        build.habilidades = normHabilidades(['Q','W','E','Q','Q','R','Q','W','Q','W','R','W','W','E','E','R','E','E']);
        gravarBuild(); ids.push(build.id);
      });
      window.__qa37 = ids; return loteParaTexto(ids); })()""")
    antes37 = s.js("window.__qa37.map(id => (%s)(library.builds.find(b => b.id === id)))" % RETRATO37)
    s.js("switchTab('build'); showBuildScreen('lista'); document.getElementById('toggle-io').classList.add('active')")
    time.sleep(0.4)
    s.js("document.getElementById('import-text').value = %s" % json.dumps(texto37))
    s.js("document.getElementById('import-btn').click()")
    time.sleep(2.5)   # o campeão vem da lista do Data Dragon, depois
    r37 = s.js("""(() => { const novas = library.builds.filter(b => !window.__qa37.includes(b.id) && /^Lote [ABC]$/.test(b.name));
      return { depois: ['Lote A', 'Lote B', 'Lote C'].map(n => { const b = novas.find(x => x.name === n); return b ? (%s)(b) : null; }),
        quantas: novas.length, msg: document.getElementById('io-msg').textContent }; })()""" % RETRATO37)
    difs = [("ABC"[k], json.loads(a), json.loads(d) if d else None) for k, (a, d) in enumerate(zip(antes37, r37["depois"])) if a != d]
    det = "3 builds iguais às originais · %s" % r37["msg"][:70] if not difs and r37["quantas"] == 3 else "%d build(s) importada(s) · diferenças: %s · %s" % (
        r37["quantas"], "; ".join("%s: %s" % (n, "faltou" if d is None else ", ".join(k for k in a if a[k] != d[k])) for n, a, d in difs) or "nenhuma", r37["msg"][:90])
    p.conta("texto", "o texto de várias builds volta como várias builds, com runas, habilidades, Mestre Forjador e campeão",
            not difs and r37["quantas"] == 3 and "Importadas 3 builds" in r37["msg"], det)
    # o cabeçalho de cada build fica com ela: escrito antes do BUILD: da seguinte (texto à
    # mão ou de IA) não vai para a anterior; e um BUILD: repetido no cabeçalho só renomeia
    cab = s.js("""(() => { const N = String.fromCharCode(10), it = CATALOG.items.filter(i => i.tier === 'Lendário')[0].namePt;
      const dois = textoParaBlocos = dividirBuilds(['BUILD: Alfa', "MODO: Summoner's Rift", 'CAMPEÃO: Jinx', '[COMUM] Core | 2x1', '- ' + it, '',
        'MODO: ARAM', 'CAMPEÃO: Ahri', 'BUILD: Beta', '[COMUM] Core | 2x1', '- ' + it].join(N)).map(textToBuild);
      const um = dividirBuilds(['BUILD: rascunho', 'MODO: ARAM', 'CAMPEÃO: Jinx', 'DESCRIÇÃO: crítico puro', 'MESTRE FORJADOR: sim',
        'BUILD: Jinx crítico', '[COMUM] Core | 2x1', '- ' + it].join(N)).map(textToBuild);
      const R = '=========='; const it2 = CATALOG.items.filter(i => i.tier === 'Lendário')[1].namePt;
      const reguaTitulo = dividirBuilds(['BUILD: Alfa', "MODO: Summoner's Rift", R, '[COMUM] Core | 2x1', '- ' + it, '',
        'BUILD: Beta', 'MODO: ARAM', R, '[COMUM] Core | 2x1', '- ' + it2].join(N)).map(textToBuild);
      const reguaCaixas = dividirBuilds(['BUILD: Alfa', '[COMUM] Core | 2x1', '- ' + it, R, '[OPCIONAL] Situacional | 2x1', '- ' + it2, '',
        'BUILD: Beta', '[COMUM] Core | 2x1', '- ' + it].join(N)).map(textToBuild);
      const comentario = dividirBuilds(['BUILD: Alfa', "MODO: Summoner's Rift", '[COMUM] Core | 2x1', '- ' + it, '',
        'MODO: ARAM', 'Segunda opção:', 'BUILD: Beta', '[COMUM] Core | 2x1', '- ' + it2].join(N)).map(textToBuild);
      const reguaDepois = dividirBuilds(['BUILD: Alfa', '[COMUM] Core | 2x1', '- ' + it, R, 'MODO: ARAM', 'BUILD: Beta', '[COMUM] Core | 2x1', '- ' + it2].join(N)).map(textToBuild);
      const resumo = rs => rs.map(r => [r.name, r.mode, r.cats.length]);
      return { dois: dois.map(r => [r.name, r.mode, r.championName]), um: um.map(r => [r.name, r.mode, r.championName, r.desc, r.masterwork, r.cats.length]),
        reguaTitulo: resumo(reguaTitulo), reguaCaixas: resumo(reguaCaixas), comentario: resumo(comentario), reguaDepois: resumo(reguaDepois) }; })()""")
    p.conta("texto", "o cabeçalho de cada build fica com ela (antes do BUILD: da seguinte, com comentário no meio; BUILD: repetido só renomeia; régua dentro da build é só enfeite)",
            cab["dois"] == [["Alfa", "Summoner's Rift", "Jinx"], ["Beta", "ARAM", "Ahri"]]
            and cab["um"] == [["Jinx crítico", "ARAM", "Jinx", "crítico puro", True, 1]]
            and cab["reguaTitulo"] == [["Alfa", "Summoner's Rift", 1], ["Beta", "ARAM", 1]]
            and cab["reguaCaixas"] == [["Alfa", "", 2], ["Beta", "", 1]]
            and cab["comentario"] == [["Alfa", "Summoner's Rift", 1], ["Beta", "ARAM", 1]]
            and cab["reguaDepois"] == [["Alfa", "", 1], ["Beta", "ARAM", 1]], "%s" % cab)
    # a mensagem do lote: a build sem caixa é avisada pelo nome (com uma build ou várias),
    # e o aviso do campeão entra no resumo, com o nome da build, em vez de apagá-lo
    def importa(texto, espera=1.8):
        s.js("switchTab('build'); showBuildScreen('lista'); document.getElementById('toggle-io').classList.add('active')")
        time.sleep(0.3)
        s.js("document.getElementById('import-text').value = %s; document.getElementById('import-btn').click(); 'ok'" % json.dumps(texto))
        time.sleep(espera)
        return s.js("document.getElementById('io-msg').textContent")
    item1 = s.js("CATALOG.items.filter(i => i.tier === 'Lendário')[0].namePt")
    REGUA = chr(10) + chr(10) + "=" * 40 + chr(10) + chr(10)
    s.js("Campeoes.carregar().then(() => 'ok')")
    m1 = importa(REGUA.join(["BUILD: Vazia V" + chr(10) + "MODO: ARAM", "BUILD: Rica A" + chr(10) + "[COMUM] Core | 2x1" + chr(10) + "- " + item1]))
    m2 = importa(REGUA.join(["BUILD: Rica B" + chr(10) + "CAMPEÃO: Fulano Inexistente" + chr(10) + "[COMUM] Core | 2x1" + chr(10) + "- " + item1,
                             "BUILD: Rica C" + chr(10) + "[COMUM] Core | 2x1" + chr(10) + "- " + item1]))
    m4 = importa(REGUA.join(["BUILD: Vazia W" + chr(10) + "MODO: ARAM", "BUILD: Rica D" + chr(10) + "CAMPEÃO: Fulano Inexistente" + chr(10) + "[COMUM] Core | 2x1" + chr(10) + "- " + item1]))
    # o aviso que chega depois (a lista do Data Dragon atrasada) entra no fim da mensagem mais nova, sem apagá-la
    s.js("window.__carOrig37 = Campeoes.carregar; Campeoes.carregar = () => new Promise(r => setTimeout(r, 900)); 'ok'")
    importa(REGUA.join(["BUILD: Rica E" + chr(10) + "CAMPEÃO: Fulano Atrasado" + chr(10) + "[COMUM] Core | 2x1" + chr(10) + "- " + item1,
                        "BUILD: Rica F" + chr(10) + "[COMUM] Core | 2x1" + chr(10) + "- " + item1]), 0.1)
    s.js("showIoMsg('Mensagem mais nova.', false); 'ok'"); time.sleep(1.6)
    m5 = s.js("document.getElementById('io-msg').textContent")
    # sem internet: uma frase só para todas as builds (doze builds eram um paredão de 7.500 caracteres)
    s.js("Campeoes.carregar = () => Promise.reject(new Error('sem rede')); 'ok'")
    m6 = importa(REGUA.join("BUILD: Sem Rede %d" % k + chr(10) + "CAMPEÃO: Jinx" + chr(10) + "[COMUM] Core | 2x1" + chr(10) + "- " + item1 for k in range(12)), 1.2)
    s.js("Campeoes.carregar = window.__carOrig37; 'ok'")
    p.conta("texto", "a mensagem do lote avisa a build sem caixa e o campeão desconhecido, sem apagar o resumo",
            "Vazia W" in m4 and "Fulano Inexistente" in m4 and m5.startswith("Mensagem mais nova.") and "Fulano Atrasado" in m5
            and m6.count("Sem internet") == 1 and "e mais 4" in m6 and len(m6) < 600 and
            "Vazia V" in m1 and "Importado" in m1 and "modo ARAM" not in m1 and "Importadas 2 builds" in m2 and "Rica B" in m2 and "Fulano Inexistente" in m2,
            "uma build + uma sem caixa: %s · duas, uma com campeão desconhecido: %s · uma + sem caixa + campeão: %s · atrasado: %s · sem internet (%d caracteres): %s" % (
                m1[:90], m2[:120], m4[:140], m5[:100], len(m6), m6[:120]))
    # o lote grava a biblioteca uma vez, no fim (60 builds travavam a página 7,5 s: 4 gravações e 2 redesenhos por build)
    lote10 = REGUA.join("BUILD: Lote %d" % k + chr(10) + "[COMUM] Core | 2x1" + chr(10) + "- " + item1 for k in range(10))
    s.js("""(() => { window.__gravacoes = 0; window.__redesenhos = 0; window.__setOrig37 = Storage.prototype.setItem; window.__rbOrig37 = renderBuild;
      Storage.prototype.setItem = function (k, v) { if (k === 'lol-builds-v3') window.__gravacoes++; return window.__setOrig37.call(this, k, v); };
      renderBuild = (...a) => { window.__redesenhos++; return window.__rbOrig37(...a); }; return 'ok'; })()""")
    m3 = importa(lote10, 1.0)
    grav = s.js("(() => { Storage.prototype.setItem = window.__setOrig37; renderBuild = window.__rbOrig37; return [window.__gravacoes, window.__redesenhos]; })()")
    p.conta("texto", "importar 10 builds grava a biblioteca e redesenha a forja uma vez, no fim", grav[0] <= 2 and grav[1] <= 3 and "Importadas 10 builds" in m3,
            "%s gravação(ões), %s redesenho(s) da forja · %s" % (grav[0], grav[1], m3[:60]))
    # um campo de uma linha só (descrição e nome da caixa, marco) com uma quebra que chegou por fora não abre linha nova
    umal = s.js("""(() => { const c = build.cats.find(x => x.items.length); const antes = { desc: c.desc, name: c.name, marco: c.marco };
      c.desc = 'linha 1' + String.fromCharCode(10) + '- Gume do Infinito'; c.marco = 'marco' + String.fromCharCode(10) + '[COMUM] falsa'; c.name = 'Core' + String.fromCharCode(10) + '# nome falso';
      const r = textToBuild(buildToText()); const i = build.cats.indexOf(c); Object.assign(c, antes);
      const rc = r.cats[i] || {}; return { caixas: r.cats.length, esperado: build.cats.length, itens: (rc.items || []).length, itensAntes: c.items.length, desc: rc.desc, marco: rc.marco, nome: rc.name }; })()""")
    p.conta("texto", "campo de uma linha com uma quebra dentro não abre linha nova no texto",
            umal["caixas"] == umal["esperado"] and umal["itens"] == umal["itensAntes"] and umal["desc"] == "linha 1 - Gume do Infinito" and umal["marco"] == "marco [COMUM] falsa",
            "%s" % umal)

    # F13-T12: texto exportado ANTES do conserto espremia as vagas vazias, e o
    # formato promete que dá para importar só os fragmentos. Os dois voltavam
    # sem runa nenhuma — e "Vida" era acusada de "não encontrada".
    texto_velho = chr(10).join(["BUILD: t", "[COMUM] Core | 3x1", "- Abatedora",
        "RUNAS: Precisão > Pressione o Ataque | Lenda: Espontaneidade | Golpe de Misericórdia",
        "FRAGMENTOS: Força Adaptativa | Vida"])
    velho = s.js("""(() => { const r = textToBuild(%s);
      const p = normRunas(r.runas); return { slots: p.slots, frag: p.fragmentos, unknown: r.unknown }; })()""" % json.dumps(texto_velho))
    p.conta("texto", "texto antigo (vagas espremidas) e só fragmentos voltam inteiros",
            velho["slots"][1:] == ["lenda-espontaneidade", "golpe-de-misericordia"] and "vida" in velho["frag"] and not velho["unknown"],
            "slots %s, fragmentos %s, não encontrei %s" % (velho["slots"], velho["frag"], velho["unknown"]))

    # F13-T13: o LINK da build é o outro jeito de mandá-la para alguém, e ele
    # não levava runas, habilidades, layout nem Mestre Forjador — mas a placa
    # promete "quem abrir recebe esta build". Aqui o link é aberto numa página
    # nova, como quem recebe, e comparado campo a campo.
    CAMPOS = """(() => JSON.stringify({ itens: build.cats.flatMap(c => c.items.map(i => [i.itemId, i.note || '', !!i.mf])),
      runas: normRunas(build.runas), habilidades: normHabilidades(build.habilidades),
      layout: layoutValido(build.layout), mestre: !!build.masterwork, modo: build.mode || '', desc: build.desc || '',
      marcadores: build.markers }))()"""
    s.js("""(() => { const t = RUNAS.trilhas[2];
      build.runas = normRunas({ primaria: t.id, assinatura: t.slots[0].runas[1].id, slots: [t.slots[1].runas[0].id, '', t.slots[3].runas[1].id],
        fragmentos: [RUNAS.fragmentos[0].runas[1].id, '', RUNAS.fragmentos[2].runas[0].id] });
      build.habilidades = normHabilidades(['Q','E','W','Q','Q','R','Q','E','Q','E','R','E','E','W','W','R','W','W']);
      build.layout = Object.keys(LAYOUTS).find(k => k !== 'tabuleiro');
      build.masterwork = true; build.desc = 'descrição do link';
      const c = build.cats.find(c => c.items.length); if (c) { c.items[0].note = 'observação'; c.items[0].mf = true; }
      gravarBuild(); return 'ok'; })()""")
    enviado = s.js(CAMPOS)
    link = s.js("buildParaLink(library.builds.find(b => b.id === build.id))")
    # página NOVA: trocar só o "#" não recarrega o documento, e aí ninguém "recebe"
    s.abrir("?link=1#" + link.split("#", 1)[1])
    time.sleep(1.2)
    s.entrar()
    recebido = s.js(CAMPOS)
    veio_do_link = s.js("build.id.startsWith('l-')")
    if not veio_do_link:
        det = "a build ativa não é a recebida pelo link (id %s)" % s.js("build.id")
    elif enviado == recebido:
        det = "runas, habilidades, layout, Mestre Forjador, itens e observações; link de %d caracteres" % len(link)
    else:
        a, b = json.loads(enviado), json.loads(recebido)
        det = "; ".join("%s: %s → %s" % (k, json.dumps(a[k], ensure_ascii=False)[:60], json.dumps(b[k], ensure_ascii=False)[:60]) for k in a if a[k] != b[k])
    p.conta("texto", "o link leva a build inteira (quem abre recebe tudo)", veio_do_link and enviado == recebido, det)

    # F13-T8: importar tem de CRIAR uma build nova (senão a comparação acima
    # passa sem testar nada) e ela tem de nascer GRAVADA — com Mestre Forjador e
    # campeão, o importador deixava rascunho, e recarregar perdia os dois.
    s.js("""(async () => { await Campeoes.carregar(); build.champion = Campeoes.porNome('Jinx');
      build.masterwork = true; gravarBuild(); return 'ok'; })()""")
    id_origem = s.js("build.id")
    texto = s.js("buildToText()")
    s.js("document.getElementById('import-text').value = %s" % json.dumps(texto))
    s.js("document.getElementById('import-btn').click()")
    time.sleep(2.5)                       # o campeão chega pelo Data Dragon, depois
    r = s.js("""(() => { const salva = library.builds.find(b => b.id === build.id) || {};
      return { nova: build.id !== %s, sujo: rascunho.sujo,
               mfSalvo: !!salva.masterwork, campeaoSalvo: salva.champion ? salva.champion.name : null }; })()""" % json.dumps(id_origem))
    p.conta("texto", "importar cria uma build nova", r["nova"])
    p.conta("texto", "a build importada nasce gravada (Mestre Forjador e campeão)",
            r["nova"] and not r["sujo"] and r["mfSalvo"] and r["campeaoSalvo"] == "Jinx",
            "rascunho sujo=%s, MF gravado=%s, campeão gravado=%s" % (r["sujo"], r["mfSalvo"], r["campeaoSalvo"]))

    # Achado da revisão da F13-T36: "*" e "•" também abrem linha de item (tópico
    # comum em texto de IA), e a caixa "Importados" — a do item que vem antes da
    # primeira caixa — nascia ANTES de conferir o nome. Um tópico solto no topo
    # deixava uma caixa vazia na build; um texto só de tópicos importava uma
    # build vazia em vez de dizer que não achou nada. Pelo botão, como o Leo faz.
    def importar(texto):
        s.js("document.getElementById('import-text').value = %s" % json.dumps(texto))
        s.js("document.getElementById('import-btn').click()")
        time.sleep(1.2)
        return s.js("""({ id: build.id, caixas: build.cats.map(c => c.name + ':' + c.items.length),
          msg: document.getElementById('io-msg').textContent })""")
    s.js("switchTab('build'); showBuildScreen('lista'); document.getElementById('toggle-io').classList.add('active')")
    time.sleep(0.4)
    id_antes = s.js("build.id")
    misto = importar(chr(10).join(["BUILD: tópicos no topo", "* Dica: fechar o núcleo antes dos 20 min",
                                   "• Contra cura, antecipar o corte", "[COMUM] Núcleo | 3x1", "- Gume do Infinito"]))
    p.conta("texto", "tópico antes da primeira caixa não vira caixa vazia",
            misto["id"] != id_antes and misto["caixas"] == ["Núcleo:1"],
            "caixas %s · aviso: %s" % (misto["caixas"], misto["msg"][:80]))
    id_antes = misto["id"]
    so = importar(chr(10).join(["BUILD: só tópicos", "* Dica: fechar o núcleo antes dos 20 min", "• Contra cura, antecipar o corte"]))
    p.conta("texto", "texto só de tópicos não importa build vazia",
            so["id"] == id_antes and "Não encontrei" in so["msg"],
            "build nova %s · caixas %s · aviso: %s" % (so["id"] != id_antes, so["caixas"], so["msg"][:80]))

    # Caixa sem grade: 6 colunas, a largura ½ de sempre, também na "Importados"
    # (Leo, 17/10/2026, escolha B — o documento dizia 3 e o importador dava 6;
    # o documento passou a dizer 6). O caminho antigo continua: "| ½" dá 6, "| 2×1" dá 2.
    grade = importar(chr(10).join(["BUILD: grades", "- Sedenta por Sangue",
                                   "[COMUM] Sem grade", "- A Coletora",
                                   "[COMUM] Largura antiga | ½", "- Gume do Infinito",
                                   "[COMUM] Com grade | 2×1", "- Dança da Morte"]))
    cols = s.js("build.cats.map(c => c.name + ':' + catCols(c))")
    # e depois do F5: a "Importados" sem colunas gravadas virava 1 coluna na
    # carga (o normalizeCats dá min(itens, 6)) — na sessão ela parecia certa
    s.js("location.reload()")
    time.sleep(2.5)
    s.entrar()
    s.js("switchTab('build')")
    time.sleep(0.6)
    # a carga normaliza as caixas de toda a biblioteca; a build aberta depois do
    # F5 pode ser outra, então a importada é procurada pelo id
    depois = s.js("(() => { const b = library.builds.find(x => x.id === %s); return b ? b.cats.map(c => c.name + ':' + catCols(c)) : ['sumiu']; })()" % json.dumps(grade["id"]))
    esperado = ["Importados:6", "Sem grade:6", "Largura antiga:6", "Com grade:2"]
    p.conta("texto", "caixa sem grade nasce com 6 colunas (e a Importados)",
            grade["id"] != id_antes and cols == esperado and depois == esperado,
            "na sessão %s · depois do F5 %s" % (cols, depois))

    # Revisão da F13-T36b: (1) o nome que não existe numa build que fica sem caixa
    # sumia do aviso — a culpa ia para a caixa; (2) um tópico de IA entre dois
    # BUILD: dividia a build, e o modo e o campeão ficavam na parte descartada.
    s.js("switchTab('build'); showBuildScreen('lista'); document.getElementById('toggle-io').classList.add('active')")
    time.sleep(0.4)
    lote = importar(chr(10).join(["BUILD: A", "[COMUM] X", "- Gume do Infinito", "",
                                  "BUILD: B", "MODO: ARAM", "- Gume do Infinto", "- Sedenta por Sangu"]))
    s.js("showBuildScreen('lista')"); time.sleep(0.3)
    so_erro = importar(chr(10).join(["BUILD: Rascunho", "- Gume do Infinto", "- A Coletra", "- Gume do Infinto"]))
    p.conta("texto", "nome errado em build sem caixa aparece no aviso",
            "Gume do Infinto" in lote["msg"] and "Sedenta por Sangu" in lote["msg"]
            and so_erro["msg"].count("Gume do Infinto") == 1 and "A Coletra" in so_erro["msg"],
            "lote: %s · só nomes errados: %s" % (lote["msg"][:110], so_erro["msg"][:110]))
    # (3) a segunda volta tentou não contar o tópico como corpo e fundiu calado uma
    # build de nomes errados com a seguinte (a reconferência pegou): o tópico entre
    # dois BUILD: separa, e a parte sem caixa é avisada com o tópico.
    div = s.js("""(() => { const N = String.fromCharCode(10);
      const r = rs => rs.map(x => [x.name, x.mode, x.championName || '', x.cats.length, x.unknown.length]);
      const topico = dividirBuilds(['BUILD: Jinx', 'MODO: ARAM', 'CAMPEÃO: Jinx', '* Dica: fechar o núcleo antes dos 20 min',
        'BUILD: Jinx crítico', '[PRIORIDADE] Núcleo | 3x1', '- Gume do Infinito'].join(N)).map(textToBuild);
      const negrito = dividirBuilds(['BUILD: Jinx ARAM', 'MODO: ARAM', 'CAMPEÃO: Jinx', 'MARCADORES: AD | Dano',
        '* **Gume do Infinito** — o núcleo', '* **Dançarina Fantasma** — velocidade', '',
        'BUILD: Caitlyn SR', 'MARCADORES: Utilidade', '[PRIORIDADE] Núcleo', '- Gume do Infinito', '- Cutelo Negro'].join(N)).map(textToBuild);
      return { topico: r(topico), negrito: r(negrito), mkCait: (negrito[1] || {}).markers || null }; })()""")
    p.conta("texto", "tópico de IA entre dois BUILD: não funde as builds",
            div["topico"] == [["Jinx", "ARAM", "Jinx", 0, 1], ["Jinx crítico", "", "", 1, 0]]
            and len(div["negrito"]) == 2 and div["negrito"][0][:4] == ["Jinx ARAM", "ARAM", "Jinx", 0]
            and div["negrito"][1][:4] == ["Caitlyn SR", "", "", 1] and len(div["mkCait"] or []) == 1, "%s" % div)


def checar_salvar(s, p):
    """F13-T31 (bug nº 14): com o navegador recusando a gravação (espaço cheio,
    armazenamento bloqueado), o Salvar dizia "salvo", apagava o botão, tocava o
    som e desarmava o aviso de saída — e a build sumia ao recarregar. Aqui o
    setItem da biblioteca é que falha; o resto do localStorage segue normal."""
    print(chr(10) + "%sSALVAR%s" % (AMARELO, FIM))
    s.nova_build()
    if not s.js("build.editing"):
        s.clicar("#edit-switch", 0.8)
    x0 = s.js("Math.round(document.getElementById('add-cat').getBoundingClientRect().left + scrollX)")
    s.js("""(() => { window.__setOrig = Storage.prototype.setItem; window.__sons = []; window.__recusar = false;
      Storage.prototype.setItem = function (k, v) { if (window.__recusar && k === 'lol-builds-v3') throw new DOMException('cheio', 'QuotaExceededError'); return window.__setOrig.call(this, k, v); };
      window.__somOrig = Som.play; Som.play = function (ev, ...a) { window.__sons.push(ev); return window.__somOrig.call(this, ev, ...a); };
      return 'ok'; })()""")
    estado = """(() => { const ev = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(ev);
      const disco = JSON.parse(localStorage.getItem('lol-builds-v3') || '{"builds":[]}').builds.find(b => b.id === build.id) || {};
      const mem = library.builds.find(b => b.id === build.id) || {};
      const tem = (b) => (b.cats || []).some(c => c.items.some(e => e.itemId === 'long-sword'));
      return { sujo: rascunho.sujo, salvar: !document.getElementById('save-btn').disabled, status: document.getElementById('save-status').textContent,
        aviso: ev.defaultPrevented, som: window.__sons.includes('build:save'), tela: buildScreen, na_forja: tem(build), na_memoria: tem(mem), no_disco: tem(disco),
        placa: document.getElementById('pub-dialog').hidden ? '' : document.getElementById('pub-title').textContent,
        foco_na_placa: !!(document.activeElement && document.activeElement.closest('#pub-dialog')),
        x: Math.round(document.getElementById('add-cat').getBoundingClientRect().left + scrollX) }; })()"""
    fecha_placa = lambda: s.js("document.getElementById('pub-dialog').hidden ? 'ok' : (fecharPub(), 'ok')")
    # Ctrl+S numa build limpa, com a gravação recusada: avisa, mas não a deixa "com alterações"
    s.js("window.__recusar = true; 'ok'")
    for tipo in ("rawKeyDown", "keyUp"):
        s.envia("Input.dispatchKeyEvent", {"type": tipo, "key": "s", "code": "KeyS", "modifiers": 2, "windowsVirtualKeyCode": 83})
    time.sleep(0.4)
    limpa = s.js(estado); fecha_placa()
    p.conta("salvar", "Ctrl+S recusado numa build limpa não a deixa \"com alterações\"",
            not limpa["sujo"] and not limpa["salvar"] and limpa["placa"] == "Não deu para salvar" and limpa["status"] == "gravação recusada",
            "sujo %s, placa \"%s\", status \"%s\"" % (limpa["sujo"], limpa["placa"], limpa["status"]))
    # a gravação volta (uma gravação passa): o aviso some sozinho — antes ficava preso, com Salvar e Descartar apagados
    s.js("window.__recusar = false; gravarBiblioteca(); 'ok'"); time.sleep(0.2)
    volta = s.js(estado)
    s.js("window.__recusar = true; 'ok'")
    p.conta("salvar", "com a gravação de volta, o aviso some sozinho", volta["status"] == "" and not volta["aviso"],
            "status \"%s\", aviso de saída %s" % (volta["status"], "armado" if volta["aviso"] else "desarmado"))
    # o rascunho de verdade
    s.js("build.cats[3].items.push({ itemId: 'long-sword', note: '' }); saveBuild(); renderBuildAll(); window.__sons = []; 'ok'")
    s.clicar("#save-btn", 0.6)
    a = s.js(estado)
    p.conta("salvar", "gravação recusada: o Salvar não diz \"salvo\"",
            a["status"] == "não deu para salvar" and a["salvar"] and a["sujo"] and a["aviso"] and not a["som"] and not a["no_disco"],
            "status \"%s\", Salvar %s, aviso de saída %s, som %s" % (a["status"], "aceso" if a["salvar"] else "APAGADO", "armado" if a["aviso"] else "DESARMADO", "tocou" if a["som"] else "não tocou"))
    p.conta("salvar", "a placa explica, com o foco nela", a["placa"] == "Não deu para salvar" and a["foco_na_placa"],
            "placa \"%s\", foco %s" % (a["placa"], "nela" if a["foco_na_placa"] else "FORA"))
    fecha_placa()
    # e cabe no lugar guardado também na Georgia, a fonte de reserva sem a Alegreya da web
    g = s.js("""(() => { const st = document.getElementById('save-status'), cs = getComputedStyle(st), sp = document.createElement('span');
      sp.textContent = st.textContent; sp.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;font-family:Georgia;font-style:' + cs.fontStyle
        + ';font-weight:' + cs.fontWeight + ';font-size:' + cs.fontSize + ';letter-spacing:' + cs.letterSpacing;
      document.body.appendChild(sp); const w = sp.getBoundingClientRect().width; sp.remove(); return { w, min: parseFloat(cs.minWidth) }; })()""")
    p.conta("salvar", "o aviso não empurra o \"+ Nova categoria\"", a["x"] == x0 and g["min"] >= g["w"],
            "x %d → %d · na Georgia o aviso tem %.0f px, o lugar %.0f px" % (x0, a["x"], g["w"], g["min"]))
    p.conta("salvar", "a cópia na memória não fica com o que não gravou", not a["na_memoria"] and a["na_forja"],
            "item na forja %s, na biblioteca da memória %s" % (a["na_forja"], a["na_memoria"]))
    # "Salvar e sair" pelo diálogo: não sai, fica na build com o aviso
    s.clicar("#build-back", 0.6)
    s.clicar('#save-dialog [data-sd="salvar"]', 0.6)
    b = s.js(estado); fecha_placa()
    p.conta("salvar", "\"Salvar e sair\" recusado: fica na build, com o aviso",
            b["tela"] == "forja" and b["sujo"] and b["status"] == "não deu para salvar" and not b["som"],
            "tela %s, status \"%s\"" % (b["tela"], b["status"]))
    # Descartar depois da recusa descarta de verdade (antes recarregava o rascunho)
    s.clicar("#discard-btn", 0.5)
    s.clicar('#save-dialog [data-sd="descartar"]', 0.6)
    d = s.js(estado)
    p.conta("salvar", "Descartar depois da recusa descarta de verdade", not d["na_forja"] and not d["na_memoria"] and not d["sujo"],
            "item na forja %s, na memória %s" % (d["na_forja"], d["na_memoria"]))
    # o coração (gravação direta) com a recusa: avisa e arma o aviso de saída
    # (a placa das gravações diretas vem na primeira recusa de uma série: uma gravação que passa começa outra)
    s.js("window.__recusar = false; gravarBiblioteca(); window.__recusar = true; showBuildScreen('lista'); 'ok'"); time.sleep(0.5)
    s.clicar('.bi-fav[data-fav="%s"]' % s.js("build.id"), 0.5)
    h = s.js(estado); fecha_placa()
    p.conta("salvar", "coração recusado: a placa avisa e o aviso de saída arma", h["placa"] == "Não deu para gravar" and h["aviso"],
            "placa \"%s\", aviso de saída %s" % (h["placa"], "armado" if h["aviso"] else "DESARMADO"))
    # caminho antigo: com a gravação de volta, o Salvar salva e diz "salvo"
    s.js("window.__recusar = false; showBuildScreen('forja'); build.cats[3].items.push({ itemId: 'long-sword', note: '' }); saveBuild(); renderBuildAll(); window.__sons = []; 'ok'")
    time.sleep(0.4)
    s.clicar("#save-btn", 0.4)
    c = s.js(estado)
    # publicação que passou no site mas não ficou guardada aqui: a placa pede para anotar o ID (servidor SIMULADO)
    s.js("""(() => { window.__fetchOrig = window.fetch;
      window.fetch = function (u, ...a) { const t = String(u);
        if (t.includes('publicar_build')) return Promise.resolve(new Response(JSON.stringify({ id: 'qa0031', versao: 1 }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
        if (t.includes('/rpc/') || t.includes('/rest/')) return Promise.resolve(new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }));
        return window.__fetchOrig.call(this, u, ...a); };
      build.name = 'Salvar de teste'; build.desc = 'descrição'; build.markers = normMarkers(MARCADORES.slice(0, 3).map(m => ({ t: 'tag', id: m.id })));
      gravarBuild(); window.__recusar = true; showBuildScreen('lista'); biSelected = build.id; renderBuildIndex(); return 'ok'; })()""")
    time.sleep(0.5)
    s.clicar('#bi-detail [data-act="publish"]', 1.0)
    pub = s.js("({ titulo: document.getElementById('pub-title').textContent, texto: document.getElementById('pub-text').textContent })")
    fecha_placa()
    s.js("window.fetch = window.__fetchOrig; window.__recusar = false; showBuildScreen('forja'); 'ok'"); time.sleep(0.4)
    p.conta("salvar", "publicada, mas sem gravar aqui: a placa pede para anotar o ID (e avisa da recusa)",
            pub["titulo"] == "Build publicada com sucesso" and "anote" in pub["texto"] and "qa0031" in pub["texto"] and "recusando gravar" in pub["texto"],
            pub["texto"][:60] + " … " + ("com" if "recusando gravar" in pub["texto"] else "SEM") + " o aviso da recusa")
    s.js("Storage.prototype.setItem = window.__setOrig; Som.play = window.__somOrig; 'ok'")
    p.conta("salvar", "com a gravação de volta, o Salvar salva", c["status"] == "salvo" and not c["sujo"] and c["no_disco"] and c["som"] and not c["aviso"],
            "status \"%s\", no disco %s, aviso de saída %s" % (c["status"], c["no_disco"], "armado" if c["aviso"] else "desarmado"))


def checar_publicar(s, p):
    """F13-T30 (bugs nºs 11, 12 e 26): o atributo hidden perdia para qualquer
    display do CSS. O pior caso: o "Fechar" aparecia durante "Publicando…", e
    dava para publicar a mesma build duas vezes. O servidor é SIMULADO: nenhum
    publicar_build sai deste navegador."""
    print(chr(10) + "%sPUBLICAR%s" % (AMARELO, FIM))
    visiveis = """[...document.querySelectorAll('[hidden]')].filter(e => { const b = e.getBoundingClientRect();
        return getComputedStyle(e).display !== 'none' && b.width > 0 && b.height > 0; })
      .map(e => e.id ? '#' + e.id : e.className)"""
    s.nova_build()
    if not s.js("build.editing"):
        s.clicar("#edit-switch", 0.8)
    fe = s.js(visiveis)
    # o Descartar some sem tirar o lugar: com hidden, o "+ Nova categoria" andava
    # 90 px e, no primeiro clique, o Descartar reaparecia embaixo do cursor
    n0 = s.js("build.cats.length")
    c = s.caixa("#add-cat")
    x0 = s.js("Math.round(document.getElementById('add-cat').getBoundingClientRect().left + scrollX)")
    xs = []
    for _ in range(2):
        for tipo in ("mousePressed", "mouseReleased"):
            s.envia("Input.dispatchMouseEvent", {"type": tipo, "x": c[0], "y": c[1], "button": "left", "clickCount": 1})
        time.sleep(0.5)
        xs.append(s.js("Math.round(document.getElementById('add-cat').getBoundingClientRect().left + scrollX)"))
    ac = s.js("({ n: build.cats.length, dlg: !document.getElementById('save-dialog').hidden })")
    if ac["dlg"]:
        s.clicar('#save-dialog [data-sd="voltar"]', 0.3)   # Continuar editando
    # uma resposta atrasada que chega com o "Alterações não salvas" aberto: a
    # placa abria POR BAIXO dele (mesmo z-index) e o Enter fechava o que não se via
    s.clicar("#build-back", 0.6)
    s.js("mostrarPub('Build publicada com sucesso', 'resposta atrasada de teste', 'sucesso'); 'ok'"); time.sleep(0.3)
    cima = s.js("""(() => { const pn = document.querySelector('#pub-dialog .md-panel').getBoundingClientRect();
      const e = document.elementFromPoint(pn.left + pn.width / 2, pn.top + pn.height / 2);
      return { pub: !!(e && e.closest('#pub-dialog')), salvar: !document.getElementById('save-dialog').hidden }; })()""")
    for tipo in ("rawKeyDown", "keyUp"):
        s.envia("Input.dispatchKeyEvent", {"type": tipo, "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27})
    time.sleep(0.3)
    esc = s.js("({ placa: document.getElementById('pub-dialog').hidden, salvar: !document.getElementById('save-dialog').hidden })")
    if not esc["placa"]:
        s.js("fecharPub(); 'ok'")
    if esc["salvar"]:
        s.clicar('#save-dialog [data-sd="voltar"]', 0.3)
    p.conta("publicar", "a placa atrasada fica por cima do \"Alterações não salvas\", e o Esc fecha só ela",
            cima["pub"] and cima["salvar"] and esc["placa"] and esc["salvar"],
            "no meio do painel: %s; Esc: placa %s, diálogo de baixo %s" % ("a placa" if cima["pub"] else "OUTRO diálogo",
            "fechou" if esc["placa"] else "ficou", "ficou" if esc["salvar"] else "FECHOU junto"))
    c2 = s.caixa("#save-btn")
    for tipo in ("mousePressed", "mouseReleased"):
        s.envia("Input.dispatchMouseEvent", {"type": tipo, "x": c2[0], "y": c2[1], "button": "left", "clickCount": 1})
    time.sleep(0.03)
    vis = s.js("getComputedStyle(document.getElementById('discard-btn')).visibility")
    time.sleep(0.5)
    # a reserva do "alterações não salvas" cobre também a fonte de reserva (Georgia), sem a Alegreya da web
    res = s.js("""(() => { const st = document.getElementById('save-status'), sp = document.createElement('span');
      sp.textContent = 'alterações não salvas'; sp.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;font-style:italic;font-size:' + getComputedStyle(st).fontSize + ';font-family:Georgia';
      document.body.appendChild(sp); const w = sp.getBoundingClientRect().width; sp.remove();
      return { min: parseFloat(getComputedStyle(st).minWidth), georgia: w }; })()""")
    p.conta("publicar", "ao salvar, o Descartar some na hora; a reserva cabe sem a fonte da web",
            vis == "hidden" and res["min"] >= res["georgia"],
            "30 ms depois: %s · reserva %.0f px, Georgia %.0f px" % (vis, res["min"], res["georgia"]))
    s.js("showBuildScreen('lista'); 'ok'"); time.sleep(0.5)
    mi = s.js(visiveis)
    p.conta("publicar", "o hidden esconde (Descartar sem rascunho, ⟳ em Minhas)", not fe and not mi,
            "forja: %s · Minhas: %s" % (fe or "nada", mi or "nada"))
    p.conta("publicar", "o \"+ Nova categoria\" não anda quando o Descartar aparece", ac["n"] > n0 and not ac["dlg"] and all(x == x0 for x in xs),
            "x %d → %s; %d → %d caixas; diálogo de descartar %s" % (x0, xs, n0, ac["n"], "ABRIU" if ac["dlg"] else "não abriu"))
    # publicar_build: preso até o roteiro soltar, ou erro 500 com __falhar; conta quantos saíram
    s.js("""(() => { window.__fetchOrig = window.fetch; window.__pubs = []; window.__soltar = null; window.__falhar = false;
      window.__resposta = { id: 'qa0030', versao: 1 };
      window.fetch = function (u, opts, ...a) { const t = String(u);
        if (t.includes('publicar_build')) { window.__pubs.push(Date.now());
          if (window.__falhar) return Promise.resolve(new Response(JSON.stringify({ message: 'falha simulada' }), { status: 500, headers: { 'Content-Type': 'application/json' } }));
          return new Promise((res) => {
            window.__soltar = () => res(new Response(JSON.stringify(window.__resposta), { status: 200, headers: { 'Content-Type': 'application/json' } })); }); }
        if (t.includes('/rpc/') || t.includes('/rest/')) return Promise.resolve(new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }));
        return window.__fetchOrig.call(this, u, opts, ...a); };
      build.name = 'Publicar de teste'; build.desc = 'descrição de teste';
      build.markers = normMarkers(MARCADORES.slice(0, 3).map(m => ({ t: 'tag', id: m.id })));
      build.cats[3].items = [{ itemId: 'long-sword', note: '' }]; gravarBuild();
      biSelected = build.id; renderBuildIndex(); return 'ok'; })()""")
    time.sleep(0.5)
    enter = lambda: [s.envia("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "text": chr(13), "unmodifiedText": chr(13), "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13}),
                     s.envia("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13})]
    # (sem o "text" o Chrome não gera o keypress e o botão não é acionado)
    s.clicar('#bi-detail [data-act="publish"]', 0.8)
    durante = s.js("""({ aguardando: document.getElementById('pub-dialog').classList.contains('aguardando'),
      fechar: getComputedStyle(document.getElementById('pub-foot')).display })""")
    enter(); time.sleep(0.6)
    n = s.js("window.__pubs.length")
    p.conta("publicar", "durante \"Publicando…\" não há Fechar", durante["aguardando"] and durante["fechar"] == "none",
            "rodapé: %s" % durante["fechar"])
    p.conta("publicar", "Enter durante a espera não manda outro pedido", n == 1, "%d pedido(s) de publicar_build" % n)
    s.js("window.__soltar && window.__soltar(); 'ok'"); time.sleep(0.8)
    ok = s.js("({ sucesso: document.getElementById('pub-dialog').classList.contains('sucesso'), pub: build.pubId })")
    s.clicar("#pub-close", 0.4)
    # erro: o Enter fecha a placa — com o foco no Publicar, atrás dela, publicava de novo
    s.js("window.__falhar = true; 'ok'")
    s.clicar('#bi-detail [data-act="publish"]', 0.8)
    antes_enter = s.js("({ n: window.__pubs.length, erro: document.getElementById('pub-dialog').classList.contains('erro') })")
    enter(); time.sleep(0.6)
    depois_enter = s.js("({ n: window.__pubs.length, fechada: document.getElementById('pub-dialog').hidden })")
    if not depois_enter["fechada"]:
        s.clicar("#pub-close", 0.3)
    p.conta("publicar", "depois de um erro, o Enter fecha a placa (não publica de novo)",
            antes_enter["erro"] and depois_enter["n"] == antes_enter["n"] and depois_enter["fechada"],
            "pedidos %d → %d; placa %s" % (antes_enter["n"], depois_enter["n"], "fechada" if depois_enter["fechada"] else "aberta"))
    # servidor lento: a espera de 30 s encurtada só aqui, trocando o relógio da página
    s.js("""(() => { window.__falhar = false; window.__resposta = { id: 'qa0030', versao: 2 }; window.__stOrig = window.setTimeout;
      window.setTimeout = (f, ms, ...a) => window.__stOrig(f, ms === 30000 ? 400 : ms, ...a); return 'ok'; })()""")
    s.clicar('#bi-detail [data-act="publish"]', 1.4)
    lento = s.js("""({ fechar: getComputedStyle(document.getElementById('pub-foot')).display,
      texto: document.getElementById('pub-text').textContent, n: window.__pubs.length })""")
    s.clicar("#pub-close", 0.4)
    s.clicar('#bi-detail [data-act="publish"]', 0.6)      # de novo, com a placa fechada e o pedido no ar
    denovo = s.js("({ n: window.__pubs.length, titulo: document.getElementById('pub-title').textContent })")
    s.clicar("#pub-close", 0.3)
    s.js("window.__soltar && window.__soltar(); 'ok'"); time.sleep(0.8)
    tarde = s.js("({ sucesso: document.getElementById('pub-dialog').classList.contains('sucesso') && !document.getElementById('pub-dialog').hidden, versao: build.pubVersao })")
    if tarde["sucesso"]:
        s.clicar("#pub-close", 0.3)
    s.js("window.setTimeout = window.__stOrig; window.fetch = window.__fetchOrig; 'ok'")
    p.conta("publicar", "servidor lento: o Fechar aparece, a trava segura e a resposta atrasada vale",
            ok["sucesso"] and ok["pub"] == "qa0030" and lento["fechar"] != "none" and "demorando" in lento["texto"]
            and denovo["n"] == lento["n"] and "Ainda publicando" in denovo["titulo"] and tarde["sucesso"] and tarde["versao"] == 2,
            "Fechar %s; de novo: %s; resposta atrasada: versão %s" % (lento["fechar"], denovo["titulo"], tarde["versao"]))


def checar_atualizacao(s, p):
    """F13-T33 (bugs nºs 13 e 41): depois de recarregar a página, só abrir outra
    build carimbava "agora" na "Última atualização" das duas, e a publicada
    passava a dizer "Há alterações depois da última publicação". A publicação
    aqui é montada por JS (os campos dela), sem servidor."""
    print(chr(10) + "%sATUALIZAÇÃO%s" % (AMARELO, FIM))
    s.limpar_memoria(); s.entrar()
    ids = s.js("""(() => { switchTab('build'); showBuildScreen('lista');
      createNewBuild('Publicada A'); build.cats[3].items = [{ itemId: 'long-sword', note: '' }]; build.desc = 'descrição';
      build.markers = normMarkers(MARCADORES.slice(0, 3).map(m => ({ t: 'tag', id: m.id }))); gravarBuild();
      const a = build.id;
      gravarMetadados(library.builds.find(b => b.id === a), { pubId: 'qa0033', pubVersao: 1, pubEm: Date.now() + 5, pubPatch: CATALOG.meta.patch });
      createNewBuild('B'); return { a, b: build.id }; })()""")
    time.sleep(0.3)
    s.abrir(); time.sleep(0.8); s.entrar()
    disco = lambda: s.js("""(() => { const d = JSON.parse(localStorage.getItem('lol-builds-v3')).builds; const f = (id) => (d.find(x => x.id === id) || {}).updatedAt;
      return { a: f(%s), b: f(%s) }; })()""" % (json.dumps(ids["a"]), json.dumps(ids["b"])))
    antes = disco()
    s.js("switchTab('build'); showBuildScreen('lista'); 'ok'"); time.sleep(3.0)
    alvo = ids["b"] if s.js("build.id") == ids["a"] else ids["a"]
    c = s.caixa('.bi-row[data-id="%s"]' % alvo)
    for n in (1, 2):
        for tipo in ("mousePressed", "mouseReleased"):
            s.envia("Input.dispatchMouseEvent", {"type": tipo, "x": c[0], "y": c[1], "button": "left", "clickCount": n})
    time.sleep(1.0)
    depois = disco()
    s.js("showBuildScreen('lista'); biSelected = %s; renderBuildIndex(); 'ok'" % json.dumps(ids["a"])); time.sleep(0.5)
    nota = s.js("(document.querySelector('#bi-detail .bd-pub-note') || {}).textContent || ''")
    p.conta("atualização", "abrir outra build não muda a \"Última atualização\"", antes == depois and "Publicada na versão 1" in nota,
            "A %s → %s, B %s → %s; nota: %s" % (antes["a"], depois["a"], antes["b"], depois["b"], nota[:45]))
    # caminho antigo: uma mudança de verdade ainda carimba a data e acende a nota
    s.js("""(() => { activateBuild(%s, true); build.cats[3].items.push({ itemId: 'long-sword', note: 'nova' }); gravarBuild();
      showBuildScreen('lista'); biSelected = build.id; renderBuildIndex(); return 'ok'; })()""" % json.dumps(ids["a"]))
    time.sleep(0.5)
    mudou = disco()
    nota2 = s.js("(document.querySelector('#bi-detail .bd-pub-note') || {}).textContent || ''")
    p.conta("atualização", "uma mudança de verdade ainda carimba a data", mudou["a"] > depois["a"] and "Há alterações" in nota2,
            "A %s → %s; nota: %s" % (depois["a"], mudou["a"], nota2[:50]))
    # a nota compara o que foi publicado (servidor SIMULADO): o Mestre Forjador, que não vai ao site, não a acende;
    # um Salvar durante uma publicação lenta, sim (a assinatura é do que foi ENVIADO)
    s.js("""(() => { window.__fetchOrig = window.fetch; window.__soltar = null; window.__lento = false;
      window.fetch = function (u, ...a) { const t = String(u);
        if (t.includes('publicar_build')) { const resp = () => new Response(JSON.stringify({ id: 'qa0033', versao: 2 }), { status: 200, headers: { 'Content-Type': 'application/json' } });
          return window.__lento ? new Promise(res => { window.__soltar = () => res(resp()); }) : Promise.resolve(resp()); }
        if (t.includes('/rpc/') || t.includes('/rest/')) return Promise.resolve(new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }));
        return window.__fetchOrig.call(this, u, ...a); };
      if (build.editing) document.getElementById('edit-switch').click();
      showBuildScreen('lista'); biSelected = build.id; renderBuildIndex(); return 'ok'; })()""")
    time.sleep(0.5)
    nota_do = lambda: s.js("(() => { showBuildScreen('lista'); biSelected = %s; renderBuildIndex(); return (document.querySelector('#bi-detail .bd-pub-note') || {}).textContent || ''; })()" % json.dumps(ids["a"]))
    s.clicar('#bi-detail [data-act="publish"]', 0.8); s.js("fecharPub(); 'ok'")
    publicada = nota_do()
    s.js("showBuildScreen('forja'); 'ok'"); time.sleep(0.5)
    # F13-T59: o Mestre Forjador só muda com o Editar (antes mudava na visualização e gravava na hora) —
    # liga, troca, salva e desliga: a mesma gravação de antes, pelo caminho que restou
    s.clicar("#edit-switch", 0.6)
    s.clicar("#mf-switch", 0.5)
    s.js("salvarAgora(); 'ok'"); time.sleep(0.3)
    s.clicar("#edit-switch", 0.6)
    mf = s.js("build.masterwork && !build.editing && !rascunho.sujo")
    depois_mf = nota_do()
    p.conta("atualização", "o Mestre Forjador não acende a nota da publicação", "Publicada na versão 2" in publicada and mf and "Publicada na versão 2" in depois_mf,
            "logo depois: %s · Mestre Forjador %s: %s" % (publicada[:26], "ligado" if mf else "?", depois_mf[:40]))
    s.js("""(() => { window.__lento = true; window.__stOrig = window.setTimeout;
      window.setTimeout = (f, ms, ...a) => window.__stOrig(f, ms === 30000 ? 300 : ms, ...a); return 'ok'; })()""")
    s.clicar('#bi-detail [data-act="publish"]', 1.0); s.js("fecharPub(); 'ok'")
    s.js("""(() => { build.cats[3].items.push({ itemId: 'long-sword', note: 'durante a espera' }); gravarBuild(); window.__soltar && window.__soltar(); return 'ok'; })()""")
    time.sleep(0.8); s.js("fecharPub(); window.setTimeout = window.__stOrig; window.fetch = window.__fetchOrig; 'ok'")
    lenta = nota_do()
    p.conta("atualização", "um Salvar durante a publicação lenta acende a nota", "Há alterações" in lenta, lenta[:60])
    # a build migrada do formato antigo nasce com data
    s.js("localStorage.clear(); localStorage.setItem('lol-build-v2', JSON.stringify({ name: 'Antiga', cats: [{ name: 'Caixa antiga', items: [] }] })); 'ok'")
    s.abrir(); time.sleep(0.8)
    mig = s.js("({ n: library.builds.length, u: (library.builds[0] || {}).updatedAt || 0 })")
    s.js("localStorage.removeItem('lol-build-v2'); 'ok'"); s.entrar()
    p.conta("atualização", "a build migrada do formato antigo tem data", mig["n"] == 1 and mig["u"] > 0, "updatedAt %s" % mig["u"])


def checar_ultima(s, p):
    """F13-T32 (bug nº 15): com uma pública aberta, a visualização contava como
    build. Excluir a última build própria gravava a biblioteca vazia (a
    visualização não vai ao disco) e, na recarga, voltava a build única do HTML
    anterior (lol-build-v2). A pública aqui é montada por JS, sem servidor."""
    print(chr(10) + "%sÚLTIMA BUILD%s" % (AMARELO, FIM))
    s.limpar_memoria(); s.entrar()
    # F13-T53: o primeiro acesso não cria build — a única build própria daqui é feita à mão
    s.js("createNewBuild('Única'); 'ok'")
    time.sleep(0.3)
    s.js("""(() => { localStorage.setItem('lol-build-v2', JSON.stringify({ name: 'Build velha do HTML anterior', cats: [{ name: 'Caixa antiga', items: [] }] }));
      switchTab('build'); showBuildScreen('lista');
      abrirPublicaTemporaria(publicaResumo({ id: 'qa0015', nome: 'Pública de teste', caixas: [], marcadores: [] }));
      showBuildScreen('lista'); biSelected = library.builds.find(b => !b.temp).id; renderBuildIndex(); return 'ok'; })()""")
    time.sleep(0.6)
    r = s.js("""(() => { const b = document.querySelector('#bi-detail [data-act="del"]');
      return { proprias: library.builds.filter(x => !x.temp).length, temp: library.builds.filter(x => x.temp).length, desligado: !b || b.disabled }; })()""")
    s.clicar('#bi-detail [data-act="del"]', 0.8)
    depois = s.js("""(() => { const d = JSON.parse(localStorage.getItem('lol-builds-v3') || '{"builds":[]}'); return { disco: d.builds.length, proprias: library.builds.filter(x => !x.temp).length }; })()""")
    p.conta("última build", "com uma pública aberta, a última build própria não se exclui",
            r["temp"] == 1 and r["proprias"] == 1 and r["desligado"] and depois["proprias"] == 1,
            "1 própria + %d visualização; Excluir %s; próprias depois: %d" % (r["temp"], "desligado" if r["desligado"] else "LIGADO", depois["proprias"]))
    # caminho antigo: com uma build própria só, "Fechar visualização" continua fechando a pública
    s.js("biSelected = library.builds.find(b => b.temp) ? library.builds.find(b => b.temp).id : null; renderBuildIndex(); 'ok'"); time.sleep(0.4)
    s.clicar('#bi-detail [data-act="del"]', 0.6)
    fechou = s.js("library.builds.filter(b => b.temp).length === 0 && library.builds.filter(b => !b.temp).length === 1")
    p.conta("última build", "com uma build só, \"Fechar visualização\" ainda fecha a pública", fechou, "")
    # a corrida (excluir uma enquanto outra espera o servidor) chega ao ramo "sem build própria":
    # a build excluída não pode voltar como cópia sem id — voltava na recarga, com o pubId já apagado
    g = s.js("""(() => { createNewBuild('P2'); const p2 = build.id; const p1 = library.builds.find(b => !b.temp && b.id !== p2).id;
      library.builds.find(b => b.id === p1).name = 'P1'; library.builds.find(b => b.id === p1).pubId = 'qa9P1'; gravarBiblioteca();
      abrirPublicaTemporaria(publicaResumo({ id: 'qa0016', nome: 'Outra pública', caixas: [], marcadores: [] }));
      deleteBuild(p1); deleteBuild(p2);
      const disco = JSON.parse(localStorage.getItem('lol-builds-v3')).builds;
      return { nulos: library.builds.filter(b => !b.id).length, disco: disco.map(b => b.name), pub: disco.some(b => b.pubId === 'qa9P1') }; })()""")
    # F13-T53: e nem uma "Build sem nome" no lugar (antes nascia uma; agora nada nasce sozinho)
    p.conta("última build", "excluir a última própria não deixa cópia fantasma nem build nova", g["nulos"] == 0 and g["disco"] == [] and not g["pub"],
            "sem id na memória: %d; no disco: %s" % (g["nulos"], g["disco"]))
    # com uma visualização ativa, o disco guarda a última build própria como a ativa
    a_ = s.js("""(() => { createNewBuild('Minha'); const propria = build.id; abrirPublicaTemporaria(publicaResumo({ id: 'qa0017', nome: 'Mais uma', caixas: [], marcadores: [] }));
      gravarBiblioteca(); return { propria, disco: JSON.parse(localStorage.getItem('lol-builds-v3')).activeId }; })()""")
    p.conta("última build", "com uma visualização aberta, a ativa gravada é a sua", a_["disco"] == a_["propria"],
            "activeId no disco: %s" % a_["disco"])
    # o Excluir da forja numa visualização fecha, sem a pergunta de excluir
    s.js("switchTab('build'); showBuildScreen('forja'); 'ok'"); time.sleep(0.5)
    nd = len(s.dialogos)
    alvo = s.js("build.temp ? build.id : null")
    s.clicar("#del-build", 0.6)
    fx = s.js("({ ficou: library.builds.some(b => b.id === %s), ativa_temp: !!build.temp })" % json.dumps(alvo))
    p.conta("última build", "o Excluir da forja numa visualização fecha, sem perguntar", alvo and not fx["ficou"] and not fx["ativa_temp"] and len(s.dialogos) == nd,
            "%s %s; perguntas: %d" % (alvo, "ficou" if fx["ficou"] else "fechou", len(s.dialogos) - nd))
    # a recarga com a biblioteca gravada vazia não ressuscita o formato antigo
    s.js("localStorage.setItem('lol-builds-v3', JSON.stringify({ builds: [], activeId: null })); 'ok'")
    s.abrir(); time.sleep(0.8)
    velha = s.js("library.builds.map(b => b.name)")
    p.conta("última build", "biblioteca vazia na recarga não traz a build do formato antigo (nem cria uma)", "Build velha do HTML anterior" not in velha and len(velha) == 0,
            "builds: %s" % velha)
    s.js("localStorage.removeItem('lol-build-v2'); 'ok'")
    s.entrar()


def checar_abas(s, p):
    """F13-T35 (bug nº 27): com duas abas abertas, cada uma gravava a biblioteca
    que tinha desde que abriu — a segunda a gravar apagava a build criada na
    primeira. Decisão do Leo: uma aba por vez. A que abre depois fica parada sob
    um véu; "Usar esta aba" recarrega do disco e assume, e é recusado enquanto a
    dona tem alteração não gravada ou espera resposta da internet. Várias abas
    de verdade no mesmo Chrome — mesmo localStorage, mesma trava (Web Locks);
    cliques e teclas de verdade. F13-T93: a aba que abre depois não fica mais
    parada — vira controle remoto (navega, acompanha a build da dona ao vivo,
    e mexer na build avisa "edite na outra aba"); o véu fica para o conferindo,
    o recusado e o perdeu."""
    print(chr(10) + "%sDUAS ABAS%s" % (AMARELO, FIM))
    s.limpar_memoria(); s.entrar()
    s.js("switchTab('build'); showBuildScreen('lista'); 'ok'"); time.sleep(0.6)
    no_disco = lambda: s.js("(JSON.parse(localStorage.getItem('lol-builds-v3') || 'null') || { builds: [] }).builds.map(x => x.name)")
    marca = lambda q: q.js("JSON.parse(localStorage.getItem('montador.dona') || 'null')")
    veu = lambda q: q.js("""(() => { const v = document.getElementById('aba-dona'); if (!v || v.hidden) return null;
      const e = document.elementFromPoint(innerWidth / 2, 30);
      return { titulo: document.getElementById('aba-dona-titulo').textContent, texto: document.getElementById('aba-dona-texto').textContent,
        emCima: !!(e && e.closest('#aba-dona')), parado: [...document.body.children].filter(x => x !== v).every(x => x.inert),
        leitor: v.getAttribute('aria-describedby') === 'aba-dona-texto' && document.getElementById('aba-dona-texto').getAttribute('aria-live') === 'polite' }; })()""")
    texto_veu = lambda q: q.js("(document.getElementById('aba-dona-texto') || {}).textContent || ''")
    # F13-T93: a aba que não é a dona vira controle remoto — a faixa no pé da tela e o que ela mostra
    rem = lambda q: q.js("""(() => { const f = document.getElementById('remota'); if (!f) return null; const r = f.getBoundingClientRect();
      return { texto: document.getElementById('remota-texto').textContent, ativa: remota.ativa, dona: souDona, veu: !!document.getElementById('aba-dona'),
        solta: ![...document.body.children].some(x => x.inert), noPe: Math.round(innerHeight - r.bottom), dentro: r.left >= 0 && r.right <= innerWidth,
        leitor: f.getAttribute('role') === 'status', nome: build.name, id: build.id, sujo: rascunho.sujo, editando: build.editing,
        plaqueta: (document.getElementById('bg-estado') || {}).textContent || '', nomes: library.builds.map(x => x.name) }; })()""")
    texto_rem = lambda q: q.js("(document.getElementById('remota-texto') || {}).textContent || ''")

    def espera(q, expr, limite=8.0):
        fim = time.time() + limite
        while time.time() < fim:
            try:
                if q.js(expr):
                    return True
            except (RuntimeError, KeyError):   # no meio de uma recarga a resposta pode vir sem "result"
                pass
            time.sleep(0.25)
        return False

    decidiu = lambda q: espera(q, "typeof decidido !== 'undefined' && decidido === true")

    def recarregou(q, clique=None, expr=None):
        """Clica de verdade (ou roda o JS) e espera a página nova decidir quem é a dona."""
        q.js("window.__velha = 1; 'ok'")
        if clique:
            q.clicar(clique, 0.3)
        else:
            q.js(expr)
        return espera(q, "typeof window.__velha === 'undefined' && document.readyState === 'complete'", 15) and decidiu(q)

    def tentar_usar(q):
        """A aba parada clica "Usar esta aba": recusado, ela nem recarrega."""
        q.js("window.__fica = 1; 'ok'")
        q.clicar("#aba-dona-usar", 0.8)
        return q.js("({ fica: window.__fica === 1, dona: souDona, texto: document.getElementById('aba-dona-texto').textContent })")

    b = s.nova_aba(); c = d = e = f = g = h = v = w = x = y = None
    try:
        # enquanto a trava não responde, a aba nova já nasce parada: um clique em
        # "Entrar na loja" não abre nada (antes, por 2 s, a loja abria e o que se
        # fazia parecia gravado e depois sumia)
        b.abrir()
        b.clicar("#entrar", 0.2, na_hora=True)
        cf = b.js("({ conferindo: !!document.querySelector('#aba-dona.conferindo'), entrou: document.getElementById('entrada').classList.contains('saindo') || document.getElementById('entrada').classList.contains('fechada'), decidido: typeof decidido === 'undefined' ? null : decidido })")
        p.conta("duas abas", "enquanto confere a trava, a aba nova já nasce parada", cf["conferindo"] and not cf["entrou"] and not cf["decidido"],
                "enquanto confere: %s" % cf)
        decidiu(b)
        # F13-T93: a segunda aba não fica mais parada sob o véu — vira controle remoto
        rb = rem(b)
        p.conta("duas abas", "a segunda aba abre como controle remoto: sem véu, a página responde, e a faixa no pé da tela diz que a build se edita na outra aba",
                bool(rb) and rb["ativa"] and not rb["dona"] and not rb["veu"] and rb["solta"] and "Controle remoto" in rb["texto"]
                and 0 <= rb["noPe"] <= 30 and rb["dentro"] and rb["leitor"], "faixa: %s" % rb)
        if rb:
            b.entrar()   # a entrada da loja abre normalmente (antes o véu a segurava)
        # a aba 1 cria uma build DEPOIS que a 2 abriu; a 2 grava o que tem na memória
        s.clicar("#bi-new", 1.0); s.js("build.name = 'Da aba 1'; gravarBuild(); showBuildScreen('lista'); 'ok'"); time.sleep(0.4)
        gravou = b.js("gravarBiblioteca()")
        disco = no_disco()
        p.conta("duas abas", "a aba de controle remoto não grava por cima da build criada na outra", "Da aba 1" in disco and gravou is False,
                "gravarBiblioteca na aba 2: %s · no disco: %s" % (gravou, disco))
        if not rb:
            return
        # F13-T93: a 2 acompanha ao vivo — a build nova da 1 na bigorna e na lista daqui
        espera(b, "build.name === 'Da aba 1' && library.builds.some(x => x.name === 'Da aba 1')", 4)
        m1 = rem(b)
        p.conta("duas abas", "controle remoto: a build que a dona cria aparece na bigorna e na lista desta aba",
                m1["nome"] == "Da aba 1" and m1["id"] == s.js("build.id") and "Da aba 1" in m1["nomes"], "aba 2: %s" % m1)
        # uma segunda build na dona (com uma só, o Excluir fica desligado e nem pergunta)
        s.js("(() => { library.builds.push({ id: newBuildId(), name: 'Segunda da 1', seq: 1, cats: [], updatedAt: Date.now() }); gravarBiblioteca(); renderLibrary(); return 'ok'; })()")
        espera(b, "library.builds.length === 2", 4)
        # o rascunho também: a 1 liga o Editar e põe um item sem salvar
        disco0 = s.js("localStorage.getItem('lol-builds-v3')")
        s.js("(() => { showBuildScreen('forja'); window.ligarEdicao(true); build.cats[0].items.push({ itemId: 'long-sword', note: '' }); saveBuild(); renderBuildAll(); return 'ok'; })()")
        espera(b, "!!build.cats[0] && build.cats[0].items.some(i => i.itemId === 'long-sword')", 4)
        b.clicar("#bg-nome", 0.6)   # o nome na plaqueta leva à forja (navegar é livre)
        m2 = rem(b)
        m2["forja"] = b.js("!document.getElementById('build-editor').hidden && !!document.querySelector('#build-canvas .item-tile')")
        p.conta("duas abas", "controle remoto: o rascunho da dona aparece ao vivo (o item na caixa, a plaqueta \"não salva\"), sem Editar nem rascunho nesta e sem nada novo no disco",
                m2["forja"] and "não salva" in m2["plaqueta"] and not m2["sujo"] and not m2["editando"] and s.js("localStorage.getItem('lol-builds-v3')") == disco0,
                "aba 2: %s" % m2)
        # mexer na build aqui avisa "edite na outra aba" e nada muda — cliques e teclas de verdade
        antes = b.js("JSON.stringify(snapshotActive())")
        avisos = []

        def tenta(acao):
            b.js("(() => { remota.aviso = null; atualizarFaixaRemota(); return 1; })()")
            acao()
            time.sleep(0.4)
            avisos.append(b.js("document.getElementById('remota-texto').textContent.includes('Edite na outra aba')"))
        perguntas = len(b.dialogos)
        # (o Editar e o clique no item da loja vão para a dona desde a F13-T94 — checagens logo abaixo)
        tenta(lambda: b.clicar("#dup-build", 0.2))                   # o Duplicar da forja
        tenta(lambda: b.clicar("#del-build", 0.2))                   # o Excluir: nem chega a perguntar (o confirm)
        tenta(lambda: b.clicar("#bg-fechar", 0.2))                   # o × da plaqueta
        tenta(lambda: b.clicar("#build-back", 0.6) or b.clicar("#bi-new", 0.2))   # "Builds" (navega) e "+ Nova build"
        tenta(lambda: (b.clicar('.tab-btn[data-tab="catalog"]', 0.6), b.clicar("#cff-fechar", 0.2)))   # o × da faixa da loja
        salvar = {}
        tenta(lambda: salvar.update(r=b.js("!document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true, cancelable: true }))")))
        ge = b.js("({ editando: build.editing, toggle: document.getElementById('edit-toggle').checked, n: library.builds.length, dialogo: !document.getElementById('save-dialog').hidden })")
        p.conta("duas abas", "controle remoto: o Duplicar, o Excluir, o ×, a Nova build, o × da loja e o Ctrl+S avisam \"edite na outra aba\" e não mexem em nada (nem no disco, nem perguntam)",
                all(avisos) and len(avisos) == 6 and b.js("JSON.stringify(snapshotActive())") == antes and not ge["editando"]
                and not ge["dialogo"] and len(b.dialogos) == perguntas and salvar.get("r") is True
                and s.js("localStorage.getItem('lol-builds-v3')") == disco0 and s.js("build.cats[0].items.length") >= 1,
                "avisos %s · perguntas %s · Ctrl+S anulado %s · aba 2 %s · mudou a build: %s"
                % (avisos, b.dialogos[perguntas:], salvar.get("r"), ge, b.js("JSON.stringify(snapshotActive())") != antes))
        # a rede de baixo: o que escapar dos avisos e tentar gravar não fica — a memória daqui volta ao
        # disco e à build da dona, e a faixa avisa
        b.js("(() => { remota.aviso = null; build.name = 'Escapou'; build.cats = []; gravarBuild(); return 1; })()")
        time.sleep(0.5)
        sn = b.js("({ nome: build.name, caixas: build.cats.length, aviso: document.getElementById('remota-texto').textContent.includes('Edite na outra aba'), nomes: library.builds.map(x => x.name) })")
        p.conta("duas abas", "controle remoto: o que escapar dos avisos e tentar gravar não fica — a memória volta ao disco e à build da dona, e a faixa avisa",
                sn["nome"] == "Da aba 1" and sn["caixas"] == s.js("build.cats.length") and sn["aviso"] and "Escapou" not in sn["nomes"]
                and s.js("localStorage.getItem('lol-builds-v3')") == disco0, "aba 2: %s" % sn)

        # ---- F13-T94: o clique no item da loja, a caixa e o Editar da remota vão para a dona ----
        # Os sons ficam anotados nas duas abas: o som é da aba do clique, não da dona
        espia_som = "(() => { window.__sons = []; if (!Som.__orig) { Som.__orig = Som.play; Som.play = (ev, c) => { window.__sons.push(ev); return Som.__orig(ev, c); }; } return 1; })()"
        b.js(espia_som); s.js(espia_som)
        cats = s.js("build.cats.map(c => c.id)")
        botas = s.js("CATALOG.items.filter(i => i.tier === 'Bota').slice(0, 2).map(i => i.slug)")
        lend = s.js("CATALOG.items.filter(i => i.tier === 'Lendário' && !findInBuild(i.slug)).slice(0, 2).map(i => i.slug)")
        carta = lambda slug: '#grid .card[data-slug="%s"] .card-name' % slug
        b.clicar('.tab-btn[data-tab="catalog"]', 0.6)
        # (a) sem caixa, o clique pergunta a caixa AQUI; a escolha vai para a dona, que põe no rascunho dela
        b.clicar(carta(botas[0]), 0.5)
        pergunta = b.js("!document.getElementById('escolher-caixa').hidden")
        if pergunta:
            b.clicar('#ec-lista .ec-caixa[data-cat="%s"]' % cats[1], 0.3)
        espera(s, "getCat(%r) && getCat(%r).items.some(i => i.itemId === %r)" % (cats[1], cats[1], botas[0]), 4)
        espera(b, "!!findInBuild(%r)" % botas[0], 4); time.sleep(0.3)
        a1 = s.js("({ na: getCat(%r).items.some(i => i.itemId === %r), caixa: build.selectedCatId, sujo: rascunho.sujo, sons: window.__sons.slice() })" % (cats[1], botas[0]))
        a2 = b.js("({ carta: document.querySelector('#grid .card[data-slug=\"%s\"]').classList.contains('in-build'), faixa: !document.getElementById('cff-caixa').hidden, sons: window.__sons.slice() })" % botas[0])
        p.conta("duas abas", "controle remoto (T94): sem caixa, o clique no item pergunta a caixa aqui; a escolha vai para a dona, que põe o item no rascunho dela — o som toca aqui, não lá",
                pergunta and a1["na"] and a1["caixa"] == cats[1] and a1["sujo"] and a2["carta"] and a2["faixa"]
                and "build:item_add" in a2["sons"] and "build:item_add" not in a1["sons"] and s.js("localStorage.getItem('lol-builds-v3')") == disco0,
                "pergunta %s · dona %s · aqui %s" % (pergunta, a1, a2))
        # (b) com a caixa escolhida (a da dona), o clique vai direto; o cadeado da dona vale; clicar de novo tira
        b.clicar(carta(lend[0]), 0.2)
        espera(s, "!!findInBuild(%r)" % lend[0], 4); time.sleep(0.3)
        b.js("(() => { document.getElementById('catalog-mode-hint').classList.remove('show'); return 1; })()")
        tranc_aqui = b.js("document.querySelector('#grid .card[data-slug=\"%s\"]').classList.contains('trancado')" % botas[1])   # o cadeado desenhado aqui, com o Editar e a caixa da dona
        b.clicar(carta(botas[1]), 0.2); time.sleep(0.6)   # duas botas na mesma caixa: o cadeado
        trava = b.js("({ hint: document.getElementById('catalog-mode-hint').classList.contains('show') ? document.getElementById('catalog-mode-hint').textContent : '' })")
        b.clicar(carta(lend[0]), 0.2)
        espera(s, "!findInBuild(%r)" % lend[0], 4); time.sleep(0.3)
        b1 = s.js("({ bota2: !!findInBuild(%r), lend: !!findInBuild(%r) })" % (botas[1], lend[0]))
        p.conta("duas abas", "controle remoto (T94): com a caixa da dona escolhida, o clique põe direto; a segunda bota já vem com o cadeado aqui e cai nele (o recado aparece aqui); clicar de novo tira",
                tranc_aqui and "trancado" in trava["hint"] and not b1["bota2"] and not b1["lend"] and "catalog:click" in b.js("window.__sons"),
                "cadeado na carta %s · recado %r · dona %s" % (tranc_aqui, trava["hint"][:70], b1))
        # (c) o "Marcar em", o "soltar" e o Esc daqui mudam a caixa da dona
        b.js("(() => { const s = document.getElementById('catalog-cat-select'); s.value = %r; s.dispatchEvent(new Event('change', { bubbles: true })); return 1; })()" % cats[2])
        espera(s, "build.selectedCatId === %r" % cats[2], 3)
        c1 = s.js("build.selectedCatId")
        espera(b, "!document.getElementById('cff-soltar').hidden", 3)
        b.clicar("#cff-soltar", 0.2)
        espera(s, "build.selectedCatId === null", 3)
        c2 = s.js("build.selectedCatId")
        b.js("(() => { const s = document.getElementById('catalog-cat-select'); s.value = %r; s.dispatchEvent(new Event('change', { bubbles: true })); return 1; })()" % cats[2])
        espera(b, "build.selectedCatId === %r" % cats[2], 3)
        for tipo in ("rawKeyDown", "keyUp"):
            b.envia("Input.dispatchKeyEvent", {"type": tipo, "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27})
        espera(s, "build.selectedCatId === null", 3)
        c3 = s.js("build.selectedCatId")
        # o clique numa caixa da forja daqui também escolhe a da dona
        b.clicar("#bg-nome", 0.6)
        b.clicar('.build-cat[data-cat-id="%s"]' % cats[3], 0.2)
        espera(s, "build.selectedCatId === %r" % cats[3], 3)
        c4 = s.js("build.selectedCatId")
        b.clicar('.tab-btn[data-tab="catalog"]', 0.6)
        p.conta("duas abas", "controle remoto (T94): o \"Marcar em\", o \"soltar\", o Esc e o clique numa caixa da forja daqui escolhem e soltam a caixa da dona",
                c1 == cats[2] and c2 is None and c3 is None and c4 == cats[3], "marcar %s · soltar %s · Esc %s · forja %s" % (c1, c2, c3, c4))
        # (d) o Editar daqui: com o rascunho na dona, desligar é recusado (o recado diz por quê); sem rascunho, desliga e liga
        b.clicar("#bg-nome", 0.6)
        b.js("(() => { remota.aviso = null; return 1; })()")
        b.clicar("#edit-switch", 0.2); time.sleep(0.6)
        d1 = {"dona": s.js("build.editing"), "faixa": texto_rem(b)}
        s.js("(() => { descartarAlteracoes(); return 'ok'; })()"); time.sleep(0.4)
        b.clicar("#edit-switch", 0.2)
        espera(s, "!build.editing", 3); espera(b, "!document.getElementById('edit-toggle').checked", 3)
        d2 = {"dona": s.js("build.editing"), "aqui": b.js("document.getElementById('edit-toggle').checked")}
        b.clicar("#edit-switch", 0.2)
        espera(s, "build.editing", 3); espera(b, "document.getElementById('edit-toggle').checked", 3)
        d3 = {"dona": s.js("build.editing"), "aqui": b.js("({ toggle: document.getElementById('edit-toggle').checked, local: build.editing })")}
        p.conta("duas abas", "controle remoto (T94): o Editar daqui é o da dona — com rascunho lá, desligar é recusado e o recado diz por quê; sem rascunho, desliga e liga; o interruptor daqui mostra o dela",
                d1["dona"] and "alterações não salvas" in d1["faixa"] and d2["dona"] is False and d2["aqui"] is False
                and d3["dona"] is True and d3["aqui"]["toggle"] and not d3["aqui"]["local"], "recusado %s · desligou %s · ligou %s" % (d1, d2, d3))
        # (e) sem o Editar na dona, o clique no item daqui avisa "ligue o Editar"; o botão do aviso liga o da dona
        s.js("(() => { window.ligarEdicao(false); return 'ok'; })()"); espera(b, "!document.getElementById('edit-toggle').checked", 3)
        b.clicar('.tab-btn[data-tab="catalog"]', 0.6)
        b.clicar(carta(lend[1]), 0.6)
        e1 = b.js("({ hint: document.getElementById('catalog-mode-hint').classList.contains('show') ? document.getElementById('catalog-mode-hint').textContent : '', faixa: document.getElementById('remota-texto').textContent })")
        if "outra aba" in e1["hint"]:
            b.clicar("#catalog-mode-hint [data-ligar-editar]", 0.2)
        espera(s, "build.editing", 3)
        e2 = {"dona": s.js("build.editing"), "item": s.js("!!findInBuild(%r)" % lend[1])}
        p.conta("duas abas", "controle remoto (T94): sem o Editar na dona, o clique no item daqui avisa \"ligue o Editar\" e não põe nada; o botão do aviso liga o Editar da dona",
                "outra aba" in e1["hint"] and "Editar" in e1["hint"] and "Ligue o Editar" in e1["faixa"] and e2["dona"] and not e2["item"],
                "aviso %r · faixa %r · dona %s" % (e1["hint"][:80], e1["faixa"][:40], e2))
        # (f) a dona com uma pergunta aberta (o "Salvar e sair?"): o pedido espera — o recado diz por quê
        s.js("(() => { build.selectedCatId = %r; build.cats[1].items.push({ itemId: %r, note: '' }); saveBuild(); renderBuild(); confirmarSaida(() => {}); return 'ok'; })()" % (cats[1], lend[0]))
        time.sleep(0.4)
        b.js("(() => { remota.aviso = null; return 1; })()")
        b.clicar(carta(lend[1]), 0.6)
        f1 = {"faixa": texto_rem(b), "item": s.js("!!findInBuild(%r)" % lend[1]), "dialogo": s.js("!document.getElementById('save-dialog').hidden")}
        s.js("(() => { fecharPerguntaDeSaida(); descartarAlteracoes(); return 'ok'; })()")
        # (g) a build trocou na dona entre o espelho e o clique: o pedido não vale para a outra build
        b.js("(() => { remota.aviso = null; canalRemoto.postMessage({ tipo: 'pedido', de: remota.id, build: 'outra-build', em: Date.now(), acao: 'editar', on: false }); return 1; })()")
        time.sleep(0.6)
        g1 = {"faixa": texto_rem(b), "dona": s.js("build.editing")}
        # (h) a dona não responde (uma versão velha da página, por exemplo): o recado diz depois de 3 s
        s.js("(() => { window.__onm = canalRemoto.onmessage; canalRemoto.onmessage = (e) => { if (e.data && e.data.tipo !== 'pedido') window.__onm(e); }; return 'ok'; })()")
        b.js("(() => { remota.aviso = null; const s = document.getElementById('catalog-cat-select'); s.value = %r; s.dispatchEvent(new Event('change', { bubbles: true })); return 1; })()" % cats[2])
        time.sleep(3.5)
        h1 = texto_rem(b)
        s.js("(() => { canalRemoto.onmessage = window.__onm; return 'ok'; })()")
        p.conta("duas abas", "controle remoto (T94): o pedido não passa por cima de uma pergunta aberta na dona, nem vale para outra build; sem resposta da dona, o recado diz em 3 s",
                "pergunta aberta" in f1["faixa"] and not f1["item"] and f1["dialogo"] and "build mudou" in g1["faixa"] and g1["dona"] and "não respondeu" in h1,
                "pergunta %s · outra build %s · sem resposta %r" % (f1, g1, h1[:60]))
        # Revisão do cético da T94:
        # (i) a pergunta da caixa aberta aqui acompanha a dona: o item que entrou lá a fecha (e não sai de lá);
        # "pôr" um item que já está e uma caixa que saiu são recusados com o recado
        b.js("(() => { remota.aviso = null; return 1; })()")
        b.clicar(carta(lend[1]), 0.6)
        i0 = b.js("!document.getElementById('escolher-caixa').hidden")
        s.js("(() => { build.selectedCatId = %r; toggleItemInBuild(%r); return 'ok'; })()" % (cats[0], lend[1]))
        espera(b, "document.getElementById('escolher-caixa').hidden", 3)
        i1 = {"fechou": b.js("document.getElementById('escolher-caixa').hidden"), "faixa": texto_rem(b), "na_dona": s.js("!!findInBuild(%r)" % lend[1])}
        pede = "(() => { remota.aviso = null; canalRemoto.postMessage(Object.assign({ tipo: 'pedido', de: remota.id, build: build.id, em: Date.now(), acao: 'item' }, %s)); return 1; })()"
        b.js(pede % json.dumps({"slug": lend[1], "so": "por"})); time.sleep(0.5)
        i2 = texto_rem(b)
        b.js(pede % json.dumps({"slug": lend[0], "caixa": "cat-que-saiu"})); time.sleep(0.5)
        i3 = {"faixa": texto_rem(b), "na_dona": s.js("!!findInBuild(%r)" % lend[0])}
        p.conta("duas abas", "controle remoto (T94, cético): a pergunta da caixa aberta aqui fecha quando o item entra lá (e ele não sai); \"pôr\" um item que já está e uma caixa que saiu são recusados com o recado",
                i0 and i1["fechou"] and "pergunta da caixa fechou" in i1["faixa"] and i1["na_dona"] and "já está na build" in i2
                and "não existe mais" in i3["faixa"] and not i3["na_dona"], "pergunta %s → %s · já está %r · caixa que saiu %s" % (i0, i1, i2[:50], i3))
        # (j) a escolha do fragmento aberta na dona (ela guarda a posição do item na caixa): o pedido espera;
        # (k) o pedido que chega depois do "não respondeu" (a dona parada num confirm) não vale mais
        s.js("(() => { document.getElementById('escolher-fragmento').hidden = false; return 'ok'; })()")
        b.js("(() => { remota.aviso = null; return 1; })()")
        b.clicar(carta(lend[0]), 0.6)
        j1 = {"faixa": texto_rem(b), "na_dona": s.js("!!findInBuild(%r)" % lend[0])}
        s.js("(() => { document.getElementById('escolher-fragmento').hidden = true; return 'ok'; })()")
        b.js(pede.replace("em: Date.now()", "em: Date.now() - 3000") % json.dumps({"slug": lend[0]})); time.sleep(0.5)
        k1 = {"faixa": texto_rem(b), "na_dona": s.js("!!findInBuild(%r)" % lend[0])}
        p.conta("duas abas", "controle remoto (T94, cético): com a escolha do fragmento aberta na dona, o pedido espera; o que chega atrasado (a dona parada num confirm) não é aplicado",
                "pergunta aberta" in j1["faixa"] and not j1["na_dona"] and "atrasado" in k1["faixa"] and not k1["na_dona"], "fragmento %s · atrasado %s" % (j1, k1))
        # (l) o cadeado dos cards daqui sobrevive à grade que nasce de novo (a busca, o filtro, a ordem)
        s.js("(() => { build.selectedCatId = %r; build.cats[1].items.push({ itemId: %r, note: '' }); saveBuild(); renderBuild(); return 'ok'; })()" % (cats[1], botas[0]))
        espera(b, "build.selectedCatId === %r && !!findInBuild(%r)" % (cats[1], botas[0]), 3); time.sleep(0.3)
        l1 = b.js("(() => { render(); const c = document.querySelector('#grid .card[data-slug=\"%s\"]'); return { trancado: !!c && c.classList.contains('trancado'), n: document.querySelectorAll('#grid .card.trancado').length }; })()" % botas[1])
        n_dona = s.js("(() => { render(); return document.querySelectorAll('#grid .card.trancado').length; })()")
        p.conta("duas abas", "controle remoto (T94, cético): o cadeado dos cards daqui sobrevive à grade que nasce de novo (busca, filtro, ordem) — os mesmos da dona",
                l1["trancado"] and n_dona > 0 and l1["n"] == n_dona, "aqui %s · na dona %s trancados" % (l1, n_dona))
        # (m) o duplo clique rápido num card daqui: entra e sai, com os dois sons (o de tirar vem com a resposta)
        b.js("(() => { window.__sons = []; return 1; })()")
        xy = b.js("(() => { const e = document.querySelector('#grid .card[data-slug=\"%s\"] .card-name'); e.scrollIntoView({ block: 'center' }); const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()" % lend[0])
        time.sleep(0.3)
        for n in (1, 2):
            for tipo in ("mousePressed", "mouseReleased"):
                b.envia("Input.dispatchMouseEvent", {"type": tipo, "x": xy[0], "y": xy[1], "button": "left", "clickCount": n})
        time.sleep(1.2)
        m1 = {"sons": b.js("window.__sons"), "na_dona": s.js("!!findInBuild(%r)" % lend[0])}
        p.conta("duas abas", "controle remoto (T94, cético): o duplo clique rápido num card daqui põe e tira, com os dois sons — o de tirar vem com a resposta",
                "build:item_add" in m1["sons"] and "catalog:click" in m1["sons"] and not m1["na_dona"], "%s" % m1)
        s.js("(() => { descartarAlteracoes(); window.ligarEdicao(false); build.selectedCatId = null; renderBuild(); return 'ok'; })()")
        espera(b, "!document.getElementById('edit-toggle').checked", 3)
        # navegar é livre: as abas da página e o endereço de cada tela
        rotas = []
        for aba in ("runas", "calc", "catalog", "build"):
            b.clicar('.tab-btn[data-tab="%s"]' % aba, 0.5)
            rotas.append(b.js("location.hash + '/' + document.querySelector('.tab-btn.active').dataset.tab"))
        p.conta("duas abas", "controle remoto: navegar é livre — Runas, Calculadora, Catálogo e Builds abrem com o endereço de cada uma",
                rotas[0] == "#runas/runas" and rotas[1] == "#calculadora/calc" and rotas[2] == "#catalogo/catalog" and rotas[3].endswith("/build"), "%s" % rotas)
        # a dona fecha a build (o ×, com o rascunho descartado): a bigorna daqui fica vazia e a forja vira a lista
        b.clicar("#bg-nome", 0.6)   # esta na forja
        s.js("(() => { descartarAlteracoes(); window.ligarEdicao(false); fecharBuild(); return 'ok'; })()")
        espera(b, "!build.id", 4)
        fe = b.js("({ id: build.id, lista: buildScreen, hash: location.hash, plaqueta: !document.getElementById('bigorna').hidden })")
        s.js("(() => { activateBuild(library.builds.find(x => x.name === 'Da aba 1').id); return 'ok'; })()")
        espera(b, "build.name === 'Da aba 1'", 4)
        p.conta("duas abas", "controle remoto: a dona fecha a build — a bigorna daqui fica vazia, a forja vira a lista (#builds); ela abre de novo e volta",
                fe["id"] is None and fe["lista"] == "lista" and fe["hash"] == "#builds" and not fe["plaqueta"] and b.js("build.name") == "Da aba 1", "fechada: %s" % fe)
        # Revisão do cético da T93: (1) o redesenho do espelho não tira o foco — a tecla seguinte entra
        # no mesmo campo da calculadora, e a linha da lista continua com o foco
        b.clicar('.tab-btn[data-tab="calc"]', 0.6)
        b.clicar("#calc-hp", 0.2)
        b.js("(() => { document.getElementById('calc-hp').select(); return 1; })()")
        b.envia("Input.insertText", {"text": "12"}); time.sleep(0.3)
        s.js("(() => { window.ligarEdicao(true); build.cats[0].items.push({ itemId: 'long-sword', note: '' }); saveBuild(); renderBuildAll(); return 'ok'; })()")
        espera(b, "!!build.cats[0] && build.cats[0].items.some(i => i.itemId === 'long-sword')", 4); time.sleep(0.3)
        b.envia("Input.insertText", {"text": "3"}); time.sleep(0.3)
        fc = b.js("({ valor: document.getElementById('calc-hp').value, foco: document.activeElement && document.activeElement.id })")
        b.clicar('.tab-btn[data-tab="build"]', 0.5)
        b.js("(() => { showBuildScreen('lista'); mostrarListaDe('minhas'); document.querySelector('#bi-rows .bi-row, .bi-row').focus(); return 1; })()")
        linha = b.js("document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.id || null : null")
        s.js("(() => { build.cats[0].items.push({ itemId: 'long-sword', note: '' }); saveBuild(); renderBuildAll(); return 'ok'; })()")
        espera(b, "build.cats[0].items.filter(i => i.itemId === 'long-sword').length === 2", 4); time.sleep(0.3)
        fl = b.js("document.activeElement && document.activeElement.classList.contains('bi-row') ? document.activeElement.dataset.id : (document.activeElement || {}).tagName")
        p.conta("duas abas", "controle remoto: a mudança da dona não tira o foco daqui — a tecla seguinte entra no mesmo campo da calculadora, e a linha da lista segue focada",
                fc["valor"] == "123" and fc["foco"] == "calc-hp" and bool(linha) and fl == linha, "calculadora %s · linha %s → %s" % (fc, linha, fl))
        # (2) a dona sai (fecha, quebra) com rascunho: a bigorna daqui volta ao disco, sem o rascunho morto; ela volta e ele aparece de novo
        time.sleep(3.2)   # o último recado da dona já tem mais de 3 s
        s.js("(() => { localStorage.setItem('montador.dona', JSON.stringify({ ...lerDona(), fora: 1 })); return 'ok'; })()")
        espera(b, "!build.cats[0].items.some(i => i.itemId === 'long-sword')", 5)
        fora = b.js("({ item: build.cats[0].items.some(i => i.itemId === 'long-sword'), plaqueta: document.getElementById('bg-estado').textContent, faixa: document.getElementById('remota-texto').textContent })")
        s.js("(() => { marcarDona(); refletirBigorna(); return 'ok'; })()")
        espera(b, "build.cats[0].items.some(i => i.itemId === 'long-sword')", 4)
        volta = b.js("({ item: build.cats[0].items.some(i => i.itemId === 'long-sword'), plaqueta: document.getElementById('bg-estado').textContent })")
        p.conta("duas abas", "controle remoto: a dona sai com rascunho — a bigorna daqui volta ao disco (sem o rascunho morto, sem \"não salva\"); ela volta e o rascunho reaparece",
                not fora["item"] and "não salva" not in fora["plaqueta"] and "saiu" in fora["faixa"] and volta["item"] and "não salva" in volta["plaqueta"],
                "dona fora: %s · de volta: %s" % (fora, volta))
        # (3) a plaqueta diz o que a dona diz: com rascunho, o Salvar é lá (não o Ctrl+S daqui); "não deu para salvar" com o mesmo título
        tt = b.js("document.getElementById('bg-estado').title")
        s.js("""(() => { window.__setOrig = Storage.prototype.setItem;
          Storage.prototype.setItem = function (k, v) { if (k === 'lol-builds-v3') throw new DOMException('cheio', 'QuotaExceededError'); return window.__setOrig.call(this, k, v); };
          salvarAgora(); fecharPub(); return 'ok'; })()""")
        espera(b, "document.getElementById('bg-estado').textContent.includes('não deu')", 4)
        pl = lambda q: q.js("({ texto: document.getElementById('bg-estado').textContent, titulo: document.getElementById('bg-estado').title })")
        pe, dn = pl(b), pl(s)
        s.js("(() => { Storage.prototype.setItem = window.__setOrig; descartarAlteracoes(); window.ligarEdicao(false); gravarBiblioteca(); return 'ok'; })()")
        p.conta("duas abas", "controle remoto: a plaqueta diz o que a dona diz — \"não deu para salvar\", com o mesmo título — e, com rascunho, que o Salvar é na outra aba",
                "na outra aba" in tt and "Ctrl+S" not in tt and "não deu para salvar" in pe["texto"] and pe == dn, "rascunho: %r · daqui %s · dona %s" % (tt, pe, dn))
        # (4) o coração de uma pública na dona redesenha a lista daqui (ID que o servidor "não tem": nada sai pela rede)
        b.js("""(() => { showBuildScreen('lista'); publicas.naoExistem.add('qa93fv'); window.__rbi = 0; const o = renderBuildIndex;
          renderBuildIndex = function () { window.__rbi++; return o.apply(this, arguments); }; return 1; })()""")
        s.js("(() => { publicas.naoExistem.add('qa93fv'); toggleFavorito('qa93fv'); return 'ok'; })()")
        espera(b, "window.__rbi > 0", 3)
        fv = b.js("({ n: window.__rbi, favs: favoritosIds() })")
        s.js("(() => { toggleFavorito('qa93fv'); return 'ok'; })()")
        p.conta("duas abas", "controle remoto: o coração de uma pública na dona redesenha a lista daqui", fv["n"] > 0 and "qa93fv" in fv["favs"], "%s" % fv)
        # (5) um link curto aberto numa aba que vira controle remoto, com o servidor (simulado) respondendo antes de
        # a trava decidir: a pública fica escolhida nas Públicas e a faixa avisa — antes abria na forja e sumia
        falso = r"""(() => { const f = window.fetch; window.fetch = function (u, ...a) { const t = String(u && u.url || u);
          if (!t.includes('supabase.co')) return f.call(this, u, ...a);
          const ok = (c) => new Response(JSON.stringify(c), { status: 200, headers: { 'Content-Type': 'application/json' } });
          if (!t.includes('/rest/v1/builds_publicas') || !t.includes('id=eq.c93c93')) return Promise.resolve(ok([]));
          const C = window.CATALOG;
          return Promise.resolve(ok([{ id: 'c93c93', nome: 'Pública do link QA', descricao: 'servidor simulado', campeao: null, modo: '', marcadores: [],
            caixas: [{ name: 'Núcleo', kind: 'comum', items: C.items.filter(i => i.tier === 'Lendário').slice(0, 2).map(i => ({ itemId: i.slug })) }],
            versao: 1, atualizado_em: new Date().toISOString(), patch: C.meta.patch, autor: 'roteiro', engajamentos: 0, pop_dia: 0, popular_semana: false,
            dias_no_top: 0, layout: null, runas: null, habilidades: null }])); }; })();"""
        y = s.nova_aba()
        y.envia("Page.addScriptToEvaluateOnNewDocument", {"source": falso})
        y.abrir("#build/c93c93"); decidiu(y); time.sleep(0.6)
        ly = y.js("({ remota: remota.ativa, sel: biSelected, tela: buildScreen, lista: biView, hash: location.hash, temp: !!build.temp, id: build.id, aviso: document.getElementById('remota-texto').textContent })")
        p.conta("duas abas", "um link curto numa aba que vira controle remoto, com a resposta antes da trava decidir: a pública fica escolhida nas Públicas e a faixa avisa (não abre na forja)",
                ly["remota"] and ly["sel"] == "pub:c93c93" and ly["tela"] == "lista" and ly["lista"] == "publicas" and ly["hash"] == "#builds"
                and not ly["temp"] and ly["id"] == s.js("build.id") and "escolhida nas Públicas" in ly["aviso"], "aba: %s" % ly)
        y.fechar_aba(); y = None
        # a aba 1 na forja com uma caixa escolhida (o Esc solta a caixa — atalho da página inteira)
        s.js("(() => { showBuildScreen('forja'); build.selectedCatId = build.cats[0] && build.cats[0].id; renderBuild(); return 'ok'; })()")
        # a aba 2 assume pelo "Usar esta aba" da faixa: recarrega do disco, com a build da aba 1
        ok = recarregou(b, "#remota-usar")
        if ok:
            b.entrar()
        espera(s, "!souDona", 3)
        va, vb2 = veu(s), veu(b)
        tem = b.js("library.builds.map(x => x.name)") if ok else []
        p.conta("duas abas", "\"Usar esta aba\" recarrega do disco e assume; a outra fica parada",
                ok and not vb2 and "Da aba 1" in tem and bool(va) and va["parado"] and "passou a usar" in va["texto"],
                "recarregou %s · aba 2: %s · véu na aba 2 %s · véu na aba 1: %s" % (ok, tem, vb2, va))
        caixa = s.js("build.selectedCatId")
        for tipo in ("rawKeyDown", "keyUp"):
            s.envia("Input.dispatchKeyEvent", {"type": tipo, "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27})
        time.sleep(0.3)
        depois = s.js("build.selectedCatId")
        # o Ctrl+S não abre o "Salvar como" do navegador (o evento sai anulado)
        salvar = s.js("!document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true, cancelable: true }))")
        p.conta("duas abas", "parada, a aba não obedece aos atalhos (o Esc não mexe na forja; o Ctrl+S não abre o \"Salvar como\")",
                bool(caixa) and depois == caixa and salvar is True,
                "caixa escolhida antes %s · depois do Esc %s · Ctrl+S anulado %s" % (caixa, depois, salvar))
        # a aba 2 cria outra; a aba 1 (que perdeu a vez) tenta gravar
        b.js("switchTab('build'); showBuildScreen('lista'); 'ok'"); time.sleep(0.6)
        b.clicar("#bi-new", 1.0); b.js("build.name = 'Da aba 2'; gravarBuild(); showBuildScreen('lista'); 'ok'"); time.sleep(0.4)
        gravou = s.js("gravarBiblioteca()")
        disco = no_disco()
        p.conta("duas abas", "a aba que perdeu a vez não grava por cima", "Da aba 1" in disco and "Da aba 2" in disco and gravou is False,
                "gravarBiblioteca na aba 1: %s · no disco: %s" % (gravou, disco))
        # a marca escrita por uma aba que já perdeu a vez (um confirm atrasado) não recusa a troca
        velha = s.js("""(async () => { const antes = localStorage.getItem('montador.dona');
          localStorage.setItem('montador.dona', JSON.stringify({ cliente: 'aba-que-perdeu', sujo: 1, ocupada: 0 }));
          const r = await donaOcupada(); localStorage.setItem('montador.dona', antes); return r; })()""")
        p.conta("duas abas", "a marca de uma aba que já perdeu a vez não recusa a troca", velha is False, "donaOcupada com a marca velha: %s" % velha)
        # com rascunho na dona, a troca é recusada (a aba parada nem recarrega)
        b.js("(() => { showBuildScreen('forja'); if (!build.editing) document.getElementById('edit-switch').click(); build.cats[0].items.push({ itemId: 'long-sword', note: '' }); saveBuild(); return 'ok'; })()")
        time.sleep(0.4)
        r = tentar_usar(s)
        p.conta("duas abas", "com alteração não salva na outra, \"Usar esta aba\" é recusado", r["fica"] and not r["dona"] and "alterações não salvas" in r["texto"],
                "ficou %s · virou dona %s · texto: %s" % (r["fica"], r["dona"], r["texto"]))
        b.js("descartarAlteracoes(); if (build.editing) document.getElementById('edit-switch').click(); 'ok'"); time.sleep(0.4)
        # com a gravação recusada na dona (T31), também: o que só está na memória dela não pode se perder
        b.js("""(() => { window.__setOrig = Storage.prototype.setItem;
          Storage.prototype.setItem = function (k, v) { if (k === 'lol-builds-v3') throw new DOMException('cheio', 'QuotaExceededError'); return window.__setOrig.call(this, k, v); };
          gravarBiblioteca(); fecharPub(); return 'ok'; })()""")
        recusada = (marca(b) or {}).get("sujo")
        r = tentar_usar(s)
        b.js("Storage.prototype.setItem = window.__setOrig; gravarBiblioteca(); 'ok'"); time.sleep(0.3)
        p.conta("duas abas", "com a gravação recusada na outra, \"Usar esta aba\" é recusado (e diz o que fazer lá)",
                recusada == 2 and r["fica"] and not r["dona"] and "gravação recusada" in r["texto"] and "Exportar/importar" in r["texto"],
                "marca na hora %s · ficou %s · virou dona %s · texto: %s" % (recusada, r["fica"], r["dona"], r["texto"]))
        # com uma publicação no ar na outra, também; a marca acompanha na hora (não na próxima volta)
        marcou = b.js("noServidor.set('qa-t35', 'publicando'); JSON.parse(localStorage.getItem('montador.dona')).ocupada === 1")
        r = tentar_usar(s)
        solto = b.js("noServidor.delete('qa-t35'); JSON.parse(localStorage.getItem('montador.dona')).ocupada === 0")
        p.conta("duas abas", "com publicação no ar na outra, \"Usar esta aba\" é recusado", marcou and solto and r["fica"] and not r["dona"] and "resposta da internet" in r["texto"],
                "marca na hora %s · solta na hora %s · ficou %s · virou dona %s · texto: %s" % (marcou, solto, r["fica"], r["dona"], r["texto"]))
        # excluir do site uma publicação que não está na biblioteca também é esperar a internet
        ex = b.js("""(async () => { window.__rpcOrig = Servidor.rpc; window.__confOrig = window.confirm; window.confirm = () => true;
          Servidor.rpc = (nome, a) => nome === 'apagar_build' ? new Promise(r => { window.__soltaRpc = r; }) : window.__rpcOrig(nome, a);
          excluirPublicacao('qa35xx'); await new Promise(r => setTimeout(r, 300));
          const esperando = JSON.parse(localStorage.getItem('montador.dona')).ocupada;
          window.__soltaRpc(true); await new Promise(r => setTimeout(r, 300));
          const depois = JSON.parse(localStorage.getItem('montador.dona')).ocupada;
          Servidor.rpc = window.__rpcOrig; window.confirm = window.__confOrig; fecharPub(); return { esperando, depois }; })()""")
        p.conta("duas abas", "excluir do site uma publicação fora da biblioteca conta como esperar a internet", ex["esperando"] == 1 and ex["depois"] == 0,
                "marca esperando %s · depois %s" % (ex["esperando"], ex["depois"]))
        # importação com campeão, esperando a lista da internet: também
        b.js("""(() => { window.__carregarOrig = Campeoes.carregar; Campeoes.carregar = () => new Promise(r => { window.__soltaCampeao = r; });
          switchTab('build'); showBuildScreen('forja');
          if (!document.getElementById('io-panel').classList.contains('show')) document.getElementById('toggle-io').click();
          const c = build.cats[0]; c.items.push({ itemId: 'long-sword', note: '' }); const t = buildToText(); c.items.pop();
          document.getElementById('import-text').value = t + String.fromCharCode(10) + 'Campeão: Ahri'; return 'ok'; })()""")
        time.sleep(0.4)
        b.clicar("#import-btn", 0.6)
        esperando = (marca(b) or {}).get("ocupada")
        r = tentar_usar(s)
        b.js("window.__soltaCampeao && window.__soltaCampeao(); Campeoes.carregar = window.__carregarOrig; 'ok'"); time.sleep(0.4)
        solto = (marca(b) or {}).get("ocupada")
        p.conta("duas abas", "com a importação esperando o campeão na outra, \"Usar esta aba\" é recusado",
                esperando == 1 and solto == 0 and r["fica"] and not r["dona"] and "resposta da internet" in r["texto"],
                "marca esperando %s · depois %s · ficou %s · texto: %s" % (esperando, solto, r["fica"], r["texto"]))
        # a dona recarrega (F5): continua dona
        b.abrir(); decidiu(b)
        f5 = b.js("({ dona: souDona, veu: !!document.getElementById('aba-dona') })")
        p.conta("duas abas", "a dona recarrega (F5) e continua dona", f5["dona"] and not f5["veu"] and s.js("!souDona"), "aba 2 depois do F5: %s" % f5)
        # a dona vai a outra página e volta (Voltar): volta inteira, do cache do navegador —
        # a parada não a tira de lá (a consulta da trava a despejava) — e retoma a marca
        b.envia("Page.bringToFront"); b.js("window.__fica = 1; 'ok'")
        b.envia("Page.navigate", {"url": b.url + "docs/qa.md"}); time.sleep(4.5)
        # F13-T93: um recado do controle remoto chega enquanto a dona está guardada — com o canal
        # aberto, o navegador a tiraria do cache do Voltar (visto: ela recarregava); fechado na saída, não
        s.js("(() => { const c = new BroadcastChannel('montador.remoto'); c.postMessage({ tipo: 'pedir' }); c.close(); return 1; })()"); time.sleep(0.8)
        fora = texto_veu(s)
        hist = b.envia("Page.getNavigationHistory")
        b.envia("Page.navigateToHistoryEntry", {"entryId": hist["entries"][hist["currentIndex"] - 1]["id"]}); time.sleep(2)
        vt = b.js("({ fica: window.__fica === 1, dona: souDona })")
        espera(s, "(document.getElementById('aba-dona-texto') || {}).textContent.includes('já está aberto')", 4)
        volta = texto_veu(s)
        p.conta("duas abas", "a dona vai a outra página e volta inteira (Voltar), mesmo com um recado do controle remoto na espera; a parada acompanha",
                "saiu do Montador" in fora and vt["fica"] and vt["dona"] and "já está aberto" in volta,
                "véu com a dona fora: %s · a dona voltou: %s · véu depois: %s" % (fora[:45], vt, volta[:45]))
        # a dona fecha: a parada avisa (pela marca) e assume com um clique; a entrada da loja volta a ter o foco
        b.fechar_aba()
        espera(s, "(document.getElementById('aba-dona-texto') || {}).textContent.includes('saiu do Montador')", 5)
        vs = veu(s) or {}
        ok = "saiu do Montador" in vs.get("texto", "") and recarregou(s, "#aba-dona-usar")
        fim = s.js("({ dona: souDona, veu: !!document.getElementById('aba-dona'), foco: document.activeElement && document.activeElement.id, nomes: library.builds.map(x => x.name) })") if ok else {}
        if ok:
            s.entrar()
        p.conta("duas abas", "a outra fechou: a parada avisa e assume, com as duas builds",
                ok and vs.get("titulo") == "A outra aba saiu" and fim["dona"] and not fim["veu"] and fim["foco"] == "entrar" and "Da aba 1" in fim["nomes"] and "Da aba 2" in fim["nomes"],
                "véu: %s · depois: %s" % (vs, fim))
        # um link de build (#b=) aberto enquanto a loja está em outra aba: o véu avisa
        # que a build só é guardada usando esta aba, e fechar pergunta antes
        s.js("switchTab('build'); showBuildScreen('lista'); 'ok'"); time.sleep(0.4)
        hash_ = s.js("(() => { const x = library.builds.find(y => y.name === 'Da aba 2'); const l = buildParaLink({ ...x, id: 'qa-link-35', name: 'Do link' }); return l.slice(l.indexOf('#')); })()")
        e = s.nova_aba(); e.abrir(hash_); decidiu(e)
        lk = e.js("({ texto: (document.getElementById('remota-texto') || {}).textContent || '', sair: !window.dispatchEvent(new Event('beforeunload', { cancelable: true })), na: library.builds.some(x => x.name === 'Do link') })")
        p.conta("duas abas", "um link de build aberto numa aba de controle remoto: a faixa avisa que ela só entra usando esta aba, e fechar pergunta",
                "só entra na biblioteca se você usar esta aba" in lk["texto"] and lk["sair"] is True and not lk["na"], "faixa: %s · aviso de saída %s · na memória %s" % (lk["texto"], lk["sair"], lk["na"]))
        e.fechar_aba(); e = None
        # a dona presa num confirm() (o Excluir) enquanto outra aba assume e cria uma build:
        # o OK de lá não pode gravar a biblioteca velha por cima. O confirm é trocado por
        # uma espera que trava a aba do mesmo jeito (o roteiro aceita os de verdade na hora).
        c = s.nova_aba(); c.abrir(); decidiu(c)
        s.js("""(() => { showBuildScreen('forja');
          window.confirm = () => { const fim = Date.now() + 9000; while (Date.now() < fim) {} return true; };
          setTimeout(() => document.getElementById('del-build').click(), 50); return 'ok'; })()""")
        time.sleep(0.5)
        assumiu = recarregou(c, expr="usarEstaAba(); 'ok'")
        if assumiu:
            c.entrar()
            c.js("switchTab('build'); showBuildScreen('lista'); 'ok'"); time.sleep(0.5)
            c.clicar("#bi-new", 1.0); c.js("build.name = 'Da aba 3'; gravarBuild(); 'ok'")
        s.js("'acordou'"); time.sleep(0.6)          # espera o "confirm" da aba 1 terminar
        disco = no_disco()
        r = s.js("({ dona: souDona, texto: (document.getElementById('aba-dona-texto') || {}).textContent || '' })")
        p.conta("duas abas", "a dona presa num diálogo não grava por cima da aba que assumiu",
                assumiu and "Da aba 3" in disco and not r["dona"] and "passou a usar" in r["texto"],
                "a outra assumiu %s · no disco: %s · aba presa: %s" % (assumiu, disco, r))
        # o "Limpar build" depois do confirm, numa aba que perdeu a vez e ainda não
        # sabe (o aviso da trava atrasado): pergunta ao navegador antes de mexer
        antes = marca(s)
        lb = s.js("""(async () => { const n = build.cats.length; souDona = true; window.confirm = () => true;
          document.getElementById('clear-build').click(); await new Promise(r => setTimeout(r, 400));
          return { antes: n, depois: build.cats.length, dona: souDona }; })()""")
        depois = marca(s)
        p.conta("duas abas", "o \"Limpar build\" numa aba que perdeu a vez sem saber não mexe em nada",
                lb["antes"] > 0 and lb["depois"] == lb["antes"] and not lb["dona"] and depois == antes,
                "caixas %s → %s · dona %s · marca antes %s · depois %s" % (lb["antes"], lb["depois"], lb["dona"], antes, depois))
        # uma aba nova espera a vez (a trava tem uma pequena espera, para o F5) enquanto
        # a dona grava e sai: a nova tem de reler o disco, não assumir com a memória velha
        d = s.nova_aba(); d.abrir()
        c.js("build.name = 'Antes de sair'; gravarBuild(); 'ok'")
        c.envia("Page.navigate", {"url": "about:blank"})
        decidiu(d); time.sleep(0.5)
        decidiu(d)
        d.js("gravarBiblioteca(); 'ok'")
        rd = d.js("({ dona: souDona, nomes: library.builds.map(x => x.name) })")
        disco = no_disco()
        p.conta("duas abas", "a biblioteca que mudou enquanto a aba nova esperava a vez é relida",
                rd["dona"] and "Antes de sair" in rd["nomes"] and "Antes de sair" in disco,
                "aba nova: %s · no disco: %s" % (rd, disco))
        # "Usar esta aba" numa aba de link: assume sem o aviso falso de saída ("Recarregar
        # site?") — o #b= fica na URL e a build do link entra na carga nova
        hash2 = d.js("(() => { const x = library.builds.find(y => !y.temp); const l = buildParaLink({ ...x, id: 'qa-link-35b', name: 'Do link 2' }); return l.slice(l.indexOf('#')); })()")
        f = s.nova_aba()
        # o diário da aba (sessionStorage, sobrevive à recarga): cada carga, o pedido de
        # assumir que ela encontrou e os cliques que chegaram ao botão — quando falha, diz onde
        f.envia("Page.addScriptToEvaluateOnNewDocument", {"source": "(() => { try { const d = JSON.parse(sessionStorage.getItem('qa.diario') || '[]');"
            " d.push('carga' + (sessionStorage.getItem('montador.assumir') ? ' com pedido' : '')); sessionStorage.setItem('qa.diario', JSON.stringify(d)); } catch (e) {}"
            " ['pointerdown', 'click'].forEach(tipo => window.addEventListener(tipo, (e) => { const d = JSON.parse(sessionStorage.getItem('qa.diario') || '[]');"
            " d.push(tipo + ':' + ((e.target && (e.target.id || e.target.className || e.target.nodeName)) || '?') + '@' + Math.round(e.clientX) + ',' + Math.round(e.clientY));"
            " sessionStorage.setItem('qa.diario', JSON.stringify(d)); }, true)); })()"})
        f.abrir(hash2); decidiu(f)
        # F13-T93 (cético): no controle remoto ela navega — o #b= sai do endereço, e o "Usar esta aba" ainda recebe a build
        f.clicar('.tab-btn[data-tab="catalog"]', 0.6)
        f.dialogos.clear()
        na_hora = f.js("(() => { const b = document.getElementById('remota-usar'); const r = b.getBoundingClientRect(); const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
                       " return document.visibilityState + '/' + document.hasFocus() + ' · no ponto ' + (e && (e.id || e.className || e.nodeName)) + ' @' + Math.round(r.left + r.width / 2) + ',' + Math.round(r.top + r.height / 2); })()")
        assumiu = recarregou(f, "#remota-usar")
        rf = f.js("({ dona: souDona, link: library.builds.some(x => x.name === 'Do link 2') })") if assumiu else \
            f.js("({ faixa: (document.getElementById('remota-texto') || {}).textContent, marca: JSON.stringify(lerDona()), diario: sessionStorage.getItem('qa.diario'), decidido })")
        avisos = [x for x in f.dialogos if x.startswith("beforeunload")]
        p.conta("duas abas", "\"Usar esta aba\" numa aba de link assume sem o aviso falso de saída, com a build do link",
                assumiu and rf["dona"] and rf["link"] and not avisos, "assumiu %s · %s · avisos: %s · na hora do clique: %s" % (assumiu, rf, avisos or "nenhum", na_hora))
        # a dona que quebra sem avisar (sem pagehide, a marca não diz "saiu"): a parada percebe pela trava
        # — e a faixa do controle remoto também (F13-T93)
        x = s.nova_aba(); x.abrir(); decidiu(x)
        tx0 = texto_rem(x)
        f.ws.send(json.dumps({"id": 99999, "method": "Page.crash"}))
        espera(s, "(document.getElementById('aba-dona-texto') || {}).textContent.includes('não responde mais')", 6)
        espera(x, "(document.getElementById('remota-texto') || {}).textContent.includes('não responde mais')", 6)
        tq, tx = texto_veu(s), texto_rem(x)
        p.conta("duas abas", "a dona que quebra sem avisar: a parada e o controle remoto percebem",
                "não responde mais" in tq and "Controle remoto" in tx0 and "não responde mais" in tx, "véu: %s · faixa antes: %s · depois: %s" % (tq[:60], tx0[:40], tx[:60]))
        x.fechar_aba(); x = None
        # a página de captura da observação (#build-observacao): o foco volta ao editor depois do "conferindo"
        s.js("""(() => { const d = JSON.parse(localStorage.getItem('lol-builds-v3')); const b = d.builds.find(x => x.id === d.activeId) || d.builds[0];
          d.activeId = b.id; if (!b.cats.length) b.cats.push({ id: 'cat-qa', name: 'QA', desc: '', kind: 'comum', span: 2, items: [] });
          if (!b.cats[0].items.length) b.cats[0].items.push({ itemId: 'long-sword', note: '' });
          localStorage.setItem('lol-builds-v3', JSON.stringify(d)); return 'ok'; })()""")
        g = s.nova_aba(); g.abrir("#build-observacao"); decidiu(g); time.sleep(0.4)
        fo = g.js("({ dona: souDona, foco: document.activeElement && document.activeElement.id, editor: document.getElementById('note-editor').classList.contains('show') })")
        p.conta("duas abas", "a página de captura da observação fica com o foco no editor", fo["dona"] and fo["editor"] and fo["foco"] == "note-text", "%s" % fo)
        # F5 da dona com outra aba ainda conferindo (na fila da trava): a dona continua dona
        h = s.nova_aba(); h.abrir()
        g.abrir(); decidiu(g); decidiu(h); time.sleep(1.5)
        # a outra pode ter pego a trava no instante do F5 e perdido de volta: fica no véu "perdeu" (que
        # segue como era, F13-T93); senão, controle remoto
        f5 = {"dona": g.js("souDona"), "outra": h.js("({ dona: souDona, remota: remota.ativa, veu: !!document.getElementById('aba-dona') })")}
        p.conta("duas abas", "F5 da dona com outra aba na fila da trava: a dona continua dona",
                f5["dona"] and not f5["outra"]["dona"] and (f5["outra"]["remota"] or f5["outra"]["veu"]), "%s" % f5)
        # outra aba toma a trava bem na hora em que esta confere se ela é sua (entre a
        # concessão e a consulta): esta não assume — senão ficavam duas donas.
        # A conferência desta aba é atrasada de propósito, para a corrida ser certa.
        g.fechar_aba(); g = None; time.sleep(0.5)
        s.js("localStorage.setItem('montador.dona', JSON.stringify({ cliente: 'qa', sujo: 0, ocupada: 0 })); 'ok'")
        v = s.nova_aba()
        v.envia("Page.addScriptToEvaluateOnNewDocument", {"source": "(() => { if (!navigator.locks) return; const req = navigator.locks.request.bind(navigator.locks); navigator.locks.request = (nome, ...r) => String(nome).startsWith('montador.eu.') ? new Promise(ok => setTimeout(ok, 1500)).then(() => req(nome, ...r)) : req(nome, ...r); })()"})
        v.abrir()
        h.js("navigator.locks.request('montador.dona', { steal: true }, () => new Promise(() => {})); 'ok'")
        time.sleep(3.5)
        rv = v.js("({ dona: souDona, veu: !!document.getElementById('aba-dona'), remota: remota.ativa })")
        p.conta("duas abas", "outra aba toma a trava enquanto esta confere: esta não assume", not rv["dona"] and (rv["veu"] or rv["remota"]), "aba: %s" % rv)
        v.fechar_aba(); v = None
        # a aba nova que desiste da espera (2 s) justo quando a marca diz "saiu" — a
        # dona recarregando, que regrava a marca logo depois — não toma a vez: confere
        # de novo em 1 s. A trava continua com a aba de antes; o roteiro faz o papel da
        # dona que volta, regravando a marca a tempo.
        s.js("localStorage.setItem('montador.dona', JSON.stringify({ cliente: 'qa', sujo: 0, ocupada: 0, fora: 1 })); 'ok'")
        w = s.nova_aba(); w.abrir(); time.sleep(2.3)
        s.js("localStorage.setItem('montador.dona', JSON.stringify({ cliente: 'qa', sujo: 0, ocupada: 0 })); 'ok'")
        time.sleep(2.0)
        rw = w.js("({ dona: souDona, veu: !!document.getElementById('aba-dona'), remota: remota.ativa })")
        p.conta("duas abas", "o \"saiu\" que a dona regrava logo depois (F5) não faz a aba nova tomar a vez", not rw["dona"] and (rw["veu"] or rw["remota"]), "aba: %s" % rw)
        w.fechar_aba(); w = None
        # a trava negada pelo navegador (dados do site bloqueados): a aba sozinha
        # funciona, como antes — não fica presa no véu
        e = s.nova_aba()
        e.envia("Page.addScriptToEvaluateOnNewDocument", {"source": "(() => { const nega = () => Promise.reject(new DOMException('The request was denied.', 'SecurityError')); if (navigator.locks) { navigator.locks.request = nega; navigator.locks.query = nega; } })()"})
        e.abrir(); decidiu(e)
        ng = e.js("({ dona: souDona, veu: !!document.getElementById('aba-dona') })")
        p.conta("duas abas", "com a trava negada pelo navegador, a aba não fica presa no véu", ng["dona"] and not ng["veu"], "aba: %s" % ng)
    finally:
        for q in (b, c, d, e, f, g, h, v, w, x, y):
            if q:
                q.fechar_aba()


def checar_orfa(s, p):
    """F13-T34 (bug nº 42): excluir a build enquanto ela é publicada deixava a
    publicação no site sem lugar nenhum que guardasse o ID. Servidor SIMULADO:
    publicar_build fica preso até o roteiro soltar; apagar_build só é contado."""
    print(chr(10) + "%sPUBLICAÇÃO ÓRFÃ%s" % (AMARELO, FIM))
    s.nova_build()
    s.js("""(() => { window.__fetchOrig = window.fetch; window.__soltar = null; window.__apagados = []; window.__proxId = 'qa0042';
      window.__pubs = 0; window.__apagarPreso = false; window.__soltarApagar = null;
      window.fetch = function (u, opts, ...a) { const t = String(u);
        if (t.includes('publicar_build')) { window.__pubs++; return new Promise(res => { window.__soltar = () => res(new Response(JSON.stringify({ id: window.__proxId, versao: 1 }), { status: 200, headers: { 'Content-Type': 'application/json' } })); }); }
        if (t.includes('apagar_build')) { window.__apagados.push(JSON.parse(opts.body).p_id); const ok = () => new Response('true', { status: 200, headers: { 'Content-Type': 'application/json' } });
          return window.__apagarPreso ? new Promise(res => { window.__soltarApagar = () => res(ok()); }) : Promise.resolve(ok()); }
        if (t.includes('/rpc/') || t.includes('/rest/')) return Promise.resolve(new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }));
        return window.__fetchOrig.call(this, u, opts, ...a); };
      window.__stOrig = window.setTimeout; window.setTimeout = (f, ms, ...a) => window.__stOrig(f, ms === 30000 ? 300 : ms, ...a);
      if (build.editing) document.getElementById('edit-switch').click();
      build.name = 'Órfã de teste'; build.desc = 'descrição'; build.markers = normMarkers(MARCADORES.slice(0, 3).map(m => ({ t: 'tag', id: m.id })));
      build.cats[3].items = [{ itemId: 'long-sword', note: '' }]; gravarBuild();
      showBuildScreen('lista'); biSelected = build.id; renderBuildIndex(); return 'ok'; })()""")
    time.sleep(0.5)
    bid = s.js("build.id")
    s.clicar('#bi-detail [data-act="publish"]', 0.9)
    s.clicar("#pub-close", 0.3)                                    # o Fechar aparece depois da espera (encurtada)
    nd = len(s.dialogos)
    s.clicar('#bi-detail [data-act="del"]', 0.5)
    lista = s.js("({ placa: document.getElementById('pub-dialog').hidden ? '' : document.getElementById('pub-title').textContent })")
    s.js("fecharPub(); showBuildScreen('forja'); 'ok'"); time.sleep(0.5)
    s.clicar("#del-build", 0.5)
    forja = s.js("({ placa: document.getElementById('pub-dialog').hidden ? '' : document.getElementById('pub-title').textContent })")
    s.js("fecharPub(); showBuildScreen('lista'); 'ok'"); time.sleep(0.5)
    s.clicar("#bi-lote", 0.4)
    if isinstance(s.caixa('.bi-row[data-id="%s"]' % bid), list):
        s.clicar('.bi-row[data-id="%s"]' % bid, 0.3); s.clicar("#bl-excluir", 0.5)
        lote = s.js("(document.getElementById('bl-msg') || {}).textContent || ''")
    else:
        lote = "(a build já tinha sido excluída)"
    s.clicar("#bl-sair", 0.3)
    ficou = s.js("library.builds.some(b => b.id === %s)" % json.dumps(bid))
    s.js("window.__soltar && window.__soltar(); 'ok'"); time.sleep(0.8)
    pub = s.js("(library.builds.find(b => b.id === %s) || {}).pubId || null" % json.dumps(bid))
    s.js("fecharPub(); 'ok'")
    p.conta("publicação órfã", "com a publicação no ar, a build não se exclui (lista, forja, lote)",
            ficou and pub == "qa0042" and lista["placa"] == "Ainda publicando" and forja["placa"] == "Ainda publicando" and "Espere terminar" in lote and len(s.dialogos) == nd,
            "lista: %s · forja: %s · lote: %s · perguntas: %d · ID gravado: %s" % (lista["placa"] or "—", forja["placa"] or "—", lote[:30] or "—", len(s.dialogos) - nd, pub))
    # despublicar durante o "Atualizar publicação": a mesma trava
    s.clicar('#bi-detail [data-act="publish"]', 0.9); s.clicar("#pub-close", 0.3)
    nd = len(s.dialogos); ap = len(s.js("window.__apagados"))
    s.clicar('#bi-detail [data-act="unpub"]', 0.5)
    unpub = s.js("({ placa: document.getElementById('pub-dialog').hidden ? '' : document.getElementById('pub-title').textContent, apagados: window.__apagados.length })")
    s.js("fecharPub(); window.__soltar && window.__soltar(); 'ok'"); time.sleep(0.8); s.js("fecharPub(); 'ok'")
    p.conta("publicação órfã", "despublicar durante o \"Atualizar publicação\" espera", unpub["placa"] == "Ainda publicando" and unpub["apagados"] == ap and len(s.dialogos) == nd,
            "placa: %s · apagar_build: %d · perguntas: %d" % (unpub["placa"] or "—", unpub["apagados"] - ap, len(s.dialogos) - nd))
    # a defesa: se a build some mesmo assim, a publicação que acabou de nascer sai do site
    s.js("window.__proxId = 'qa0042b'; 'ok'")
    s.clicar('#bi-detail [data-act="publish"]', 0.9)
    s.js("(() => { deleteBuild(%s); window.__soltar && window.__soltar(); return 'ok'; })()" % json.dumps(bid)); time.sleep(0.9)
    fim = s.js("({ placa: document.getElementById('pub-dialog').hidden ? '' : document.getElementById('pub-title').textContent, apagados: window.__apagados })")
    # publicar durante uma exclusão no ar: a trava vale nos dois sentidos
    s.js("""(() => { fecharPub(); createNewBuild('Excluindo'); build.desc = 'descrição'; build.markers = normMarkers(MARCADORES.slice(0, 3).map(m => ({ t: 'tag', id: m.id })));
      build.cats[3].items = [{ itemId: 'long-sword', note: '' }]; gravarBuild();
      gravarMetadados(library.builds.find(b => b.id === build.id), { pubId: 'qa0043', pubVersao: 1, pubEm: Date.now(), pubPatch: CATALOG.meta.patch });
      window.__apagarPreso = true; showBuildScreen('lista'); biSelected = build.id; renderBuildIndex(); return 'ok'; })()""")
    time.sleep(0.5)
    s.clicar('#bi-detail [data-act="del"]', 0.9); s.clicar("#pub-close", 0.3)      # o "Tirando do site" ganha o Fechar
    pubs = s.js("window.__pubs")
    s.clicar('#bi-detail [data-act="publish"]', 0.5)
    exc = s.js("({ placa: document.getElementById('pub-dialog').hidden ? '' : document.getElementById('pub-title').textContent, pubs: window.__pubs })")
    s.js("fecharPub(); window.__soltarApagar && window.__soltarApagar(); 'ok'"); time.sleep(0.6)
    p.conta("publicação órfã", "publicar durante uma exclusão no ar espera", exc["placa"] == "Ainda tirando do site" and exc["pubs"] == pubs,
            "placa: %s · publicar_build: %d" % (exc["placa"] or "—", exc["pubs"] - pubs))
    # F13-T45 (nº 49): tirar do site duas vezes — o segundo pedido cobria o
    # sucesso do primeiro com um erro falso ("apague pelo painel do Supabase")
    s.js("""(() => { fecharPub(); createNewBuild('Dupla'); build.desc = 'descrição'; build.markers = normMarkers(MARCADORES.slice(0, 3).map(m => ({ t: 'tag', id: m.id })));
      build.cats[3].items = [{ itemId: 'long-sword', note: '' }]; gravarBuild();
      gravarMetadados(library.builds.find(b => b.id === build.id), { pubId: 'qa0049', pubVersao: 1, pubEm: Date.now(), pubPatch: CATALOG.meta.patch });
      window.__apagarPreso = true; window.__soltarApagar = null; showBuildScreen('lista'); biSelected = build.id; renderBuildIndex(); return 'ok'; })()""")
    time.sleep(0.5)
    ap = len(s.js("window.__apagados")); nd = len(s.dialogos)
    s.clicar('#bi-detail [data-act="unpub"]', 0.9); s.clicar("#pub-close", 0.3)
    s.clicar('#bi-detail [data-act="unpub"]', 0.5)
    dupla = s.js("({ placa: document.getElementById('pub-dialog').hidden ? '' : document.getElementById('pub-title').textContent, apagados: window.__apagados.length })")
    s.js("fecharPub(); window.__soltarApagar && window.__soltarApagar(); 'ok'"); time.sleep(0.8)
    final = s.js("({ placa: document.getElementById('pub-dialog').hidden ? '' : document.getElementById('pub-title').textContent })")
    p.conta("publicação órfã", "tirar do site duas vezes: o segundo espera, sem erro falso",
            dupla["placa"] == "Ainda tirando do site" and dupla["apagados"] - ap == 1 and len(s.dialogos) - nd == 1 and final["placa"] == "Build retirada do site",
            "segundo clique: %s · apagar_build: %d · perguntas: %d · no fim: %s" % (dupla["placa"] or "—", dupla["apagados"] - ap, len(s.dialogos) - nd, final["placa"] or "—"))
    s.js("fecharPub(); window.setTimeout = window.__stOrig; window.fetch = window.__fetchOrig; 'ok'")
    p.conta("publicação órfã", "se a build some mesmo assim, a publicação sai do site", fim["placa"] == "Publicação desfeita" and "qa0042b" in fim["apagados"],
            "placa: %s · apagar_build: %s" % (fim["placa"] or "—", fim["apagados"]))


def checar_exclusao(s, p):
    """F13-T14: excluir uma build publicada prometia "ela também sai do site" e,
    se o servidor falhasse, apagava daqui calada — a publicação ficava no ar e o
    ID dela sumia. O servidor é SIMULADO: o pedido apagar_build nunca sai deste
    navegador, e o confirm é respondido pelo roteiro."""
    print(chr(10) + "%sEXCLUSÃO%s" % (AMARELO, FIM))
    s.js("""(() => { window.__fetchOrig = window.fetch; window.__confirmOrig = window.confirm;
      window.fetch = function (u, ...a) {
        if (String(u).includes('apagar_build')) return Promise.reject(new TypeError('Failed to fetch'));
        return window.__fetchOrig.call(this, u, ...a); };
      window.__confirms = []; window.__respostas = [true, false];   // sim ao Excluir; não a "apagar só daqui"
      window.confirm = (m) => { window.__confirms.push(m); return window.__respostas.length ? window.__respostas.shift() : false; };
      return 'ok'; })()""")
    s.nova_build()
    bid = s.js("""(() => { build.name = 'Publicada de teste'; build.pubId = 'qa0000';
      build.cats[3].items = CATALOG.items.slice(0, 2).map(i => ({ itemId: i.slug, note: '' })); gravarBuild(); return build.id; })()""")
    s.nova_build()
    s.js("switchTab('build'); showBuildScreen('lista'); biSelected = %s; renderBuildIndex(); 'ok'" % json.dumps(bid))
    time.sleep(0.5)
    s.js("""(() => { const b = [...document.querySelectorAll('[data-act="del"]')][0]; if (b) b.click(); return !!b; })()""")
    time.sleep(1.0)
    r = s.js("""(() => ({ ficou: library.builds.some(b => b.id === %s),
      pub: (library.builds.find(b => b.id === %s) || {}).pubId || null, perguntas: window.__confirms }))()""" % (json.dumps(bid), json.dumps(bid)))
    p.conta("exclusão", "servidor fora do ar: a publicada não some calada",
            len(r["perguntas"]) == 2 and "continua no site" in r["perguntas"][1],
            (r["perguntas"][1][:70] if len(r["perguntas"]) > 1 else "só %d pergunta(s)" % len(r["perguntas"])))
    p.conta("exclusão", "dizendo não, a build fica, com o ID guardado", r["ficou"] and r["pub"] == "qa0000")
    s.js("window.fetch = window.__fetchOrig; window.confirm = window.__confirmOrig; 'ok'")


def checar_rascunho(s, p):
    """F13-T24 (bug nº 37): abrir de novo a build que já está na forja recarregava
    a cópia salva por cima do rascunho, calado. Chega-se à lista com o rascunho
    sujo pela aba Builds (a troca de aba não pergunta, de propósito: F10-T2); aqui
    esse caminho é montado por JS e o gesto testado é o de verdade — duplo clique
    na linha, o botão Editar do detalhe, o coração. Não basta ver o item na forja:
    se o rascunho fosse gravado calado ele também estaria lá, então a checagem
    olha o `rascunho.sujo` e o localStorage."""
    print("\n%sRASCUNHO%s" % (AMARELO, FIM))
    s.nova_build()
    id_b = s.js("build.id")
    s.nova_build()
    id_a = s.js("build.id")
    if not s.js("build.editing"):
        s.clicar("#edit-switch", 0.8)
    s.js("""(() => { build.cats[3].items.push({ itemId: 'long-sword', note: 'rascunho' }); saveBuild(); renderBuildAll();
      showBuildScreen('lista'); return 'ok'; })()""")
    time.sleep(0.6)
    estado = lambda: s.js("""(() => { const disco = JSON.parse(localStorage.getItem('lol-builds-v3') || '{"builds":[]}').builds;
      const d = (id) => disco.find(b => b.id === id) || {};
      return { na_forja: build.cats.some(c => c.items.some(e => e.note === 'rascunho')), sujo: rascunho.sujo,
        no_disco: (d(%s).cats || []).some(c => c.items.some(e => e.note === 'rascunho')),
        forja: !document.getElementById('build-editor').hidden, ativa: build.id,
        fav_a: !!d(%s).fav, fav_b: !!d(%s).fav, dialogo: !document.getElementById('save-dialog').hidden }; })()"""
                          % (json.dumps(id_a), json.dumps(id_a), json.dumps(id_b)))
    intacto = lambda e: e["na_forja"] and e["sujo"] and not e["no_disco"] and e["ativa"] == id_a
    antes = estado()
    linha = '.bi-row[data-id="%s"]' % id_a
    c = s.caixa(linha)
    for n in (1, 2):
        for tipo in ("mousePressed", "mouseReleased"):
            s.envia("Input.dispatchMouseEvent", {"type": tipo, "x": c[0], "y": c[1], "button": "left", "clickCount": n})
    time.sleep(1.0)
    e = estado()
    p.conta("rascunho", "duplo clique na build aberta não apaga o rascunho", intacto(antes) and intacto(e) and e["forja"],
            "na forja %s, sujo %s, no disco %s" % (e["na_forja"], e["sujo"], e["no_disco"]))
    s.js("showBuildScreen('lista'); 'ok'"); time.sleep(0.5)
    s.clicar(linha, 0.5)
    s.clicar('#bi-detail [data-act="edit"]', 1.0)
    e = estado()
    p.conta("rascunho", "o Editar do detalhe também não", intacto(e) and e["forja"],
            "na forja %s, sujo %s, no disco %s" % (e["na_forja"], e["sujo"], e["no_disco"]))
    # o coração é gesto da lista: grava na hora, com o Editar ligado, sem o rascunho
    s.js("showBuildScreen('lista'); 'ok'"); time.sleep(0.5)
    s.clicar('.bi-fav[data-fav="%s"]' % id_b, 0.5)
    s.clicar('.bi-fav[data-fav="%s"]' % id_a, 0.5)
    e = estado()
    p.conta("rascunho", "o coração grava na hora, sem gravar o rascunho", e["fav_a"] and e["fav_b"] and intacto(e),
            "fav A %s, fav B %s, sujo %s, rascunho no disco %s" % (e["fav_a"], e["fav_b"], e["sujo"], e["no_disco"]))
    # caminho antigo: o Descartar continua voltando à cópia salva, e o favorito fica
    s.clicar(linha, 0.3)
    s.clicar('#bi-detail [data-act="edit"]', 1.0)
    s.clicar("#discard-btn", 0.5)
    s.clicar('#save-dialog [data-sd="descartar"]', 1.0)
    e = estado()
    p.conta("rascunho", "Descartar ainda volta ao salvo (e o favorito fica)",
            not e["na_forja"] and not e["sujo"] and e["fav_a"] and s.js("build.fav") is True,
            "na forja %s, sujo %s, fav %s" % (e["na_forja"], e["sujo"], e["fav_a"]))


def checar_troca(s, p):
    """F13-T25 (bug nº 38): na forja, trocar de build, criar e duplicar perguntam
    pelo rascunho; na lista e no Importar, os mesmos gestos gravavam o rascunho
    calados. E o que só mexe em OUTRA build (excluir, a janela "Falta pouco para
    publicar") gravava junto o rascunho da aberta. Cada checagem monta o próprio
    estado (a build A aberta, suja, na lista) por JS; o gesto testado é o de
    verdade. O diálogo só é respondido se apareceu: no código de antes ele não
    aparece, e cada checagem tem de falhar por si, não o grupo parar na primeira."""
    print("\n%sTROCA DE BUILD%s" % (AMARELO, FIM))
    ids = []
    for _ in range(3):
        s.nova_build()
        ids.append(s.js("build.id"))
    id_c, id_b, id_a = ids
    if not s.js("build.editing"):
        s.clicar("#edit-switch", 0.8)

    def preparar():
        s.js("""(() => { rascunho.sujo = false; activateBuild(%s, true); renderBuildAll();
          build.cats[3].items.push({ itemId: 'long-sword', note: 'rascunho' }); saveBuild(); renderBuildAll();
          showBuildScreen('lista'); return 'ok'; })()""" % json.dumps(id_a))
        time.sleep(0.5)

    def estado():
        return s.js("""(() => { const disco = JSON.parse(localStorage.getItem('lol-builds-v3') || '{"builds":[]}').builds;
          const d = (id) => disco.find(b => b.id === id) || {};
          return { ativa: build.id === %s ? 'A' : build.id === %s ? 'B' : build.name, sujo: rascunho.sujo,
            dialogo: !document.getElementById('save-dialog').hidden,
            a_disco: (d(%s).cats || []).some(c => c.items.some(e => e.note === 'rascunho')),
            nome_a: d(%s).name || '', existe_c: library.builds.some(b => b.id === %s), n: library.builds.length }; })()"""
                    % (json.dumps(id_a), json.dumps(id_b), json.dumps(id_a), json.dumps(id_a), json.dumps(id_c)))

    def responder(sd):
        if s.js("!document.getElementById('save-dialog').hidden"):
            s.clicar('#save-dialog [data-sd="%s"]' % sd, 1.0)

    def duplo(sel):
        c = s.caixa(sel)
        for n in (1, 2):
            for tipo in ("mousePressed", "mouseReleased"):
                s.envia("Input.dispatchMouseEvent", {"type": tipo, "x": c[0], "y": c[1], "button": "left", "clickCount": n})
        time.sleep(1.0)

    def limpar_a():   # tira da cópia salva de A o rascunho que um "Salvar" de propósito gravou
        s.js("(() => { const a = library.builds.find(b => b.id === %s); a.cats.forEach(c => c.items = c.items.filter(x => x.note !== 'rascunho')); gravarBiblioteca(); return 'ok'; })()" % json.dumps(id_a))

    preparar()
    duplo('.bi-row[data-id="%s"]' % id_b)
    e = estado()
    responder("voltar")
    e2 = estado()
    p.conta("troca", "abrir outra build pela lista pergunta",
            e["dialogo"] and e["ativa"] == "A" and not e["a_disco"] and e2["ativa"] == "A" and e2["sujo"],
            "diálogo %s, ativa %s, rascunho no disco %s" % (e["dialogo"], e["ativa"], e["a_disco"]))
    # pelo teclado: Enter na linha abre o diálogo com o foco nele, e o Enter
    # seguinte responde "Continuar editando" em vez de acionar a lista por trás
    preparar()
    s.clicar('.bi-row[data-id="%s"]' % id_b, 0.4)
    for tipo in ("keyDown", "keyUp"):
        s.envia("Input.dispatchKeyEvent", {"type": tipo, "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "text": chr(13)})
    time.sleep(0.6)
    foco = s.js("document.activeElement.dataset.sd || document.activeElement.className")
    for tipo in ("keyDown", "keyUp"):
        s.envia("Input.dispatchKeyEvent", {"type": tipo, "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "text": chr(13)})
    time.sleep(0.6)
    e = estado()
    p.conta("troca", "o diálogo recebe o foco (Enter responde nele)", foco == "voltar" and not e["dialogo"] and e["ativa"] == "A" and e["sujo"],
            "foco em %r, diálogo aberto %s, ativa %s" % (foco, e["dialogo"], e["ativa"]))
    responder("voltar")
    preparar()
    duplo('.bi-row[data-id="%s"]' % id_b)
    viu = s.js("!document.getElementById('save-dialog').hidden")
    responder("salvar")
    e = estado()
    p.conta("troca", "\"Salvar e sair\" grava e abre a outra", viu and e["ativa"] == "B" and e["a_disco"] and not e["sujo"],
            "diálogo %s, ativa %s, rascunho de A no disco %s" % (viu, e["ativa"], e["a_disco"]))
    limpar_a()
    preparar()
    n0 = s.js("library.builds.length")
    s.clicar("#bi-new", 0.6)
    e = estado()
    responder("voltar")
    p.conta("troca", "\"+ Nova build\" da lista pergunta", e["dialogo"] and e["n"] == n0 and not e["a_disco"],
            "diálogo %s, builds %d → %d, rascunho no disco %s" % (e["dialogo"], n0, e["n"], e["a_disco"]))
    preparar()
    s.clicar('.bi-row[data-id="%s"]' % id_c, 0.5)
    s.clicar('#bi-detail [data-act="del"]', 1.2)
    e = estado()
    p.conta("troca", "excluir outra build não grava o rascunho", not e["existe_c"] and e["sujo"] and not e["a_disco"],
            "excluída %s, sujo %s, rascunho de A no disco %s" % (not e["existe_c"], e["sujo"], e["a_disco"]))
    # F13-T45 (nº 45): com rascunho, publicar pergunta ANTES da janela "Falta
    # pouco" — antes ela abria com o rascunho, e o marcador escolhido ali levava
    # a lista do rascunho para a cópia salva. Continuar editando não grava nada.
    preparar()
    s.clicar('.bi-row[data-id="%s"]' % id_a, 0.5)
    s.clicar('#bi-detail [data-act="publish"]', 0.8)
    e = estado()
    aberta = s.js("!document.getElementById('pub-falta').hidden")
    responder("voltar")
    p.conta("troca", "publicar com rascunho pergunta antes da janela \"Falta pouco\"",
            e["dialogo"] and not aberta and not e["a_disco"],
            "pergunta %s, janela %s, rascunho no disco %s" % (e["dialogo"], aberta, e["a_disco"]))
    # Salvar e seguir: a janela abre depois, e o que se digita nela grava na cópia
    # viva (a da T25: o Salvar troca o objeto da build na biblioteca).
    preparar()
    s.clicar('.bi-row[data-id="%s"]' % id_a, 0.5)
    s.clicar('#bi-detail [data-act="publish"]', 0.8)
    responder("salvar")
    aberta = s.js("!document.getElementById('pub-falta').hidden")
    s.clicar("#pf-desc", 0.2)
    s.envia("Input.insertText", {"text": "Descrição depois do Salvar"})
    time.sleep(0.6)
    desc = s.js("(JSON.parse(localStorage.getItem('lol-builds-v3')).builds.find(b => b.id === %s) || {}).desc || ''" % json.dumps(id_a))
    s.clicar("#pf-close", 0.4)
    p.conta("troca", "Salvar e seguir: a janela abre e o que se digita grava", aberta and desc == "Descrição depois do Salvar",
            "janela %s, descrição no disco %r" % (aberta, desc))
    limpar_a()
    preparar()
    s.js("showBuildScreen('forja'); 'ok'"); time.sleep(0.6)
    if not s.js("document.getElementById('io-panel').classList.contains('show')"):
        s.clicar("#toggle-io", 0.5)
    s.js("document.getElementById('import-text').value = 'BUILD: Importada na troca\\n[COMUM] Core\\n- Gume do Infinito'; 'ok'")
    s.clicar("#import-btn", 0.8)
    e = estado()
    responder("descartar")
    e2 = estado()
    p.conta("troca", "Importar pergunta (e Descartar não grava)",
            e["dialogo"] and e["ativa"] == "A" and e2["ativa"] == "Importada na troca" and not e2["a_disco"],
            "diálogo %s, depois: %s, rascunho de A no disco %s" % (e["dialogo"], e2["ativa"], e2["a_disco"]))


# F13-T50: o daltonismo medido como a pessoa vê. Simulação de Machado, Oliveira
# e Fernandes (2009), com a tabela publicada (severidade 0,1 a 1,0; conferida com
# o colorspacious, cvd.py). F13-T50b: antes era só a plena e uma "parcial" feita
# a meio caminho da identidade, que não é a de Machado e escondia o pior caso
# (a menor distância não cresce junto com a severidade). A distância é a ΔE2000
# entre as cores (CIELAB D65).
DALT_T = {
    "protan": {
        1: [[0.856167, 0.182038, -0.038205], [0.029342, 0.955115, 0.015544], [-0.00288, -0.001563, 1.004443]],
        2: [[0.734766, 0.334872, -0.069637], [0.05184, 0.919198, 0.028963], [-0.004928, -0.004209, 1.009137]],
        3: [[0.630323, 0.465641, -0.095964], [0.069181, 0.890046, 0.040773], [-0.006308, -0.007724, 1.014032]],
        4: [[0.539009, 0.579343, -0.118352], [0.082546, 0.866121, 0.051332], [-0.007136, -0.011959, 1.019095]],
        5: [[0.458064, 0.679578, -0.137642], [0.092785, 0.846313, 0.060902], [-0.007494, -0.016807, 1.024301]],
        6: [[0.38545, 0.769005, -0.154455], [0.100526, 0.829802, 0.069673], [-0.007442, -0.02219, 1.029632]],
        7: [[0.319627, 0.849633, -0.169261], [0.106241, 0.815969, 0.07779], [-0.007025, -0.028051, 1.035076]],
        8: [[0.259411, 0.923008, -0.18242], [0.110296, 0.80434, 0.085364], [-0.006276, -0.034346, 1.040622]],
        9: [[0.203876, 0.990338, -0.194214], [0.112975, 0.794542, 0.092483], [-0.005222, -0.041043, 1.046265]],
        10: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    },
    "deutan": {
        1: [[0.866435, 0.177704, -0.044139], [0.049567, 0.939063, 0.01137], [-0.003453, 0.007233, 0.99622]],
        2: [[0.760729, 0.319078, -0.079807], [0.090568, 0.889315, 0.020117], [-0.006027, 0.013325, 0.992702]],
        3: [[0.675425, 0.43385, -0.109275], [0.125303, 0.847755, 0.026942], [-0.00795, 0.018572, 0.989378]],
        4: [[0.605511, 0.52856, -0.134071], [0.155318, 0.812366, 0.032316], [-0.009376, 0.023176, 0.9862]],
        5: [[0.547494, 0.607765, -0.155259], [0.181692, 0.781742, 0.036566], [-0.01041, 0.027275, 0.983136]],
        6: [[0.498864, 0.674741, -0.173604], [0.205199, 0.754872, 0.039929], [-0.011131, 0.030969, 0.980162]],
        7: [[0.457771, 0.731899, -0.18967], [0.226409, 0.731012, 0.042579], [-0.011595, 0.034333, 0.977261]],
        8: [[0.422823, 0.781057, -0.203881], [0.245752, 0.709602, 0.044646], [-0.011843, 0.037423, 0.974421]],
        9: [[0.392952, 0.82361, -0.216562], [0.263559, 0.69021, 0.046232], [-0.01191, 0.040281, 0.97163]],
        10: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.01182, 0.04294, 0.968881]],
    },
    "tritan": {
        1: [[0.92667, 0.092514, -0.019184], [0.021191, 0.964503, 0.014306], [0.008437, 0.054813, 0.93675]],
        2: [[0.89572, 0.13333, -0.02905], [0.029997, 0.9454, 0.024603], [0.013027, 0.104707, 0.882266]],
        3: [[0.905871, 0.127791, -0.033662], [0.026856, 0.941251, 0.031893], [0.01341, 0.148296, 0.838294]],
        4: [[0.948035, 0.08949, -0.037526], [0.014364, 0.946792, 0.038844], [0.010853, 0.193991, 0.795156]],
        5: [[1.017277, 0.027029, -0.044306], [-0.006113, 0.958479, 0.047634], [0.006379, 0.248708, 0.744913]],
        6: [[1.104996, -0.046633, -0.058363], [-0.032137, 0.971635, 0.060503], [0.001336, 0.317922, 0.680742]],
        7: [[1.193214, -0.109812, -0.083402], [-0.058496, 0.97941, 0.079086], [-0.002346, 0.403492, 0.598854]],
        8: [[1.257728, -0.139648, -0.118081], [-0.078003, 0.975409, 0.102594], [-0.003316, 0.501214, 0.502102]],
        9: [[1.278864, -0.125333, -0.153531], [-0.084748, 0.957674, 0.127074], [-0.000989, 0.601151, 0.399838]],
        10: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.3039]],
    },
}


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _delin(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _rgb_css(txt):
    """rgb()/rgba() e também color(srgb r g b / a), que é como o Chrome devolve um color-mix"""
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", txt or "")
    if m:
        return [int(m.group(i)) / 255 for i in (1, 2, 3)]
    m = re.match(r"color\(srgb\s+([\d.e-]+)\s+([\d.e-]+)\s+([\d.e-]+)", txt or "")
    return [round(float(m.group(i)) * 255) / 255 for i in (1, 2, 3)] if m else None


def _simula(rgb, tipo, sev):
    """sev: 1 a 10 (décimos da severidade de Machado)."""
    if tipo == "normal":
        return rgb
    mm = DALT_T[tipo][sev]
    l = [_lin(c) for c in rgb]
    return [_delin(min(1, max(0, sum(mm[i][j] * l[j] for j in range(3))))) for i in range(3)]


def _lab(rgb):
    r, g, b = [_lin(c) for c in rgb]
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    return (116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z)))


def _de2000(l1, l2):
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    cb = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(cb ** 7 / (cb ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + g), a2 * (1 + g)
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dh = h2p - h1p
    if c1p * c2p == 0:
        dh = 0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dHp = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dh / 2))
    lbp, cbp = (L1 + L2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbp = (h1p + h2p + 360) / 2
    else:
        hbp = (h1p + h2p - 360) / 2
    t = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dth = 30 * math.exp(-((hbp - 275) / 25) ** 2)
    rc = 2 * math.sqrt(cbp ** 7 / (cbp ** 7 + 25 ** 7))
    sl = 1 + 0.015 * (lbp - 50) ** 2 / math.sqrt(20 + (lbp - 50) ** 2)
    sc, sh = 1 + 0.045 * cbp, 1 + 0.015 * cbp * t
    rt = -math.sin(math.radians(2 * dth)) * rc
    dl, dc = (L2 - L1) / sl, (c2p - c1p) / sc
    return math.sqrt(dl ** 2 + dc ** 2 + (dHp / sh) ** 2 + rt * dc * (dHp / sh))


def separacao(cores, tipos):
    """A menor distância entre duas das cores, no pior dos tipos e severidades."""
    rgbs = [_rgb_css(c) for c in cores]
    if len(rgbs) < 2 or None in rgbs:
        return 0.0
    pior = 999.0
    for tipo in tipos:
        for sev in ((0,) if tipo == "normal" else range(1, 11)):
            labs = [_lab(_simula(c, tipo, sev)) for c in rgbs]
            for i in range(len(labs)):
                for j in range(i + 1, len(labs)):
                    pior = min(pior, _de2000(labs[i], labs[j]))
    return pior


def contraste(txt_css, fundo):
    """razão de contraste da WCAG entre a cor CSS e um fundo [r, g, b] em 0..1"""
    c = _rgb_css(txt_css)
    if not c:
        return 0.0
    lum = lambda x: 0.2126 * _lin(x[0]) + 0.7152 * _lin(x[1]) + 0.0722 * _lin(x[2])
    a, b = sorted((lum(c), lum(fundo)), reverse=True)
    return (a + 0.05) / (b + 0.05)


# o papel da calculadora: --loja-papel com o véu branco de 22% do .calc-card
PAPEL_CALC = [0.78 * c + 0.22 for c in (0xe5 / 255, 0xd3 / 255, 0xad / 255)]


DALT_LE = r"""(() => {
  const cor = {};
  for (const c of document.querySelectorAll('.card[data-slug]')) {
    const it = CATALOG.items.find(i => i.slug === c.dataset.slug);
    const k = it && it.itemClass && it.itemClass.core;
    const sup = c.querySelector('.card-surface');
    if (sup && ['AD', 'AP', 'Vitalidade'].includes(k) && !cor[k]) cor[k] = getComputedStyle(sup, '::before').backgroundColor;
  }
  const r = document.querySelector('input[name="ac-daltonismo"]:checked');
  const pinta = r ? [...r.parentElement.querySelectorAll('.pinta b')].map(b => getComputedStyle(b).backgroundColor) : [];
  const t = document.createElement('div'); t.className = 'bd-ordem';
  t.innerHTML = '<i class="lQ">Q</i><i class="lW">W</i><i class="lE">E</i><i class="lR">R</i>';
  document.body.appendChild(t);
  const qwer = [...t.children].map(i => getComputedStyle(i).color); t.remove();
  const calc = document.querySelector('.calc-card.phys');
  const magia = document.querySelector('.calc-card.magic');
  const todos = document.querySelector('.class-tab[data-classe=""]');
  // F13-T50b: as leituras alternativas da build (.lc) e o veredito da
  // calculadora, montados de propósito para ler o CSS que vale na tela
  const prova = document.createElement('div');
  prova.innerHTML = ['ad', 'ap', 'vit'].map(k => `<div class="lc ${k}"><img class="item-art" alt=""></div>`).join('')
    + '<section class="calc-card phys"><div class="calc-verdict ok"></div><div class="calc-verdict warn-res"></div><div class="calc-verdict warn-hp"></div></section>';
  document.body.appendChild(prova);
  const lc = [...prova.querySelectorAll('.lc .item-art')].map(e => getComputedStyle(e).borderTopColor);
  const veredito = [...prova.querySelectorAll('.calc-verdict')].map(e => getComputedStyle(e).borderTopColor);
  prova.remove();
  const h3 = (c) => c ? getComputedStyle(c.querySelector('.calc-card-head h3')).color : null;
  const abs = calc ? calc.querySelector('.calc-absorb .absorbed b') : null;
  return { nuc: [cor.AD, cor.AP, cor.Vitalidade], pinta, qwer, lc, veredito,
           texto_calc: [h3(calc), h3(magia), abs ? getComputedStyle(abs).color : null],
           magia: magia ? getComputedStyle(magia).getPropertyValue('--accent').trim() : null,
           ap: getComputedStyle(document.body).getPropertyValue('--loja-ap').trim(),
           brasa: getComputedStyle(document.body).getPropertyValue('--forja-brasa').trim(),
           todos: todos ? getComputedStyle(todos).backgroundImage + ' | ' + getComputedStyle(todos).color : null,
           marcado: r ? r.value : null,
           classes: [...document.body.classList].filter(c => c.startsWith('dalt-')),
           calc: calc ? getComputedStyle(calc).getPropertyValue('--accent').trim() : null,
           ad: getComputedStyle(document.body).getPropertyValue('--loja-ad').trim() };
})()"""


def checar_daltonismo(s, p):
    """F13-T50: um modo por tipo, e cada um medido na tela — a faixa de núcleo dos
    cards de verdade, não o CSS."""
    tipos = ("protan", "deutan", "tritan")
    s.js("switchTab('catalog')")
    time.sleep(0.5)
    s.clicar("#acess-btn")
    m = {}
    for modo in ("geral",) + tipos:
        s.clicar("#ac-dalt-" + modo, 0.35)
        m[modo] = s.js(DALT_LE)
    ok = all(m[k]["classes"] == ["dalt-" + k] and m[k]["marcado"] == k and None not in m[k]["nuc"] for k in m)
    p.conta("acessibilidade", "cada tipo de daltonismo liga a sua paleta", ok,
            "; ".join("%s: %s" % (k, ",".join(m[k]["classes"])) for k in m))
    p.conta("acessibilidade", "a amostra do menu é a cor que vai à tela",
            all(m[k]["pinta"] == m[k]["nuc"] for k in m),
            "; ".join(k for k in m if m[k]["pinta"] != m[k]["nuc"]) or "")
    g = separacao(m["geral"]["nuc"], tipos)
    gn = separacao(m["geral"]["nuc"], ("normal",))
    p.conta("acessibilidade", "a Geral separa o núcleo nas três formas", g >= 33 and gn >= 30,
            "pior %.1f (normal %.1f)" % (g, gn))
    det, bom = [], True
    for t in tipos:
        prop, dela = separacao(m[t]["nuc"], (t,)), separacao(m["geral"]["nuc"], (t,))
        nor = separacao(m[t]["nuc"], ("normal",))
        det.append("%s %.1f×%.1f" % (t, prop, dela))
        bom = bom and prop >= 40 and prop >= dela + 4 and nor >= 30
    p.conta("acessibilidade", "cada tipo separa mais que a Geral nele", bom, "; ".join(det))
    gq = separacao(m["geral"]["qwer"], tipos)
    det, bom = ["geral %.1f" % gq], gq >= 18
    for t in tipos:
        prop, dela = separacao(m[t]["qwer"], (t,)), separacao(m["geral"]["qwer"], (t,))
        det.append("%s %.1f×%.1f" % (t, prop, dela))
        bom = bom and prop >= 25 and prop >= dela + 4
    p.conta("acessibilidade", "a ordem das habilidades também separa", bom, "; ".join(det))
    # F13-T50b: a visão normal também — o Q W E R da Tritanopia ficava em 23,7
    qn = {k: separacao(m[k]["qwer"], ("normal",)) for k in m}
    p.conta("acessibilidade", "a ordem das habilidades separa na visão normal", all(v >= 24 for v in qn.values()),
            "; ".join("%s %.1f" % (k, v) for k, v in qn.items()))
    rgb = lambda c: (_rgb_css(c) or [None])[:3]
    vered_ok = all([rgb(x) for x in m[k]["veredito"]] == [rgb(m[k]["nuc"][2]), rgb(m[k]["nuc"][0]), rgb(m[k]["nuc"][1])] for k in m)
    p.conta("acessibilidade", "a calculadora segue a cor do núcleo",
            all(m[k]["calc"] and m[k]["calc"] == m[k]["ad"] and m[k]["magia"] and m[k]["magia"] == m[k]["ap"] for k in m) and vered_ok,
            "; ".join("%s %s/%s %s/%s" % (k, m[k]["calc"], m[k]["ad"], m[k]["magia"], m[k]["ap"]) for k in m
                      if m[k]["calc"] != m[k]["ad"] or m[k]["magia"] != m[k]["ap"]) + ("" if vered_ok else " · bordas do veredito"))
    cr = {k: min(contraste(c, PAPEL_CALC) for c in m[k]["texto_calc"]) for k in m}
    p.conta("acessibilidade", "o texto da calculadora se lê no papel", all(v >= 4.5 for v in cr.values()),
            "; ".join("%s %.1f:1" % (k, v) for k, v in cr.items()))
    p.conta("acessibilidade", "as leituras alternativas seguem o núcleo",
            all(m[k]["lc"] == m[k]["nuc"] for k in m), "; ".join(k for k in m if m[k]["lc"] != m[k]["nuc"]))
    s.clicar("#ac-dalt-off", 0.35)
    d = s.js(DALT_LE)
    padrao = [_rgb_css(c) for c in d["nuc"]]
    esperado = [[0xc8 / 255, 0x64 / 255, 0x1e / 255], [0x7b / 255, 0x4f / 255, 0xb5 / 255], [0x4d / 255, 0x8b / 255, 0x3a / 255]]
    p.conta("acessibilidade", "desligado volta às cores do jogo",
            d["classes"] == [] and not s.js("document.body.classList.contains('ac-daltonismo')") and padrao == esperado,
            ",".join(d["nuc"] or []))
    p.conta("acessibilidade", "a aba Todos fica no latão em todo modo",
            d["todos"] is not None and all(m[k]["todos"] == d["todos"] for k in m),
            "; ".join(k for k in m if m[k]["todos"] != d["todos"]))
    p.conta("acessibilidade", "a brasa da forja não muda com o modo",
            bool(d["brasa"]) and all(m[k]["brasa"] == d["brasa"] for k in m),
            "; ".join("%s %s" % (k, m[k]["brasa"]) for k in m if m[k]["brasa"] != d["brasa"]))
    p.conta("acessibilidade", "o Desligado das leituras alternativas é o do jogo", d["lc"] == d["nuc"], ",".join(d["lc"] or []))
    s.clicar("#acess-btn")
    # F13-T50b: o menu pelo teclado — o Esc devolve o foco ao botão, o Tab para
    # fora fecha, e a explicação do tipo é anunciada
    s.clicar("#acess-btn")
    s.clicar("#ac-dalt-geral", 0.3)
    tecla = lambda k, c, v: [s.envia("Input.dispatchKeyEvent", {"type": t, "key": k, "code": c, "windowsVirtualKeyCode": v, "nativeVirtualKeyCode": v}) for t in ("keyDown", "keyUp")]
    tecla("Escape", "Escape", 27)
    time.sleep(0.3)
    esc = s.js("({ fechou: document.getElementById('acess-menu').hidden, foco: document.activeElement && document.activeElement.id })")
    s.clicar("#acess-btn")
    s.js("document.getElementById('ac-dalt-geral').focus(); 'ok'")
    tecla("Tab", "Tab", 9)
    time.sleep(0.3)
    tab = s.js("({ fechou: document.getElementById('acess-menu').hidden, foco: document.activeElement && (document.activeElement.id || document.activeElement.tagName) })")
    viva = s.js("document.getElementById('dalt-diz').getAttribute('aria-live')")
    p.conta("acessibilidade", "o menu de acessibilidade se usa pelo teclado",
            esc["fechou"] and esc["foco"] == "acess-btn" and tab["fechou"] and viva == "polite",
            "Esc: %s; Tab: %s; aria-live=%s" % (esc, tab, viva))
    if not s.js("document.getElementById('acess-menu').hidden"):
        s.clicar("#acess-btn")
    # F13-T50b: cada tipo sobrevive ao recarregar (antes só a Geral era provada)
    volta = {}
    for t in tipos:
        s.clicar("#acess-btn")
        s.clicar("#ac-dalt-" + t, 0.3)
        s.clicar("#acess-btn")
        s.abrir()
        time.sleep(1.0)
        s.entrar()
        volta[t] = s.js("document.body.classList.contains('dalt-%s') && document.getElementById('ac-dalt-%s').checked" % (t, t))
        s.js("switchTab('catalog')")
        time.sleep(0.4)
    p.conta("acessibilidade", "cada tipo sobrevive ao recarregar", all(volta.values()),
            "; ".join("%s %s" % (k, "ok" if v else "perdeu") for k, v in volta.items()))
    # o "ligado" de antes (true) não pode virar desligado nem tipo nenhum
    s.js("localStorage.setItem('acessibilidade', JSON.stringify({ daltonismo: true }))")
    s.abrir()
    time.sleep(1.0)
    s.entrar()
    p.conta("acessibilidade", "o daltonismo ligado de antes vira a Geral",
            s.js("""document.body.classList.contains('ac-daltonismo') && document.body.classList.contains('dalt-geral')
                    && document.getElementById('ac-dalt-geral').checked"""))
    s.js("localStorage.removeItem('acessibilidade')")
    s.abrir()
    time.sleep(1.0)
    s.entrar()

def checar_bigorna(s, p):
    """F13-T51 (Leo, 18/10/2026: "sempre estou em uma build ativa… precisa ter
    alguma forma de demonstrar que tem uma build ativa ou se é para sair da
    edição"): a plaqueta sob a aba Builds e a faixa da loja dizem, de qualquer
    tela, qual build está aberta e se há alteração por salvar (o nº 39)."""
    print("\n%sBIGORNA%s" % (AMARELO, FIM))
    s.nova_build()
    longo = "Jinx ADC — crítico com Mata-Cráquens, Gume do Infinito e Furacão"   # 63 letras: o pior nome
    s.js("""(() => { if (build.editing) document.getElementById('edit-switch').click();
      build.name = %s; gravarBuild(); renderBuildAll(); return 'ok'; })()""" % json.dumps(longo))
    time.sleep(0.4)
    le = r"""(() => { const p = document.getElementById('bigorna'), n = document.getElementById('bg-nome');
      if (!p) return null; const r = p.getBoundingClientRect(), b = document.getElementById('search-input');
      const aba = document.querySelector('.tab-btn[data-tab="build"]').getBoundingClientRect(), pa = document.getElementById('bg-parar');
      return { visivel: !p.hidden && r.width > 0, estado: p.dataset.estado, nome: n.textContent, titulo: n.title,
               rot: document.getElementById('bg-rot').textContent, info: document.getElementById('bg-estado').textContent,
               parar: !pa.hidden && pa.getBoundingClientRect().width > 0, baixo: Math.round(r.bottom), direita: Math.round(r.right),
               estouro: p.scrollWidth - p.clientWidth, parar_dentro: pa.hidden || pa.getBoundingClientRect().right <= r.right + 0.5,
               desvio: Math.round(Math.abs(r.left - aba.left)),
               busca: b && b.getBoundingClientRect().height ? Math.round(b.getBoundingClientRect().top) : null,
               cab: Math.round(document.querySelector('header.top').getBoundingClientRect().height) }; })()"""
    telas = [("catalog", None), ("build", "lista"), ("build", "forja"), ("runas", None), ("calc", None)]
    ruins = []
    for aba, tela in telas:
        s.js("switchTab('%s'); %s window.scrollTo(0, 0); 'ok'" % (aba, ("showBuildScreen('%s');" % tela) if tela else ""))
        time.sleep(0.4)
        r = s.js(le)
        if not r or not r["visivel"] or r["nome"] != longo or longo not in (r["titulo"] or ""):
            ruins.append(aba + (":" + tela if tela else ""))
    p.conta("bigorna", "a plaqueta nomeia a build em todas as telas", not ruins, "sem a plaqueta: " + ", ".join(ruins) if ruins else "5 telas")
    # F13-T86: a aba ativa é ~2 px mais larga; trocar de aba com clique de verdade (sem chamar o
    # posicionarBigorna) não pode deixar a plaqueta fora do lugar — 4 px depois da aba Builds
    passos = {}
    for aba in ("build", "runas", "calc", "catalog"):
        s.clicar('.tab-btn[data-tab="%s"]' % aba, 0.6)
        passos[aba] = s.js("(() => { const p = document.getElementById('bigorna'); return p.hidden ? null : p.offsetLeft - document.querySelector('.tab-btn[data-tab=build]').offsetLeft; })()")
    p.conta("bigorna", "trocar de aba não tira a plaqueta de baixo da aba Builds", all(v == 4 for v in passos.values()), "%s" % passos)
    # o nº 39: com o Editar ligado e um item por salvar, a loja, as Runas e a
    # Calculadora dizem "não salva" — na tela, não só no DOM
    s.js("switchTab('build'); showBuildScreen('forja'); window.scrollTo(0, 0); 'ok'")
    time.sleep(0.4)
    s.clicar("#edit-switch", 0.6)
    s.js("build.cats[1].items.push({ itemId: 'long-sword', note: '' }); saveBuild(); renderBuildAll(); 'ok'")
    time.sleep(0.3)
    fora = {}
    for aba in ("catalog", "runas", "calc"):
        s.js("switchTab('%s'); window.scrollTo(0, 0); 'ok'" % aba)
        time.sleep(0.4)
        r = s.js(le)
        fora[aba] = bool(r and r["visivel"] and r["estado"] == "sujo" and "não salva" in r["info"] and r["parar"])
    s.js("switchTab('catalog'); window.scrollTo(0, 0); 'ok'")
    time.sleep(0.3)
    faixa = s.js("""(() => { const f = document.getElementById('cff-sujo'), x = document.getElementById('catalog-forja-faixa');
      return !!f && !f.hidden && f.getBoundingClientRect().width > 0 && x.getBoundingClientRect().width > 0; })()""")
    p.conta("bigorna", "fora da forja a plaqueta diz editando e não salva", all(fora.values()) and faixa,
            "; ".join("%s %s" % (k, "ok" if v else "não diz") for k, v in fora.items()) + "; faixa %s" % faixa)
    # o pior estado (nome longo, editando, não salva, com caixa na faixa) em cada resolução
    s.js("build.selectedCatId = build.cats[2].id; renderBuild(); 'ok'")
    medidas, ruins = [], []
    for w, h in RESOLUCOES + [(1440, 900)]:
        s.tela(w, h)
        s.js("switchTab('catalog'); window.scrollTo(0, 0); posicionarBigorna(); 'ok'")
        time.sleep(0.4)
        com = s.js(le)
        sem = s.js("(() => { const p = document.getElementById('bigorna'); p.hidden = true; const a = Math.round(document.querySelector('header.top').getBoundingClientRect().height); p.hidden = false; return a; })()") if com else None
        fx = s.js("(() => { const f = document.getElementById('catalog-forja-faixa'), r = f.getBoundingClientRect(); return { estouro: f.scrollWidth - f.clientWidth, alto: Math.round(r.height) }; })()")
        ok = (com and com["visivel"] and com["estado"] == "sujo" and com["cab"] == sem and com["busca"] is not None
              and com["baixo"] <= com["busca"] and com["direita"] <= w and com["estouro"] <= 1 and com["parar_dentro"]
              and com["desvio"] <= 8 and fx["estouro"] <= 1 and fx["alto"] <= 48)
        medidas.append("%d: cab %s/%s, faixa %spx" % (w, com and com["cab"], sem, fx["alto"]))
        if not ok:
            ruins.append("%dx%d (%s; faixa %s)" % (w, h, com, fx))
    s.js("build.selectedCatId = null; renderBuild(); 'ok'")
    s.tela_normal()
    p.conta("bigorna", "no pior estado, nada estoura nem mexe no cabeçalho", not ruins, "; ".join(ruins) or "; ".join(medidas))
    # o Ctrl+S de qualquer tela
    s.js("switchTab('catalog'); 'ok'")
    time.sleep(0.3)
    for tipo in ("keyDown", "keyUp"):
        s.envia("Input.dispatchKeyEvent", {"type": tipo, "key": "s", "code": "KeyS", "modifiers": 2, "windowsVirtualKeyCode": 83})
    time.sleep(0.5)
    ctrl = s.js("""(() => { const d = JSON.parse(localStorage.getItem('lol-builds-v3') || '{}');
      const b = (d.builds || []).find(x => x.id === build.id);
      return { sujo: rascunho.sujo, noDisco: !!b && b.cats[1].items.some(e => e.itemId === 'long-sword'), estado: document.getElementById('bigorna').dataset.estado,
               faixa_sujo: !document.getElementById('cff-sujo').hidden }; })()""")
    p.conta("bigorna", "o Ctrl+S salva da loja", not ctrl["sujo"] and ctrl["noDisco"] and ctrl["estado"] == "editando" and not ctrl["faixa_sujo"], "%s" % ctrl)
    # "parar de editar" pela plaqueta: com rascunho, pergunta; sem rascunho, desliga
    s.js("build.cats[1].items.push({ itemId: 'dagger', note: '' }); saveBuild(); 'ok'")
    time.sleep(0.3)
    s.clicar("#bg-parar", 0.5)
    perguntou = s.js("!document.getElementById('save-dialog').hidden")
    if perguntou:
        s.clicar('#save-dialog [data-sd="descartar"]', 0.6)
    depois = s.js("({ editando: build.editing, sujo: rascunho.sujo, adaga: build.cats[1].items.some(e => e.itemId === 'dagger'), parar: !document.getElementById('bg-parar').hidden, estado: document.getElementById('bigorna').dataset.estado, foco: document.activeElement && document.activeElement.id })")
    s.js("switchTab('build'); showBuildScreen('forja'); 'ok'")
    time.sleep(0.3)
    s.clicar("#edit-switch", 0.6)
    s.js("switchTab('runas'); 'ok'")
    time.sleep(0.3)
    s.clicar("#bg-parar", 0.5)
    limpo = s.js("({ editando: build.editing, dialogo: !document.getElementById('save-dialog').hidden, foco: document.activeElement && document.activeElement.id })")
    p.conta("bigorna", "parar de editar pela plaqueta",
            perguntou and not depois["editando"] and not depois["sujo"] and not depois["adaga"] and not depois["parar"]
            and depois["estado"] == "aberta" and not limpo["editando"] and not limpo["dialogo"] and limpo["foco"] == "bg-nome",
            "perguntou %s; depois de descartar %s; sem rascunho %s" % (perguntou, depois, limpo))
    # o nome leva à forja — saindo da lista, para provar que é ele quem abre a forja
    s.js("switchTab('build'); showBuildScreen('lista'); switchTab('calc'); 'ok'")
    time.sleep(0.4)
    s.clicar("#bg-nome", 0.6)
    forja = s.js("({ aba: !document.getElementById('view-build').classList.contains('hidden'), forja: !document.getElementById('build-editor').hidden, tela: buildScreen })")
    p.conta("bigorna", "o nome na plaqueta leva à forja", forja["aba"] and forja["forja"] and forja["tela"] == "forja", "%s" % forja)
    # renomear pelo campo de verdade: a plaqueta e a faixa mudam sem redesenhar a loja
    # (F13-T59: o nome só muda com o Editar — o "parar de editar" acima o desligou)
    s.js("window.scrollTo(0, 0); 'ok'")
    s.clicar("#edit-switch", 0.6)
    s.clicar("#build-name-input", 0.3)
    s.js("document.getElementById('build-name-input').select(); 'ok'")
    s.envia("Input.insertText", {"text": "Ezreal meio"})
    time.sleep(0.2)
    s.clicar('.tab-btn[data-tab="catalog"]', 0.6)
    renome = s.js("({ nome: build.name, plaqueta: document.getElementById('bg-nome').textContent, faixa: document.getElementById('cff-build').textContent })")
    s.js("salvarAgora(); ligarEdicao(false); 'ok'")   # e volta ao estado de antes: gravado, sem o Editar
    time.sleep(0.3)
    p.conta("bigorna", "renomear muda a plaqueta e a faixa na hora",
            renome["nome"] == "Ezreal meio" and renome["plaqueta"] == "Ezreal meio" and renome["faixa"] == "Ezreal meio", "%s" % renome)
    # a faixa da loja: sem caixa diz a build; com caixa, a caixa; e fica no topo ao rolar
    s.js("switchTab('catalog'); build.selectedCatId = null; renderBuild(); window.scrollTo(0, 0); 'ok'")
    time.sleep(0.4)
    sem_caixa = s.js("""(() => { const f = document.getElementById('catalog-forja-faixa');
      return { visivel: !f.hidden && f.getBoundingClientRect().width > 0, build: document.getElementById('cff-build').textContent, caixa: !document.getElementById('cff-caixa').hidden,
               dica: document.getElementById('cff-dica').textContent }; })()""")
    s.js("window.scrollTo(0, 1600); 'ok'")
    time.sleep(0.5)
    presa = s.js("(() => { const r = document.getElementById('catalog-forja-faixa').getBoundingClientRect(); return [Math.round(r.top), Math.round(r.bottom)]; })()")
    s.js("window.scrollTo(0, 0); build.selectedCatId = build.cats[2].id; renderBuild(); 'ok'")
    time.sleep(0.3)
    com_caixa = s.js("({ caixa: !document.getElementById('cff-caixa').hidden, nome: document.getElementById('cff-nome').textContent, soltar: !document.getElementById('cff-soltar').hidden, esperado: build.cats[2].name })")
    s.js("build.selectedCatId = null; renderBuild(); 'ok'")
    p.conta("bigorna", "a faixa da loja diz a build e fica no topo ao rolar",
            sem_caixa["visivel"] and sem_caixa["build"] == "Ezreal meio" and not sem_caixa["caixa"] and "ligue o Editar" in sem_caixa["dica"]   # F13-T76: sem o Editar, a dica diz para ligá-lo
            and 0 <= presa[0] <= 20 and com_caixa["caixa"] and com_caixa["nome"] == com_caixa["esperado"] and com_caixa["soltar"],
            "sem caixa %s; rolada a 1600 a faixa fica em %s; com caixa %s" % (sem_caixa, presa, com_caixa))
    # a gravação recusada chega à plaqueta na hora (o coração da lista, o lote…)
    erro = s.js("""(() => { const orig = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'lol-builds-v3') throw new DOMException('cheio', 'QuotaExceededError'); return orig.call(this, k, v); };
      switchTab('catalog'); gravarBiblioteca();
      const r = { estado: document.getElementById('bigorna').dataset.estado, info: document.getElementById('bg-estado').textContent };
      Storage.prototype.setItem = orig; if (!document.getElementById('pub-dialog').hidden) fecharPub();
      gravarBiblioteca(); r.depois = document.getElementById('bigorna').dataset.estado; return r; })()""")
    p.conta("bigorna", "a gravação recusada aparece na plaqueta na hora",
            erro["estado"] == "erro" and "gravação recusada" in erro["info"] and erro["depois"] != "erro", "%s" % erro)
    # vendo uma pública: com o Editar ligado antes, ele não atravessa para ela
    s.js("switchTab('build'); showBuildScreen('forja'); 'ok'")
    time.sleep(0.3)
    if not s.js("build.editing"):
        s.clicar("#edit-switch", 0.6)
    s.js("""(() => { abrirPublicaTemporaria({ pubId: 'qa-bigorna', name: 'Pública do roteiro', cats: [], mode: '', champ: null,
      markers: [], desc: '', runas: null, habilidades: null, layout: null, pubPatch: CATALOG.meta.patch }); return 'ok'; })()""")
    time.sleep(0.6)
    ligar = s.js("(() => { const b = document.getElementById('ml-ligar'); if (b) b.click(); return build.editing; })()")
    s.js("switchTab('catalog'); 'ok'")
    time.sleep(0.3)
    vendo = s.js(le)
    extra = s.js("({ editando: build.editing, faixa: document.getElementById('cff-rot').textContent.trim().startsWith('Vendo') })")
    p.conta("bigorna", "vendo uma pública: só visualização, sem Editar",
            vendo and vendo["estado"] == "vendo" and vendo["rot"] == "Vendo" and "só visualização" in vendo["info"] and not vendo["parar"]
            and not extra["editando"] and not ligar and extra["faixa"],
            "%s; %s; o Ligar Editar ligou: %s" % (vendo, extra, ligar))
    # a visualização some ao recarregar; volta tudo ao normal para os grupos seguintes
    s.abrir()
    time.sleep(1.0)
    s.entrar()

def checar_fechar(s, p):
    """F13-T52 (Leo, 19/10/2026: "só acho que deveria ter uma opção de fechar!!!"):
    o × da plaqueta e da faixa tira a build da bigorna e ela continua na lista;
    sem build, a plaqueta some, o item da loja só abre a ficha (Leo, 19/10/2026),
    e nada grava numa build que não existe."""
    print("\n%sFECHAR A BUILD%s" % (AMARELO, FIM))
    estado = r"""(() => { const v = id => { const e = document.getElementById(id); return !!e && !e.hidden && e.getBoundingClientRect().width > 0; };
      let disco = 'ilegivel'; try { disco = JSON.parse(localStorage.getItem(STORAGE_KEY)).activeId; } catch (e) { }
      const ec = document.getElementById('escolher-caixa');
      return { id: build.id, nome: build.name, estado: document.getElementById('bigorna').dataset.estado,
               plaqueta: v('bigorna'), fechar: v('bg-fechar'),
               ativa: library.activeId, disco, editando: !!build.editing || document.body.classList.contains('editando'),
               lista: !document.getElementById('build-index').hidden, forja: !document.getElementById('build-editor').hidden,
               foco: document.activeElement && (document.activeElement.id || (document.activeElement.dataset.tab ? 'aba:' + document.activeElement.dataset.tab : '')),
               faixa: v('catalog-forja-faixa'), ficha: document.getElementById('overlay').classList.contains('show'),
               dialogo: ec.hidden ? null : ec.querySelector('.md-title').textContent, sujo: rascunho.sujo,
               proprias: buildsProprias().map(b => b.id) }; })()"""
    so = lambda r, *ks: {k: r[k] for k in ks}
    # 1. o × da plaqueta, numa build limpa, de dentro da forja
    s.nova_build()
    s.js("""(() => { if (build.editing) document.getElementById('edit-switch').click();
      build.name = 'Fechar A'; build.cats[1].items.push({ itemId: 'long-sword', note: '' }); gravarBuild(); renderBuildAll(); return 'ok'; })()""")
    time.sleep(0.3)
    a = s.js("build.id")
    s.clicar("#bg-fechar", 0.6)
    r = s.js(estado)
    # (Leo, 19/10/2026: "se a forja está vazia, então não mostra nada": sem
    # build, a plaqueta some, e o foco vai para a aba Builds, de onde ela pendia)
    p.conta("fechar", "o × da plaqueta fecha a build, a plaqueta some e a build continua na lista",
            r["id"] is None and not r["plaqueta"] and not r["fechar"] and r["ativa"] is None and r["disco"] is None
            and a in r["proprias"] and r["lista"] and not r["forja"] and r["foco"] == "aba:build" and not r["editando"],
            "%s" % so(r, "id", "plaqueta", "fechar", "ativa", "disco", "lista", "forja", "foco", "editando"))

    # 2. com rascunho, o × pergunta antes: Voltar fica; Salvar e sair grava e fecha
    s.js("activateBuild(%s); switchTab('build'); showBuildScreen('forja'); 'ok'" % json.dumps(a))
    time.sleep(0.4)
    s.clicar("#edit-switch", 0.6)
    s.js("build.cats[1].items.push({ itemId: 'dagger', note: '' }); saveBuild(); renderBuildAll(); switchTab('catalog'); window.scrollTo(0, 0); 'ok'")
    time.sleep(0.4)
    s.clicar("#bg-fechar", 0.4)
    perguntou = s.js("!document.getElementById('save-dialog').hidden")
    voltou = None
    if perguntou:
        s.clicar('#save-dialog [data-sd="voltar"]', 0.4)
        voltou = s.js(estado)
        s.clicar("#cff-fechar", 0.4)   # a faixa da loja tem o mesmo ×
        if s.js("!document.getElementById('save-dialog').hidden"):
            s.clicar('#save-dialog [data-sd="salvar"]', 0.6)
    r = s.js(estado)
    gravou = s.js("(() => { const b = library.builds.find(x => x.id === %s); return !!b && b.cats[1].items.some(e => e.itemId === 'dagger'); })()" % json.dumps(a))
    p.conta("fechar", "com rascunho o × pergunta antes (Voltar fica; Salvar e sair grava e fecha)",
            bool(perguntou and voltou and voltou["id"] == a and voltou["sujo"] and r["id"] is None and gravou
                 and not r["sujo"] and not r["faixa"] and not r["editando"]),
            "perguntou %s; depois do Voltar %s; no fim %s; gravou %s" % (perguntou, voltou and so(voltou, "id", "sujo"), so(r, "id", "sujo", "faixa", "editando"), gravou))

    # 3. a bigorna fica vazia de verdade: nada da build fechada sobra
    s.js(r"""(() => { activateBuild(%s); build.mode = ALL_MODES[0]; build.masterwork = true; build.desc = 'resto';
      build.champion = { key: '1', id: 'Annie', name: 'Annie' };
      if (typeof RUNAS !== 'undefined' && RUNAS.trilhas) build.runas = normRunas({ primaria: RUNAS.trilhas[0].id });
      build.habilidades = normHabilidades(['Q', 'W', 'E', 'Q']); build.layout = 'trilha';
      gravarBuild(); build.selectedCatId = build.cats[0].id; renderBuildAll();
      const zero = { name: '', cats: [], mode: '', masterwork: false, desc: '', champion: null, markers: normMarkers(null),
        runas: normRunas(null), habilidades: normHabilidades(null), selectedCatId: null, layout: 'tabuleiro', temp: false,
        revisao: null, pubId: null, pubOrigem: null, fav: false };
      window.__qaSobra = () => Object.keys(zero).filter(k => JSON.stringify(build[k]) !== JSON.stringify(zero[k]));
      return 'ok'; })()""" % json.dumps(a))
    time.sleep(0.3)
    antes = s.js("__qaSobra()")
    s.clicar("#bg-fechar", 0.6)
    sobra = s.js("__qaSobra()")
    preparados = ["name", "cats", "mode", "masterwork", "desc", "champion", "runas", "habilidades", "selectedCatId", "layout"]
    vazios_antes = [k for k in preparados if k not in antes]
    p.conta("fechar", "fechada, nada da build sobra na bigorna",
            not sobra and not vazios_antes and s.js("build.id") is None,
            "sobrou: %s; campos que não estavam preenchidos antes: %s" % (sobra, vazios_antes))

    # 4. sem build, o clique no item só abre a ficha (Leo, 19/10/2026: "ele
    #    simplesmente abre as informações dos itens e não pergunta se eu quero
    #    inserir em alguma build") — nada entra em build nenhuma, nada nasce
    s.nova_build()
    s.js("""(() => { if (build.editing) document.getElementById('edit-switch').click();
      build.name = 'Fechar B'; build.cats[0].items.push({ itemId: 'dagger', note: '' }); gravarBuild(); renderBuildAll(); return 'ok'; })()""")
    time.sleep(0.3)
    b = s.js("build.id")
    s.js("switchTab('catalog'); window.scrollTo(0, 0); 'ok'")
    time.sleep(0.3)
    s.clicar("#bg-fechar", 0.6)
    antes = s.js("JSON.stringify(library.builds.map(x => [x.id, x.cats]))")
    resultados = []
    for slug in ("long-sword", "dagger"):   # um que nenhuma das duas tem pela caixa escolhida, e um que a B tem
        s.js("window.scrollTo(0, 0); 'ok'")
        s.clicar('#grid .card[data-slug="%s"] .card-name' % slug, 0.6)
        r = s.js(estado)
        r["nome_ficha"] = s.js("(() => { const m = document.getElementById('modal'); return !!m && m.textContent.includes(byId[%s].namePt); })()" % json.dumps(slug))
        s.js("closeModal(); 'ok'")
        time.sleep(0.3)
        resultados.append((slug, r))
    depois = s.js("JSON.stringify(library.builds.map(x => [x.id, x.cats]))")
    ruins = [(slug, so(r, "ficha", "nome_ficha", "dialogo", "id", "plaqueta")) for slug, r in resultados
             if not (r["ficha"] and r["nome_ficha"] and r["dialogo"] is None and r["id"] is None and not r["plaqueta"])]
    p.conta("fechar", "sem build, o clique no item só abre a ficha",
            not ruins and antes == depois,
            "ruins: %s; a biblioteca mudou: %s" % (ruins, antes != depois) if ruins or antes != depois else "Espada Longa e Adaga: ficha aberta, nenhuma pergunta, nada gravado")

    # 5. fechar uma pública aberta para ver volta para a build de antes — que
    #    não é a primeira da lista — ou para a bigorna vazia, se estava vazia
    publica = """(() => { abrirPublicaTemporaria({ pubId: 'qa-fechar', name: 'Pública do fechar', cats: [], mode: '', champ: null,
      markers: [], desc: '', runas: null, habilidades: null, layout: null, pubPatch: CATALOG.meta.patch }); return build.temp; })()"""
    primeira = s.js("buildsProprias()[0].id")
    s.js("activateBuild(%s); 'ok'" % json.dumps(b))
    time.sleep(0.3)
    vendo1 = s.js(publica)
    time.sleep(0.4)
    s.js("switchTab('catalog'); window.scrollTo(0, 0); 'ok'")
    s.clicar("#bg-fechar", 0.6)
    volta1 = s.js("build.id")
    s.clicar("#bg-fechar", 0.6)   # agora a B: a bigorna fica vazia
    vendo2 = s.js(publica)
    time.sleep(0.4)
    s.js("switchTab('catalog'); window.scrollTo(0, 0); 'ok'")
    s.clicar("#bg-fechar", 0.6)
    r = s.js(estado)
    p.conta("fechar", "fechar uma pública volta para a build de antes (ou para a bigorna vazia)",
            vendo1 and volta1 == b and b != primeira and vendo2 and r["id"] is None and not r["plaqueta"] and r["disco"] is None,
            "com a B: voltou para a B %s (a primeira da lista é outra: %s); com a bigorna vazia: %s" % (volta1 == b, b != primeira, so(r, "id", "plaqueta", "disco")))

    # 6. sem build, nada grava numa build que não existe: Runas só Ler, a
    #    calculadora não puxa, a forja não abre, o "Marcar em" fica parado
    n0 = s.js("library.builds.length")
    s.js("switchTab('runas'); runasEstado.modo = 'montar'; renderRunas(); 'ok'")
    time.sleep(0.4)
    runas = s.js("""(() => { const m = document.querySelector('.runas-modo[data-modo="montar"]');
      return { modo: runasEstado.modo, montar: !!m && m.disabled }; })()""")
    s.js("switchTab('calc'); 'ok'")
    time.sleep(0.4)
    calc = s.js("(() => { const b = document.getElementById('calc-from-build'); return !!b && b.disabled; })()")
    s.js("switchTab('build'); showBuildScreen('forja'); 'ok'")
    time.sleep(0.4)
    r = s.js(estado)
    marcar = s.js("document.getElementById('catalog-cat-select').disabled")
    p.conta("fechar", "sem build: Runas só Ler, calculadora sem puxar, forja fechada",
            runas["modo"] == "ler" and runas["montar"] and calc and r["lista"] and not r["forja"] and marcar
            and s.js("library.builds.length") == n0 and r["id"] is None,
            "runas %s; calculadora parada %s; %s; Marcar em parado %s" % (runas, calc, so(r, "lista", "forja", "id"), marcar))
    s.abrir()
    time.sleep(1.0)
    s.entrar()

def checar_entrada(s, p):
    """F13-T53 (Leo, 19/10/2026: "ao recarregar mantenha a build que já estava
    aberta, e o primeiro acesso fica completamente vazio por conta do tour ter
    uma etapa que vai ensinar"): nada abre nem nasce sozinho."""
    print("\n%sENTRADA SEM BUILD%s" % (AMARELO, FIM))
    le = """(() => { const p = document.getElementById('bigorna'); let disco = null;
      try { disco = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); } catch (e) { disco = 'ilegivel'; }
      const vazio = document.querySelector('#build-index .bi-empty');
      return { id: build.id, nome: build.name, builds: library.builds.map(b => b.name), plaqueta: !p.hidden,
               disco: disco && disco.builds ? { n: disco.builds.length, ativa: disco.activeId } : disco,
               vazio: vazio ? vazio.textContent : null, editando: !!build.editing,
               lista: !document.getElementById('build-index').hidden, forja: !document.getElementById('build-editor').hidden }; })()"""
    # 1. o primeiro acesso: nenhuma build, nada no disco, a lista convida a criar
    s.limpar_memoria(); s.entrar()
    s.js("switchTab('build'); 'ok'")
    time.sleep(0.5)
    r = s.js(le)
    p.conta("entrada", "o primeiro acesso começa sem build nenhuma",
            r["id"] is None and r["builds"] == [] and not r["plaqueta"] and (r["disco"] is None or r["disco"]["n"] == 0)
            and r["lista"] and not r["forja"] and r["vazio"] and "Nenhuma build ainda" in r["vazio"],
            "%s" % r)
    # 2. o F5 volta a build que estava aberta — a segunda da lista, não a primeira
    s.nova_build()
    s.js("build.name = 'Entrada A'; gravarBuild(); 'ok'")
    s.nova_build()
    s.js("build.name = 'Entrada B'; gravarBuild(); 'ok'")
    a, b = s.js("[library.builds[0].id, library.builds[1].id]")
    s.abrir(); time.sleep(0.8); s.entrar()
    r1 = s.js(le)
    # 3. com a bigorna vazia, o F5 continua vazio
    s.js("switchTab('catalog'); window.scrollTo(0, 0); 'ok'")
    time.sleep(0.4)
    s.clicar("#bg-fechar", 0.6)
    s.abrir(); time.sleep(0.8); s.entrar()
    r2 = s.js(le)
    p.conta("entrada", "o F5 mantém a build que estava aberta (e a bigorna vazia, se estava vazia)",
            r1["id"] == b and r1["nome"] == "Entrada B" and r1["plaqueta"] and r2["id"] is None and not r2["plaqueta"]
            and r2["builds"] == ["Entrada A", "Entrada B"],
            "com a B aberta voltou %s; fechada voltou %s (%s)" % (r1["nome"] if r1["id"] else None, r2["id"], r2["builds"]))
    # 4. excluir a build aberta deixa a bigorna vazia — nenhuma outra entra no lugar
    s.js("activateBuild(%s); switchTab('build'); showBuildScreen('forja'); 'ok'" % json.dumps(b))
    time.sleep(0.5)
    s.clicar("#del-build", 0.8)   # o confirm nativo é aceito pelo roteiro
    r = s.js(le)
    p.conta("entrada", "excluir a build aberta deixa a bigorna vazia",
            r["id"] is None and not r["plaqueta"] and r["builds"] == ["Entrada A"] and r["lista"] and not r["forja"]
            and r["disco"] and r["disco"]["ativa"] is None,
            "%s" % {k: r[k] for k in ("id", "plaqueta", "builds", "lista", "forja", "disco")})
    # 5. os links de captura da forja não ligam o Editar sem build
    s.js("localStorage.setItem(STORAGE_KEY, JSON.stringify({ builds: JSON.parse(localStorage.getItem(STORAGE_KEY)).builds, activeId: null })); 'ok'")
    s.abrir("?r=1#build-observacao"); time.sleep(1.0)   # o ?r=1 força a carga (só o # não recarrega)
    r = s.js(le)
    editor = s.js("(() => { const e = document.getElementById('note-editor'); return !!e && e.classList.contains('show'); })()")
    p.conta("entrada", "#build-observacao sem build não liga o Editar",
            r["id"] is None and not r["editando"] and not editor and not r["forja"],
            "%s; editor de observação aberto: %s" % ({k: r[k] for k in ("id", "editando", "forja")}, editor))
    s.abrir(); time.sleep(0.8); s.entrar()

def checar_entrada_loja(s, p):
    """F13-T97: a entrada da loja é o posto de troca na nevasca do Freljord (o conceito B da
    F13-T96). Com perfil limpo ela aparece desenhada, com a placa, a dica e o foco no #entrar;
    o clique de verdade em qualquer lugar abre (portas girando, câmera, um som só) e fecha
    no fim; os IDs só se selecionam; o Enter abre uma vez; com menos movimento, nada de
    câmera; o link direto fecha na hora e mudo; e depois de fechada, nada da entrada roda.
    F13-T99: a região é sorteada a cada visita (o Freljord, Noxus, Shurima) — tudo isso vale
    para as três, cada uma forçada pelo ?entrada=; e o sorteio varia e monta só a sorteada.
    F13-T100: o som da abertura pronto antes do clique e tocando em até 80 ms dele; o clique não baixa
    os outros sons; a loja escondida não anima por baixo; e os quadros da abertura nas três regiões."""
    print("\n%sENTRADA DA LOJA%s" % (AMARELO, FIM))
    # o som que toca de verdade (o elemento de áudio), contado desde o começo de cada página
    sonda = s.envia("Page.addScriptToEvaluateOnNewDocument", {"source": """(() => { window.__tocou = [];
      const o = HTMLMediaElement.prototype.play;
      HTMLMediaElement.prototype.play = function () { window.__tocou.push(String(this.currentSrc || this.src).split('/').pop()); return o.apply(this, arguments); }; })();"""})["identifier"]
    espia = """(() => { window.__sons = []; if (!Som.__orig) { Som.__orig = Som.play; Som.play = (ev, c) => { window.__sons.push(ev); return Som.__orig(ev, c); }; }
      const e = document.getElementById('entrada'); window.__entT = [[performance.now(), e.className]];
      new MutationObserver(() => window.__entT.push([performance.now(), e.className])).observe(e, { attributes: true, attributeFilter: ['class'] });
      // F13-T102: a cada quadro da abertura, a opacidade da entrada e a escala da câmera (o último antes de fechar)
      window.__entQ = []; const q = () => { if (e.classList.contains('fechada')) return;
        if (e.classList.contains('saindo')) { const m = document.getElementById('en-mundo'), sc = m && /scale\\(([\\d.]+)\\)/.exec(m.style.transform);
          window.__entQ.push([performance.now(), +getComputedStyle(e).opacity, sc ? +sc[1] : null]); }
        requestAnimationFrame(q); };
      requestAnimationFrame(q);
      return 1; })()"""
    estado = """(() => { const e = document.getElementById('entrada'), fe = document.querySelector('#entrada .en-folha.en-esq'), m = document.getElementById('en-mundo');
      const t = window.__entT || [], ini = t.find(x => /saindo/.test(x[1])), fim = t.find(x => /fechada/.test(x[1]));
      return { cls: e.className, folha: fe ? getComputedStyle(fe).transform : null, mundo: m ? m.style.transform : null,
               sons: (window.__sons || []).filter(x => x === 'catalog:open'), todos: window.__sons || [], tocou: (window.__tocou || []).filter(f => /open_catalog/.test(f)).length,
               dur: ini && fim ? Math.round(fim[0] - ini[0]) : null, sel: String(getSelection()),
               ult: (window.__entQ || []).slice(-1)[0] || null,
               foco: document.activeElement && document.activeElement.id }; })()"""

    def pagina(caminho=""):
        s.abrir(caminho)
        fim = time.time() + 6
        while time.time() < fim and s.js("typeof decidido !== 'undefined' && !decidido"):
            time.sleep(0.1)
        time.sleep(0.3)

    def espera_fechar(limite=5):
        fim = time.time() + limite
        while time.time() < fim and not s.js("document.getElementById('entrada').classList.contains('fechada')"):
            time.sleep(0.05)

    def clique_em(x, y):
        s.envia("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        for tipo in ("mousePressed", "mouseReleased"):
            s.envia("Input.dispatchMouseEvent", {"type": tipo, "x": x, "y": y, "button": "left", "clickCount": 1})

    # F13-T102: a duração do open_catalog, decodificada do arquivo (o roteiro roda mudo; decodificar não toca)
    s.abrir()
    SOM_ABRE = s.js("""(async () => { const b = await (await fetch('assets/audio/open_catalog.mp3')).arrayBuffer();
      const ctx = new (window.OfflineAudioContext || window.webkitOfflineAudioContext)(1, 44100, 44100);
      const a = await ctx.decodeAudioData(b); return Math.round(a.duration * 1000); })()""")

    def rodada(rg):
        """As checagens da entrada numa região, forçada pelo ?entrada= (F13-T99)."""
        R = NOME_REGIAO[rg]
        arg = "?entrada=" + rg

        def conta(nome, ok, det):
            p.conta("entrada da loja", "%s: %s" % (R, nome), ok, det)

        s.tela(1440, 900)
        # (a) perfil limpo: a fachada da região desenhada, a placa, a dica e o foco no #entrar; e só ela montada
        s.js("localStorage.clear(); sessionStorage.clear(); 'ok'")
        pagina(arg)
        a = s.js("""(() => { const e = document.getElementById('entrada'), b = document.getElementById('entrar'), pl = document.querySelector('.entrada-placa');
          const vis = x => { if (!x) return false; const r = x.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.top < innerHeight && r.bottom > 0; };
          const marca = document.getElementById(%s);
          return { aberta: getComputedStyle(e).display !== 'none' && !/saindo|fechada/.test(e.className),
                   regiao: e.dataset.regiao === %s,
                   fachada: !!marca && marca.innerHTML.length > 400 && document.querySelectorAll('#entrada .en-braseiro svg').length === 2 && vis(document.getElementById('en-mundo')),
                   placa: vis(pl), dica: b && b.tagName === 'BUTTON' && b.textContent.trim() === '(Clique em qualquer local para abrir)'
                     && b.getAttribute('aria-label') === 'Entrar na loja' && vis(b) && b.tabIndex === 0,
                   foco: document.activeElement === b }; })()""" % (json.dumps(MARCA_REGIAO[rg]), json.dumps(rg)))
        conta("com perfil limpo: a fachada da região, a placa, a dica e o foco no #entrar", all(a.values()), "%s" % a)

        # (b) clique de verdade num ponto vazio da cena (o céu): abre, as portas giram, a câmera anda, um som
        s.js(espia)
        antes = s.js(estado)
        clique_em(720, 60)
        time.sleep(0.15)
        logo = s.js(estado)
        time.sleep(0.6)
        meio = s.js(estado)
        espera_fechar()
        depois = s.js(estado)
        conta("o clique em qualquer lugar abre: portas, câmera, um som e fecha no fim",
              "saindo" in logo["cls"] and "fechada" not in logo["cls"] and meio["folha"] != antes["folha"]
              and meio["mundo"] != antes["mundo"] and "fechada" in depois["cls"] and depois["sons"] == ["catalog:open"]
              and depois["tocou"] == 1 and depois["dur"] is not None,
              "logo: %s; portas %s → %s; câmera %s → %s; sons %s (tocou %s); saindo→fechada em %s ms"
              % (logo["cls"], antes["folha"], meio["folha"], antes["mundo"], meio["mundo"], depois["sons"], depois["tocou"], depois["dur"]))
        # F13-T102 (Leo, 02/11/2026: "a duração da animação não é muito sincronizada com o som"): a cena acaba
        # junto com o som — fecha até 300 ms depois do fim do open_catalog (e não antes dele menos 150 ms),
        # com a câmera já no fim do zoom e a entrada já esmaecida no último quadro (nada some de uma vez)
        ult = depois["ult"] or [0, 1, 0]
        conta("a abertura acaba junto com o som: fecha até 120 ms depois do fim dele, com a câmera no fim e a cena já esmaecida",
              depois["dur"] is not None and SOM_ABRE <= depois["dur"] <= SOM_ABRE + 120 and ult[1] <= 0.3 and (ult[2] or 0) >= 6.5,
              "som %d ms · saindo→fechada em %s ms · último quadro: opacidade %.2f, câmera %s" % (SOM_ABRE, depois["dur"], ult[1], ult[2]))

        # F13-T102: a duração vem do arquivo, não de um número escrito — com um som de 1,7 s (fingido no
        # Som.duracao), a abertura fecha aos ~1,75 s, ainda esmaecida no fim
        if rg == "freljord":
            pagina(arg)
            s.js(espia)
            s.js("Som.duracao = () => 1.7; 'ok'")
            clique_em(720, 60)
            espera_fechar()
            lg = s.js(estado)
            ul = lg["ult"] or [0, 1, 0]
            conta("a duração da abertura vem do áudio: com um som de 1,7 s, ela fecha aos ~1,75 s, com a câmera no fim e esmaecida",
                  lg["dur"] is not None and 1700 <= lg["dur"] <= 1820 and ul[1] <= 0.3 and (ul[2] or 0) >= 6.5,
                  "saindo→fechada em %s ms · último quadro: opacidade %.2f, câmera %s" % (lg["dur"], ul[1], ul[2]))

        # (g) depois de fechada: nenhum quadro da entrada pedido em 1 s, e nada no console
        n_erros = len(s.erros)
        s.js("""(() => { window.__raf = 0; const o = window.requestAnimationFrame; window.__rafOrig = o;
          window.requestAnimationFrame = function (f) { window.__raf++; return o.call(window, f); }; return 1; })()""")
        m0 = s.js("document.getElementById('en-mundo').style.transform")
        time.sleep(1.0)
        g = s.js("({ raf: window.__raf, mundo: document.getElementById('en-mundo').style.transform })")
        s.js("window.requestAnimationFrame = window.__rafOrig; 1")
        conta("fechada, nada da entrada roda (nenhum quadro pedido em 1 s) e o console fica limpo",
              g["raf"] == 0 and g["mundo"] == m0 and len(s.erros) == n_erros and not s.erros,
              "%s quadro(s) pedido(s) em 1 s; câmera parada: %s; erros: %s" % (g["raf"], g["mundo"] == m0, "; ".join(s.erros[:2]) or "nenhum"))

        # (c) o clique num ID não abre, e seleciona o ID inteiro
        pagina(arg)
        s.js(espia)
        s.js("getSelection().removeAllRanges(); 1")
        pt = s.caixa(".entrada-contato .ea-id")
        clique_em(pt[0], pt[1])
        time.sleep(0.5)
        c = s.js(estado)
        conta("o clique no ID não abre: seleciona o ID inteiro",
              not re.search(r"saindo|fechada", c["cls"]) and c["sel"] == "Brelgo#RPG" and c["sons"] == [],
              "classe %r; seleção %r; sons %s" % (c["cls"], c["sel"], c["sons"]))

        # (d) o Enter abre uma vez só: no #entrar (vira clique) e com o foco no corpo da página
        s.js("getSelection().removeAllRanges(); document.getElementById('entrar').focus(); 1")
        _tecla(s, "Enter")
        espera_fechar()
        d1 = s.js(estado)
        pagina(arg)
        s.js(espia)
        s.js("document.activeElement && document.activeElement.blur(); 1")
        _tecla(s, "Enter")
        espera_fechar()
        d2 = s.js(estado)
        conta("o Enter abre uma vez só (no #entrar e com o foco na página)",
              all("fechada" in d["cls"] and d["sons"] == ["catalog:open"] and d["tocou"] == 1 for d in (d1, d2)),
              "no #entrar: sons da entrada %s (todos %s), tocou %s, %s; na página: sons da entrada %s (todos %s), tocou %s, %s"
              % (d1["sons"], d1["todos"], d1["tocou"], d1["cls"], d2["sons"], d2["todos"], d2["tocou"], d2["cls"]))

        # (e) com menos movimento (do sistema): a câmera não anda e fecha rápido
        s.envia("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
        try:
            pagina(arg)
            s.js(espia)
            antes = s.js(estado)
            clique_em(720, 60)
            vistos = []
            for _ in range(5):
                time.sleep(0.12)
                vistos.append(s.js("document.getElementById('en-mundo').style.transform"))
            espera_fechar()
            e = s.js(estado)
        finally:
            s.envia("Emulation.setEmulatedMedia", {"features": []})
        conta("com menos movimento a câmera não anda e a entrada fecha logo",
              all(v == antes["mundo"] for v in vistos) and "fechada" in e["cls"] and e["dur"] is not None and e["dur"] <= 950
              and e["sons"] == ["catalog:open"],
              "câmera %s → %s; saindo→fechada em %s ms; sons %s" % (antes["mundo"], sorted(set(vistos)), e["dur"], e["sons"]))

        # (f) o link que entra direto fecha na hora, sem som e sem montar a cena (nem a forçada)
        pagina(arg + "&r=97#calc")
        f = s.js("""(() => { const e = document.getElementById('entrada');
          return { cls: e.className, display: getComputedStyle(e).display, montada: e.querySelectorAll('.en-palco, style').length,
                   tocou: (window.__tocou || []).filter(f => /open_catalog/.test(f)).length }; })()""")
        conta("o link com # (#calc) entra direto: fechada na hora, sem som e sem montar a cena",
              "fechada" in f["cls"] and "saindo" not in f["cls"] and f["display"] == "none" and f["tocou"] == 0 and f["montada"] == 0,
              "%s" % f)

        # F13-T97, a revisão do cético: cada conserto com a sua checagem
        # (i) o 2º clique durante a abertura, sobre um card escondido da loja, não abre a ficha nem toca a loja
        pagina(arg)
        s.js(espia)
        alvo = s.js("""(() => { for (let y = 320; y < innerHeight - 60; y += 40) for (let x = 200; x < innerWidth - 200; x += 60) {
            const el = document.elementsFromPoint(x, y).find(e => !e.closest('#entrada'));
            if (el && el.closest('.card[data-slug]')) return [x, y]; } return null; })()""")
        clique_em(*alvo)
        time.sleep(0.7)
        clique_em(*alvo)
        espera_fechar()
        time.sleep(0.3)
        i = s.js("({ ficha: document.getElementById('overlay').classList.contains('show'), todos: window.__sons || [] })")
        s.js("(() => { const o = document.getElementById('overlay'); if (o.classList.contains('show')) closeModal && closeModal(); return 1; })()")
        conta("o 2º clique durante a abertura, sobre a loja escondida, não atravessa: nem ficha aberta, nem som da loja",
              alvo is not None and not i["ficha"] and not any(x in i["todos"] for x in ("catalog:click", "catalog:pergaminho")),
              "ponto %s; ficha aberta %s; sons %s" % (alvo, i["ficha"], i["todos"]))

        # (j) o "Menos movimento" da loja (não o do sistema): as portas esmaecem e a entrada some aos poucos
        s.js("localStorage.setItem('acessibilidade', JSON.stringify({ movimento: true })); 1")
        try:
            pagina(arg)
            s.js(espia)
            clique_em(720, 60)
            ops = []
            for _ in range(6):
                time.sleep(0.12)
                ops.append(s.js("""(() => { const f = document.querySelector('#entrada .en-folha.en-esq'), e = document.getElementById('entrada');
                  return [+getComputedStyle(f).opacity, +getComputedStyle(e).opacity]; })()"""))
            espera_fechar()
            j = s.js(estado)
        finally:
            s.js("localStorage.removeItem('acessibilidade'); 1")
        conta("com o \"Menos movimento\" da loja, as portas esmaecem e a entrada some aos poucos (não de golpe)",
              min(o[0] for o in ops) < 0.5 and any(0.05 < o[1] < 0.95 for o in ops) and "fechada" in j["cls"] and j["dur"] is not None and j["dur"] <= 950,
              "opacidade [porta, entrada] a cada 120 ms: %s; saindo→fechada em %s ms" % ([[round(a, 2), round(b, 2)] for a, b in ops], j["dur"]))

        # (k) arrastar para selecionar o ID (apertar nele e soltar fora dele) não abre a loja
        pagina(arg)
        s.js(espia)
        s.js("getSelection().removeAllRanges(); 1")
        # o gesto de quem seleciona: aperta perto do fim do ID e solta logo depois dele, na mesma linha
        # (o clique vai para o ancestral comum, que não é o ID). A placa balança o tempo todo: o balanço fica
        # parado durante o gesto, senão o ponto medido anda e o soltar às vezes ainda cai no ID
        s.js("(() => { const g = document.querySelector('#entrada .en-placa-grupo'); if (g) g.getAnimations().forEach(a => a.pause()); return 1; })()")
        fimx, fimy = s.js("(() => { const r = document.querySelector('.entrada-contato .ea-id').getBoundingClientRect(); return [Math.round(r.right), Math.round((r.top + r.bottom) / 2)]; })()")
        s.envia("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": fimx - 4, "y": fimy})
        s.envia("Input.dispatchMouseEvent", {"type": "mousePressed", "x": fimx - 4, "y": fimy, "button": "left", "clickCount": 1})
        # (só "buttons": com "button" no mover, o Chrome começa a arrastar o texto selecionado e não há clique)
        s.envia("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": fimx + 25, "y": fimy + 2, "buttons": 1})
        s.envia("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": fimx + 25, "y": fimy + 2, "button": "left", "clickCount": 1})
        time.sleep(0.5)
        k = s.js(estado)
        conta("arrastar para selecionar o ID (apertar nele e soltar fora) não abre a loja",
              not re.search(r"saindo|fechada", k["cls"]) and k["sons"] == [],
              "classe %r; seleção %r; sons %s" % (k["cls"], k["sel"], k["sons"]))

        # (l) com a entrada de pé, a roda do mouse não rola a loja escondida; ao entrar, a rolagem volta
        s.js("window.scrollTo(0, 0); 1")
        for _ in range(4):
            s.envia("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": 720, "y": 450, "deltaX": 0, "deltaY": 600})
            time.sleep(0.1)
        l1 = s.js("({ y: scrollY, trava: document.documentElement.classList.contains('com-entrada'), over: getComputedStyle(document.documentElement).overflowY })")

        # (m) o Tab não sai da entrada (o aria-modal): o foco fica no #entrar
        s.js("document.getElementById('entrar').focus(); 1")
        for _ in range(3):
            _tecla(s, "Tab")
        m = s.js("({ foco: document.activeElement && document.activeElement.id, hash: location.hash, cls: document.getElementById('entrada').className })")
        clique_em(720, 60)
        espera_fechar()
        l2 = s.js("({ y: scrollY, trava: document.documentElement.classList.contains('com-entrada'), over: getComputedStyle(document.documentElement).overflowY })")
        conta("com a entrada de pé, a roda do mouse não rola a loja escondida; ao entrar, a loja abre no topo e rola de novo",
              l1["y"] == 0 and l1["trava"] and l1["over"] == "hidden" and l2["y"] == 0 and not l2["trava"] and l2["over"] != "hidden",
              "de pé %s; depois de entrar %s" % (l1, l2))
        conta("o Tab não sai da entrada: o foco fica no #entrar (nada por baixo é acionado)",
              m["foco"] == "entrar" and not re.search(r"saindo|fechada", m["cls"]),
              "%s" % m)

        # (o) parada na tela, a entrada não ocupa a thread principal (o pulso da dica)
        pagina(arg)
        time.sleep(4.5)                     # a chegada da dica e o pulso já começaram
        s.envia("Performance.enable")
        met = lambda: {x["name"]: x["value"] for x in s.envia("Performance.getMetrics")["metrics"]}
        m1 = met(); time.sleep(2.0); m2 = met()
        s.envia("Performance.disable")
        tarefa = (m2["TaskDuration"] - m1["TaskDuration"]) / max(0.1, m2["Timestamp"] - m1["Timestamp"])
        conta("parada na tela, a entrada quase não gasta a thread principal (menos de 15%)",
              tarefa < 0.15, "%.0f ms de tarefa por segundo" % (tarefa * 1000))

        # (q) o peso: a entrada não baixa imagem grande — o que ela usa (fundos, máscaras e <image>) tem menos
        # de 300 KB cada (no Freljord, a janela usa o jpg pequeno do card); a textura de 2,8 MB nunca
        q = s.js(r"""(() => { const usa = new Set(), base = location.href;
          document.querySelectorAll('#entrada, #entrada *').forEach(el => {
            for (const pr of ['background-image', 'mask-image', '-webkit-mask-image', 'border-image-source']) {
              // fora os data: (o que vai dentro deles não é pedido) e as referências na própria página (url(#…))
              const v = (getComputedStyle(el).getPropertyValue(pr) || '').replace(/url\("data:[^"]*"\)/g, '');
              for (const m of v.matchAll(/url\("?([^")]+)"?\)/g)) if (!/^#/.test(m[1])) usa.add(new URL(m[1], base).href); }
            if (el.tagName === 'image') usa.add(new URL(el.getAttribute('href') || el.getAttribute('xlink:href'), base).href); });
          const rec = performance.getEntriesByType('resource');
          const tam = [...usa].map(u => { const e = rec.find(x => x.name === u); return [u.split('/').slice(-2).join('/'), e ? e.decodedBodySize : null]; });
          return { usa: tam, png: rec.filter(e => /regioes\/texturas\//.test(e.name)).map(e => e.name.split('/').pop()) }; })()""")
        conta("o peso: o que a entrada usa é leve (cada imagem < 300 KB) e a textura de 2,8 MB não baixa",
              bool(q["usa"]) and all(t is not None and t < 300000 for _, t in q["usa"]) and not q["png"]
              and (rg != "freljord" or any(u.endswith("cards/freljord.jpg") for u, _ in q["usa"])),
              "%s" % q)

        # (p) em janela menor que as quatro do roteiro, a letra da placa não cai abaixo do piso
        menores = {}
        for w, h in ((1366, 768), (1024, 768)):
            s.tela(w, h)
            time.sleep(0.5)
            menores["%dx%d" % (w, h)] = s.js("""(() => { const ef = el => { const r = el.getBoundingClientRect(); return parseFloat(getComputedStyle(el).fontSize) * (r.width / Math.max(1, el.offsetWidth)); };
              const pl = document.querySelector('.entrada-placa').getBoundingClientRect(), nt = document.querySelector('.entrada-nota').getBoundingClientRect();
              return { rot: +ef(document.querySelector('.entrada-contato .ea-rot')).toFixed(1), nota: +ef(document.querySelector('.entrada-nota')).toFixed(1),
                       id: +ef(document.querySelector('.entrada-contato .ea-id')).toFixed(1),
                       dentro: pl.top >= 0 && pl.right <= innerWidth && nt.bottom <= innerHeight && nt.right <= innerWidth }; })()""")
        s.tela(1440, 900)
        conta("em 1366×768 e 1024×768 a letra da placa não cai abaixo do piso (rótulo ≥ 10 px, nota e ID ≥ 12 px) e a placa fica na tela",
              all(v["rot"] >= 10 and v["nota"] >= 12 and v["id"] >= 12 and v["dentro"] for v in menores.values()), "%s" % menores)

        # (r) F13-T99, o diretor de arte: em Noxus a cinza não passa por cima da placa nem da etiqueta (nem para
        # em cima do texto com menos movimento) — a placa é pintada depois da camada da cinza; em Shurima, a lasca
        # caída ao pé da porta saiu (o disco partido aparece uma vez só, no alto do portal)
        if rg == "noxus":
            r = s.js("""(() => { const e = document.getElementById('entrada'), cinza = document.getElementById('en-neveTela'), g = document.querySelector('#entrada .en-placa-grupo');
              const topo = x => { while (x && x.parentElement !== e) x = x.parentElement; return x; };
              const filhos = [...e.children], ip = filhos.indexOf(topo(g)), ic = filhos.indexOf(cinza);
              return { placa: ip, cinza: ic, etiqueta: !!g.querySelector('.en-etiqueta'),
                       zcinza: getComputedStyle(cinza).zIndex, zplaca: getComputedStyle(topo(g)).zIndex }; })()""")
            conta("a cinza não passa por cima da placa nem da etiqueta: a placa é pintada depois da camada da cinza",
                  r["placa"] > r["cinza"] >= 0 and r["etiqueta"] and r["zcinza"] == "auto" and r["zplaca"] == "auto", "%s" % r)
        if rg == "shurima":
            r = s.js("""(() => ({ discos: document.querySelectorAll('#entrada use').length ? [...document.querySelectorAll('#entrada use')].filter(u => /#en-disco-arte$/.test(u.getAttribute('href') || '')).length : 0,
              lasca: !!document.querySelector('#entrada [clip-path="url(#en-cCunha)"], #en-cunha-clip, #en-esquerda-porta') }))()""")
            conta("a lasca caída ao pé da porta saiu: o disco partido aparece uma vez só, no alto do portal",
                  r["discos"] == 1 and not r["lasca"], "%s" % r)

        # (n) com a fonte para dislexia, o Riot ID cabe inteiro no pergaminho (não sai cortado)
        s.js("localStorage.setItem('acessibilidade', JSON.stringify({ dislexia: true })); 1")
        try:
            dis = {}
            for w, h in ((1440, 900), (1280, 800)):
                s.tela(w, h)
                pagina(arg)
                s.js("document.fonts.ready.then(() => 1)")
                time.sleep(0.6)
                dis["%dx%d" % (w, h)] = s.js("""(() => { const per = document.querySelector('.en-pergaminho') || document.querySelector('.entrada-placa');
                  const b = per.getBoundingClientRect();
                  return { fonte: document.fonts.check('16px OpenDyslexic') && document.body.classList.contains('ac-dislexia'),
                           ids: [...document.querySelectorAll('.entrada-contato .ea-id')].map(e => { const r = e.getBoundingClientRect(); return [e.textContent, Math.round(b.right - r.right), Math.round(r.left - b.left)]; }) }; })()""")
        finally:
            s.js("localStorage.removeItem('acessibilidade'); 1")
            s.tela(1440, 900)
        conta("com a fonte para dislexia, os IDs cabem inteiros no pergaminho (o Riot ID não sai cortado)",
              all(v["fonte"] and len(v["ids"]) == 2 and all(i[1] >= 0 and i[2] >= 0 for i in v["ids"]) for v in dis.values()),
              "folga [ID, à direita, à esquerda] por resolução: %s" % dis)

    try:
        for rg in REGIOES_ENTRADA:
            rodada(rg)

        # (s) F13-T99: sem o parâmetro, a região é sorteada a cada carga (12 cargas dão pelo menos duas) e
        # só a sorteada está montada: um tema, um <style>, nenhum molde sobrando, nada das outras duas
        s.tela(1440, 900)
        vistas, ruins = [], []
        for _ in range(12):
            pagina()
            v = s.js("""(() => { const e = document.getElementById('entrada'), rg = e.dataset.regiao;
              const marcas = %s, outras = Object.keys(marcas).filter(k => k !== rg && document.getElementById(marcas[k]));
              return { rg, estilos: e.querySelectorAll('style').length, moldes: document.querySelectorAll('template.en-tema, template[id^="en-tema-"]').length,
                       palcos: e.querySelectorAll('.en-palco').length, outras,
                       propria: !!(rg && document.getElementById(marcas[rg])) }; })()""" % json.dumps(MARCA_REGIAO))
            vistas.append(v["rg"])
            if not (v["rg"] in REGIOES_ENTRADA and v["estilos"] == 1 and v["moldes"] == 0 and v["propria"] and not v["outras"]
                    and v["palcos"] == 2):   # F13-T111: o palco do mundo e o da placa, nas três
                ruins.append(v)
        repetidas = [i for i in range(1, len(vistas)) if vistas[i] == vistas[i - 1]]
        p.conta("entrada da loja", "sem o parâmetro, a região é sorteada a cada carga (12 cargas dão pelo menos duas regiões) e nunca repete a da visita anterior",
                len(set(vistas)) >= 2 and not repetidas, "regiões vistas: %s; repetidas em seguida nas cargas %s" % (vistas, repetidas or "nenhuma"))
        p.conta("entrada da loja", "só a região sorteada está montada (um tema, um <style>, nenhum molde sobrando, nada das outras)",
                not ruins, "%s" % (ruins[:2] or "12 de 12 cargas com uma região só"))

        # (t) F13-T111 (anotado na T99): a neve do Freljord e a areia de Shurima passavam por cima da placa. Nas
        # três regiões, a placa mora na camada .en-palco-placa, que vem DEPOIS da .en-neve-tela (pinta por
        # cima dela), com o primeiro plano junto; a camada só pega o clique na placa
        placas = []
        for rg in REGIOES_ENTRADA:
            s.abrir("?entrada=%s" % rg)
            time.sleep(0.6)
            placas.append(s.js("""(() => { const e = document.getElementById('entrada'), p = document.getElementById('en-placa'), t = document.getElementById('en-neveTela');
              const camada = p && p.closest('.en-palco-placa'), perto = document.getElementById('en-perto');
              return { rg: e.dataset.regiao, camada: !!camada, depois: !!(t && camada && (t.compareDocumentPosition(camada) & Node.DOCUMENT_POSITION_FOLLOWING)),
                       perto: !!(perto && camada && camada.contains(perto)),
                       clique: camada ? [getComputedStyle(camada).pointerEvents, getComputedStyle(p).pointerEvents] : null }; })()"""))
        p.conta("entrada da loja", "a neve e a areia não passam por cima da placa: nas três regiões a placa está na camada própria, depois do clima, com o primeiro plano junto; a camada só pega o clique na placa",
                [x["rg"] for x in placas] == list(REGIOES_ENTRADA)
                and all(x["camada"] and x["depois"] and x["perto"] and x["clique"] == ["none", "auto"] for x in placas),
                "; ".join("%s: camada %s, depois do clima %s, primeiro plano %s, clique %s" % (x["rg"], x["camada"], x["depois"], x["perto"], x["clique"]) for x in placas))

        # F13-T100 (Leo, 01/11/2026: "o som está mal sincronizado com a animação de abertura" — chegava tarde;
        # "tem vezes que os frames pulam"). Uma sonda própria em cada carga: o relógio do clique, os elementos de
        # áudio criados (e quando), o play e o "playing" do open_catalog, e os quadros (rAF) da abertura.
        sonda_t100 = s.envia("Page.addScriptToEvaluateOnNewDocument", {"source": """(() => {
          const T = window.__t100 = { clique: null, criados: [], q: [] };
          const A = window.Audio;
          window.Audio = function () { const e = new A(...arguments); T.criados.push([performance.now(), e]); return e; };
          window.Audio.prototype = A.prototype;
          document.addEventListener('click', () => { if (T.clique != null) return; T.clique = performance.now();
            T.raios = document.getAnimations().filter(a => a.animationName === 'burst-spin' && a.playState === 'running').length;
            let ult = T.clique; const f = (t) => { T.q.push(t - ult); ult = t; if (t - T.clique < 2150 && !document.getElementById('entrada').classList.contains('fechada')) requestAnimationFrame(f); };   // F13-T102: só a abertura (fecha no fim do som)
            requestAnimationFrame(f);
            setTimeout(() => { T.raiosMeio = document.getAnimations().filter(a => a.animationName === 'burst-spin' && a.playState === 'running').length; }, 900); }, true);
          const o = HTMLMediaElement.prototype.play;
          HTMLMediaElement.prototype.play = function () {
            if (/open_catalog/.test(this.src) && T.play == null) { const a = this; T.play = performance.now(); T.rs = a.readyState;
              a.addEventListener('playing', () => { T.playing = performance.now(); }, { once: true }); }
            return o.apply(this, arguments); }; })();"""})["identifier"]
        LE_T100 = """(() => { const T = window.__t100, c = T.clique, r = x => x == null || c == null ? null : Math.round(x - c);
          const nome = e => decodeURIComponent(String(e.src || '').split('/').pop());
          return { antes: T.criados.filter(x => c == null || x[0] < c).map(x => nome(x[1])),
                   noClique: T.criados.filter(x => c != null && x[0] >= c && x[0] < c + Math.max(1100, EntradaLoja.FIM)).length,   // F13-T102: até a abertura fechar
                   rs: T.rs == null ? null : T.rs, play: r(T.play), playing: r(T.playing),
                   raios: T.raios, raiosMeio: T.raiosMeio,
                   q: T.q.map(x => Math.round(x * 10) / 10) }; })()"""

        def abre_e_mede(rg, antigo=False):
            """Uma abertura de verdade (clique no céu), com a página nova. `antigo`: o comportamento de antes da
            F13-T100 de volta, só nesta carga — os raios da loja girando por baixo e os ~80 sons baixando no clique."""
            pagina("?entrada=" + rg)
            fim = time.time() + 4
            while time.time() < fim and not s.js("typeof Som.pronto === 'function' && Som.pronto('catalog:open')"):
                time.sleep(0.1)
            time.sleep(0.4)
            pronto = s.js("typeof Som.pronto === 'function' && Som.pronto('catalog:open')")
            if antigo:
                s.js("""(() => { const st = document.createElement('style');
                  st.textContent = 'html.com-entrada .card-burst { animation: burst-spin 14s linear infinite !important; }'; document.head.appendChild(st);
                  const d = Som.destravar; Som.destravar = () => d(0); return 1; })()""")
                time.sleep(0.3)
            antes = s.js(LE_T100)
            clique_em(720, 60)
            time.sleep(2.5)
            espera_fechar()
            r = s.js(LE_T100)
            r["pronto"] = pronto
            r["tocouAntes"] = antes["play"] is not None or antes["playing"] is not None
            r["criadosAntes"] = antes["antes"]
            longos = [x for x in r["q"] if x > 34]
            r["pior"] = max(r["q"]) if r["q"] else None
            r["soma"] = round(sum(longos))
            time.sleep(0.6)
            r["raiosDepois"] = s.js("document.getAnimations().filter(a => a.animationName === 'burst-spin' && a.playState === 'running').length")
            return r

        try:
            s.tela(1440, 900)
            s.js("localStorage.clear(); sessionStorage.clear(); 'ok'")
            com, sem = {}, {}
            for volta in range(2):                       # intercalado: a mesma máquina, no mesmo momento, mede os dois
                for rg in REGIOES_ENTRADA:
                    com.setdefault(rg, []).append(abre_e_mede(rg))
                    sem.setdefault(rg, []).append(abre_e_mede(rg, antigo=True))

            # (t) o som da abertura: o arquivo pronto antes do clique (baixado e decodificado, nada tocando; o único
            # áudio criado antes do clique é o dele) e o "playing" em até 80 ms do clique
            ruins = []
            for rg in REGIOES_ENTRADA:
                for r in com[rg]:
                    if not (r["pronto"] and not r["tocouAntes"] and r["criadosAntes"] and all(n.startswith("open_catalog") for n in r["criadosAntes"])
                            and r["rs"] == 4 and r["playing"] is not None and r["playing"] <= 80):
                        ruins.append("%s: pronto %s, tocou antes %s, criados antes %s, readyState no play %s, playing a %s ms"
                                     % (NOME_REGIAO[rg], r["pronto"], r["tocouAntes"], r["criadosAntes"][:3], r["rs"], r["playing"]))
            p.conta("entrada da loja", "o som da abertura já está pronto antes do clique (sem tocar nada) e começa em até 80 ms do clique",
                    not ruins, "; ".join(ruins[:3]) or "playing a %s ms do clique (6 aberturas); antes do clique só o open_catalog existe, pronto e parado"
                    % sorted(r["playing"] for rg in REGIOES_ENTRADA for r in com[rg]))

            # (u) o clique não baixa os outros ~80 sons junto com o da abertura: eles ficam para depois dela
            n_clique = [r["noClique"] for rg in REGIOES_ENTRADA for r in com[rg]]
            p.conta("entrada da loja", "no clique, nenhum outro som começa a baixar junto com o da abertura (o resto baixa depois dela)",
                    max(n_clique) == 0 and all(r["noClique"] > 40 for rg in REGIOES_ENTRADA for r in sem[rg]),
                    "áudios criados entre o clique e o fim da abertura: %s (o comportamento antigo, na mesma rodada: %s)"
                    % (n_clique, [r["noClique"] for rg in REGIOES_ENTRADA for r in sem[rg]]))

            # (v) por baixo da entrada, os raios dos cards não giram (eram 225 camadas animadas a cada quadro da câmera);
            # depois de fechada, voltam a girar — o efeito do hover dos cards fica intacto
            raios = [(r["raios"], r["raiosMeio"], r["raiosDepois"]) for rg in REGIOES_ENTRADA for r in com[rg]]
            p.conta("entrada da loja", "durante a abertura a loja escondida não gira os raios dos cards; ao fechar, os 225 voltam",
                    all(a == 0 and b == 0 and d == 225 for a, b, d in raios),
                    "[no clique, no meio da abertura, depois de fechada] por abertura: %s" % raios)

            # (w) os quadros: nenhuma região passa do teto no melhor de duas aberturas (medido no Chrome sem janela —
            # que aqui usa a placa de vídeo —, com folga sobre o consertado: pior 60–130 ms), e os quadros longos
            # (> 34 ms) somam no máximo 30% da abertura, na média. F13-T102: a comparação com o comportamento antigo
            # (cair 20%) saiu — com a abertura casada com o som (~1,2 s), as duas somas ficaram pequenas e a diferença
            # virou ruído (137% numa rodada, 84% na seguinte); os consertos da T100 seguem vigiados um a um (t, u, v)
            TETO = 200
            melhor = {rg: min(r["pior"] for r in com[rg]) for rg in REGIOES_ENTRADA}
            n_ab = sum(len(com[rg]) for rg in REGIOES_ENTRADA)
            media = sum(r["soma"] for rg in REGIOES_ENTRADA for r in com[rg]) / float(n_ab or 1)
            dur_ab = s.js("Math.round(EntradaLoja.FIM)")
            p.conta("entrada da loja", "a abertura das três regiões fica abaixo do teto de quadro (%d ms) e os quadros longos somam no máximo 30%% dela, na média" % TETO,
                    all(v is not None and v <= TETO for v in melhor.values()) and media <= 0.3 * dur_ab,
                    "pior quadro (melhor de duas) %s; quadros > 34 ms por abertura: média %d ms de %d ms (%.0f%%); agora %s; com o comportamento antigo, na mesma rodada, %s"
                    % (melhor, media, dur_ab, 100.0 * media / dur_ab,
                       {NOME_REGIAO[rg]: [r["soma"] for r in com[rg]] for rg in REGIOES_ENTRADA},
                       {NOME_REGIAO[rg]: [r["soma"] for r in sem[rg]] for rg in REGIOES_ENTRADA}))
        finally:
            s.envia("Page.removeScriptToEvaluateOnNewDocument", {"identifier": sonda_t100})
    finally:
        s.envia("Page.removeScriptToEvaluateOnNewDocument", {"identifier": sonda})
        s.tela_normal()

    # (h) o som só pelo Som: nenhum new Audio( fora do módulo Som
    idx = open(os.path.join(RAIZ, "index.html"), encoding="utf-8").read()
    ini = idx.find("const Som = (() => {")
    fim_som = idx.find("\n})();", ini)
    fora = [idx.count("\n", 0, m.start()) + 1 for m in re.finditer(r"new Audio\(", idx)
            if not (ini <= m.start() <= fim_som) and "//" not in idx[idx.rfind("\n", 0, m.start()) + 1:m.start()]]   # comentário não conta
    p.conta("entrada da loja", "nenhum new Audio( fora do módulo Som", ini > 0 and not fora,
            "fora do Som nas linhas %s" % fora if fora else "só o Som cria áudio")

    s.abrir(); time.sleep(0.8); s.entrar()


def checar_desatualizadas(s, p):
    """F13-T56 (Leo, 19/10/2026: "builds marcadas como desatualizada não devem
    aparecer nas públicas por ser desatualizado"): a aba Públicas mostra só o
    catálogo de agora — fora da lista e da popularidade —, diz quantas ficaram de
    fora, e pelo ID a desatualizada ainda se acha. Lista montada aqui, sem servidor."""
    print("\n%sPÚBLICAS DESATUALIZADAS%s" % (AMARELO, FIM))
    # F13-T61: desatualizada é a de item mudado (fora das Opcionais) desde o patch
    # dela, não toda a de patch antigo. As "Velha…" levam um item que mudou no
    # último patch (do data/mudancas.js); as "Antiga…" são de patch antigo sem
    # item mudado (ou com ele só na Opcional) e continuam na lista.
    s.js("""(() => { const agora = CATALOG.meta.patch, vs = MUDANCAS.versoes, velho = vs[vs.length - 1].desde;
      const mud = Object.keys(vs[vs.length - 1].itens)[0];
      const comMudado = [{ name: 'Core', kind: 'comum', items: [{ itemId: 'long-sword' }, { itemId: mud }] }];
      const linha = (id, nome, patch, extra) => Object.assign({ id, nome, descricao: '', campeao: null, modo: '', marcadores: [],
        caixas: [{ name: 'Core', items: [{ itemId: 'long-sword' }] }], versao: 1, atualizado_em: new Date().toISOString(),
        patch, autor: '', engajamentos: 0, pop_dia: 0, popular_semana: false, dias_no_top: 0, layout: null, runas: null, habilidades: null }, extra || {});
      publicas.lista = [linha('aa0001', 'Atual Um', agora), linha('aa0002', 'Atual Dois', agora, { pop_dia: 3 }),
        linha('aa0003', 'Sem patch', null), linha('bb0001', 'Velha Popular', velho, { pop_dia: 99, popular_semana: true, caixas: comMudado }),
        linha('bb0002', 'Velha Comum', velho, { caixas: comMudado }),
        linha('bb0003', 'Velha Escolha', velho, { caixas: [{ name: 'Bota', kind: 'escolha', items: [{ itemId: 'long-sword' }, { itemId: mud }] }] }),
        linha('cc0001', 'Antiga Intacta', velho),
        linha('cc0002', 'Antiga Opcional', velho, { caixas: [{ name: 'Core', kind: 'comum', items: [{ itemId: 'long-sword' }] }, { name: 'Extra', kind: 'opcional', items: [{ itemId: mud }] }] })];
      publicas.favs = []; publicas.erro = null; publicas.carregadoEm = Date.now();
      switchTab('build'); showBuildScreen('lista'); document.getElementById('bi-search').value = '';
      document.querySelector('.bi-tab[data-view="publicas"]').click(); return 'ok'; })()""")
    time.sleep(0.6)
    le = """(() => { const r = document.getElementById('bi-rows'), f = r.querySelector('.bi-fora');
      return { nomes: [...r.querySelectorAll('.bi-row')].map(x => x.querySelector('.bi-name, .bi-nome, b') ? (x.querySelector('.bi-name, .bi-nome, b').textContent || '').trim() : x.textContent.trim().slice(0, 30)),
               texto: r.innerText.replace(/\\s+/g, ' '), fora: f ? f.textContent : null,
               desat: r.querySelectorAll('.bi-etiqueta.desatualizada').length, hoje: r.querySelectorAll('.bi-etiqueta.hoje').length }; })()"""
    r = s.js(le)
    some = not any(n in r["texto"] for n in ("Velha Popular", "Velha Comum", "Velha Escolha"))
    p.conta("desatualizadas", "a aba Públicas tira a de item mudado (nem na popularidade)",
            some and all(n in r["texto"] for n in ("Atual Um", "Atual Dois", "Sem patch")) and r["desat"] == 0 and r["hoje"] == 1,
            "%s" % {k: r[k] for k in ("texto", "desat", "hoje")})
    p.conta("desatualizadas", "a de patch antigo sem item mudado continua (Opcional não conta)",
            "Antiga Intacta" in r["texto"] and "Antiga Opcional" in r["texto"], "%s" % r["texto"][:160])
    p.conta("desatualizadas", "a lista diz quantas ficaram de fora",
            bool(r["fora"]) and r["fora"] == "3 builds publicadas no catálogo estão desatualizadas estando de fora até serem republicadas para o Patch-%s. Pelo ID, ainda dá para achar." % s.js("CATALOG.meta.patch"),
            "nota: %r" % r["fora"])
    # a lista registra uma impressão por linha: a barreira da sessão segura todas na página
    barrados = s.js("window.__eventosBarrados || 0")
    p.conta("desatualizadas", "as impressões da lista não saem da página (barreira do roteiro)", barrados >= 3,
            "%d eventos segurados" % barrados)
    # pelo ID exato, a desatualizada aparece, com a etiqueta
    s.js("(() => { const b = document.getElementById('bi-search'); b.value = 'bb0002'; b.dispatchEvent(new Event('input', { bubbles: true })); return 'ok'; })()")
    time.sleep(0.6)
    r2 = s.js(le)
    p.conta("desatualizadas", "pelo ID, a desatualizada ainda se acha (com a etiqueta)",
            "Velha Comum" in r2["texto"] and r2["desat"] == 1 and "Atual Um" not in r2["texto"],
            "%s" % {k: r2[k] for k in ("texto", "desat")})
    s.js("""(() => { const b = document.getElementById('bi-search'); b.value = ''; b.dispatchEvent(new Event('input', { bubbles: true }));
      publicas.lista = []; publicas.carregadoEm = 0; document.querySelector('.bi-tab[data-view="minhas"]').click(); return 'ok'; })()""")
    s.abrir(); time.sleep(0.8); s.entrar()

def checar_mudancas(s, p):
    """F13-T61 (Leo, 21/10/2026: "marcar como desatualizada builds que contêm —
    opcional não conta — os itens que foram atualizados; builds que não têm nenhum
    item modificado se mantêm"). O registro (data/mudancas.js), a revisão das
    builds próprias ao carregar, a borda vermelha na forja e nas leituras, e as
    cópias de uma pública. As builds são montadas no disco e a página recarrega:
    é o caminho de quem abre o app depois de um patch."""
    print("\n%sDESATUALIZADA SÓ COM ITEM MUDADO%s" % (AMARELO, FIM))
    reg = s.js("""(() => { const vs = (window.MUDANCAS || {}).versoes || [], u = vs[vs.length - 1] || {};
      return { patch: u.patch, desde: u.desde, atual: CATALOG.meta.patch, n: vs.length,
               itens: Object.keys(u.itens || {}).map(sl => (byId[sl] || {}).namePt || sl).sort() }; })()""")
    # a entrega do Capítulo 1 de 22/10/2026 lista os cinco; ícone e fonte mudaram nos 225 e não contam
    esperado = sorted(["Quebra-Bastião", "Auronúcleo", "Grevas Vorazes", "Caminho Imortal", "Húbris"])
    p.conta("mudanças", "o registro acompanha o catálogo (e o 16.21.1 tem os 5 itens da entrega)",
            reg["patch"] == reg["atual"] and (reg["patch"] != "16.21.1" or reg["itens"] == esperado),
            "%s → %s: %s" % (reg["desde"], reg["patch"], ", ".join(reg["itens"])))

    s.js("""(() => { const agora = CATALOG.meta.patch, vs = MUDANCAS.versoes, u = vs[vs.length - 1], velho = u.desde;
      const pen = vs.length > 1 ? vs[vs.length - 2] : null;
      const mud = Object.keys(u.itens)[0];
      const mudAntigo = pen ? Object.keys(pen.itens).find(sl => !u.itens[sl] && byId[sl]) : mud;
      const cx = (n, kind, ids) => ({ id: 'qa-c' + n, name: kind, kind, cols: 3, items: ids.map(i => ({ itemId: i, note: '' })) });
      const b = (id, name, patch, cats, extra) => Object.assign({ id, name, seq: 9, mode: '', cats, patch, updatedAt: 1 }, extra || {});
      const builds = [
        b('qa-m1', 'Mudou no núcleo', velho, [cx(1, 'comum', ['long-sword', mud])]),
        b('qa-m2', 'Mudou só na opcional', velho, [cx(2, 'comum', ['long-sword']), cx(3, 'opcional', [mud])]),
        b('qa-m3', 'Mudou na alternativa', velho, [cx(4, 'escolha', ['long-sword', mud])]),
        b('qa-m4', 'Nada mudou', velho, [cx(5, 'comum', ['long-sword'])]),
        b('qa-m5', 'Dois patches atrás', pen ? pen.desde : velho, [cx(6, 'prioridade', [mudAntigo])]),
        b('qa-m6', 'Revisão antiga sem mudança', agora, [cx(7, 'comum', ['long-sword'])], { revisao: { de: pen ? pen.desde : velho, para: agora, removidos: [] } }),
        b('qa-m7', 'Item que saiu', agora, [cx(8, 'comum', ['long-sword', 'item-que-saiu-do-catalogo'])]),
        // a revisão gravada pelo código de antes (sem "mudados", patch já no atual) é refeita desde o "de" dela
        b('qa-m8', 'Revisão antiga com mudança', agora, [cx(9, 'comum', [mud])], { revisao: { de: velho, para: agora, removidos: [] } }),
      ];
      localStorage.clear();
      localStorage.setItem('lol-builds-v3', JSON.stringify({ builds, activeId: null }));
      window.__qaMud = { mud, mudAntigo }; return 'ok'; })()""")
    alvo = s.js("window.__qaMud")
    s.abrir(); time.sleep(0.8); s.entrar()
    rev = s.js("""(() => { const o = {}; library.builds.forEach(b => { o[b.id] = { mud: b.revisao ? (b.revisao.mudados || []) : null,
      tirados: b.revisao ? (b.revisao.removidos || []).length : 0, patch: b.patch === CATALOG.meta.patch }; }); return o; })()""")
    mud, ant = alvo["mud"], alvo["mudAntigo"]
    quer = {"qa-m1": [mud], "qa-m2": None, "qa-m3": [mud], "qa-m4": None, "qa-m5": [ant], "qa-m6": None, "qa-m8": [mud]}
    erradas = [k for k, v in quer.items() if (rev.get(k) or {}).get("mud") != v]
    m7 = rev.get("qa-m7") or {}
    p.conta("mudanças", "ao carregar, só a build com item mudado (fora da Opcional) fica em revisão",
            not erradas and m7.get("tirados") == 1 and all(v["patch"] for v in rev.values()),
            "erradas: %s" % ", ".join("%s=%s" % (k, rev.get(k)) for k in erradas) if erradas
            else "núcleo, alternativa da Escolha 1, dois patches atrás e revisão antiga com item mudado sim; Opcional, nada mudado e revisão antiga sem item mudado não; o item que saiu sim")
    s.js("switchTab('build'); showBuildScreen('lista'); document.querySelector('.bi-tab[data-view=\"minhas\"]').click(); 'ok'")
    time.sleep(0.6)
    etiq = s.js("""(() => [...document.querySelectorAll('#bi-rows .bi-row')].filter(r => r.querySelector('.bi-etiqueta.desatualizada'))
      .map(r => r.dataset.id).sort())()""")
    p.conta("mudanças", "a etiqueta desatualizada só nelas", etiq == ["qa-m1", "qa-m3", "qa-m5", "qa-m7", "qa-m8"], "%s" % etiq)
    resumo = s.js("""(() => { const conta = (id) => { biSelected = id; renderBuildIndex();
        return [...document.querySelectorAll('#bi-detail .bd-items img')].map(i => i.classList.contains('mudou')); };
      return { m1: conta('qa-m1'), m4: conta('qa-m4') }; })()""")
    p.conta("mudanças", "no resumo da lista, a borda vermelha no item que mudou",
            resumo["m1"] == [False, True] and resumo["m4"] == [False], "%s" % resumo)

    # a forja: borda vermelha no item que mudou, não no resto
    s.js("activateBuild('qa-m3'); showBuildScreen('forja'); 'ok'")
    time.sleep(0.8)
    forja = s.js("""(() => { const t = [...document.querySelectorAll('.build-cat .item-tile')];
      const mud = %s, cel = (id) => t.find(x => build.cats[0].items[Number(x.dataset.index)].itemId === id);
      const a = cel(mud), b = cel('long-sword');
      return { mudou: !!a && a.classList.contains('mudou'), resto: !!b && b.classList.contains('mudou'),
               borda: a ? getComputedStyle(a.querySelector('.item-icon')).borderTopColor : '',
               aviso: (document.getElementById('revisao-warning').textContent || '').includes('borda vermelha') }; })()""" % json.dumps(mud))
    s.hover(".build-cat .item-tile.mudou .item-icon")
    balao = s.js("(document.getElementById('item-tooltip').textContent || '').includes('Mudou no jogo')")
    p.conta("mudanças", "na forja, a borda vermelha no item que mudou (na Escolha 1 também)",
            forja["mudou"] and not forja["resto"] and forja["borda"] == "rgb(224, 80, 60)" and forja["aviso"] and balao,
            "%s; balão diz: %s" % (forja, balao))
    leit = s.js("""(async () => { const lay = Object.keys(LAYOUTS).find(k => k !== 'tabuleiro'); build.layout = lay; ligarEdicao(false); renderBuildAll();
      await new Promise(r => setTimeout(r, 300));
      const r = { lay, marcados: document.querySelectorAll('#build-canvas .lc.mudou').length, cards: document.querySelectorAll('#build-canvas .lc').length };
      build.layout = 'tabuleiro'; renderBuildAll(); return r; })()""")
    p.conta("mudanças", "nas leituras alternativas também", leit["marcados"] == 1 and leit["cards"] >= 2, "%s" % leit)
    # a Opcional não ganha borda, mesmo com o item que mudou dentro
    s.js("activateBuild('qa-m2'); showBuildScreen('forja'); 'ok'")
    time.sleep(0.6)
    opc = s.js("document.querySelectorAll('.build-cat .item-tile.mudou').length")
    # salvar fecha a revisão e tira a borda (o caminho de antes: o aviso some ao salvar)
    s.js("activateBuild('qa-m1'); showBuildScreen('forja'); ligarEdicao(true); build.desc = 'conferida'; saveBuild(); salvarAgora(); ligarEdicao(false); 'ok'")
    time.sleep(0.6)
    salvo = s.js("({ rev: build.revisao, bordas: document.querySelectorAll('.build-cat .item-tile.mudou').length })")
    p.conta("mudanças", "a Opcional não ganha borda; salvar fecha a revisão e tira a borda",
            opc == 0 and salvo["rev"] is None and salvo["bordas"] == 0, "opcional %s; depois de salvar %s" % (opc, salvo))

    # as cópias de uma pública desatualizada herdam a revisão (Copiar e editar, e o lote)
    copia = s.js("""(() => { const vs = MUDANCAS.versoes, velho = vs[vs.length - 1].desde, mud = %s;
      publicas.lista = [{ id: 'qq0001', nome: 'Pública velha', descricao: 'x', campeao: null, modo: '', marcadores: [], versao: 1,
        atualizado_em: new Date().toISOString(), patch: velho, autor: '', engajamentos: 0, pop_dia: 0, popular_semana: false, dias_no_top: 0,
        layout: null, runas: null, habilidades: null, caixas: [{ name: 'Core', kind: 'comum', items: [{ itemId: 'long-sword' }, { itemId: mud }] }] }];
      const d = publicaResumo(publicas.lista[0]);
      copiarPublica(d); const r1 = build.revisao && build.revisao.mudados;
      const antes = library.builds.length; guardarPublicaNaBiblioteca(d); const nova = library.builds[library.builds.length - 1];
      publicas.lista = [];
      return { copiar: r1, lote: library.builds.length === antes + 1 ? (nova.revisao && nova.revisao.mudados) : 'não guardou',
               patch: nova.patch === CATALOG.meta.patch }; })()""" % json.dumps(mud))
    p.conta("mudanças", "a cópia de uma pública desatualizada herda a revisão",
            copia["copiar"] == [mud] and copia["lote"] == [mud] and copia["patch"], "%s" % copia)
    s.js("localStorage.clear(); 'ok'")
    s.abrir(); time.sleep(0.8); s.entrar()


def checar_acessibilidade(s, p):
    print("\n%sACESSIBILIDADE%s" % (AMARELO, FIM))
    s.js("switchTab('catalog')")
    time.sleep(0.5)
    s.clicar("#acess-btn")
    for chave in ("movimento", "brilho", "leitura", "dalt-geral"):
        s.clicar("#ac-" + chave, 0.25)
    ligadas = s.js("[...document.body.classList].filter(c => c.startsWith('ac-')).length")
    p.conta("acessibilidade", "os quatro interruptores ligam", ligadas == 4, "%s de 4" % ligadas)
    p.conta("acessibilidade", "menos movimento zera as transições",
            s.js("""(() => { const c = document.querySelector('.card-surface');
              return !c || /^0s/.test(getComputedStyle(c).transitionDuration); })()"""))
    # F13-T10: cada interruptor cumpre o que o próprio rótulo promete.
    s.nova_build()
    s.js("build.cats[1].items = CATALOG.items.slice(0, 2).map(it => ({ itemId: it.slug, note: '' })); renderBuildAll(); 'ok'")
    time.sleep(0.4)
    tam = s.js("""(() => { const t = document.querySelector('.item-tile .tile-name');
      return t ? parseFloat(getComputedStyle(t).fontSize) : 0; })()""")
    p.conta("acessibilidade", "leitura calma aumenta o nome no molde da forja", tam >= 12, "%spx" % tam)
    s.js("""(() => { window.__choveu = false; const o = new MutationObserver(() => {
        if (document.querySelector('.chovendo')) window.__choveu = true; });
      o.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['class'] });
      switchTab('catalog'); switchTab('build'); showBuildScreen('lista'); return 'ok'; })()""")
    time.sleep(1.2)
    p.conta("acessibilidade", "menos movimento para a chuva de entrada", not s.js("window.__choveu"))
    s.js("switchTab('build'); showBuildScreen('forja'); 'ok'")
    time.sleep(0.5)
    brilho = s.js(r"""(() => {
      const quente = (x) => { const m = x.match(/rgba?\((\d+), (\d+), (\d+)/); if (!m) return false;
        const [r, g, b] = m.slice(1).map(Number); return r > 200 && g > 60 && g < 200 && b < 90; };
      let n = 0;
      document.querySelectorAll('body *').forEach(e => { const r = e.getBoundingClientRect(); if (r.width < 1) return;
        const bs = getComputedStyle(e).boxShadow; if (!bs || bs === 'none') return;
        if (bs.split(/,(?![^(]*\))/).some(x => !/inset/.test(x) && quente(x) && !/0px 0px 0px/.test(x.replace(/rgba?\([^)]*\)/, '')))) n++; });
      return { halos: n, brasa: /255, 110, 30/.test(getComputedStyle(document.body).backgroundImage) }; })()""")
    p.conta("acessibilidade", "menos brilho apaga a brasa e os halos da forja",
            brilho["halos"] == 0 and not brilho["brasa"], "%s halo(s), brasa=%s" % (brilho["halos"], brilho["brasa"]))
    s.abrir()
    time.sleep(1.0)
    s.entrar()
    p.conta("acessibilidade", "os ajustes sobrevivem ao recarregar",
            s.js("[...document.body.classList].filter(c => c.startsWith('ac-')).length") == 4)
    s.js("localStorage.removeItem('acessibilidade')")
    s.abrir()
    time.sleep(1.0)
    s.entrar()
    checar_daltonismo(s, p)


def checar_publicas(s, p, online):
    print("\n%sBUILDS PUBLICADAS%s" % (AMARELO, FIM))
    if not online:
        p.conta("públicas", "a lista vem do servidor", True, "pulada (--offline)", pulou=True)
        return
    s.js("switchTab('build'); showBuildScreen('lista')")
    time.sleep(0.6)
    # F13-T2: contar os redesenhos. Eram ~80 em 4 segundos, com a página morta —
    # cada marcador de habilidade pedia a lista inteira de volta.
    s.js("""(() => { window.__redesenhos = 0; const f = window.renderBuildIndex;
      window.renderBuildIndex = function (...a) { window.__redesenhos++; return f.apply(this, a); };
      return 'ok'; })()""")
    s.js("""document.querySelector('.bi-tab[data-view=\"publicas\"]').click()""")
    # A lista vem do Supabase e traz o retrato de cada campeão do Data Dragon:
    # depende de rede, então espera até aparecer em vez de cronometrar no chute.
    estado = {"linhas": 0, "texto": ""}
    fim = time.time() + 30
    while time.time() < fim:
        try:
            estado = s.js("""(() => { const l = document.getElementById('bi-rows');
              return { linhas: l.querySelectorAll('.bi-row').length,
                       texto: l.innerText.replace(/\\s+/g, ' ').slice(0, 90) }; })()""")
        except RuntimeError as e:
            estado = {"linhas": 0, "texto": str(e)[:90]}
        if estado["linhas"]:
            break
        time.sleep(2)
    # Foi exatamente isto que ficou quebrado em 20/09: a view caiu inteira porque
    # faltava o grant das colunas novas, e a lista veio vazia com um aviso.
    p.conta("públicas", "a lista vem do servidor", estado["linhas"] > 0,
            "%d builds — %s" % (estado["linhas"], estado["texto"]))
    p.conta("públicas", "nenhum 'permission denied'", "permission denied" not in estado["texto"].lower())
    # F13-T56: a lista quis contar as impressões, e a barreira da sessão segurou todas
    time.sleep(0.5)
    barrados = s.js("window.__eventosBarrados || 0")
    p.conta("públicas", "o roteiro não registra evento no servidor de verdade", barrados > 0,
            "%d eventos segurados na página (impressões da lista)" % barrados)
    # e a lista de verdade não traz desatualizada
    real = s.js("""(() => ({ desat: document.querySelectorAll('#bi-rows .bi-etiqueta.desatualizada').length,
      fora: publicas.lista.filter(p => !publicaNoCatalogoAtual(p)).length,
      nota: !!document.querySelector('#bi-rows .bi-fora') }))()""")
    p.conta("públicas", "a lista do servidor não mostra desatualizada", real["desat"] == 0 and real["nota"] == (real["fora"] > 0),
            "%d desatualizadas (item mudado desde o patch delas) no servidor, ficaram de fora; nota no pé: %s" % (real["fora"], real["nota"]))

    time.sleep(3)
    try:
        n = s.js("window.__redesenhos")
        vivo = s.js("document.querySelectorAll('#bi-rows .bi-row').length") > 0
    except RuntimeError as e:
        n, vivo = -1, False
    # O número varia com a rede: é um redesenho por quadro em que chega a lista
    # de habilidades de algum campeão, então 6 com cache quente e 15 com cache
    # frio, nas mesmas 42 builds. O que se pega aqui é a disparada — eram ~80 e
    # subindo até a página morrer —, não um valor exato.
    p.conta("públicas", "sem tempestade de redesenho", 0 <= n <= 30 and vivo,
            "%s redesenhos; página %s" % (n if n >= 0 else "?", "viva" if vivo else "MUDA"))
    # a arte das habilidades ainda tem de chegar: a letra vira ícone sozinha
    try:
        arte = s.js("""(() => ({ letras: document.querySelectorAll('#bi-rows .mk-letra').length,
          icones: document.querySelectorAll('#bi-rows .mk-hab:not(.mk-letra)').length }))()""")
        p.conta("públicas", "a arte da habilidade chega no marcador",
                arte["letras"] == 0, "%s letras, %s ícones" % (arte["letras"], arte["icones"]))
    except RuntimeError as e:
        p.conta("públicas", "a arte da habilidade chega no marcador", False, str(e)[:80])

    # F13-T6: os dois laços de pedidos ao Supabase achados pela caçada de bugs
    # (117 e 126 pedidos em 5 s). Conta os pedidos que o app faz sozinho,
    # parado, depois de uma ação só.
    s.js("""(() => { window.__pedidos = 0; if (!window.__fetchEspiado) { const f = window.fetch;
      window.fetch = function (u, ...a) { if (String(u).includes('supabase')) window.__pedidos++;
        return f.call(this, u, ...a); }; window.__fetchEspiado = true; } return 'ok'; })()""")
    s.js("""(() => { const c = document.getElementById('bi-search'); c.value = 'cabeca';
      c.dispatchEvent(new Event('input', { bubbles: true })); return 'ok'; })()""")
    time.sleep(4)
    n = s.js("window.__pedidos")
    p.conta("públicas", "busca por ID que não existe não vira laço", n <= 1, "%s pedido(s) em 4 s" % n)
    s.js("""(() => { const c = document.getElementById('bi-search'); c.value = '';
      c.dispatchEvent(new Event('input', { bubbles: true })); return 'ok'; })()""")

    s.js("localStorage.setItem('publicacao.favoritos', JSON.stringify(['ffffff'])); window.__pedidos = 0; 'ok'")
    s.js("""document.querySelector('.bi-tab[data-view="minhas"]').click(); 'ok'""")
    time.sleep(4)
    n = s.js("window.__pedidos")
    p.conta("públicas", "favorita apagada do site não vira laço", n <= 1,
            "%s pedido(s) em 4 s; favoritos agora: %s" % (n, s.js("favoritosIds()")))


def checar_resolucoes(s, p):
    print("\n%sRESOLUCOES (1440, depois 1080, depois 900)%s" % (AMARELO, FIM))
    s.js("switchTab('catalog')")
    time.sleep(0.5)
    fora_js = """(() => {
      const mau = [];
      document.querySelectorAll('.card, .build-cat, .runa, .trilha-btn, .bh-grade, .oficina, .top-inner')
        .forEach(el => { const r = el.getBoundingClientRect();
          if (r.width > 0 && (r.right > innerWidth + 1 || r.left < -1))
            mau.push(el.className.split(' ')[0]); });
      return { rolagem: document.documentElement.scrollWidth > innerWidth + 1,
               fora: [...new Set(mau)].slice(0, 4) }; })()"""
    # Até 22/09 só o catálogo era medido, e a forja em 1280 rolava de lado sem
    # ninguém ver. Agora as três telas, em cada resolução — e com a PIOR build
    # que o catálogo permite, escolhida pelos dados: o item com o atributo mais
    # longo (o Biscoito, 255 caracteres, estourava a faixa da build em 1280) e o
    # de nome mais longo, mais alguns para encher as fileiras. Medir com uma
    # build comportada é o jeito de não achar nada. E no pior ESTADO também: a
    # faixa de atributos só aparece com o Editar ligado (F12), e a primeira
    # versão desta checagem media em modo leitura — passou com o bug lá dentro.
    s.nova_build()
    if not s.js("document.body.classList.contains('editando')"):
        s.clicar("#edit-switch", 0.8)
    pior = s.js("""(() => {
      const maiorAttr = (it) => Math.max(0, ...(it.attributes || []).map(a => (a.stat || '').length));
      const porAttr = CATALOG.items.slice().sort((a, b) => maiorAttr(b) - maiorAttr(a))[0];
      const porNome = CATALOG.items.slice().sort((a, b) => b.namePt.length - a.namePt.length)[0];
      const lend = CATALOG.items.filter(i => i.tier === 'Lendário').slice(0, 5);
      const c = build.cats[3];
      c.items = [porAttr, porNome, ...lend].map(it => ({ itemId: it.slug, note: 'observação de teste' }));
      build.habilidades = normHabilidades(['Q', 'W', 'E']);   // sem ponto a grade some no modo leitura
      renderBuildAll();
      return porAttr === porNome ? porAttr.namePt : porAttr.namePt + ' / ' + porNome.namePt; })()""")
    # Runas no pior modo também: o Completo (etiquetas, notas, controle de grupo
    # abertos), em cada trilha. Até a F13-T17 elas eram medidas em Ícones, e a
    # etiqueta que estourava o card com a Leitura calma ficava escondida.
    trilhas = s.js("RUNAS.trilhas.map(t => t.id)")
    # E com a Leitura calma ligada, que é o texto maior que o app tem: medir com
    # ela depender de um grupo anterior tê-la deixado ligada é medir por sorte.
    tinha_leitura = s.js("document.body.classList.contains('ac-leitura')")
    s.js("document.body.classList.add('ac-leitura'); 'ok'")
    for largura, altura in RESOLUCOES:
        s.tela(largura, altura)
        ruins = []
        for tela, cmd in (("catálogo", "switchTab('catalog')"), ("forja", "switchTab('build'); showBuildScreen('forja')"),
                          ("runas", "switchTab('runas')")):
            s.js(cmd + "; 'ok'")
            time.sleep(0.4)
            passos = [None]
            if tela == "runas":
                s.js("""(() => { const b = document.querySelector('.runas-modo[data-modo="ler"]'); if (b) b.click();
                  document.querySelector('.runas-vista[data-vista=completo]').click(); })()""")
                passos = trilhas
            for t in passos:
                if t:
                    s.js("""(() => { const b = [...document.querySelectorAll('#runas-trilhas [data-trilha]')]
                      .find(x => x.dataset.trilha === %s); if (b) b.click(); })()""" % json.dumps(t))
                    time.sleep(0.3)
                r = s.js(fora_js)
                if r["rolagem"] or r["fora"]:
                    ruins.append("%s%s (%s)" % (tela, " / " + t if t else "", ", ".join(r["fora"]) or "rolagem"))
                    break
        p.conta("resoluções", "%dx%d sem nada fora da tela" % (largura, altura), not ruins,
                ("catálogo, forja e runas (Completo, cinco trilhas), com Leitura calma e " + pior) if not ruins else "; ".join(ruins))
        # Leo, 23/10/2026: a grade de habilidades dividia a linha com o nome e
        # encolhia até 337 px — casas de 10 px em qualquer tela. Nos dois modos:
        # o menor caso muda (2560 editando, 1280 lendo).
        casas = s.js("""(async () => { switchTab('build'); showBuildScreen('forja');
          const mede = async (ed) => { ligarEdicao(ed); await new Promise(r => setTimeout(r, 250));
            const c = document.querySelector('#build-habs:not([hidden]) .bh-cel'); if (!c) return null;
            const r = c.getBoundingClientRect(); return Math.round(Math.min(r.width, r.height)); };
          const ler = await mede(false), editar = await mede(true); return { ler, editar }; })()""")
        p.conta("resoluções", "%dx%d: a grade de habilidades com casas de 24 px ou mais" % (largura, altura),
                all(v is not None and v >= 24 for v in casas.values()), "lendo %s px, editando %s px" % (casas["ler"], casas["editar"]))
    if not tinha_leitura:
        s.js("document.body.classList.remove('ac-leitura'); 'ok'")
    s.js("switchTab('catalog'); 'ok'")
    s.tela_normal()


def checar_console(s, p):
    print("\n%sCONSOLE%s" % (AMARELO, FIM))
    p.conta("console", "nenhuma exceção durante o roteiro", not s.erros, "; ".join(s.erros[:3]))
    if s.dialogos:
        print("  %sdiálogos nativos que apareceram e foram aceitos: %s%s" % (CINZA, "; ".join(s.dialogos[:4]), FIM))
    # 404 de arquivo é o bug clássico do Pages: nome com outra caixa de letra.
    # o favicon.ico não existe de propósito: o 404 dele não é arquivo perdido
    quatro04 = [r for r in s.rede if "404" in r and "favicon" not in r]
    p.conta("console", "nenhum arquivo faltando (404)", not quatro04, "; ".join(quatro04[:3]))


def checar_robo(p):
    """F13-T73: o leitor do robô de patch (data/robo/ler_fonte.py). Sem rede e sem
    navegador: o leitor de Lua com um texto de prova, as referências "=>", as
    regras da comparação num catálogo de mentira e a conta refeita sobre a foto
    guardada — o relatório no repositório tem de dizer o que ela diz."""
    print("\n%sROBÔ DE PATCH%s" % (AMARELO, FIM))
    import importlib
    pasta = os.path.join(RAIZ, "data", "robo")
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    lua = importlib.import_module("lua_tabela")
    lf = importlib.import_module("ler_fonte")

    prova = ('-- comentário\nreturn {\n'
             '  ["A"] = { ["id"] = 1, ["n"] = -2.5, ["t"] = "aspas \\"dentro\\" e\\nquebra", ["ok"] = true, ["nada"] = nil,\n'
             '    ["lista"] = {"x", "y",}, ["sub"] = { k = 3 }, --[[ comentário longo ]] ["id"] = 7,\n'
             '    --[=[ com nível: ["fantasma"] = 1, ]] ainda dentro ]=] ["sumiu"] = 1, ["sumiu"] = nil },\n'
             '  ["B"] = { ["stats"] = { ["hp"] = "=>A" }, ["type"] = "=>C" },\n'
             '  ["C"] = { ["type"] = {"Epic"} },\n'
             '  ["X"] = { ["type"] = "=>Y" }, ["Y"] = { ["type"] = "=>X" },\n}\n')
    avisos = []
    d = lua.ler_modulo(prova, avisos)
    a = d["A"]
    def corta(texto):
        try:
            lua.ler_modulo(texto, [])
        except lua.ErroLua as e:
            return str(e)
        return None
    # cortado dentro da tabela e logo depois de um "=": cada um pega uma guarda diferente
    cortado = [corta(prova[:-6]), corta('return { ["a"] = ')]
    p.conta("robô", "o leitor de Lua lê o que um módulo de dados usa (o comentário com nível, o \"= nil\" que não cria chave), avisa a chave repetida e para no texto cortado",
            a == {"id": 7, "n": -2.5, "t": 'aspas "dentro" e\nquebra', "ok": True, "lista": ["x", "y"], "sub": {"k": 3}}
            and len(avisos) == 2 and "'id'" in avisos[0] and "'sumiu'" in avisos[1] and all(cortado),
            "A %s · avisos %s · cortado %r" % (a, avisos, cortado))

    r, faltou = lf.resolver(d)
    p.conta("robô", "as referências \"=>\" resolvem; a sem o campo e a que dá volta ficam no aviso (sem virar nada calado)",
            r["B"]["type"] == ["Epic"] and r["B"]["stats"]["hp"] == "=>A" and len(faltou) == 3
            and any("B: stats.hp" in x for x in faltou) and sum(1 for x in faltou if x.startswith(("X:", "Y:"))) == 2,
            "B %s · faltou %s" % (r["B"], faltou))

    # a foto do patch do catálogo é a base: com a wiki numa revisão nova, não se regrava
    import tempfile
    tmp = tempfile.mkdtemp()
    json.dump({"wiki": {"revid": 1, "sha256": "a"}, "ddragon": {"versao": "9.9.1"}}, open(os.path.join(tmp, "meta.json"), "w"))
    nova = {"wiki": {"revid": 2, "sha256": "b"}, "ddragon": {"versao": "9.9.1"}}
    base = {"do catálogo": bool(lf.foto_e_base(tmp, "9.9.1", "9.9.1", nova)), "de outro patch": bool(lf.foto_e_base(tmp, "9.9.1", "9.8.1", nova)),
            "mesma revisão": lf.foto_igual(tmp, {"wiki": {"revid": 1, "sha256": "a"}, "ddragon": {"versao": "9.9.1"}})}
    p.conta("robô", "a foto do patch do catálogo é a base e não se regrava com a wiki numa revisão nova; a de outro patch se refaz; a mesma revisão nem se regrava",
            base == {"do catálogo": True, "de outro patch": False, "mesma revisão": True}, "%s" % base)

    # a contagem por fora não depende da formatação, e a base é a revisão que o Capítulo 1 registrou
    com_tab = prova.replace('  ["B"] = {', '\t[ "B" ] = {')
    contagem = {"prova": lf.contar_por_fora(prova), "com tab": lf.contar_por_fora(com_tab), "lido": len(lua.ler_modulo(com_tab, []))}
    rev_cap1 = lf.revisao_do_capitulo1()
    # 3ª rodada: entrada de 1º nível repetida (Lua válido) não trava a contagem; e a base é a revisão do Capítulo 1
    repetida = prova.replace('  ["C"] = { ["type"] = {"Epic"} },', '  ["C"] = { ["type"] = {"Epic"} },\n  ["C"] = { ["type"] = {"Epic"} },')
    contagem["repetida"] = (lf.contar_por_fora(repetida), len(lua.ler_modulo(repetida, [])))
    acoes = [lf.acao_da_base(True, 1, 1, False), lf.acao_da_base(True, 1, 2, False), lf.acao_da_base(False, None, 2, False),
             lf.acao_da_base(True, 1, 2, True), lf.acao_da_base(False, None, None, False), lf.acao_da_base(True, 1, None, False)]
    p.conta("robô", "a contagem por fora não depende da formatação (tab, espaço no colchete, entrada repetida); a foto base é a revisão que o Capítulo 1 registrou no catálogo (e se refaz quando não é)",
            contagem["prova"] == contagem["com tab"] == contagem["lido"] == 5 and contagem["repetida"] == (5, 5) and rev_cap1 is not None
            and acoes == ["ok", "refazer", "criar", "avisar", "ok", "avisar"]
            and rev_cap1 == lf.ler_foto(lf.ler_catalogo()["meta"]["patch"])[2]["wiki"]["revid"],
            "%s · revisão do Capítulo 1 %s · ações da base %s" % (contagem, rev_cap1, acoes))

    # as regras, num catálogo de mentira: cada linha é um caso que o catálogo de verdade tem
    cat = {"meta": {"patch": "0.0.1"}, "items": [
        {"id": 4004, "namePt": "Variante", "nameEn": "Variant", "priceGold": 100, "gameModes": ["ARAM", "ARAM: Mayhem"]},
        {"id": 2151, "namePt": "Grátis", "nameEn": "Free", "priceGold": 0, "priceNote": "não comprável; concedido pela runa X"},
        {"id": 2138, "namePt": "Elixir", "nameEn": "Elx", "priceGold": 500, "condition": "Limitado a 1 efeito de Elixir por vez."},
        {"id": 3001, "namePt": "Sem nome", "nameEn": "Unnamed", "priceGold": 10,
         "abilities": [{"name": "—", "nameEn": "transformação", "type": "passiva"}, {"name": "Fenda", "nameEn": "Cleave", "type": "passiva única"}]},
        {"id": 3002, "namePt": "Dividido", "nameEn": "Split", "priceGold": 2300},
        {"id": 3003, "namePt": "Errado", "nameEn": "Wrong", "priceGold": 999,
         "attributes": [{"stat": "Vida", "unit": "flat", "value": 100}]},
    ]}
    wiki = {"Variant": {"id": 224004, "buy": 100, "modes": {"aram": True}},
            "Free": {"id": 2151},
            "Elx": {"id": 2138, "buy": 500, "itemlimit": "Elixir"},
            "Unnamed": {"id": 3001, "buy": 10, "effects": {"pass": {"name": "Cleave", "unique": True}}},
            "Split": {"id": 3002, "buy": 2250},
            "Wrong": {"id": 3003, "buy": 1000, "stats": {"hp": 150}}}
    dd = {"data": {"4004": {"name": "Variante", "gold": {"total": 100, "purchasable": True}},
                   "2151": {"name": "Grátis", "gold": {"total": 50, "purchasable": False}},
                   "2138": {"name": "Elixir", "gold": {"total": 500, "purchasable": True}},
                   "3001": {"name": "Sem nome", "gold": {"total": 10, "purchasable": True}},
                   "3002": {"name": "Dividido", "gold": {"total": 2300, "purchasable": True}},
                   "3003": {"name": "Errado", "gold": {"total": 1000, "purchasable": True}}}}
    dif, conta, so_cat, sem_par, dividida = lf.comparar(cat, wiki, dd)
    achado = {k: [x[0] for x in v] for k, v in dif.items() if v}
    p.conta("robô", "as regras da comparação: id de variante, item não comprável, Elixir por extenso e efeito sem nome passam; a fonte dividida e o erro de verdade aparecem",
            achado == {"preco": ["Errado (Wrong)"], "atributos": ["Errado (Wrong)"], "ddragon": ["Errado (Wrong)"]} and [x[:2] for x in dividida] == [("preço", "Dividido (Split)")] and not sem_par,
            "a conferir %s · dividida %s" % (achado, dividida))

    # a foto do patch do catálogo e o relatório: a conta refeita sem rede tem de bater
    cat_real = lf.ler_catalogo()
    patch = cat_real["meta"]["patch"]
    try:
        w, ddx, meta = lf.ler_foto(patch)
    except OSError as e:
        p.conta("robô", "a foto do patch %s existe (rode data/robo/ler_fonte.py)" % patch, False, str(e)[:120])
        return
    dif, conta, so_cat, sem_par, dividida = lf.comparar(cat_real, lf.resolver(w)[0], ddx)
    total = sum(len(v) for v in dif.values())
    rel = os.path.join(pasta, "relatorio_%s.md" % patch)
    resumo = re.search(r"\*\*(Nenhuma diferença|(\d+) diferenças?) a conferir\.\*\* (\d+) itens do catálogo casados com a wiki \((\d+) sem par\); (\d+) em que",
                       open(rel, encoding="utf-8").read()) if os.path.exists(rel) else None
    no_rel = resumo and (int(resumo.group(2) or 0), int(resumo.group(3)), int(resumo.group(4)), int(resumo.group(5)))
    p.conta("robô", "a foto do patch %s está inteira e o relatório bate com a conta refeita sem rede" % patch,
            len(w) == meta["wiki"]["itens"] and meta["patch"] == patch and no_rel == (total, len(cat_real["items"]) - len(sem_par), len(sem_par), len(dividida)),
            "%d itens na foto (meta %s) · conta %s · relatório %s" % (len(w), meta["wiki"]["itens"], (total, len(cat_real["items"]) - len(sem_par), len(sem_par), len(dividida)), no_rel))


def checar_robo_regra(p):
    """F13-T74: a regra de segurança do robô (data/robo/aplicar_patch.py). Sem rede:
    patches simulados a partir da foto do patch do catálogo, com um caso de cada —
    o robô aplica só o que mudou na fonte que o catálogo seguia, refaz o que tem
    fórmula no dado (preço de componente, custo de combinação conferido contra o
    "base" do Data Dragon, Reembolso) e manda o resto para "a conferir". A revisão
    adversarial da T74 (24/10/2026) achou casos em que o robô APLICAVA dado errado
    (a fonte sem o dado virava valor; referência "=>" sem destino; item que saía):
    cada um tem um caso aqui. E a camada do repositório bate com o catálogo."""
    print("\n%sROBÔ: A REGRA%s" % (AMARELO, FIM))
    import importlib, copy
    pasta = os.path.join(RAIZ, "data", "robo")
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    lf = importlib.import_module("ler_fonte")
    ap = importlib.import_module("aplicar_patch")
    cat = lf.ler_catalogo()
    w0, dd0, m0 = lf.ler_foto(cat["meta"]["patch"])
    idc = {i["nameEn"]: str(i["id"]).split(" ")[0] for i in cat["items"]}
    por_en = {i["nameEn"]: i for i in cat["items"]}
    def novo():
        return copy.deepcopy(w0), copy.deepcopy(dd0), copy.deepcopy(m0)
    def roda(w1, dd1, m1):
        c = ap.regra(cat, (w0, dd0, m0), (w1, dd1, m1))
        return c, c["itens"], {(x["slug"], x["campo"]): x["porque"] for x in c["aConferir"]}
    def soma(slug, delta, w1, dd1, base=True):   # o preço de um item nas duas fontes
        # base=True: o item ficou mais caro por ele mesmo (o custo de combinação sobe junto,
        # como no Data Dragon); base=False: ficou mais caro porque um componente subiu
        it = next(i for i in cat["items"] if i["slug"] == slug)
        if isinstance(w1[it.get("wikiName") or it["nameEn"]].get("buy"), (int, float)):   # "=>Outro": vem do outro
            w1[it.get("wikiName") or it["nameEn"]]["buy"] += delta
        dd1["data"][idc[it["nameEn"]]]["gold"]["total"] += delta
        if base:
            dd1["data"][idc[it["nameEn"]]]["gold"]["base"] += delta

    # o patch principal: um caso de cada linha da tabela do docs/robo_de_patch.md
    w1, dd1, m1 = novo()
    # os preços sobem como no jogo: o do Quebra-Bastião por ele mesmo (o custo de
    # combinação sobe junto) e o da Espada Longa, que leva junto toda a árvore acima dela
    proprio = {"Bastionbreaker": 100, "Long Sword": 25}
    memo = {}
    def alta(en):
        if en not in memo:
            memo[en] = proprio.get(en, 0) + sum(alta(x["nameEn"]) * int(x.get("qty") or 1)
                                                for x in (por_en[en].get("components") or []) if x["nameEn"] in por_en)
        return memo[en]
    for i in cat["items"]:
        if alta(i["nameEn"]):
            soma(i["slug"], alta(i["nameEn"]), w1, dd1, base=False)
            dd1["data"][idc[i["nameEn"]]]["gold"]["base"] += proprio.get(i["nameEn"], 0)
    w1["Bastionbreaker"]["stats"]["lethality"] = 20                       # atributo muda
    w1["Bastionbreaker"]["effects"]["pass"]["description"] += " (texto novo)"   # texto: a conferir
    w1["Atma's Reckoning"]["buy"] = 2600                                  # só a wiki; o catálogo segue o Data Dragon: nada
    w1["Atma's Reckoning"].setdefault("stats", {})["ah"] = 15             # o catálogo não seguia a fonte (10 × nada): a conferir
    dd1["data"][idc["Redemption"]]["gold"]["total"] += 50; dd1["data"][idc["Redemption"]]["gold"]["base"] += 50   # só o Data Dragon, que o catálogo segue: aplica
    w1["Abyssal Mask"]["stats"]["mana"] = 300                             # atributo que entra
    w1["Abyssal Mask"]["buy"] = 2700                                      # só a wiki, e o catálogo seguia as duas: a conferir
    w1["Test Blade"] = {"id": 999999, "tier": 3, "type": ["Legendary"], "modes": {"classic sr 5v5": True, "aram": True}, "buy": 3000}
    del w1["Kindlegem"]                                                   # o item sai da wiki
    c, it, conf = roda(w1, dd1, m1)
    bb = it.get("bastionbreaker", {}).get("campos", {})
    preco_bb = por_en["Bastionbreaker"]["priceGold"] + alta("Bastionbreaker")
    reemb = round(preco_bb * 7.5 / 100, 2)
    p.conta("robô", "a regra aplica o que mudou na fonte que o catálogo seguia, e refaz Reembolso e custo de combinação pela fórmula do dado",
            bb.get("priceGold") == preco_bb and bb.get("combineCost") == por_en["Bastionbreaker"]["combineCost"] + 100
            and (bb.get("cashback") or {}).get("raw") == "7,5%% de %sg = %sg (líquido: %sg)" % (ap.fmt_num(preco_bb), ap.fmt_num(reemb), ap.fmt_num(preco_bb - reemb))
            and "+20 de Letalidade" in [x["raw"] for x in bb.get("attributes", [])]
            and set(it["bastionbreaker"]["contaVelha"]) >= {"costAnalysis", "itemClass"}
            and it.get("redemption", {}).get("campos", {}).get("priceGold") == 2350 and not it.get("atma-s-reckoning", {}).get("campos")
            and ("atma-s-reckoning", "preço") not in conf and "não seguia" in conf.get(("atma-s-reckoning", "Aceleração de Habilidade"), ""),
            "Quebra-Bastião %s · Redenção %s · campos do Atma %s" % ({k: bb.get(k) for k in ("priceGold", "combineCost")}, it.get("redemption", {}).get("campos"), it.get("atma-s-reckoning", {}).get("campos")))
    tiamat = it.get("tiamat", {}).get("campos", {})
    ls = [x for x in tiamat.get("components", []) if x["nameEn"] == "Long Sword"]
    p.conta("robô", "o preço novo de um componente chega aos itens que o usam; o custo de combinação refeito bate com o \"base\" do Data Dragon",
            ls and all(x["priceGold"] == 375 for x in ls) and tiamat.get("priceGold") == por_en["Tiamat"]["priceGold"] + 50
            and tiamat.get("combineCost") == por_en["Tiamat"]["combineCost"]
            and len([s for s, e in it.items() if any(m["campo"] == "preço de componente" for m in e["mudou"])]) >= 10
            and not any(campo == "custo de combinação" for _, campo in conf),
            "Tiamat %s" % {k: tiamat.get(k) for k in ("priceGold", "combineCost")})
    am = it.get("abyssal-mask", {}).get("campos", {})
    p.conta("robô", "o atributo que entra é aplicado (e marca a categoria); o resto vai para a conferir (fontes divergindo, texto de efeito, item que sai) e o item novo é listado",
            "+300 de Mana" in [x["raw"] for x in am.get("attributes", [])] and "priceGold" not in am and "attributeCategory" in it.get("abyssal-mask", {}).get("contaVelha", [])
            and "divergem" in conf.get(("abyssal-mask", "preço"), "") and "texto" in conf.get(("bastionbreaker", "efeito Shaped Charge"), "")
            and "saiu" in conf.get(("kindlegem", "item"), "") and [x["nome"] for x in c["novos"]] == ["Test Blade"],
            "Máscara %s · a conferir %s · novos %s" % (am.get("attributes") and [x["raw"] for x in am["attributes"]], sorted(conf), [x["nome"] for x in c["novos"]]))

    # os achados da revisão: nada disso pode virar "aplica"
    casos = {}
    w1, dd1, m1 = novo()                    # o item sai do jogo: some do Data Dragon da SR/ARAM e a wiki desliga os modos
    del dd1["data"][idc["Bastionbreaker"]]
    w1["Bastionbreaker"]["modes"] = {k: False for k in w1["Bastionbreaker"]["modes"]}
    c, it, conf = roda(w1, dd1, m1)
    casos["saiu do jogo"] = "bastionbreaker" not in it and "Data Dragon" in conf.get(("bastionbreaker", "item"), "")
    w1, dd1, m1 = novo()                    # só a wiki desliga os modos
    w1["Hextech Gunblade"]["modes"] = {k: False for k in w1["Hextech Gunblade"]["modes"]}
    c, it, conf = roda(w1, dd1, m1)
    casos["sem modos"] = "hextech-gunblade" not in it and "modos" in conf.get(("hextech-gunblade", "item"), "")
    w1, dd1, m1 = novo()                    # "=>" sem destino: a wiki renomeia a Manamune; a Muramana aponta para ela
    w1["Manamune (nova)"] = w1.pop("Manamune")
    c, it, conf = roda(w1, dd1, m1)
    casos["=> sem destino"] = "muramana" not in it and "sem destino" in conf.get(("muramana", "item"), "")
    w1, dd1, m1 = novo()                    # a Espada Longa deixa de ser comprável: as duas fontes perdem o preço
    del w1["Long Sword"]["buy"]; dd1["data"][idc["Long Sword"]]["gold"]["purchasable"] = False
    c, it, conf = roda(w1, dd1, m1)
    casos["preço que some"] = "long-sword" not in it and "não tem mais" in conf.get(("long-sword", "preço"), "") and not it
    w1, dd1, m1 = novo()                    # receita esvaziada nas duas fontes: é do Capítulo 1
    w1["Tiamat"]["recipe"] = []; dd1["data"][idc["Tiamat"]]["from"] = []
    c, it, conf = roda(w1, dd1, m1)
    casos["receita"] = "tiamat" not in it and "Capítulo 1" in conf.get(("tiamat", "receita"), "")
    w1, dd1, m1 = novo()                    # item não comprável: a wiki passa a dar preço
    nome_slm = next(i.get("wikiName") or i["nameEn"] for i in cat["items"] if i["slug"] == "slightly-magical-footwear")
    w1[nome_slm]["buy"] = 300
    c, it, conf = roda(w1, dd1, m1)
    casos["não comprável"] = "slightly-magical-footwear" not in it and "não se compra" in conf.get(("slightly-magical-footwear", "preço"), "")
    w1, dd1, m1 = novo()                    # o nome em português muda: o texto do Capítulo 1 cita nomes
    dd1["data"][idc["Whispering Circlet"]]["name"] = "Diadema Sussurrante"
    c, it, conf = roda(w1, dd1, m1)
    casos["nome"] = "whispering-circlet" not in it and "Limitado a 1" in conf.get(("whispering-circlet", "nome"), "")
    w1, dd1, m1 = novo()                    # atributo que o robô não lê: não vira "a fonte não tem"
    w1["Doran's Shield"]["stats"]["hpregen"] = w1["Doran's Shield"]["stats"].pop("hp5flat")
    c, it, conf = roda(w1, dd1, m1)
    casos["atributo ilegível"] = "doran-s-shield" not in it and "não lê" in conf.get(("doran-s-shield", "atributos"), "")
    w1, dd1, m1 = novo()                    # o componente sobe, mas o preço do pai fica dividido: o custo de combinação não se refaz
    soma("long-sword", 25, w1, dd1); dd1["data"][idc["Tiamat"]]["gold"]["total"] += 50   # o Data Dragon sobe a Tiamat, a wiki não
    c, it, conf = roda(w1, dd1, m1)
    ti = it.get("tiamat", {})
    casos["pai em aberto"] = "combineCost" not in ti.get("campos", {}) and "combineCost" in ti.get("contaVelha", []) and "divergem" in conf.get(("tiamat", "preço"), "")
    w1, dd1, m1 = novo()                    # o componente sobe e o pai não sobe em fonte nenhuma: a conta não fecha com o "base"
    soma("long-sword", 25, w1, dd1)
    c, it, conf = roda(w1, dd1, m1)
    ti = it.get("tiamat", {})
    casos["base do Data Dragon"] = "combineCost" not in ti.get("campos", {}) and "Data Dragon diz" in conf.get(("tiamat", "custo de combinação"), "")
    w1, dd1, m1 = novo()                    # a Manamune sobe; a Muramana (transformação, sem compra, preço "=>Manamune") fica
    soma("manamune", 100, w1, dd1)          # com o preço em aberto — e sem o Data Dragon para conferir (o catálogo dá 0 de combinação)
    c, it, conf = roda(w1, dd1, m1)
    mu = it.get("muramana", {})
    casos["transformação"] = "combineCost" not in mu.get("campos", {}) and "combineCost" in mu.get("contaVelha", []) and "não se compra" in conf.get(("muramana", "preço"), "")
    # 2ª rodada da revisão (24/10/2026)
    w1, dd1, m1 = novo()                    # item inteiro na conferência não ganha conta: a Espada Longa sobe e a Tiamat some do Data Dragon
    soma("long-sword", 25, w1, dd1); del dd1["data"][idc["Tiamat"]]
    c, it, conf = roda(w1, dd1, m1)
    casos["inteiro sem conta"] = "combineCost" not in it.get("tiamat", {}).get("campos", {}) and "components" not in it.get("tiamat", {}).get("campos", {}) and ("tiamat", "item") in conf
    casos["valor em ouro velho"] = (c.get("statPricesVelhos") == ["Espada Longa"] and {"costAnalysis", "itemClass"} <= set(it.get("infinity-edge", {}).get("contaVelha", []))
                                     and "costAnalysis" in it.get("elixir-of-iron", {}).get("contaVelha", []))   # 3ª rodada: o Elixir não tem atributo, mas a conta é pelo valor em ouro
    w1, dd1, m1 = novo()                    # preço com nota do Capítulo 1 ("gratuito", "valor de venda…"): a conferir
    gr = next(i for i in cat["items"] if "gratuito" in (i.get("priceNote") or "") and isinstance(w0.get(i.get("wikiName") or i["nameEn"], {}).get("buy"), int))
    soma(gr["slug"], 75, w1, dd1)
    c, it, conf = roda(w1, dd1, m1)
    casos["nota no preço"] = "priceGold" not in it.get(gr["slug"], {}).get("campos", {}) and "nota no preço" in conf.get((gr["slug"], "preço"), "")
    w1, dd1, m1 = novo()                    # a wiki renomeia a chave de modo em todo item: ninguém "sai da Summoner's Rift"
    for v in w1.values():
        if isinstance(v.get("modes"), dict) and "classic sr 5v5" in v["modes"]:
            v["modes"]["classic sr"] = v["modes"].pop("classic sr 5v5")
    c, it, conf = roda(w1, dd1, m1)
    casos["chave de modo"] = not any("gameModes" in e["campos"] for e in it.values()) and sum(1 for (_, campo), x in conf.items() if campo == "modos" and "chaves" in x) > 100
    w1, dd1, m1 = novo()                    # dia de patch: um número no meio da edição (Letalidade 18 → 1038)
    w1["Bastionbreaker"]["stats"]["lethality"] = 1038
    c, it, conf = roda(w1, dd1, m1)
    casos["salto"] = "bastionbreaker" not in it and "salto" in conf.get(("bastionbreaker", "Letalidade"), "")
    # a foto do patch novo, tirada meia hora depois de uma edição. 3ª rodada: a revisão velha
    # (editada antes de o Data Dragon trocar o patch) não basta — conta também a 1ª foto do patch.
    # 4ª rodada: a idade conta até a última leitura que VIU a revisão, não até agora
    # (datas de janeiro: longe de "agora", a conta que medisse até agora seria pega)
    m = {"patch": "16.22.1", "lido_em": "2026-01-14T10:30:00Z", "primeira_foto": "2026-01-14T10:30:00Z",
         "wiki": {"revid": 5, "sha256": "x", "revisao_de": "2026-01-14T10:00:00Z"}}
    m_antiga = dict(m, wiki=dict(m["wiki"], revisao_de="2026-01-10T10:00:00Z"))
    # 5ª rodada: a leitura casa com a foto pelo conteúdo (sha256), e a idade conta da revisão que ela viu
    visto = lambda em, sha="x", rev_de=None: dict({"patch": "16.22.1", "revid": 6, "sha256": sha, "em": em}, **({"revisao_de": rev_de} if rev_de else {}))
    casos["wiki assentada"] = (not ap.assentada(m) and not ap.assentada(m, visto("2026-01-14T20:00:00Z")) and ap.assentada(m, visto("2026-01-15T11:00:00Z"))
                               and not ap.assentada(m, visto("2026-01-17T11:00:00Z", sha="y"))      # a leitura viu outro texto: a foto não envelhece sozinha
                               and not ap.assentada(m, visto("2026-01-16T11:00:00Z", rev_de="2026-01-15T12:00:00Z"))   # o mesmo texto numa revisão nova (desfeita): conta dela
                               and ap.assentada(m, visto("2026-01-16T13:00:00Z", rev_de="2026-01-15T12:00:00Z"))
                               and not ap.assentada(m_antiga, visto("2026-01-14T20:00:00Z")) and ap.assentada(m_antiga, visto("2026-01-15T11:00:00Z"))
                               and not ap.assentada({"wiki": {}}))
    # 3ª rodada: o zero é o salto maior; o atributo que entra tem teto; o item com salto espera inteiro
    w1, dd1, m1 = novo()
    w1["Bastionbreaker"]["stats"]["lethality"] = 0
    c, it, conf = roda(w1, dd1, m1)
    zero_attr = "bastionbreaker" not in it and "salto" in conf.get(("bastionbreaker", "Letalidade"), "")
    w1, dd1, m1 = novo()
    dd1["data"][idc["Redemption"]]["gold"]["total"] = 0
    c, it, conf = roda(w1, dd1, m1)
    zero_preco = "priceGold" not in it.get("redemption", {}).get("campos", {}) and "salto" in conf.get(("redemption", "preço"), "")
    casos["zero"] = zero_attr and zero_preco
    w1, dd1, m1 = novo()
    w1["Bastionbreaker"]["stats"]["hp"] = 1038
    c, it, conf = roda(w1, dd1, m1)
    casos["teto do que entra"] = "bastionbreaker" not in it and "acima do maior" in conf.get(("bastionbreaker", "Vida"), "")
    w1, dd1, m1 = novo()
    w1["Bastionbreaker"]["stats"]["lethality"] = 1038; w1["Bastionbreaker"]["stats"]["ad"] = 60
    c, it, conf = roda(w1, dd1, m1)
    casos["item espera inteiro"] = "bastionbreaker" not in it and "espera inteiro" in conf.get(("bastionbreaker", "item"), "")
    w1, dd1, m1 = novo()                    # 3ª rodada: os modos seguem também os mapas do Data Dragon
    w1["Tiamat"]["modes"]["aram"] = False
    c, it, conf = roda(w1, dd1, m1)
    casos["modos com o Data Dragon"] = "gameModes" not in it.get("tiamat", {}).get("campos", {}) and "divergem" in conf.get(("tiamat", "modos"), "")
    w1, dd1, m1 = novo()                    # 3ª rodada: plano que vira percentual com o mesmo número
    w1["Boots"]["stats"]["ms"] = w1["Boots"]["stats"].pop("msflat")
    c, it, conf = roda(w1, dd1, m1)
    casos["unidade"] = "attributes" not in it.get("boots", {}).get("campos", {}) and "unidade" in conf.get(("boots", "atributos"), "")
    casos["Elixires na conta velha"] = True     # conferido no patch principal, abaixo
    w1, dd1, m1 = novo()                    # o Ápice divide pelo preço: fica marcado como conta do patch anterior
    alvo = next(i for i in cat["items"] if i.get("apexNumeric") and i.get("priceGold") and (i.get("wikiName") or i["nameEn"]) in w0
                and isinstance(w0[i.get("wikiName") or i["nameEn"]].get("buy"), int) and not i.get("components"))
    soma(alvo["slug"], 50, w1, dd1)
    c, it, conf = roda(w1, dd1, m1)
    casos["Ápice"] = "apexNumeric" in it.get(alvo["slug"], {}).get("contaVelha", [])
    p.conta("robô", "o que as três rodadas da revisão acharam não vira \"aplica\": item que sai, sem modos, \"=>\" sem destino, preço que some, receita, não comprável, nome, atributo ilegível, nota no preço, chave de modo, salto (e o zero), teto do que entra, unidade, modos contra o Data Dragon, wiki não assentada; contas velhas marcadas",
            all(casos.values()), "%s" % casos)

    # 4ª rodada da revisão (24/10/2026): cada achado confirmado tem um caso
    rev_cap1 = lf.revisao_do_capitulo1()
    c4 = {}
    def com(mexe):
        w1, dd1, m1 = novo()
        mexe(w1, dd1)
        return roda(w1, dd1, m1)
    def pos(d, k, v):
        d[k] = v
    c, it, conf = com(lambda w, d: pos(w["Bastionbreaker"]["stats"], "hp", 0))
    zero = "bastionbreaker" not in it and "entra com 0" in conf.get(("bastionbreaker", "Vida"), "")
    c, it, conf = com(lambda w, d: pos(w["Bastionbreaker"]["stats"], "hp", -1038))
    negativo = "bastionbreaker" not in it
    c, it, conf = com(lambda w, d: pos(w["Bastionbreaker"]["stats"], "as", 0.45))
    fracao = "bastionbreaker" not in it and "abaixo do menor" in conf.get(("bastionbreaker", "Velocidade de Ataque (percent)"), "")
    c, it, conf = com(lambda w, d: pos(w["Bastionbreaker"]["stats"], "ad", True))
    verdadeiro = "bastionbreaker" not in it and "não lê" in conf.get(("bastionbreaker", "atributos"), "")
    c4["o que entra com 0, negativo, fração ou true"] = zero and negativo and fracao and verdadeiro
    c, it, conf = com(lambda w, d: pos(w["Guardian's Horn"]["stats"], "hp5", w["Guardian's Horn"]["stats"].pop("hp5flat")))
    berrante = "attributes" not in it.get("guardian-s-horn", {}).get("campos", {}) and "unidade" in conf.get(("guardian-s-horn", "atributos"), "")
    c, it, conf = com(lambda w, d: pos(w["Bastionbreaker"]["stats"], "armpen", w["Bastionbreaker"]["stats"].pop("lethality")))
    c4["a unidade pela família (Regeneração, Letalidade)"] = berrante and "bastionbreaker" not in it and "unidade" in conf.get(("bastionbreaker", "atributos"), "")
    def porta_preco(w, d):
        w["Bastionbreaker"]["buy"] *= 10; w["Bastionbreaker"]["stats"]["lethality"] = 15
    c, it, conf = com(porta_preco)
    porta1 = "bastionbreaker" not in it and "espera inteiro" in conf.get(("bastionbreaker", "item"), "")
    def porta_ilegivel(w, d):
        soma("bastionbreaker", 100, w, d); w["Bastionbreaker"]["stats"]["lethality"] = "18?"
    c, it, conf = com(porta_ilegivel)
    c4["o salto por outra porta segura o item"] = porta1 and "bastionbreaker" not in it and "espera inteiro" in conf.get(("bastionbreaker", "item"), "")
    def tiamat_espera(w, d):
        soma("long-sword", 25, w, d); d["data"][idc["Tiamat"]]["gold"]["base"] -= 50; w["Tiamat"]["stats"]["ad"] = 200
    c, it, conf = com(tiamat_espera)
    ti = it.get("tiamat", {})
    c4["o item que espera leva a marca da conta que outro deixou velha"] = (not ti.get("campos") and {"components", "combineCost", "costAnalysis", "itemClass"} <= set(ti.get("contaVelha", []))
                                                                        and "espera inteiro" in conf.get(("tiamat", "item"), "")
                                                                        and "fragments" in it.get("stat-bonus", {}).get("contaVelha", []))
    def sem_nb(w, d):
        for v in w.values():
            if isinstance(v, dict) and isinstance(v.get("modes"), dict):
                v["modes"].pop("nb", None)
        d["data"][idc["Tiamat"]]["maps"]["12"] = False
    c, it, conf = com(sem_nb)
    c4["a chave de modo que o robô não lê não desliga o Data Dragon"] = "gameModes" not in it.get("tiamat", {}).get("campos", {}) and "divergem" in conf.get(("tiamat", "modos"), "")
    def chave_mayhem(w, d):   # chave nova que o robô lê, com os modos iguais: o Data Dragon ainda conta
        w["Tiamat"]["modes"]["mayhem"] = w["Tiamat"]["modes"]["aram"]; d["data"][idc["Tiamat"]]["maps"]["12"] = False
    c, it, conf = com(chave_mayhem)
    c4["a chave nova com os modos iguais ainda olha o Data Dragon"] = "gameModes" not in it.get("tiamat", {}).get("campos", {}) and "chaves" in conf.get(("tiamat", "modos"), "")
    c, it, conf = com(lambda w, d: pos(w["Overlord's Bloodmail"]["stats"], "hp", 600))
    c4["a conta escrita na Mecânica fica marcada"] = "abilities" in it.get("overlord-s-bloodmail", {}).get("contaVelha", [])
    c, it, conf = com(lambda w, d: pos(w["Cull"]["stats"], "spec", "+5 [[health]] [[on-hit]]"))
    c4["o atributo em texto livre (spec)"] = "cull" not in it and "spec" in conf.get(("cull", "atributos"), "")
    def voltam(w, d):
        w["Galeforce"]["modes"]["classic sr 5v5"] = True
        d["data"]["999998"] = {"name": "Lâmina de Teste", "gold": {"base": 3000, "total": 3000, "purchasable": True, "sell": 2100}, "from": [], "maps": {"11": True, "12": False}}
    c, it, conf = com(voltam)
    nv = {x["nome"]: x for x in c["novos"]}
    c4["o item que volta e o que só o Data Dragon traz são novos"] = nv.get("Galeforce", {}).get("volta") is True and nv.get("Lâmina de Teste", {}).get("fonte") == "só o Data Dragon"
    def req_e_tier(w, d):
        w["Elixir of Iron"]["req"] = "[[Experience (champion)|Level 11]] required to purchase."; w["Tiamat"]["tier"] = 3
    c, it, conf = com(req_e_tier)
    c4["a condição (req) e o tier da wiki"] = "condição" in conf.get(("elixir-of-iron", "req"), "") and "tier" in conf.get(("tiamat", "tier"), "")
    c, it, conf = com(lambda w, d: soma("bastionbreaker", 100, w, d))
    bb = it.get("bastionbreaker", {})
    c4["cada campo da camada leva o valor do catálogo de que nasceu"] = (set(bb.get("base", {})) == set(bb.get("campos", {})) and bb["base"].get("priceGold") == por_en["Bastionbreaker"]["priceGold"]
                                                                       and bb["base"].get("cashback") == por_en["Bastionbreaker"].get("cashback"))
    c4["a camada de outro catálogo não vale"] = (ap.camada_ainda_vale({"de": "16.21.1", "catalogo": {"sha256": "x"}}, "16.21.1", "x")
                                                 and not ap.camada_ainda_vale({"de": "16.20.1", "catalogo": {"sha256": "x"}}, "16.21.1", "x")
                                                 and not ap.camada_ainda_vale({"de": "16.21.1", "catalogo": {"sha256": "y"}}, "16.21.1", "x")
                                                 and not ap.camada_ainda_vale({"de": "16.21.1"}, "16.21.1", "x") and not ap.camada_ainda_vale(None, "16.21.1", "x"))
    import tempfile
    md = open(lf.CATALOGO_MD, encoding="utf-8").read()
    with tempfile.TemporaryDirectory() as tmp:
        def rev_com(paragrafo):
            caminho = os.path.join(tmp, "cat.md")
            open(caminho, "w", encoding="utf-8").write(md + "\n\n" + paragrafo + "\n")
            return lf.revisao_do_capitulo1(caminho, patch=cat["meta"]["patch"])
        ajuste = rev_com("# Ajustes — correção de 25/10/2026 (fora de patch)\n\nO catálogo continua em %s. Fontes: `Module:ItemData/data` (revisão 4095000)." % cat["meta"]["patch"])
    c4["a revisão da base é a da reconciliação do patch do catálogo"] = ajuste == rev_cap1 and lf.revisao_do_capitulo1(patch="16.20.1") not in (None, rev_cap1)
    nomes = [i.get("wikiName") or i["nameEn"] for i in cat["items"]]
    lua_ok = "return {\n" + "".join('  ["%s"] = { },\n' % n for n in nomes) + "}\n"
    pg = {"title": "Module:ItemData/data"}
    c4["a base que não é o módulo não vira base"] = (lf.base_confere(pg, {n: {} for n in nomes}, lua_ok, cat) == ""
                                                     and "página" in lf.base_confere({"title": "Bastionbreaker"}, {n: {} for n in nomes}, lua_ok, cat)
                                                     and "casa só" in lf.base_confere(pg, {"Outro": {}}, 'return {\n  ["Outro"] = { },\n}', cat)
                                                     and "metade" in lf.base_confere(pg, {nomes[0]: {}}, lua_ok, cat))
    # 5ª rodada da revisão (24/10/2026): cada achado confirmado tem um caso
    c5 = {}
    c, it, conf = com(lambda w, d: pos(w["Bastionbreaker"]["stats"], "ad", 155))
    longe = "bastionbreaker" not in it and "bem acima" in conf.get(("bastionbreaker", "Dano de Ataque"), "")
    c, it, conf = com(lambda w, d: pos(w["Bloodthirster"]["stats"], "ad", 85))    # o maior do catálogo ganha 5: passa
    c5["o atributo que muda para longe da faixa (55 → 155)"] = longe and "attributes" in it.get("bloodthirster", {}).get("campos", {})
    def redencao(w, d):
        d["data"][idc["Redemption"]]["gold"]["total"] += 50; d["data"][idc["Redemption"]]["gold"]["base"] += 50
    c, it, conf = com(redencao)
    # a Redenção não é referência do valor em ouro: a marca da análise de custo vem do preço dela
    nota_rd = ({"notes", "costAnalysis"} <= set(it.get("redemption", {}).get("contaVelha", [])) and not c.get("statPricesVelhos")
               and "redemption" not in ap.referencias_de_preco(cat))
    c, it, conf = com(lambda w, d: soma("cull", 25, w, d))
    c5["o preço aplicado marca o texto que faz conta com ele"] = nota_rd and "apex" in it.get("cull", {}).get("contaVelha", [])
    c, it, conf = com(lambda w, d: pos(w["Hubris"]["stats"], "ad", 60))
    hub = "apex" in it.get("hubris", {}).get("contaVelha", [])
    c, it, conf = com(lambda w, d: pos(w["Atma's Reckoning"]["stats"], "hp", 750))
    c5["o número antigo citado sem \"de\" e o \"do próprio item\""] = hub and "abilities" in it.get("atma-s-reckoning", {}).get("contaVelha", [])
    def anjo(w, d):
        w["Guardian Angel"]["modes"]["aram"] = True; d["data"][idc["Guardian Angel"]]["maps"]["12"] = True
    c, it, conf = com(anjo)
    ga = it.get("guardian-angel", {})
    c5["o modo aplicado marca a nota de ARAM"] = "gameModes" in ga.get("campos", {}) and "aramNotes" in ga.get("contaVelha", [])
    c, it, conf = com(lambda w, d: soma("long-sword", 25, w, d))
    c5["o valor em ouro velho marca a conta de ouro no texto"] = "abilities" in it.get("stat-bonus", {}).get("contaVelha", []) and "notes" in it.get("redemption", {}).get("contaVelha", [])
    def variante(w, d):
        d["data"]["221001"] = {"name": "Botas", "gold": {"base": 300, "total": 300, "purchasable": True, "sell": 210}, "from": [], "maps": {"11": False, "12": True}}
        d["data"]["999998"] = {"name": "Lâmina de Teste", "gold": {"base": 3000, "total": 3000, "purchasable": True, "sell": 2100}, "from": [], "maps": {"11": True, "12": False}}
    c, it, conf = com(variante)
    nv = [x["nome"] for x in c["novos"]]
    c5["a variante de um item do catálogo não é item novo"] = "Botas" not in nv and "Lâmina de Teste" in nv
    c5["o catálogo pelo conteúdo (CRLF = LF)"] = ap.sha_do_texto(b"a\r\nb\r\n") == ap.sha_do_texto(b"a\nb\n") and ap.sha_do_texto(b"a\nb\n") != ap.sha_do_texto(b"a\nc\n")
    with tempfile.TemporaryDirectory() as tmp:
        def rev_em(texto_md):
            caminho = os.path.join(tmp, "cat.md")
            open(caminho, "w", encoding="utf-8", newline="\r\n").write(texto_md)    # em CRLF, como no disco do Leo
            return lf.revisao_do_capitulo1(caminho, patch=cat["meta"]["patch"])
        P = cat["meta"]["patch"]
        sessao = rev_em(md + "\n\n# Ajustes — sessão de correção de 25/10/2026\n\nOrigem: pendências. Patch conferido no início da sessão: `versions.json` = %s (inalterado). Fontes: `Module:ItemData/data` (revisão 4095000).\n" % P)
        cab = md.index("# Ajustes — reconciliação do patch %s" % P)
        fim = md.index("\n", cab)
        dentro = rev_em(md[:fim] + "\n\nFontes à parte: `Module:ItemData/data` (revisão 4095000).\n" + md[fim:])
        refeita = rev_em(md + "\n\n# Ajustes — reconciliação do patch %s (refeita em 26/10/2026)\n\nFontes: `Module:ItemData/data` (revisão 4095000).\n" % P)
    c5["a revisão vem da seção da reconciliação do patch (não do Ajuste de sessão)"] = sessao == rev_cap1 and dentro is None and refeita == 4095000
    # cada porta da marca de texto, isolada: uma nota escrita de propósito numa cópia do catálogo
    def nota(slug, texto, mexe):
        cat2 = copy.deepcopy(cat)
        alvo = next(i for i in cat2["items"] if i["slug"] == slug)
        alvo["notes"] = texto; alvo["apex"] = None; alvo["abilities"] = []
        w1, dd1, m1 = novo()
        mexe(w1, dd1)
        return "notes" in ap.regra(cat2, (w0, dd0, m0), (w1, dd1, m1))["itens"].get(slug, {}).get("contaVelha", [])
    bb = por_en["Bastionbreaker"]
    reemb_velho = ap.fmt_num(bb["cashback"]["refundGold"])
    # "de ouro", e não "g": a Adaga Serrilhada e a Espada Longa são referência do valor em ouro, e
    # a marca de toda conta de ouro ("1.000g") esconderia a porta que o caso quer ver
    portas = {
        "combinação": nota("bastionbreaker", "Combinação de %s de ouro." % ap.fmt_num(bb["combineCost"]), lambda w, d: soma("bastionbreaker", 100, w, d)),
        "Reembolso": nota("bastionbreaker", "Reembolso de %s de ouro." % reemb_velho, lambda w, d: soma("bastionbreaker", 100, w, d)),
        "componente": nota("bastionbreaker", "a Adaga Serrilhada a %s de ouro." % ap.fmt_num(por_en["Serrated Dirk"]["priceGold"]), lambda w, d: soma("serrated-dirk", 50, w, d)),
        "componente do que espera": nota("tiamat", "Espada Longa a %s de ouro, duas vezes." % ap.fmt_num(por_en["Long Sword"]["priceGold"]),
                                         lambda w, d: (soma("long-sword", 25, w, d), pos(w["Tiamat"]["stats"], "ad", 200))),
        "o atributo e o \"do próprio item\"": nota("overlord-s-bloodmail", "Tirania cresce com a Vida do próprio item.", lambda w, d: pos(w["Overlord's Bloodmail"]["stats"], "hp", 600)),
        "controle: nota que não cita nada": not nota("bastionbreaker", "Sem número aqui.", lambda w, d: soma("bastionbreaker", 100, w, d)),
    }
    c5["o texto que cita a combinação, o Reembolso e o componente fica marcado"] = all(portas.values())
    p.conta("robô", "o que a 4ª rodada achou não vira \"aplica\": o que entra com 0/negativo/fração/true, a unidade pela família, o salto por outra porta, a conta que outro item deixa velha (componente, fragmentos, Mecânica), a chave de modo que o robô não lê, o spec, req e tier; os novos que voltam; a camada presa ao catálogo; a base ligada ao patch",
            all(c4.values()), "%s" % ([k for k, v in c4.items() if not v] or "todos"))
    p.conta("robô", "o que a 5ª rodada achou não vira \"aplica\": o atributo que muda para longe da faixa; o texto que faz conta com o preço, o atributo, o modo e o valor em ouro fica marcado; a variante não é item novo; o catálogo pelo conteúdo; a revisão da seção da reconciliação; a espera pelo conteúdo",
            all(c5.values()), "%s · portas da marca de texto %s" % ([k for k, v in c5.items() if not v] or "todos", [k for k, v in portas.items() if not v] or "todas"))

    # O teste com dado real (24/10/2026): a regra do catálogo 16.20.1 (o do commit da
    # reconciliação, lido do git) e da foto do 16.20.1 (a revisão que o Capítulo 1 registrou)
    # para a foto do 16.21.1 — contra o que o Capítulo 1 de fato pôs no catálogo 16.21.1. Todo
    # valor aplicado tem de ser o dele, e toda mudança de dado dele tem de estar aplicada,
    # marcada ou com o item a conferir (a data citada num texto, "pt_BR 16.20.1", não é dado)
    import subprocess
    bruto = subprocess.run(["git", "-C", RAIZ, "show", "3c9c754:data/catalog.js"], capture_output=True).stdout.decode("utf-8")
    velho = json.loads(bruto[bruto.index("{"): bruto.rindex("}") + 1]) if bruto else None
    if velho is None or not os.path.isdir(os.path.join(RAIZ, "data", "robo", "fonte", "16.20.1")):
        p.conta("robô", "o teste com dado real (16.20.1 → 16.21.1)", False, "sem o catálogo 16.20.1 no git ou sem a foto do 16.20.1")
    else:
        hist = ap.regra(velho, lf.ler_foto("16.20.1"), lf.ler_foto(cat["meta"]["patch"]))
        V, N_ = {i["slug"]: i for i in velho["items"]}, {i["slug"]: i for i in cat["items"]}
        attrs = lambda l: sorted((a.get("stat"), a.get("unit"), a.get("value")) for a in (l or []) if isinstance(a, dict))
        def igual(campo, x, y):
            if campo == "attributes":
                return attrs(x) == attrs(y)
            if campo == "components":
                return sorted((c.get("nameEn"), c.get("priceGold"), c.get("qty")) for c in x or []) == sorted((c.get("nameEn"), c.get("priceGold"), c.get("qty")) for c in y or [])
            if campo == "cashback":
                return (x or {}).get("refundGold") == (y or {}).get("refundGold") and (x or {}).get("netGold") == (y or {}).get("netGold")
            return x == y
        aplicados = [(s, k) for s, e in hist["itens"].items() for k in e["campos"]]
        errados = [(s, k) for s, k in aplicados if not igual(k, hist["itens"][s]["campos"][k], N_.get(s, {}).get(k))]
        a_conferir = {x["slug"] for x in hist["aConferir"]}
        sem_data = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True).replace("16.20.1", "16.21.1")
        silencio = []
        for s, n in N_.items():
            v = V.get(s)
            e = hist["itens"].get(s, {"campos": {}, "contaVelha": []})
            for k in ("priceGold", "attributes", "gameModes", "combineCost", "components", "cashback", "abilities", "apex", "apexNumeric",
                      "notes", "aramNotes", "mayhemNotes", "costAnalysis", "itemClass", "masterwork", "attributeCategory", "condition", "tier", "fragments"):
                if v is None or igual(k, v.get(k), n.get(k)) or sem_data(v.get(k)) == sem_data(n.get(k)):
                    continue
                if k not in e["campos"] and k not in e["contaVelha"] and s not in a_conferir:
                    silencio.append((s, k))
        p.conta("robô", "o teste com dado real: do 16.20.1 ao 16.21.1, o que o robô aplicaria é o que o Capítulo 1 fez, e toda mudança dele está aplicada, marcada ou a conferir",
                bool(aplicados) and not errados and not silencio,
                "%d campos aplicados, %d errados %s · %d itens a conferir · em silêncio %s" % (len(aplicados), len(errados), errados[:5], len(a_conferir), silencio[:8] or "nada"))

    # F13-T78: o robô roda todo dia no GitHub Actions; a camada igual não se regrava (sem commit só
    # de data), e o serviço tem o que precisa (os dois passos, a escrita, o aviso)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        cam = os.path.join(tmp, "camada.js")
        vazia = {"itens": {}, "aConferir": [], "novos": []}
        ap.escrever_camada(vazia, cat["meta"]["patch"], cat["meta"]["patch"], m0, m0, caminho=cam)
        velho = open(cam, encoding="utf-8").read()
        antigo = re.sub(r'"gerado": "[^"]*"', '"gerado": "2026-01-01T00:00:00Z"', velho)
        open(cam, "w", encoding="utf-8", newline="\n").write(antigo)
        ap.escrever_camada(vazia, cat["meta"]["patch"], cat["meta"]["patch"], m0, m0, caminho=cam)
        ficou = open(cam, encoding="utf-8").read() == antigo
        ap.escrever_camada({"itens": {}, "aConferir": [{"slug": "x", "item": "X", "campo": "preço", "porque": "teste"}], "novos": []},
                           cat["meta"]["patch"], "16.22.1", m0, m0, caminho=cam)
        mudou = '"gerado": "2026-01-01T00:00:00Z"' not in open(cam, encoding="utf-8").read()
    wf = os.path.join(RAIZ, ".github", "workflows", "robo.yml")
    yml = open(wf, encoding="utf-8").read() if os.path.exists(wf) else ""
    tem = [x for x in ("cron:", "workflow_dispatch", "contents: write", "issues: write", "python -I data/robo/ler_fonte.py",
                       "python -I data/robo/aplicar_patch.py", "git add -A data/robo data/atualizacao_patch.js", "gh issue create") if x not in yml]
    p.conta("robô", "no GitHub Actions todo dia: a camada igual não se regrava (sem commit só de data), a que mudou sim; o serviço lê, aplica, grava e avisa",
            ficou and mudou and not tem, "igual ficou %s · mudada regravou %s · falta no robo.yml %s" % (ficou, mudou, tem or "nada"))

    # a camada do repositório: a do patch do catálogo, vazia — e um JS que se lê
    txt = open(os.path.join(RAIZ, "data", "atualizacao_patch.js"), encoding="utf-8").read()
    corpo = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
    p.conta("robô", "a camada do repositório é do patch do catálogo (sem nada a aplicar enquanto não há patch novo)",
            corpo["de"] == cat["meta"]["patch"] and (corpo["para"] != corpo["de"] or (not corpo["itens"] and not corpo["aConferir"])),
            "de %s para %s · %d itens · %d a conferir" % (corpo["de"], corpo["para"], len(corpo["itens"]), len(corpo["aConferir"])))

def checar_cadeado_ajustes(s, p):
    """F13-T76 (Leo, 24/10/2026): com a rota Suporte, os outros itens iniciais ficam trancados
    (o Atlas Mundial já vem comprado); a Opcional e a Escolha 1 ficam fora do cadeado — escolhida
    a caixa, os cadeados somem; sem o Editar, nada de cadeado na loja, e toda tentativa de mexer
    na build avisa e faz o Editar pulsar (três pulsos; com menos movimento, só o brilho)."""
    print("\n%sCADEADO: OS AJUSTES%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("""(() => { if (rascunho.sujo) descartarAlteracoes(); ligarEdicao(true);
      const por = (n) => CATALOG.items.find(i => i.namePt === n).slug;
      build.mode = "Summoner's Rift"; build.rota = 'suporte'; build.runas = normRunas(null);
      while (build.cats.length < 3) build.cats.push({ id: 'cat-qa-' + build.cats.length + '-' + Date.now(), name: 'Caixa', desc: '', kind: 'comum', span: 2, cols: 3, rows: 0, items: [] });
      build.cats = build.cats.slice(0, 3);
      ['comum', 'opcional', 'escolha'].forEach((k, i) => { build.cats[i].kind = k; build.cats[i].items = []; });
      build.cats[0].items = [{ itemId: por('Hidra Raivosa'), note: '' }];
      build.cats[2].items = [{ itemId: por('Hidra Titânica'), note: '' }];
      build.selectedCatId = build.cats[0].id; switchTab('catalog'); renderBuildAll(); window.__por = por; return 'ok'; })()""")
    time.sleep(0.8)
    def card(slug):
        return s.js("(() => { const c = document.querySelector('#grid .card[data-slug=\"%s\"]'); return c ? { trancado: c.classList.contains('trancado'), motivo: c.dataset.cadeado || '' } : null; })()" % slug)
    def caixa(i):   # escolhe a caixa como o jogador: o seletor "Marcar em" da loja
        s.js("(() => { const sel = document.getElementById('catalog-cat-select'); sel.value = build.cats[%d].id; sel.dispatchEvent(new Event('change')); return 1; })()" % i)
        time.sleep(0.3)
    doran, atlas, cancao = card("doran-s-blade"), card("world-atlas"), card("bloodsong")
    s.js("(() => { build.rota = 'top'; renderBuildAll(); return 1; })()"); time.sleep(0.3)
    doran_top = card("doran-s-blade")
    s.js("(() => { build.rota = 'suporte'; renderBuildAll(); return 1; })()"); time.sleep(0.3)
    p.conta("cadeado: ajustes", "com a rota Suporte, os outros itens iniciais ficam trancados (o Atlas Mundial já vem comprado); o Atlas e a linha dele, não; com a Top, a Lâmina de Doran volta",
            bool(doran) and doran["trancado"] and "Atlas Mundial já vem comprado" in doran["motivo"] and atlas and not atlas["trancado"]
            and cancao and not cancao["trancado"] and doran_top and not doran_top["trancado"],
            "Doran %s · Atlas %s · Canção %s · Doran na Top %s" % (doran, atlas, cancao, doran_top))

    # uma Hidra do mesmo grupo que não está na build (o card de item que já está na build não leva cadeado)
    outra = s.js("""(() => { const na = new Set(build.cats.flatMap(c => c.items.map(e => e.itemId)));
      const tier = byId[__por('Hidra Raivosa')].tier;   // do mesmo tier: a Tiamat (Épico) é do grupo, mas não tranca a Lendária
      return Object.entries(travas().grupos).find(([slug, g]) => g.includes('Hidra') && !na.has(slug) && byId[slug].tier === tier)[0]; })()""")
    caixa(0); comum = {"doran": card("doran-s-blade"), "hidra": card(outra)}
    caixa(1); opcional = {"doran": card("doran-s-blade"), "hidra": card(outra)}
    caixa(2); escolha = {"doran": card("doran-s-blade"), "hidra": card(outra)}
    s.js("(() => { switchTab('build'); showBuildScreen('forja'); renderBuildAll(); return 1; })()"); time.sleep(0.6)
    tile = s.js("(() => { const c = build.cats[2]; const t = document.querySelector('.item-tile[data-cat-id=\"' + c.id + '\"][data-index=\"0\"]'); return t ? t.classList.contains('trancado') : null; })()")
    p.conta("cadeado: ajustes", "a Opcional e a Escolha 1 são a exceção: escolhida a caixa, os cadeados da loja somem; na Escolha 1 a segunda Hidra não ganha cadeado",
            comum["doran"]["trancado"] and comum["hidra"]["trancado"] and not opcional["doran"]["trancado"] and not opcional["hidra"]["trancado"]
            and not escolha["doran"]["trancado"] and not escolha["hidra"]["trancado"] and tile is False,
            "Comum %s · Opcional %s · Escolha 1 %s · cadeado no ladrilho da Escolha 1 %s" % (comum, opcional, escolha, tile))

    # sem o Editar: nada de cadeado na loja; o clique no item não mexe e avisa, com o Editar pulsando
    s.js("(() => { ligarEdicao(false); switchTab('catalog'); renderBuildAll(); return 1; })()"); time.sleep(0.6)
    trancados = s.js("document.querySelectorAll('#grid .card.trancado, #grid .card.nao-soma').length")
    antes = s.js("JSON.stringify(build.cats.map(c => c.items.map(e => e.itemId)))")
    s.clicar('#grid .card[data-slug="doran-s-blade"] .card-name', 0.5)
    depois = s.js("JSON.stringify(build.cats.map(c => c.items.map(e => e.itemId)))")
    loja = s.js("""(() => { const h = document.getElementById('catalog-mode-hint'), b = h.querySelector('[data-ligar-editar]');
      return { aviso: h.classList.contains('show') ? h.textContent : '', pulsa: !!(b && b.classList.contains('chamar')), voltas: b ? getComputedStyle(b).animationIterationCount : null }; })()""")
    s.clicar('#catalog-mode-hint [data-ligar-editar]', 0.5)
    ligou = s.js("build.editing")
    p.conta("cadeado: ajustes", "sem o Editar, a loja não mostra cadeado e o clique no item não mexe na build: avisa, o Editar pulsa (três vezes) e o \"Ligar Editar\" do aviso liga",
            trancados == 0 and antes == depois and "ligue o Editar" in loja["aviso"] and loja["pulsa"] and loja["voltas"] == "3" and ligou is True,
            "cadeados na loja %s · build igual %s · %s · ligou %s" % (trancados, antes == depois, loja, ligou))

    # a forja: o toque no campo que o modo leitura desliga (o modo de jogo, disabled) avisa; nas Runas também
    s.js("(() => { ligarEdicao(false); switchTab('build'); showBuildScreen('forja'); renderBuildAll(); document.getElementById('edit-hint').classList.remove('show'); return 1; })()"); time.sleep(0.6)
    s.clicar("#build-mode", 0.4)
    forja = s.js("""(() => ({ aviso: document.getElementById('edit-hint').classList.contains('show') ? document.getElementById('edit-hint').textContent : '',
      pulsa: document.getElementById('edit-switch').classList.contains('chamar'), modo: build.mode }))()""")
    s.js("(() => { document.getElementById('edit-hint').classList.remove('show'); runasEstado.modo = 'montar'; switchTab('runas'); return 1; })()"); time.sleep(0.8)
    # montando a página da build sem o Editar, trocar a trilha primária é a tentativa de mexer
    outra_trilha = s.js("(() => { const b = [...document.querySelectorAll('.trilha-btn[data-trilha]')].find(x => !x.classList.contains('ativa')); return b ? b.dataset.trilha : null; })()")
    tem_runa = bool(outra_trilha)
    if tem_runa:
        s.clicar('.trilha-btn[data-trilha="%s"]' % outra_trilha, 0.4)
    runas = s.js("""(() => ({ aviso: document.getElementById('edit-hint').classList.contains('show'),
      pulsa: !!(document.getElementById('rd-ligar') && document.getElementById('rd-ligar').classList.contains('chamar')) }))()""")
    s.js("(() => { document.body.classList.add('ac-movimento'); switchTab('build'); showBuildScreen('forja'); chamarEditar(); return 1; })()"); time.sleep(0.3)
    parado = s.js("(() => { const e = getComputedStyle(document.getElementById('edit-switch')); return { animacao: e.animationName, brilho: e.boxShadow !== 'none' }; })()")
    s.js("(() => { document.body.classList.remove('ac-movimento'); return 1; })()")
    p.conta("cadeado: ajustes", "sem o Editar, tocar no modo de jogo (desligado) avisa e faz o Editar pulsar; nas Runas, trocar a trilha avisa e o \"Ligar Editar\" de lá pulsa; com menos movimento, o brilho fica parado",
            "ligue o Editar" in forja["aviso"] and forja["pulsa"] and tem_runa and runas["aviso"] and runas["pulsa"]
            and parado["animacao"] == "none" and parado["brilho"],
            "forja %s · runas %s (runa na tela %s) · menos movimento %s" % (forja, runas, tem_runa, parado))
    s.js("(() => { ligarEdicao(true); switchTab('build'); return 1; })()")


def checar_camada_robo(s, p):
    """F13-T77: o app lê a camada do robô (data/atualizacao_patch.js) por cima do catálogo — só
    a do patch do catálogo, e item a item só se o catálogo ainda disser o "base" de cada campo.
    Numa aba própria, a camada de um patch simulado entra pelo caminho de verdade (a página carrega
    o arquivo; o roteiro só troca o que ele diz): o preço e o atributo aplicados, o selo no card,
    o bloco na ficha, o aviso no alto da loja; o item cujo catálogo mudou fica como o catálogo diz."""
    print("\n%sCAMADA DO ROBÔ%s" % (AMARELO, FIM))
    import importlib, copy
    pasta = os.path.join(RAIZ, "data", "robo")
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    lf = importlib.import_module("ler_fonte")
    ap = importlib.import_module("aplicar_patch")
    cat = lf.ler_catalogo()
    patch = cat["meta"]["patch"]
    w0, dd0, m0 = lf.ler_foto(patch)
    w1, dd1, m1 = copy.deepcopy(w0), copy.deepcopy(dd0), copy.deepcopy(m0)
    idc = {i["nameEn"]: str(i["id"]).split(" ")[0] for i in cat["items"]}
    w1["Bastionbreaker"]["buy"] += 100; dd1["data"][idc["Bastionbreaker"]]["gold"]["total"] += 100; dd1["data"][idc["Bastionbreaker"]]["gold"]["base"] += 100
    w1["Bastionbreaker"]["stats"]["lethality"] = 20
    w1["Bastionbreaker"]["effects"]["pass"]["description"] += " (texto novo)"
    dd1["data"][idc["Redemption"]]["gold"]["total"] += 50; dd1["data"][idc["Redemption"]]["gold"]["base"] += 50
    w1["Abyssal Mask"]["buy"] = 2700
    c = ap.regra(cat, (w0, dd0, m0), (w1, dd1, m1))
    camada = {"de": patch, "para": "16.22.1", "itens": c["itens"], "aConferir": c["aConferir"], "novos": c["novos"], "statPricesVelhos": c.get("statPricesVelhos", [])}
    # o Capítulo 1 mexeu na Redenção depois que a camada nasceu: o "base" não bate e ela fica como o catálogo diz
    camada["itens"]["redemption"]["base"]["priceGold"] = 9999
    preco_bb = next(i for i in cat["items"] if i["slug"] == "bastionbreaker")["priceGold"]
    preco_rd = next(i for i in cat["items"] if i["slug"] == "redemption")["priceGold"]

    # a camada do repositório (vazia, do próprio patch) não liga nada
    vazia = s.js("({ ativo: ROBO.ativo, selos: document.querySelectorAll('.robo-selo').length, aviso: document.getElementById('robo-aviso').hidden })")
    outro = s.js("""(() => { const r = { itens: {}, aConferir: {}, novos: [], statPricesVelhos: [] };
      aplicarCamadaDoRobo(JSON.parse(JSON.stringify(CATALOG)), { de: '16.20.1', para: '16.21.1', itens: { 'bastionbreaker': { campos: { priceGold: 1 }, base: { priceGold: byId['bastionbreaker'].priceGold } } } }, r);
      return { ativo: !!r.ativo, itens: Object.keys(r.itens).length }; })()""")

    r = Sessao(s.url)
    try:
        r.envia("Page.addScriptToEvaluateOnNewDocument", {"source": "(() => { const C = %s; Object.defineProperty(window, 'ATUALIZACAO_PATCH', { configurable: true, get() { return C; }, set(v) {} }); })()" % json.dumps(camada, ensure_ascii=False)})
        r.abrir(); r.tela(1600, 900); r.entrar()
        r.js("(() => { switchTab('catalog'); return 1; })()"); time.sleep(0.8)
        dado = r.js("""(() => { const bb = byId['bastionbreaker'], rd = byId['redemption'];
          const selo = (s) => { const e = document.querySelector('#grid .card[data-slug="' + s + '"] .robo-selo'); return e ? e.className + ':' + e.textContent : ''; };
          return { ativo: ROBO.ativo, bb: bb.priceGold, letal: bb.attributes.filter(a => a.stat === 'Letalidade').map(a => a.value), rd: rd.priceGold,
                   recusou: ROBO.itens.redemption ? ROBO.itens.redemption.recusados : null,
                   selo_bb: selo('bastionbreaker'), selo_am: selo('abyssal-mask'), selo_rd: selo('redemption'),
                   aviso: document.getElementById('robo-aviso').hidden ? '' : document.getElementById('robo-aviso').textContent }; })()""")
        r.js("(() => { openModal('bastionbreaker'); return 1; })()"); time.sleep(0.6)
        ficha = r.js("(() => { const f = document.querySelector('#modal .modal-section.robo'); return f ? f.textContent.replace(/\\s+/g, ' ') : ''; })()")
        # F13-T82: a build com item que o robô viu mudar fica desatualizada (fora das Opcionais), com a borda vermelha
        r.js("(() => { document.getElementById('overlay').classList.remove('show'); return 1; })()")
        garantir_build_editavel(r)
        etiqueta = r.js("""(() => { ligarEdicao(true);
          build.cats = [{ id: 'qa-r1', name: 'Núcleo', desc: '', kind: 'comum', span: 2, cols: 3, rows: 0, items: [{ itemId: 'bastionbreaker', note: '' }, { itemId: 'long-sword', note: '' }] },
                        { id: 'qa-r2', name: 'Talvez', desc: '', kind: 'opcional', span: 2, cols: 3, rows: 0, items: [{ itemId: 'abyssal-mask', note: '' }] }];
          switchTab('build'); showBuildScreen('forja'); renderBuildAll();
          const tile = (s) => { const t = [...document.querySelectorAll('.item-tile')].find(x => build.cats[Number(x.dataset.catId === 'qa-r1' ? 0 : 1)].items[Number(x.dataset.index)].itemId === s); return t ? t.classList.contains('mudou') : null; };
          const html = etiquetaHtml(buildResumo({ id: build.id }));
          return { robo: itensDoRobo(build.cats), borda_bb: tile('bastionbreaker'), borda_ls: tile('long-sword'), borda_am: tile('abyssal-mask'), etiqueta: /desatualizada/.test(html) && /patch 16\\.22\\.1/.test(html) }; })()""")
        erros = list(r.erros)
    finally:
        r.fechar()
    p.conta("camada do robô", "a camada do repositório (do próprio patch) não liga nada, e a de outro patch é ignorada",
            vazia == {"ativo": False, "selos": 0, "aviso": True} and outro == {"ativo": False, "itens": 0}, "repositório %s · outro patch %s" % (vazia, outro))
    p.conta("camada do robô", "a camada do patch do catálogo entra: o preço e a Letalidade aplicados, o selo \"patch 16.22.1\" no card e o \"a conferir\" no que o robô não aplicou; o item que o Capítulo 1 mexeu depois fica como o catálogo diz",
            dado["ativo"] and dado["bb"] == preco_bb + 100 and dado["letal"] == [20] and dado["rd"] == preco_rd and dado["recusou"] and "priceGold" in dado["recusou"]
            and dado["selo_bb"].endswith(":patch 16.22.1") and "conferir" in dado["selo_am"] and dado["selo_rd"] == ""
            and dado["aviso"].startswith("Patch 16.22.1") and not erros, "%s · erros %s" % (dado, erros[:2]))
    p.conta("camada do robô", "na ficha, o bloco do robô diz o que já foi aplicado (de → para, de onde), o que está a conferir e as contas do patch anterior",
            "Patch 16.22.1 · pelo Update Tracker" in ficha and "Já aplicado" in ficha and "%s → %s" % (ap.fmt_num(preco_bb), ap.fmt_num(preco_bb + 100)) in ficha
            and "A conferir" in ficha and "Shaped Charge" in ficha and "Do patch %s" % patch in ficha and "análise de custo" in ficha, ficha[:400])
    p.conta("camada do robô", "a build com item que o robô viu mudar fica desatualizada, com a borda vermelha nele (o da Opcional não conta, o que não mudou também não)",
            etiqueta["robo"] == ["bastionbreaker"] and etiqueta["borda_bb"] is True and etiqueta["borda_ls"] is False and etiqueta["borda_am"] is False and etiqueta["etiqueta"],
            "%s" % etiqueta)


def checar_marcadores_ajuda(s, p):
    """F13-T79 (docs/ux_forja.md, ponto 6: "os marcadores não dizem para que servem"): com o Editar
    ligado e marcador faltando, uma linha ao lado dos espaços diz para que eles servem e quantos
    faltam; com os três, ou sem o Editar, ela não aparece."""
    print("\n%sMARCADORES: A AJUDA%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    def linha(marcadores, editando):
        s.js("(() => { ligarEdicao(%s); build.markers = normMarkers(%s); switchTab('build'); showBuildScreen('forja'); renderBuildAll(); renderMarkSlots(); return 1; })()"
             % ("true" if editando else "false", json.dumps(marcadores)))
        time.sleep(0.3)
        return s.js("(() => { const a = document.querySelector('#build-marks .mark-ajuda'); return a && getComputedStyle(a).display !== 'none' ? a.textContent : ''; })()")
    um = [{"t": "item", "slug": "infinity-edge"}]
    tres = um + [{"t": "item", "slug": "bloodthirster"}, {"t": "item", "slug": "rabadon-s-deathcap"}]
    vazia, com_um, cheia, leitura = linha([], True), linha(um, True), linha(tres, True), linha([], False)
    s.js("(() => { ligarEdicao(true); return 1; })()")
    p.conta("marcadores: ajuda", "com o Editar e marcador faltando, a linha diz para que servem (e quantos faltam); com os três, ou sem o Editar, some",
            "obrigatórios para publicar" in vazia and "faltam 2" in com_um and cheia == "" and leitura == "",
            "vazia %r · com um %r · com três %r · sem o Editar %r" % (vazia, com_um, cheia, leitura))


def checar_notas(s, p):
    """F13-T80: as notas de atualização — o mural da loja (a opção B do Leo, 25/10/2026). O
    data/notas.js em dia com os commits de tarefa (docs/gerar_notas.py) e nenhuma tarefa sem nota;
    o ícone com o número da atualização, aceso enquanto a versão não foi vista; o clique abre o
    mural (Em breve, Apoie o projeto, as notas por data em Adicionado · Ajustado · Removido); o ×,
    o Esc e o clique fora fecham."""
    print("\n%sNOTAS DE ATUALIZAÇÃO%s" % (AMARELO, FIM))
    out = subprocess.run([sys.executable, "-I", os.path.join(RAIZ, "docs", "gerar_notas.py"), "--conferir"], capture_output=True, text=True, encoding="utf-8").stdout.strip()
    p.conta("notas", "o data/notas.js está em dia com os commits de tarefa, e nenhuma tarefa ficou sem nota", out == "em dia · sem nota: nenhuma", out)
    s.js("(() => { try { localStorage.removeItem('notas.vista'); } catch (e) {} refletirNotasBtn(); switchTab('catalog'); window.scrollTo(0, 0); return 1; })()")
    time.sleep(0.3)
    antes = s.js("({ novo: document.getElementById('notas-btn').classList.contains('novo'), num: document.querySelector('#notas-btn .nb-num').textContent, at: ATUALIZACAO })")
    s.clicar("#notas-btn", 0.6)
    aberto = s.js("""(() => { const m = document.getElementById('mural'); const r = m.getBoundingClientRect();
      return { visivel: !m.hidden && r.width > 0, texto: m.textContent.replace(/\\s+/g, ' '), datas: m.querySelectorAll('.bilhete:not(.embreve):not(.apoie)').length,
               expandido: document.getElementById('notas-btn').getAttribute('aria-expanded'), novo: document.getElementById('notas-btn').classList.contains('novo'),
               cabe: r.right <= window.innerWidth + 1 && r.left >= 0 }; })()""")
    s.envia("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    s.envia("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    time.sleep(0.3)
    esc_fecha = s.js("document.getElementById('mural').hidden")
    s.clicar("#notas-btn", 0.6)
    s.clicar("#mural .m-fechar", 0.4)
    x_fecha = s.js("document.getElementById('mural').hidden")
    s.clicar("#notas-btn", 0.6)
    s.envia("Input.dispatchMouseEvent", {"type": "mousePressed", "x": 200, "y": 450, "button": "left", "clickCount": 1})
    s.envia("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": 200, "y": 450, "button": "left", "clickCount": 1})
    time.sleep(0.3)
    fora_fecha = s.js("document.getElementById('mural').hidden")
    p.conta("notas", "o ícone mostra o número da atualização e fica aceso até a versão ser vista; o clique abre o mural com o Em breve, o Apoie o projeto e as notas por data",
            antes["novo"] and antes["num"] == antes["at"] and aberto["visivel"] and aberto["expandido"] == "true" and not aberto["novo"] and aberto["cabe"]
            and "Mural da loja" in aberto["texto"] and "Em breve na loja" in aberto["texto"] and "Nunca pedirei por doações. Me ajude divulgando com seus amigos!" in aberto["texto"]
            and aberto["datas"] >= 1 and ("Adicionado" in aberto["texto"] or "Ajustado" in aberto["texto"]),
            "antes %s · aberto %s" % (antes, {k: (v if k != "texto" else v[:160]) for k, v in aberto.items()}))
    p.conta("notas", "o Esc, o × e o clique fora fecham o mural", esc_fecha and x_fecha and fora_fecha, "Esc %s · × %s · fora %s" % (esc_fecha, x_fecha, fora_fecha))


def checar_enderecos(s, p):
    """F13-T81 (Leo, 22/10/2026: "ao clicar em Builds fica /builds, em Runas /runas"): um endereço
    por tela, pelo #. Com clique de verdade nas abas, o endereço acompanha; o voltar do navegador
    volta de tela; e o link direto (#runas, numa aba nova) abre na tela dele."""
    print("\n%sENDEREÇO POR TELA%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    tela = """(() => ({ hash: location.hash, aba: (document.querySelector('.tab-btn.active') || {}).dataset ? document.querySelector('.tab-btn.active').dataset.tab : null,
      forja: !document.getElementById('build-editor').hidden }))()"""
    # a aba Builds abre na tela em que se estava (a lista ou a forja): começa na lista
    s.js("(() => { showBuildScreen('lista'); switchTab('catalog'); return 1; })()"); time.sleep(0.3)
    passos = {}
    for aba, nome in (("build", "builds"), ("runas", "runas"), ("mapa", "mapa"), ("calc", "calculadora"), ("catalog", "catalogo")):
        s.clicar('.tab-btn[data-tab="%s"]' % aba, 0.5)
        passos[nome] = s.js(tela)["hash"]
    s.clicar('.tab-btn[data-tab="build"]', 0.5)
    s.js("(() => { showBuildScreen('forja'); return 1; })()"); time.sleep(0.3)
    forja = s.js(tela)
    s.js("history.back(); 1"); time.sleep(0.6)
    volta1 = s.js(tela)
    s.js("history.back(); 1"); time.sleep(0.6)
    volta2 = s.js(tela)
    s.js("history.forward(); 1"); time.sleep(0.6)
    avanca = s.js(tela)
    p.conta("endereço por tela", "o endereço acompanha a aba (#builds, #runas, #mapa, #calculadora, #catalogo, #forja); o voltar e o avançar do navegador trocam de tela",
            passos == {"builds": "#builds", "runas": "#runas", "mapa": "#mapa", "calculadora": "#calculadora", "catalogo": "#catalogo"}
            and forja["hash"] == "#forja" and forja["forja"] and volta1["hash"] == "#builds" and volta1["aba"] == "build" and not volta1["forja"]
            and volta2["hash"] == "#catalogo" and volta2["aba"] == "catalog" and avanca["hash"] == "#builds" and avanca["aba"] == "build",
            "abas %s · forja %s · voltar %s, %s · avançar %s" % (passos, forja, volta1, volta2, avanca))
    r = Sessao(s.url)
    try:
        r.abrir("#runas"); r.tela(1600, 900); r.entrar(); time.sleep(0.5)
        direto = r.js(tela)
        r.js("(() => { location.hash = '#calculadora'; return 1; })()"); time.sleep(0.6)   # como quem troca o endereço na barra
        calc = r.js(tela)
        erros = list(r.erros)
    finally:
        r.fechar()
    p.conta("endereço por tela", "o link direto abre na tela dele (#runas numa aba nova; #calculadora trocado na barra de endereço)",
            direto["hash"] == "#runas" and direto["aba"] == "runas" and calc["aba"] == "calc" and not erros, "direto %s · calculadora %s · erros %s" % (direto, calc, erros[:2]))


def checar_autor(s, p):
    """F13-T83: o autor opcional na publicação — um apelido lembrado neste navegador, que vai no
    p_autor. Servidor SIMULADO: o roteiro segura o publicar_build e só lê o que sairia."""
    print("\n%sAUTOR NA PUBLICAÇÃO%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("""(() => { window.__autores = []; window.__fetchOrigA = window.fetch;
      window.fetch = function (u, ...a) { const t = String(u);
        if (t.includes('publicar_build')) { const o = a[0] || {}; try { window.__autores.push(JSON.parse(o.body).p_autor); } catch (e) {}
          return Promise.resolve(new Response(JSON.stringify({ id: 'qa0083', versao: 1 }), { status: 200, headers: { 'Content-Type': 'application/json' } })); }
        if (t.includes('/rpc/') || t.includes('/rest/')) return Promise.resolve(new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }));
        return window.__fetchOrigA.call(this, u, ...a); };
      try { localStorage.removeItem('montador.autor'); } catch (e) {}
      if (rascunho.sujo) descartarAlteracoes();
      build.name = 'Autor de teste'; build.desc = 'descrição'; build.markers = normMarkers(MARCADORES.slice(0, 3).map(m => ({ t: 'tag', id: m.id })));
      if (!build.cats.some(c => c.items.length)) build.cats[0].items.push({ itemId: 'long-sword', note: '' });
      gravarBuild(); switchTab('build'); showBuildScreen('lista'); biSelected = build.id; renderBuildIndex(); return 1; })()""")
    time.sleep(0.6)
    vazio = s.js("document.getElementById('bd-autor') ? document.getElementById('bd-autor').value : null")
    s.clicar("#bd-autor", 0.2)
    s.envia("Input.insertText", {"text": "  brelgo QA  "})
    s.clicar("#bi-detail .bd-pub-note", 0.3)        # sai do campo: o change grava
    guardado = s.js("localStorage.getItem('montador.autor')")
    s.clicar('#bi-detail [data-act="publish"]', 1.0)
    s.js("(() => { if (!document.getElementById('pub-dialog').hidden && !document.getElementById('pub-foot').hidden) fecharPub(); renderBuildIndex(); return 1; })()"); time.sleep(0.4)
    lembrado = s.js("document.getElementById('bd-autor').value")
    s.js("(() => { const i = document.getElementById('bd-autor'); i.value = ''; i.dispatchEvent(new Event('change', { bubbles: true })); return 1; })()")
    s.clicar('#bi-detail [data-act="publish"]', 1.0)
    s.js("(() => { if (!document.getElementById('pub-dialog').hidden && !document.getElementById('pub-foot').hidden) fecharPub(); window.fetch = window.__fetchOrigA; return 1; })()")
    enviados = s.js("window.__autores")
    p.conta("autor", "o apelido digitado vai no p_autor (sem os espaços das pontas), fica lembrado no navegador, e o campo vazio publica sem autor",
            vazio == "" and guardado == "brelgo QA" and lembrado == "brelgo QA" and enviados == ["brelgo QA", ""],
            "vazio %r · guardado %r · lembrado %r · enviados %s" % (vazio, guardado, lembrado, enviados))


def checar_dislexia(s, p):
    """F13-T85: a fonte para dislexia (OpenDyslexic, em assets/fonts/opendyslexic/). Com clique de
    verdade no interruptor da Acessibilidade: a fonte carrega e vale no texto e nos títulos, nada
    estoura para o lado em 1600 e 1280 (a loja e a forja; era a plaqueta da bigorna que passava 57 px),
    fica lembrada; desligar volta à Alegreya. O caminho antigo: com a fonte normal a plaqueta segue a
    4 px da aba Builds, antes de ligar e depois de desligar."""
    print("\n%sFONTE PARA DISLEXIA%s" % (AMARELO, FIM))
    garantir_build_editavel(s)
    s.js("(() => { switchTab('catalog'); window.scrollTo(0, 0); return 1; })()"); time.sleep(0.3)
    PLAQUETA = "(() => { const p = document.getElementById('bigorna'); return p.hidden ? null : p.offsetLeft - document.querySelector('.tab-btn[data-tab=\"build\"]').offsetLeft; })()"
    antes = s.js(PLAQUETA)   # F13-T86: sem a deriva de 2 px ao trocar de aba, mede direto
    s.clicar("#acess-btn", 0.4)
    s.clicar('label.som-opt:has(#ac-dislexia)', 0.6)
    fonte = s.js("""(async () => { await document.fonts.ready; await document.fonts.load('16px OpenDyslexic');
      const c = getComputedStyle(document.querySelector('.counts')).fontFamily, h = getComputedStyle(document.querySelector('header.top h1')).fontFamily;
      return { classe: document.body.classList.contains('ac-dislexia'), texto: c, titulo: h, carregou: document.fonts.check('16px OpenDyslexic'),
               guardado: JSON.parse(localStorage.getItem('acessibilidade') || '{}').dislexia === true }; })()""")
    s.envia("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    s.envia("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    lados, cortes = {}, {}
    for w, h in ((1600, 900), (1280, 800)):
        s.tela(w, h)
        for aba in ("catalog", "build"):
            s.js("(() => { switchTab('%s'); if ('%s' === 'build') showBuildScreen('forja'); window.scrollTo(0, 0); return 1; })()" % (aba, aba)); time.sleep(0.4)
            lados["%d %s" % (w, aba)] = s.js("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            if aba == "catalog":   # a letra larga não corta atributo nem nome: a linha quebra e o card cresce
                cortes["%d" % w] = s.js("""[...document.querySelectorAll('#grid .card')].filter(c => [...c.querySelectorAll('.attr-line, .card-name .en')].some(e => e.scrollWidth > e.clientWidth + 1)
                  || c.querySelector('.card-main').scrollHeight > c.querySelector('.card-main').clientHeight + 1).length""")
    s.tela_normal()
    s.js("(() => { switchTab('catalog'); return 1; })()")
    s.clicar("#acess-btn", 0.4)
    s.clicar('label.som-opt:has(#ac-dislexia)', 0.4)
    volta = s.js("({ classe: document.body.classList.contains('ac-dislexia'), texto: getComputedStyle(document.querySelector('.counts')).fontFamily })")
    volta["plaqueta"] = s.js(PLAQUETA)
    s.envia("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    s.envia("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    primeira = lambda f: f.split(",")[0].strip().strip('"').strip("'")
    p.conta("dislexia", "o interruptor troca o texto e os títulos pela OpenDyslexic (carregada), fica lembrado, nada estoura para o lado em 1600 e 1280 nem corta atributo no card; desligado, volta à Alegreya e a plaqueta à aba Builds",
            fonte["classe"] and fonte["carregou"] and primeira(fonte["texto"]) == "OpenDyslexic" and primeira(fonte["titulo"]) == "OpenDyslexic" and fonte["guardado"]
            and all(v <= 1 for v in lados.values()) and not volta["classe"] and primeira(volta["texto"]) == "Alegreya"
            and antes == 4 and volta["plaqueta"] == 4 and all(v == 0 for v in cortes.values()),
            "ligada %s · lados %s · cards cortados %s · desligada %s · plaqueta antes %s" % (fonte, lados, cortes, volta, antes))


def checar_tags_somam(s, p):
    """F13-T89 (Leo, 29/10/2026: "o que eu quero é que sejam exibidos os itens que tem a tag A+B"):
    com clique de verdade nos chips da loja, marcar A e B num grupo de várias tags mostra só quem
    tem as duas (Efeitos Especiais e Atributo); num grupo de valor único (Tier), dois chips somam.
    O par é escolhido no catálogo de modo que "A e B" seja menor que "A ou B" e não zere, e o
    esperado é contado por fora, direto do CATALOG."""
    print("\n%sTAGS SOMAM%s" % (AMARELO, FIM))
    s.js("(() => { switchTab('catalog'); clearAllFilters(); window.scrollTo(0, 0); return 1; })()"); time.sleep(0.4)
    pares = s.js("""(() => {
      const base = CATALOG.items.filter(it => itemInClass(it, state.classe));
      const tags = { effects: it => it.specialEffects || [], stats: it => (it.attributes || []).map(a => a.stat) };
      const opcoes = { effects: CATALOG.meta.specialEffects.filter(v => !DAMAGE_OPTIONS.includes(v)), stats: ALL_STATS.map(([st]) => st) };
      const out = {};
      for (const g of ['effects', 'stats']) {
        const conta = v => base.filter(it => tags[g](it).includes(v)).length;
        let melhor = null;
        for (const a of opcoes[g]) for (const b of opcoes[g]) {
          if (a >= b) continue;
          const na = conta(a), nb = conta(b), ambos = base.filter(it => tags[g](it).includes(a) && tags[g](it).includes(b)).length;
          const ou = na + nb - ambos;
          if (ambos > 0 && ambos < Math.min(na, nb) && (!melhor || ou - ambos > melhor.ou - melhor.ambos)) melhor = { a, b, na, nb, ambos, ou };
        }
        out[g] = melhor;
      }
      const tiers = ['Épico', 'Lendário'].filter(x => TIER_ORDER.includes(x));
      out.tiers = { a: tiers[0], b: tiers[1], soma: base.filter(it => tiers.includes(it.tier)).length };
      return out;
    })()""")
    cards = "document.querySelectorAll('#grid .card').length"
    abre = lambda g: s.js("(() => { const w = document.querySelector('.filter-group[data-group=\"%s\"]'); if (w.classList.contains('collapsed')) w.querySelector('.filter-group-title').click(); return 1; })()" % g)
    chip = lambda g, v: '.chip[data-group="%s"][data-value=%s]' % (g, json.dumps(v, ensure_ascii=False))
    medidas = {}
    for g in ("effects", "stats", "tiers"):
        par = pares.get(g)
        if not par:
            medidas[g] = None
            continue
        s.js("(() => { clearAllFilters(); return 1; })()"); time.sleep(0.3)
        abre(g); time.sleep(0.3)
        s.clicar(chip(g, par["a"]), 0.4)
        so_a = s.js(cards)
        s.clicar(chip(g, par["b"]), 0.5)
        medidas[g] = {"par": [par["a"], par["b"]], "so_a": so_a, "a_e_b": s.js(cards),
                      "esperado": par["ambos"] if g != "tiers" else par["soma"],
                      "marcados": s.js("[...state['%s']]" % g)}
    s.js("(() => { clearAllFilters(); return 1; })()")
    ok = all(m and len(m["marcados"]) == 2 and m["a_e_b"] == m["esperado"] for m in medidas.values())
    ok = ok and medidas["effects"]["a_e_b"] < medidas["effects"]["so_a"] and medidas["stats"]["a_e_b"] < medidas["stats"]["so_a"]
    ok = ok and medidas["tiers"]["a_e_b"] > medidas["tiers"]["so_a"]
    p.conta("tags somam", "duas tags no mesmo grupo mostram só quem tem as duas (Efeitos, Atributo); no Tier, dois chips somam",
            ok, "; ".join("%s %s: só A %s, A+B %s (esperado %s)" % (g, m["par"], m["so_a"], m["a_e_b"], m["esperado"]) if m else "%s: sem par" % g
                          for g, m in medidas.items()))


def checar_link_curto(s, p):
    """F13-T91 (Leo, 30/10/2026): o link curto da build publicada, "#build/<id de 6>", abre direto
    na pública, só visualização; o "Copiar link" de uma publicada copia o curto e o de uma não
    publicada continua com o "#b=". Servidor SIMULADO numa aba própria: o fetch ao Supabase é
    respondido na página (uma pública conhecida; "fff911" não existe; "eee911" cai a rede) e o
    navigator.clipboard.writeText só anota o que sairia. Nada vai ao servidor de verdade."""
    print("\n%sLINK CURTO DA BUILD PUBLICADA%s" % (AMARELO, FIM))
    ID, NOME = "9a1b01", "Link Curto QA"
    falso = r"""(() => {
      const ID = '%s', NOME = '%s';
      // os itens vêm do catálogo da página, nunca digitados aqui
      const linha = () => { const C = window.CATALOG;
        return { id: ID, nome: NOME, descricao: 'pública do roteiro', campeao: null, modo: '', marcadores: [],
          caixas: [{ name: 'Núcleo', kind: 'comum', items: C.items.filter(i => i.tier === 'Lendário').slice(0, 3).map(i => ({ itemId: i.slug })) }],
          versao: 2, atualizado_em: new Date().toISOString(), patch: C.meta.patch, autor: 'roteiro', engajamentos: 0,
          pop_dia: 0, popular_semana: false, dias_no_top: 0, layout: null, runas: null, habilidades: null }; };
      window.__pedidosServidor = []; window.__copiado = [];
      const f = window.fetch;
      window.fetch = function (u, ...a) {
        const t = String(u && u.url || u);
        if (!t.includes('supabase.co')) return f.call(this, u, ...a);
        window.__pedidosServidor.push(t.replace(/^.*\/(rest\/v1|rpc)\//, ''));
        if (t.includes('id=eq.eee911')) return Promise.reject(new TypeError('Failed to fetch'));
        let corpo = null;
        if (t.includes('/rest/v1/builds_publicas')) corpo = (t.includes('id=eq.') || t.includes('id=in.')) ? (t.includes(ID) ? [linha()] : []) : [linha()];
        return Promise.resolve(new Response(JSON.stringify(corpo), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      };
      try { navigator.clipboard.writeText = (x) => { window.__copiado.push(String(x)); return Promise.resolve(); }; } catch (e) {}
    })();""" % (ID, NOME)
    r = Sessao(s.url)

    def espera(expr, limite=8.0):
        fim = time.time() + limite
        while time.time() < fim:
            try:
                if r.js(expr):
                    return True
            except RuntimeError:
                pass
            time.sleep(0.2)
        return False

    tela = """(() => ({ hash: location.hash, aba: document.querySelector('.tab-btn.active') ? document.querySelector('.tab-btn.active').dataset.tab : null,
      forja: !document.getElementById('build-editor').hidden, lista: !document.getElementById('build-index').hidden, view: biView,
      temp: !!build.temp, origem: build.pubOrigem || null, nome: build.name, id: build.id,
      aviso: (document.getElementById('temp-warning') || {}).innerText || '',
      entrada: document.getElementById('entrada').classList.contains('fechada'),
      placa: document.getElementById('pub-dialog').hidden ? null : { titulo: document.getElementById('pub-title').textContent, texto: document.getElementById('pub-text').innerText } }))()"""
    try:
        r.envia("Page.addScriptToEvaluateOnNewDocument", {"source": falso})
        r.tela(1600, 900)
        # (a) a página aberta com o link curto de uma pública conhecida
        r.abrir("#build/" + ID)
        espera("typeof build !== 'undefined' && build.temp && build.pubOrigem === '%s' && !document.getElementById('build-editor').hidden" % ID)
        time.sleep(0.6)
        a = r.js(tela)
        p.conta("link curto", "abrir a página com #build/<id> abre a pública direto, só visualização, com o nome certo (e o endereço fica no link)",
                a["hash"] == "#build/" + ID and a["aba"] == "build" and a["forja"] and a["temp"] and a["origem"] == ID
                and a["nome"] == NOME and "Só visualização" in a["aviso"] and a["entrada"] and not a["placa"],
                "%s" % {k: a[k] for k in ("hash", "aba", "forja", "temp", "origem", "nome", "entrada", "placa")})
        # o "Copiar link" da forja, na pública aberta para ver: sai o curto (sem a forja, o grupo segue
        # e a falha fica nesta checagem, não num "não achei" que esconde as seguintes)
        forja_link = {"ult": None, "base": "", "titulo": ""}
        if a["forja"]:
            r.clicar("#toggle-io", 0.5)
            r.clicar("#link-btn", 0.6)
            forja_link = r.js("({ ult: window.__copiado[window.__copiado.length - 1] || null, base: location.href.split('#')[0], titulo: document.getElementById('link-btn').title })")
        # sair para outra tela escreve o endereço dela (T81); o voltar do navegador reabre a pública
        r.clicar('.tab-btn[data-tab="catalog"]', 0.6)
        saiu = r.js(tela)
        r.js("history.back(); 1")
        espera("location.hash === '#build/%s' && !document.getElementById('build-editor').hidden && build.temp" % ID, 5)
        time.sleep(0.4)
        voltou = r.js(tela)
        p.conta("link curto", "ao sair da pública para outra tela, o endereço volta a ser o da tela (#catalogo); o voltar do navegador reabre a pública",
                saiu["hash"] == "#catalogo" and saiu["aba"] == "catalog" and voltou["hash"] == "#build/" + ID
                and voltou["aba"] == "build" and voltou["forja"] and voltou["origem"] == ID,
                "saiu %s · voltou %s" % ({k: saiu[k] for k in ("hash", "aba")}, {k: voltou[k] for k in ("hash", "aba", "forja", "origem")}))

        # (b) ID que não existe, rede que cai, e # torto: aviso claro, a lista das Públicas, nada quebra
        r.erros.clear()
        r.abrir("?inexistente=1#build/fff911")
        espera("!document.getElementById('pub-dialog').hidden", 8)
        time.sleep(0.4)
        b1 = r.js(tela)
        if b1["placa"]:   # sem placa, a falha fica na checagem (não num "não achei" que esconde as seguintes)
            r.clicar("#pub-close", 0.4)
        fechou = r.js("document.getElementById('pub-dialog').hidden")
        r.abrir("?semrede=1#build/eee911")
        espera("!document.getElementById('pub-dialog').hidden", 8)
        time.sleep(0.4)
        b2 = r.js(tela)
        tortos = {}
        for h in ("#build/ABC123", "#build/9a1b011", "#build/9a1b0'"):
            r.abrir("?torto=%d%s" % (len(tortos), h))
            time.sleep(1.2)
            q = r.js(tela)
            tortos[h] = {"placa": q["placa"], "temp": q["temp"], "pedidos_id": r.js("window.__pedidosServidor.filter(x => x.includes('id=eq.')).length")}
        erros = list(r.erros)
        ok_b1 = (b1["placa"] and b1["placa"]["titulo"] == "Build não encontrada" and "fff911" in b1["placa"]["texto"]
                 and b1["hash"] == "#builds" and b1["aba"] == "build" and b1["lista"] and b1["view"] == "publicas" and not b1["temp"] and fechou)
        ok_b2 = (b2["placa"] and b2["placa"]["titulo"] == "Não deu para abrir o link" and "internet" in b2["placa"]["texto"]
                 and b2["view"] == "publicas" and b2["lista"] and not b2["temp"])
        ok_t = all(not v["placa"] and not v["temp"] and v["pedidos_id"] == 0 for v in tortos.values())
        p.conta("link curto", "ID inexistente ou sem rede: a placa diz o motivo, o app fica na lista das Públicas, e nenhuma exceção no console; # torto é ignorado (sem pedido ao servidor)",
                ok_b1 and ok_b2 and ok_t and not erros,
                "inexistente %s · sem rede %s · tortos %s · erros %s" % ({k: b1[k] for k in ("placa", "hash", "view", "lista")},
                                                                    {k: b2[k] for k in ("placa", "view")}, tortos, erros[:2]))

        # (c) "Copiar link", com clique de verdade: a não publicada sai pelo #b=, a publicada e a pública pelo curto
        r.abrir("?copiar=1#builds"); r.entrar()
        r.nova_build()
        r.js("""(() => { build.name = 'Sem publicar QA'; build.cats[0].items.push({ itemId: CATALOG.items.find(i => i.tier === 'Épico').slug, note: '' });
          gravarBuild(); showBuildScreen('lista'); mostrarListaDe('minhas'); biSelected = build.id; renderBuildIndex(); return 1; })()""")
        time.sleep(0.5)
        t_longo = r.js("document.querySelector('#bi-detail [data-act=\"link\"]').title")
        r.clicar('#bi-detail [data-act="link"]', 0.6)
        longo = r.js("window.__copiado[window.__copiado.length - 1] || null")
        r.js("""(() => { const b = library.builds.find(x => x.id === build.id); b.pubId = build.pubId = '%s'; b.pubVersao = build.pubVersao = 2;
          gravarBiblioteca(); renderBuildIndex(); return 1; })()""" % ID)
        time.sleep(0.4)
        t_curto = r.js("document.querySelector('#bi-detail [data-act=\"link\"]').title")
        r.clicar('#bi-detail [data-act="link"]', 0.6)
        curto = r.js("({ ult: window.__copiado[window.__copiado.length - 1] || null, msg: document.getElementById('bd-link-msg').innerText })")
        r.clicar('.bi-tab[data-view="publicas"]', 0.6)
        espera("!!document.querySelector('.bi-row[data-pub=\"%s\"]')" % ID, 6)
        r.clicar('.bi-row[data-pub="%s"]' % ID, 0.5)
        r.clicar('#bi-detail [data-act="link"]', 0.6)
        publica = r.js("({ ult: window.__copiado[window.__copiado.length - 1] || null, base: location.href.split('#')[0] })")
        base = publica["base"]
        # F13-T95: fora do GitHub Pages (um servidor local) o curto segue #build/<id>; no site (--site) é
        # a página b/<id>/, falando do card no Discord (o passo l confere o site de mentira)
        no_site = base.startswith(SITE)
        marca_curta = ("b/%s/" % ID) if no_site else ("#build/" + ID)
        fala = lambda txt: ("Discord" in txt) == no_site
        p.conta("link curto", "Copiar link: a não publicada copia o #b=; a publicada (Minhas), a pública (Públicas) e a aberta para ver (forja) copiam o curto; o title diz qual sai — fora do site #build/<id>, sem falar do card no Discord; no site, b/<id>/",
                bool(longo) and longo.startswith(base + "#b=") and curto["ult"] == ((SITE + marca_curta) if no_site else base + marca_curta)
                and "Link curto copiado" in curto["msg"] and fala(curto["msg"])
                and publica["ult"] == ((SITE + marca_curta) if no_site else base + marca_curta)
                and forja_link["ult"] == ((SITE + marca_curta) if no_site else forja_link["base"] + marca_curta)
                and "#b=" in t_longo and marca_curta in t_curto and marca_curta in forja_link["titulo"] and fala(t_curto),
                "não publicada %r · publicada %r · pública %r · forja %r · títulos %r / %r" % (
                    (longo or "")[:60], curto["ult"], publica["ult"], forja_link["ult"], t_longo[:40], t_curto[:40]))

        # (d) o caminho antigo: o #b= continua abrindo a build, e #runas / #builds trocam de tela
        r.erros.clear()
        r.abrir("?antigo=1#" + longo.split("#", 1)[1])
        espera("typeof build !== 'undefined' && build.name === 'Sem publicar QA' && !document.getElementById('build-editor').hidden", 6)
        time.sleep(0.5)
        d0 = r.js(tela)
        r.js("(() => { location.hash = '#runas'; return 1; })()"); time.sleep(0.6)
        d1 = r.js(tela)
        r.js("(() => { location.hash = '#builds'; return 1; })()"); time.sleep(0.6)
        d2 = r.js(tela)
        erros = list(r.erros)
        p.conta("link curto", "caminho antigo: o link #b= continua abrindo a build na forja (o # fica como veio), e #runas e #builds continuam trocando de tela",
                d0["nome"] == "Sem publicar QA" and str(d0["id"]).startswith("l-") and d0["forja"] and d0["hash"].startswith("#b=") and not d0["temp"]
                and d1["aba"] == "runas" and d2["aba"] == "build" and d2["lista"] and not erros,
                "b= %s · runas %s · builds %s · erros %s" % ({k: d0[k] for k in ("nome", "id", "forja", "temp")}, d1["aba"], {k: d2[k] for k in ("aba", "lista")}, erros[:2]))

        # (l) F13-T95: no site, o link b/<id>/. A aba abre o app em https://brelgo.github.io/forja/ — o GitHub
        # Pages de mentira (pages_falso) responde com os arquivos desta pasta, a página que o robô gera e o
        # 404.html, como o Pages. O Copiar link de uma pública copia b/<id>/ e fala do card; a página leva à
        # pública no app; sem página (o robô ainda não passou, ou a build saiu), o 404.html leva também — com
        # barra, sem barra, com index.html e com barra a mais no começo; outro endereço fica no 404 com o Voltar
        # (no --site, o Pages de verdade: o mesmo caminho, menos a página gerada, que lá não existe)
        local = s.url.startswith("http://127.0.0.1")
        if True:
            import importlib
            pasta = os.path.join(RAIZ, "data", "robo")
            if pasta not in sys.path:
                sys.path.insert(0, pasta)
            cards = importlib.import_module("cards")
            if local:
                ligar_site_falso(r)
                PAGINAS_EXTRAS["/forja/b/%s/" % ID] = cards.pagina({"id": ID, "nome": NOME}, {"quem": ""}, "roteiro")
            url0 = r.url
            r.url = SITE
            try:
                r.abrir("?site=1#builds"); r.entrar()
                espera("!!document.querySelector('.bi-tab[data-view=\"publicas\"]')", 8)
                r.clicar('.bi-tab[data-view="publicas"]', 0.6)
                espera("!!document.querySelector('.bi-row[data-pub=\"%s\"]')" % ID, 8)
                r.clicar('.bi-row[data-pub="%s"]' % ID, 0.5)
                t_site = r.js("document.querySelector('#bi-detail [data-act=\"link\"]').title")
                r.clicar('#bi-detail [data-act="link"]', 0.6)
                c_site = r.js("({ ult: window.__copiado[window.__copiado.length - 1] || null, msg: (document.getElementById('bd-link-msg') || {}).innerText || '', origem: location.origin })")
                l1 = None
                if local:
                    r.abrir("b/%s/" % ID)
                    espera("typeof build !== 'undefined' && location.hash === '#build/%s' && build.temp && build.pubOrigem === '%s'" % (ID, ID), 8)
                    # se a página levou para outro lugar (o 404, sem o app), a tela não existe: vale o endereço
                    l1 = r.js("document.getElementById('build-editor') ? %s : { hash: location.pathname + location.hash, temp: false, origem: null, aba: null }" % tela)
                    l1["caminho"] = r.js("location.pathname")
                vistos = []
                for falta in ("b/9a1b0f/", "b/9a1b0e", "b/9a1b0d/index.html", "//forja/b/9a1b0c/"):
                    fid = falta.rstrip("/").replace("/index.html", "")[-6:]
                    r.envia("Page.navigate", {"url": (SITE + falta) if not falta.startswith("//") else "https://brelgo.github.io" + falta})
                    espera("location.pathname === '/forja/' && (window.__pedidosServidor || []).some(x => x.includes('id=eq.%s'))" % fid, 8)
                    vistos.append(r.js("({ url: location.href, caminho: location.pathname, pediu: (window.__pedidosServidor || []).some(x => x.includes('id=eq.%s')) })" % fid))
                r.abrir("nada/aqui.html")
                time.sleep(0.4)
                l3 = r.js("({ caminho: location.pathname, titulo: document.title, h1: (document.querySelector('h1') || {}).textContent || '', volta: (document.getElementById('volta') || {}).href || '' })")
                # fora do Pages (o servidor local, que também serve o 404.html), o Voltar vai para a raiz
                l4 = None
                if local:
                    r.envia("Page.navigate", {"url": url0 + "nada/aqui.html"})
                    espera("!!document.getElementById('volta')", 5)
                    l4 = r.js("(document.getElementById('volta') || {}).href || ''")
            finally:
                PAGINAS_EXTRAS.pop("/forja/b/%s/" % ID, None)
                r.url = url0
            p.conta("link curto", "no site: o Copiar link de uma pública copia b/<id>/ (a página do card) e o title e o recado falam do card no Discord",
                    c_site["ult"] == SITE + "b/%s/" % ID and "No Discord" in c_site["msg"] and "b/%s/" % ID in t_site and "Discord" in t_site,
                    "copiou %r · recado %r · title %r" % (c_site["ult"], c_site["msg"][-80:], t_site[:70]))
            p.conta("link curto", "no site: a página gerada pelo robô abre a pública no app (#build/<id>); sem página, o 404.html leva ao #build/<id> (com barra, sem barra, com index.html e com barra a mais no começo); outro endereço errado fica no 404 com o Voltar para a raiz do site",
                    (l1 is None or (l1["hash"] == "#build/" + ID and l1["caminho"] == "/forja/" and l1["temp"] and l1["origem"] == ID and l1["aba"] == "build"))
                    and len(vistos) == 4 and all(v["caminho"] == "/forja/" and v["url"].startswith(SITE) and v["pediu"] for v in vistos)
                    and l3["caminho"] == "/forja/nada/aqui.html" and "não existe" in l3["h1"] and l3["volta"] == SITE
                    and (l4 is None or l4 == url0),
                    "página %s · sem página %s · errado %s · Voltar fora do Pages %r" % ({k: l1[k] for k in ("caminho", "hash", "temp", "origem")} if l1 else "(no Pages de verdade não há a página do roteiro)", [v["url"][-22:] + (" ok" if v["pediu"] else " sem pedido") for v in vistos], l3, l4))

        # (m) aberto do disco não há página: o curto segue o #build/<id>, sem falar em Discord
        r.envia("Page.navigate", {"url": "file:///" + os.path.join(RAIZ, "index.html").replace(os.sep, "/").replace(" ", "%20")})
        espera("typeof linkCurtoDaPublica === 'function'", 10)
        m1 = r.js("({ link: linkCurtoDaPublica('%s'), titulo: tituloDoLink('%s'), aviso: avisoDoCurto(), base: location.href.split('#')[0] })" % (ID, ID))
        p.conta("link curto", "caminho antigo: aberto do disco, o curto continua #build/<id> (não há página b/ no disco), e o title e o recado não falam do card no Discord",
                m1["link"] == m1["base"] + "#build/" + ID and "#build/" + ID in m1["titulo"] and "Discord" not in m1["titulo"] + m1["aviso"],
                "link %r · title %r · recado %r" % (m1["link"][-30:], m1["titulo"][:60], m1["aviso"][-60:]))
    finally:
        r.fechar()
    _link_curto_lento(s, p, ID, NOME)


def checar_card_pronto(s, p):
    """F13-T109 (Leo, 03/11/2026): o card na hora. (1) Sem navegador: o robô dos cards acorda com o
    aviso do Supabase (repository_dispatch "build-publicada"), e o supabase.sql tem a função e os três
    gatilhos — o de update só pelas colunas de conteúdo (os contadores mudam a cada visita) — e nenhum
    token escrito. (2) Na aba, no GitHub Pages de mentira (pages_falso), o aviso "card pronto" ("acho
    bom ter alguma coisa para notificar que o card do ID está pronto"): a placa diz que o robô está
    forjando e troca para pronto quando a página b/<id>/ aparece (nova) ou o ?v= do card muda
    (atualização); com a placa fechada, o recado vai na faixa da tela; sem mudança até o limite, a
    placa diz por quê; do servidor local, nada disso aparece. Servidor das builds SIMULADO: nenhum
    publicar_build sai deste navegador."""
    print("\n%sCARD PRONTO%s" % (AMARELO, FIM))
    yml = open(os.path.join(RAIZ, ".github", "workflows", "cards.yml"), encoding="utf-8").read()
    on = yml.split("\njobs:")[0]
    p.conta("card pronto", "o robô dos cards acorda com o aviso do Supabase (repository_dispatch, tipo build-publicada), e as rodadas de antes continuam (meia hora, pedido e push)",
            bool(re.search(r"\n  repository_dispatch:\s*(#[^\n]*)?\n\s+types:\s*\[\s*build-publicada\s*\]", on))
            and "schedule:" in on and "workflow_dispatch:" in on and "push:" in on,
            "on: %s" % " ".join(re.findall(r"\n  ([a-z_]+):", on)))
    sql = open(os.path.join(RAIZ, "docs", "servidor", "supabase.sql"), encoding="utf-8").read()
    gat = {m.group(1): m.group(2) for m in re.finditer(r"create trigger (avisar_cards_\w+) (after [^\n]*?) on public\.builds\s*\n\s*for each row execute function public\.avisar_robo_dos_cards\(\);", sql)}
    upd = re.match(r"after update of (.*)$", gat.get("avisar_cards_ao_mudar", ""))
    cols = {c.strip() for c in upd.group(1).split(",")} if upd else set()
    conteudo = {"nome", "descricao", "campeao", "modo", "marcadores", "caixas", "patch", "autor", "layout", "runas", "habilidades", "rota"}
    fn = re.search(r"create or replace function public\.avisar_robo_dos_cards\(\).*?end \$\$;", sql, re.S)
    fn = fn.group(0) if fn else ""
    p.conta("card pronto", "o supabase.sql tem a função que avisa o robô (o token do Vault, a API do GitHub, erro engolido, sem execução para o público) e os três gatilhos; o de update só pelas colunas de conteúdo",
            gat.get("avisar_cards_ao_publicar") == "after insert" and gat.get("avisar_cards_ao_apagar") == "after delete" and cols == conteudo
            and "vault.decrypted_secrets where name = 'github_cards'" in fn and "repos/Brelgo/forja/dispatches" in fn and "'build-publicada'" in fn
            and "exception when others then" in fn and "security definer" in fn
            and "revoke all on function public.avisar_robo_dos_cards() from public, anon, authenticated;" in sql,
            "gatilhos %s · colunas a mais %s, a menos %s · função %s" % (sorted(gat), sorted(cols - conteudo), sorted(conteudo - cols), "achada" if fn else "NÃO ACHADA"))
    vazou = []
    for raiz, pastas, arqs in os.walk(RAIZ):
        pastas[:] = [d for d in pastas if d not in (".git", "node_modules")]
        for a in arqs:
            if os.path.splitext(a)[1].lower() in (".html", ".js", ".py", ".sql", ".md", ".yml", ".json", ".txt"):
                try:
                    x = open(os.path.join(raiz, a), encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                if re.search(r"github_pat_[A-Za-z0-9_]{20,}|\bgh[pousr]_[A-Za-z0-9]{30,}", x):
                    vazou.append(os.path.relpath(os.path.join(raiz, a), RAIZ))
    p.conta("card pronto", "nenhum token do GitHub escrito no repositório (ele mora só no Vault)", not vazou, ", ".join(vazou[:3]))

    ID, NOVO, NOME = "c0ffee", "c0ffef", "Card Pronto QA"
    falso = r"""(() => {
      window.__resposta = { id: '%s', versao: 1 }; window.__pubs = 0; window.__pedidosB = [];
      const f = window.fetch;
      window.fetch = function (u, ...a) {
        const t = String(u && u.url || u);
        if (/\/forja\/b\//.test(t)) window.__pedidosB.push(t);
        if (!t.includes('supabase.co')) return f.call(this, u, ...a);
        const ok = (c) => Promise.resolve(new Response(JSON.stringify(c), { status: 200, headers: { 'Content-Type': 'application/json' } }));
        if (t.includes('publicar_build')) { window.__pubs++; return ok(window.__resposta); }
        return ok(t.includes('/rpc/') ? null : []);
      };
    })();""" % ID
    r = Sessao(s.url)

    def espera(expr, limite=8.0):
        fim = time.time() + limite
        while time.time() < fim:
            try:
                if r.js(expr):
                    return True
            except RuntimeError:
                pass
            time.sleep(0.2)
        return False

    def pagina(versao):
        PAGINAS_EXTRAS["/forja/b/%s/" % ID] = cards.pagina({"id": ID, "nome": NOME}, {"quem": ""}, "roteiro", versao)

    estado = """(() => { const c = document.querySelector('#pub-text .pub-card'), h = document.getElementById('edit-hint');
      return { placa: !document.getElementById('pub-dialog').hidden, card: c ? c.dataset.card : null, estado: c ? c.dataset.estado : null,
        texto: c ? c.innerText : '', faixa: h && h.classList.contains('show') ? h.innerText : '', pubs: window.__pubs, b: window.__pedidosB.length,
        faixaVista: h ? Number(getComputedStyle(h).opacity) : 0 }; })()"""

    def publicar():
        r.js("(() => { biSelected = build.id; renderBuildIndex(); return 1; })()")
        time.sleep(0.3)
        r.clicar('#bi-detail [data-act="publish"]', 0.6)
        espera("document.getElementById('pub-dialog').classList.contains('sucesso')", 5)

    import importlib
    pasta = os.path.join(RAIZ, "data", "robo")
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    cards = importlib.import_module("cards")
    local = s.url.startswith("http://127.0.0.1")
    url0 = r.url
    try:
        r.envia("Page.addScriptToEvaluateOnNewDocument", {"source": falso})
        r.tela(1600, 900)
        if not local:
            p.conta("card pronto", "na aba (só com o GitHub Pages de mentira, da pasta)", True, "pulado no --site")
            return
        ligar_site_falso(r)
        PAGINAS_EXTRAS.pop("/forja/b/%s/" % ID, None)
        r.url = SITE
        r.abrir("?cardpronto=1#builds"); r.entrar()
        r.nova_build()
        r.js("""(() => { CardPronto.cfg.espera = 250; CardPronto.cfg.limite = 2500;
          build.name = '%s'; build.desc = 'descrição do roteiro';
          build.markers = normMarkers(MARCADORES.slice(0, MAX_MARCADORES).map(m => ({ t: 'tag', id: m.id })));
          build.cats[0].items = [{ itemId: CATALOG.items.find(i => i.tier === 'Lendário').slug, note: '' }];
          gravarBuild(); showBuildScreen('lista'); return 1; })()""" % NOME)
        time.sleep(0.5)

        # (a) publicação nova: forjando enquanto não há página; pronto quando ela aparece
        publicar()
        a0 = r.js(estado)
        time.sleep(1.0)
        a1 = r.js(estado)
        pagina("aaa111")
        espera("(document.querySelector('#pub-text .pub-card') || { dataset: {} }).dataset.estado === 'pronto'", 4)
        a2 = r.js(estado)
        p.conta("card pronto", "publicação nova: a placa diz que o robô está forjando (e para colar no Discord depois do aviso) enquanto a página b/<id>/ não existe, e troca para \"pronto\" quando ela aparece",
                a0["placa"] and a0["card"] == ID and a0["estado"] == "forjando" and "forjando" in a0["texto"] and "Discord" in a0["texto"]
                and a1["estado"] == "forjando" and a1["b"] >= 2
                and a2["placa"] and a2["estado"] == "pronto" and "pronto" in a2["texto"],
                "logo %s · 1 s depois %s (%d leituras da b/) · com a página %s" % (a0["estado"], a1["estado"], a1["b"], a2["estado"]))
        r.clicar("#pub-close", 0.3)

        # (b) atualização com a placa fechada: o ?v= de antes não conta; o novo dá o recado na faixa
        publicar()
        b0 = r.js(estado)
        r.clicar("#pub-close", 0.3)
        time.sleep(1.0)
        b1 = r.js(estado)
        pagina("bbb222")
        espera("document.getElementById('edit-hint').classList.contains('show')", 4)
        time.sleep(0.5)   # a faixa entra com transição de 0,25 s
        b2 = r.js(estado)
        p.conta("card pronto", "atualização: o card de antes (o mesmo ?v=) não vale como pronto; com a placa fechada, o ?v= novo dá o recado na faixa da tela, com o nome da build",
                b0["estado"] == "forjando" and not b1["placa"] and not b1["faixa"]
                and "Card do Discord de %s pronto" % NOME in b2["faixa"] and b2["faixaVista"] > 0.9,
                "logo %s · fechada, 1 s depois: faixa %r · com o ?v= novo: faixa %r (opacidade %.2f)" % (b0["estado"], b1["faixa"][:40], b2["faixa"][:70], b2["faixaVista"]))

        # (c) atualização que não muda o card: no limite, a placa diz que o de antes continua valendo
        publicar()
        espera("(document.querySelector('#pub-text .pub-card') || { dataset: {} }).dataset.estado === 'demorou'", 5)
        c1 = r.js(estado)
        r.clicar("#pub-close", 0.3)
        # (d) publicada de novo com outro ID (a de antes sumiu do servidor): sem página, "ainda não saiu"
        r.js("window.__resposta = { id: '%s', versao: 1 }; 1" % NOVO)
        publicar()
        espera("(document.querySelector('#pub-text .pub-card') || { dataset: {} }).dataset.estado === 'demorou'", 5)
        d1 = r.js(estado)
        r.clicar("#pub-close", 0.3)
        p.conta("card pronto", "sem mudança até o limite: na atualização, a placa diz que o card de antes continua valendo (ou o robô refaz); na publicação com ID novo e sem página, que o card ainda não saiu",
                c1["card"] == ID and c1["estado"] == "demorou" and "não mudou" in c1["texto"]
                and d1["card"] == NOVO and d1["estado"] == "demorou" and "ainda não saiu" in d1["texto"],
                "atualização %s %r · ID novo %s %s %r" % (c1["estado"], c1["texto"][:30], d1["card"], d1["estado"], d1["texto"][:30]))

        # (e) caminho antigo: do servidor local (fora do Pages) não há card — nem linha, nem leitura da b/
        r.url = url0
        r.abrir("?cardlocal=1#builds"); r.entrar()
        r.js("window.__resposta = { id: '%s', versao: 1 }; 1" % ID)
        r.nova_build()
        r.js("""(() => { build.name = '%s'; build.desc = 'descrição do roteiro';
          build.markers = normMarkers(MARCADORES.slice(0, MAX_MARCADORES).map(m => ({ t: 'tag', id: m.id })));
          build.cats[0].items = [{ itemId: CATALOG.items.find(i => i.tier === 'Lendário').slug, note: '' }];
          gravarBuild(); showBuildScreen('lista'); return 1; })()""" % NOME)
        time.sleep(0.5)
        publicar()
        time.sleep(0.8)
        e1 = r.js(estado)
        p.conta("card pronto", "caminho antigo: fora do GitHub Pages (servidor local, disco) a publicação continua como era — sem a linha do card e sem ler a b/",
                e1["placa"] and e1["pubs"] == 1 and e1["card"] is None and e1["b"] == 0,
                "placa %s · publicações %d · linha %s · leituras da b/ %d" % (e1["placa"], e1["pubs"], e1["card"], e1["b"]))
        r.clicar("#pub-close", 0.3)
        if r.erros:
            p.conta("card pronto", "sem erro no console da aba", False, "; ".join(map(str, r.erros[:2])))
    finally:
        PAGINAS_EXTRAS.pop("/forja/b/%s/" % ID, None)
        r.url = url0
        r.fechar()


def _jpeg_tamanho(dados):
    """(largura, altura) de um JPEG, lida do marcador SOF — sem depender do PIL."""
    if dados[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(dados):
        if dados[i] != 0xFF:
            return None
        m = dados[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            return (dados[i + 7] << 8 | dados[i + 8], dados[i + 5] << 8 | dados[i + 6])
        i += 2 + (dados[i + 2] << 8 | dados[i + 3])
    return None


def checar_card(s, p):
    """F13-T95 (Leo, 31/10/2026) e F13-T98 (Leo, 01/11/2026: "os usuários gostaram mais do conceito 1
    do card do Discord"): o card da build no Discord, agora no desenho da Ficha da build. O robô dos
    cards (data/robo/cards.py) fotografa o molde data/robo/card.html para cada build publicada e
    escreve b/<id>/: a página com as etiquetas da prévia e o card.jpg. Aqui: os quadros que o molde
    monta (fichaDaBuild: o Core, a bota e o suporte, os iniciais, os situacionais), a ordem das
    habilidades, o desenho de verdade (o retrato, a arte, as runas, a ordem com os ícones, o nome
    comprido, sem campeão, o HTML, o rodapé, nada estourando), a rede (as fontes, a folha pendurada,
    as habilidades do campeão que não vêm); a página gerada (escapada, a imagem com endereço inteiro, o
    caminho para o #build/<id>); a assinatura (refaz só o que mudou, agora com as runas e a ordem; a
    incompleta refaz); o que o robô apaga e o que não apaga. As builds são do roteiro, os itens e as
    runas vêm do catálogo e de data/runas.js; tudo numa pasta temporária — nada vai ao servidor nem
    ao b/."""
    print("\n%sCARD DO DISCORD%s" % (AMARELO, FIM))
    import importlib
    import shutil
    import tempfile
    pasta = os.path.join(RAIZ, "data", "robo")
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    cards = importlib.import_module("cards")
    r = Sessao(s.url)

    def espera(expr, limite=10.0):
        fim = time.time() + limite
        while time.time() < fim:
            try:
                if r.js(expr):
                    return True
            except RuntimeError:
                pass
            time.sleep(0.2)
        return False

    try:
        r.envia("Page.navigate", {"url": s.url + "data/robo/card.html"})
        espera("typeof window.desenhar === 'function' && typeof CATALOG === 'object' && typeof RUNAS === 'object'")
        # (a) os quadros da Ficha: os itens de cada caso vêm do catálogo, pelo tier
        casos = r.js(r"""(() => {
          const C = CATALOG.items, T = t => C.filter(i => i.tier === t);
          const pecaDe = (a, b) => (b.components || []).some(c => c.namePt === a.namePt);
          const dadiva = C.find(i => i.tier === 'Lendário (Evolução)');
          // os Lendários que não são o item de suporte (o que a Dádiva vira também é tier Lendário)
          const L = T('Lendário').filter(i => !pecaDe(dadiva, i)), B = T('Bota'), S = T('Starter'), Co = T('Consumível'), Tr = T('Trinket'), E = T('Épico');
          const porNome = Object.fromEntries(C.map(i => [i.namePt, i]));
          const deBota = i => (i.components || []).some(c => (porNome[c.namePt] || {}).tier === 'Bota');
          const evB = C.find(i => i.tier === 'Evolução' && deBota(i)), evL = C.find(i => i.tier === 'Evolução' && !deBota(i));
          const cx = (kind, ...its) => ({ kind, items: its.map(i => ({ itemId: typeof i === 'string' ? i : i.slug })) });
          const botaBase = B.find(b => B.some(o => pecaDe(b, o))), botaFinal = B.find(o => pecaDe(botaBase, o)), outraFinal = B.find(o => o !== botaFinal && pecaDe(botaBase, o));
          const evBpeca = C.find(i => i.tier === 'Bota' && pecaDe(i, evB));
          const supVirado = T('Lendário').find(i => pecaDe(dadiva, i));
          const sl = (...its) => its.map(i => i.slug);
          const caso = (caixas, core, bota, suporte, iniciais, situacionais, aMais) =>
            ({ got: fichaDaBuild({ caixas }), want: { core, bota, suporte, iniciais, situacionais, aMais: aMais || 0 } });
          const ini = [...S, ...Co, ...Tr];
          return {
            ekko: caso([cx('comum', S[0], Co[0], Tr[0]), cx('comum', B[1]), cx('prioridade', L[0], L[1], L[2]), cx('opcional', L[3]),
                        cx('escolha', L[4], L[5]), cx('escolha', L[6]), cx('escolha', L[7])],
                       sl(L[0], L[1], L[2]), sl(B[1]), [], sl(S[0], Co[0], Tr[0]), sl(L[4], L[5], L[6], L[7])),
            opcional_e_escolha: caso([cx('opcional', L[0], L[1]), cx('escolha', L[2], L[3]), cx('comum', L[4])], sl(L[2], L[4]), [], [], [], sl(L[3])),
            evolucao: caso([cx('comum', evB, evL)], sl(evL), sl(evB), [], [], []),
            sem_lendario: caso([cx('comum', S[0], E[0], B[0])], sl(E[0]), sl(B[0]), [], sl(S[0]), []),
            so_iniciais: caso([cx('comum', S[0], B[0])], [], sl(B[0]), [], sl(S[0]), []),
            sem_lendario_com_sentinela: caso([cx('comum', Tr[0], E[0])], sl(E[0]), [], [], sl(Tr[0]), []),
            fora_do_catalogo: caso([cx('comum', 'nao-existe-no-catalogo', L[0])], sl(L[0]), [], [], [], []),
            lendarios_a_mais: caso([cx('comum', L[0], L[1], L[2], L[3], L[4], L[5])], sl(L[0], L[1], L[2]), [], [], [], sl(L[3], L[4], L[5])),
            repetido: caso([cx('comum', L[0]), cx('comum', L[0], L[1])], sl(L[0], L[1]), [], [], [], []),
            vazia: caso([], [], [], [], [], []),
            // o itemId é de quem publica — nome de propriedade herdada não é item
            prototipo: caso([cx('comum', 'constructor', '__proto__', 'toString', 'valueOf', 'hasOwnProperty')], [], [], [], [], []),
            prototipo_e_inicial: caso([cx('comum', S[0], 'constructor'), cx('escolha', '__proto__', 'toString', L[0])], [], [], [], sl(S[0]), sl(L[0])),
            // a bota da build, não a peça "Botas"; a outra bota da Escolha vira situacional
            botas: caso([cx('comum', L[0], botaBase), cx('escolha', botaFinal, outraFinal)], sl(L[0]), sl(botaFinal), [], [], sl(outraFinal)),
            bota_e_evolucao: caso([cx('comum', L[0], evBpeca, evB)], sl(L[0]), sl(evB), [], [], []),
            // o item de suporte vai para "Bota e suporte" (o virado da Dádiva no lugar dela), nunca para o Core
            suporte: caso([cx('comum', S[0], Co[0]), cx('comum', B[1]), cx('comum', supVirado, L[0], L[1], L[2])], sl(L[0], L[1], L[2]), sl(B[1]), sl(supVirado), sl(S[0], Co[0]), []),
            suporte_dadiva_e_virado: caso([cx('comum', dadiva, supVirado, L[0])], sl(L[0]), [], sl(supVirado), [], []),
            suporte_so_dadiva: caso([cx('comum', S[0], dadiva, L[0])], sl(L[0]), [], sl(dadiva), sl(S[0]), []),
            // os iniciais: Starter, Consumível e Trinket, até seis
            iniciais_seis: caso([cx('comum', ...ini.slice(0, 8))], [], [], [], sl(...ini.slice(0, 6)), []),
            // situacionais: só Lendário ou bota das Escolhas (o resto das opções não), sem repetir o que já aparece
            escolha_nao_lendaria: caso([cx('comum', L[0]), cx('escolha', Co[0], E[0], S[1], L[1])], sl(L[0]), [], [], sl(Co[0]), sl(L[1])),
            sem_repetir: caso([cx('escolha', L[0], L[1]), cx('escolha', L[1], L[2]), cx('comum', L[3]), cx('escolha', L[2], L[0])], sl(L[0], L[1], L[3]), [], [], [], sl(L[2])),
            // até 15, e o "+ N" do resto
            quinze: caso([cx('comum', L[0], L[1], L[2]), cx('escolha', ...L.slice(3, 21), B[1])], sl(L[0], L[1], L[2]), [], [], [], sl(...L.slice(3, 18)), 4),
            quinze_exatos: caso([cx('comum', L[0], L[1], L[2]), cx('escolha', ...L.slice(3, 18))], sl(L[0], L[1], L[2]), [], [], [], sl(...L.slice(3, 18)), 0),
          };
        })()""")
        errados = {k: v for k, v in casos.items() if v["got"] != v["want"]}
        p.conta("card do Discord", "os quadros da Ficha: o Core com os 3 primeiros Lendários do Total (sem Opcional; da Escolha só a 1ª), a bota da build (não a peça \"Botas\"; a evolução de bota é bota), o item de suporte em \"Bota e suporte\" (o virado da Dádiva no lugar dela), os iniciais (Starter, Consumível, Trinket; até 6), os situacionais (as opções das Escolhas que são Lendário ou bota e os Lendários fora do Core, sem repetir, até 15 e o \"+ N\"); sem Lendário, o resto vai para o Core; item fora do catálogo, repetido e com nome de propriedade (\"constructor\", \"__proto__\", \"toString\") não contam",
                not errados and len(casos) == 22, "errados: %s" % json.dumps(errados, ensure_ascii=False)[:400] if errados else "%d casos" % len(casos))

        # (b) a ordem de maximização das habilidades
        ordens = r.js(r"""(() => ({
          qew: ordemDasHabilidades(['Q','E','W','Q','Q','R','Q','E','Q','E','R','E','E','W','W','R','W','W']),
          // o Q vem primeiro, mas o W chega a 5 antes: vale quem chega a 5
          wqe: ordemDasHabilidades(['Q','W','E','W','W','R','W','Q','W','Q','R','Q','Q','E','E','R','E','E']),
          parcial: ordemDasHabilidades(['W','W','Q']),
          empate: ordemDasHabilidades(['E','Q']),
          so_r: ordemDasHabilidades(['R','R','R']),
          vazia: ordemDasHabilidades([]),
          nula: ordemDasHabilidades(null),
          texto: ordemDasHabilidades('QWE'),
          nulls: ordemDasHabilidades([null, 'Q', null, 'W', undefined, 'X', 'constructor']),
        }))()""")
        quer = {"qew": ["Q", "E", "W"], "wqe": ["W", "Q", "E"], "parcial": ["W", "Q"], "empate": ["E", "Q"], "so_r": [], "vazia": [], "nula": [], "texto": [], "nulls": ["Q", "W"]}
        p.conta("card do Discord", "a ordem das habilidades: a que chega a 5 pontos primeiro vem antes (Q›E›W; W›Q›E mesmo com o Q no nível 1); sem o 5º, a com mais pontos e depois a primeira; só R, vazia, nula, texto e nulls no meio não quebram (o R e o lixo ficam de fora)",
                ordens == quer, "%s" % {k: v for k, v in ordens.items() if quer.get(k) != v} or "%d casos" % len(quer))

        # (c) o desenho: cada build desenhada de verdade, com a foto que o robô tiraria
        def desenha(build):
            return r.js("desenhar(%s)" % json.dumps(build, ensure_ascii=False))

        caixas = r.js("""(() => { const C = CATALOG.items, dadiva = C.find(i => i.tier === 'Lendário (Evolução)'), B = C.filter(i => i.tier === 'Bota');
          const L = C.filter(i => i.tier === 'Lendário' && !(i.components || []).some(c => c.namePt === dadiva.namePt));
          const S = C.filter(i => i.tier === 'Starter'), Co = C.filter(i => i.tier === 'Consumível');
          return [{ kind: 'comum', items: [{ itemId: S[0].slug }, { itemId: Co[0].slug }] }, { kind: 'comum', items: [{ itemId: B[1].slug }] },
                  { kind: 'prioridade', items: L.slice(0, 3).map(i => ({ itemId: i.slug })) },
                  { kind: 'escolha', items: L.slice(3, 5).map(i => ({ itemId: i.slug })) }]; })()""")
        # as runas da build, tiradas de data/runas.js (a 1ª de cada fileira das duas primeiras trilhas)
        runas = r.js("""(() => { const T = RUNAS.trilhas, um = s => s.runas[0].id;
          return { primaria: T[0].id, assinatura: um(T[0].slots[0]), slots: T[0].slots.slice(1, 4).map(um), secundaria: T[1].id,
                   secundarios: [um(T[1].slots[1]), um(T[1].slots[2])], fragmentos: (RUNAS.fragmentos || []).map(f => f.runas[0].id) }; })()""")
        patch = r.js("CATALOG.meta.patch")
        ordem_qew = ["Q", "E", "W", "Q", "Q", "R", "Q", "E", "Q", "E", "R", "E", "E", "W", "W", "R", "W", "W"]
        base = {"id": "abc124", "nome": "AA AP", "autor": "Brelgo", "campeao": {"id": "Ekko", "name": "Ekko"}, "modo": "Summoner's Rift",
                "rota": "selva", "patch": patch, "caixas": caixas, "runas": runas, "habilidades": ordem_qew}
        DOM = r"""(() => { const c = document.getElementById('card'), q = s => c.querySelector(s), t = s => { const e = q(s); return e ? e.textContent : null; };
          const paineis = [...c.querySelectorAll('.painel')].map(e => ({ h: e.querySelector('h3').textContent, txt: e.innerText }));
          const pe = q('.pe'), b = q('.build');
          return { nome: t('.nome'), build: t('.build'), tags: t('.tags'), pe: pe ? pe.textContent : null, retrato: !!q('.retrato'), fundo: !!q('.fundo'),
                   habIcones: c.querySelectorAll('.hab img.ico').length, habLetras: c.querySelectorAll('.hab .letra').length,
                   runaIcones: c.querySelectorAll('.runas img').length, vazios: c.querySelectorAll('.painel .vazio').length, paineis,
                   buildLinha: b ? { corta: b.scrollWidth > b.clientWidth, alt: b.getBoundingClientRect().height, fs: parseFloat(getComputedStyle(b).fontSize),
                                     reticencias: getComputedStyle(b).textOverflow === 'ellipsis' } : null,
                   nomeLinha: (() => { const n = q('.nome'); return { corta: n.scrollWidth > n.clientWidth, alt: n.getBoundingClientRect().height,
                                     fs: parseFloat(getComputedStyle(n).fontSize), reticencias: getComputedStyle(n).textOverflow === 'ellipsis' }; })(),
                   peLinha: pe ? { corta: pe.scrollWidth > pe.clientWidth, reticencias: getComputedStyle(pe).textOverflow === 'ellipsis',
                                   dentro: pe.getBoundingClientRect().right <= c.getBoundingClientRect().right - 16 } : null }; })()"""
        painel = lambda d, h: next((x["txt"] for x in d["dom"]["paineis"] if x["h"].startswith(h)), None)
        umaLinha = lambda l: l and l["corta"] and l["reticencias"] and l["alt"] < l["fs"] * 1.6

        cheio = desenha(base); cheio["dom"] = r.js(DOM)
        p.conta("card do Discord", "o desenho de uma build de verdade: o retrato, a arte, o nome do campeão em cima e o da build embaixo, as runas com os ícones, a ordem Q›E›W com os ícones do campeão, os quadros, as fontes e nenhum ícone quebrado — e nada estourando (o \"cabe\")",
                cheio["arte"] and cheio["fontes"] and cheio["quebradas"] == 0 and cheio["faltou"] == [] and cheio["cabe"] and cheio["temRunas"]
                and cheio["ordem"] == ["Q", "E", "W"] and cheio["dom"]["habIcones"] == 3 and cheio["dom"]["habLetras"] == 0
                and cheio["dom"]["runaIcones"] >= 8 and cheio["dom"]["retrato"] and cheio["dom"]["fundo"]
                and cheio["dom"]["nome"] == "Ekko" and cheio["dom"]["build"] == "AA AP" and cheio["dom"]["tags"] == "Selva · Summoner's Rift"
                and cheio["quem"] == "Ekko · Selva · Summoner's Rift" and len(cheio["core"]) == 3 and len(cheio["bota"]) == 1 and len(cheio["iniciais"]) == 2
                and len(cheio["situacionais"]) == 2 and cheio["dom"]["vazios"] == 0,
                "%s · dom %s" % ({k: cheio[k] for k in ("arte", "fontes", "quebradas", "faltou", "cabe", "temRunas", "ordem")},
                                 {k: cheio["dom"][k] for k in ("habIcones", "habLetras", "runaIcones", "retrato", "nome", "build", "tags")}))

        sr = desenha(dict(base, runas=None)); sr["dom"] = r.js(DOM)
        sr2 = desenha(dict(base, runas={"assinatura": "constructor", "slots": ["__proto__", "toString"], "primaria": "valueOf"})); sr2["dom"] = r.js(DOM)
        so = desenha(dict(base, habilidades=[])); so["dom"] = r.js(DOM)
        so2 = desenha(dict(base, habilidades=["R", "R"])); so2["dom"] = r.js(DOM)
        p.conta("card do Discord", "sem runas (ou com runas que não existem, \"constructor\"/\"__proto__\"): o quadro diz \"sem runas\"; sem a ordem (vazia ou só R): \"sem a ordem\" — e nada falta (o card não fica incompleto por isso)",
                not sr["temRunas"] and "sem runas" in painel(sr, "RUNAS") and sr["dom"]["runaIcones"] == 0 and sr["faltou"] == [] and sr["cabe"]
                and not sr2["temRunas"] and "sem runas" in painel(sr2, "RUNAS") and sr2["quebradas"] == 0
                and so["ordem"] == [] and "sem a ordem" in painel(so, "ORDEM") and so["dom"]["habIcones"] == 0 and so["faltou"] == []
                and so2["ordem"] == [] and "sem a ordem" in painel(so2, "ORDEM") and so2["faltou"] == [],
                "sem runas %r · runas tortas %r · sem ordem %r · só R %r" % (painel(sr, "RUNAS"), painel(sr2, "RUNAS"), painel(so, "ORDEM"), painel(so2, "ORDEM")))

        longo = desenha(dict(base, nome="Forja " * 40)); longo["dom"] = r.js(DOM)
        semch = desenha(dict(base, campeao=None)); semch["dom"] = r.js(DOM)
        semch_longo = desenha(dict(base, campeao=None, rota="", modo="", nome="Bigorna " * 30)); semch_longo["dom"] = r.js(DOM)
        p.conta("card do Discord", "o nome da build comprido é cortado com \"…\" numa linha só; sem campeão: sem retrato e sem arte, o nome grande vira o da build (o comprido também numa linha, com \"…\"), a ordem fica nas letras e nada falta",
                umaLinha(longo["dom"]["buildLinha"]) and longo["cabe"] and longo["dom"]["nome"] == "Ekko"
                and not semch["dom"]["retrato"] and not semch["dom"]["fundo"] and not semch["arte"] and semch["dom"]["nome"] == "AA AP" and semch["dom"]["build"] is None
                and semch["faltou"] == [] and semch["dom"]["habLetras"] == 3 and semch["dom"]["habIcones"] == 0 and semch["cabe"] and semch["quem"] == "Selva · Summoner's Rift"
                and umaLinha(semch_longo["dom"]["nomeLinha"]) and semch_longo["cabe"] and semch_longo["dom"]["tags"] is None,
                "longo %s · sem campeão %s · sem campeão e longo %s" % (longo["dom"]["buildLinha"], {k: semch["dom"][k] for k in ("retrato", "nome", "build", "habLetras")},
                                                                        semch_longo["dom"]["nomeLinha"]))

        r.js("(() => { window.__inj = 0; return 1; })()")
        h1 = desenha(dict(base, nome='<img src=x onerror="window.__inj=1">Nome', autor="<b>QA</b>", descricao="<script>window.__inj=2</script>")); h1["dom"] = r.js(DOM)
        h1["tags"] = r.js("document.querySelectorAll('#card .build img, #card .pe b, #card script').length")
        h2 = desenha(dict(base, campeao=None, nome='<img src=x onerror="window.__inj=3">Sem', autor="")); h2["dom"] = r.js(DOM)
        time.sleep(0.4)
        inj = r.js("window.__inj")
        p.conta("card do Discord", "nome, autor e descrição com HTML saem como texto (com e sem campeão), sem rodar nada",
                inj == 0 and h1["dom"]["build"].startswith("<img") and h1["dom"]["pe"].startswith("por <b>QA</b>") and h1["tags"] == 0
                and h2["dom"]["nome"].startswith("<img"),
                "inj %r · build %r · pe %r · sem campeão %r" % (inj, h1["dom"]["build"][:20], h1["dom"]["pe"], h2["dom"]["nome"][:20]))

        a1 = desenha(base); a1["dom"] = r.js(DOM)
        a2 = desenha(dict(base, autor="")); a2["dom"] = r.js(DOM)
        a3 = desenha(dict(base, autor="Brelgo - criada por Mylon, Kennzy, e mais uma turma inteira de amigos da selva e do rio")); a3["dom"] = r.js(DOM)
        a4 = desenha(dict(base, autor="", patch="")); a4["dom"] = r.js(DOM)
        p.conta("card do Discord", "o rodapé: \"por <autor> · patch\"; sem autor, só o patch (sem \"por\"); sem os dois, sem rodapé; o autor comprido corta com \"…\" dentro do card — e o card cabe",
                a1["pe"] == "por Brelgo · patch " + patch and a1["dom"]["pe"] == a1["pe"] and not a1["dom"]["peLinha"]["corta"]
                and a2["pe"] == "patch " + patch and a2["dom"]["pe"] == "patch " + patch and "por" not in a2["dom"]["pe"].lower()
                and a4["pe"] == "" and a4["dom"]["pe"] is None
                and a3["dom"]["peLinha"]["corta"] and a3["dom"]["peLinha"]["reticencias"] and a3["dom"]["peLinha"]["dentro"] and a3["cabe"],
                "curto %r · sem autor %r · sem nada %r · comprido %s cabe %s" % (a1["dom"]["pe"], a2["dom"]["pe"], a4["dom"]["pe"], a3["dom"]["peLinha"], a3["cabe"]))

        ci = desenha(dict(base, campeao={"id": "CampeaoQueNaoExiste", "name": "Ninguém"}))
        p.conta("card do Discord", "campeão que o Data Dragon não tem: sem arte, sem o retrato e sem as habilidades — o desenho sai (as letras no lugar dos ícones, nada quebrado) e \"faltou\" diz o quê (o robô a dá por incompleta)",
                not ci["arte"] and ci["quebradas"] == 0 and "retrato" in ci["faltou"] and "habilidades" in ci["faltou"] and ci["cabe"] and cards.falta_algo(dict(base, campeao={"id": "X"}), ci),
                "%s" % {k: ci[k] for k in ("arte", "quebradas", "faltou", "cabe")})

        # o prazo: um endereço que não responde vira falha em vez de pendurar o desenho (e a rodada inteira)
        prazo = r.js("Promise.race([carregar('%s__pendura', 400).then(v => ({ v })), new Promise(ok => setTimeout(() => ok({ v: 'pendurou' }), 3000))])" % s.url)
    finally:
        r.fechar()

    # (d) a rede: as fontes e as habilidades do campeão, cada uma bloqueada numa aba nova
    rf = Sessao(s.url)
    fontes = {}

    def abre(sufixo, limite=20):
        rf.envia("Page.navigate", {"url": s.url + "data/robo/card.html?" + sufixo})
        fim = time.time() + limite
        while time.time() < fim and not rf.js("typeof window.desenhar === 'function'"):
            time.sleep(0.2)

    def tenta(nome, extra=None):
        try:
            d = rf.js("desenhar(%s)" % json.dumps(base, ensure_ascii=False))
            fontes[nome] = dict({"fontes": d["fontes"], "cabe": d["cabe"], "faltou": d["faltou"], "erro": None}, **(extra or {}))
            return d
        except RuntimeError as e:
            fontes[nome] = dict({"fontes": None, "erro": str(e)[:80]}, **(extra or {}))
            return None

    rede = {}
    try:
        rf.envia("Network.enable"); rf.envia("Network.setCacheDisabled", {"cacheDisabled": True})
        for nome, bloqueio in (("css", "*fonts.googleapis.com*"), ("arquivo", "*fonts.gstatic.com*")):
            rf.envia("Network.setBlockedURLs", {"urls": [bloqueio]})
            abre(nome)
            tenta(nome)
        # só o itálico da Alegreya (as tags) falhando: o card sai incompleto, não com uma linha em
        # Georgia. Os endereços dos arquivos vêm da própria folha, pedida com o navegador da aba
        href = re.search(r'<link id="fontes" href="([^"]+)"', open(os.path.join(RAIZ, "data", "robo", "card.html"), encoding="utf-8").read()).group(1).replace("&amp;", "&")
        folha = urllib.request.urlopen(urllib.request.Request(href, headers={"User-Agent": rf.js("navigator.userAgent")}), timeout=20).read().decode("utf-8")
        italicos = re.findall(r"font-family: 'Alegreya';\s*font-style: italic;[^}]*?url\((https://[^)]+)\)", folha)
        rf.envia("Network.setBlockedURLs", {"urls": italicos})
        abre("italico")
        tenta("italico", {"arquivos": len(italicos)})
        # F13-T98: as habilidades do campeão (o JSON do Data Dragon) que não vêm: o desenho sai com as
        # letras, "faltou" diz "habilidades" e o robô dá a foto por incompleta (tenta de novo na próxima)
        rf.envia("Network.setBlockedURLs", {"urls": ["*ddragon.leagueoflegends.com/cdn/*/data/pt_BR/champion/*"]})
        abre("habilidades")
        d = rf.js("desenhar(%s)" % json.dumps(base, ensure_ascii=False))
        rede["habilidades"] = {"faltou": d["faltou"], "arte": d["arte"], "fontes": d["fontes"], "quebradas": d["quebradas"], "cabe": d["cabe"],
                               "letras": rf.js("document.querySelectorAll('#card .hab .letra').length"), "incompleta": cards.falta_algo(base, d)}
        # e o retrato que não vem
        rf.envia("Network.setBlockedURLs", {"urls": ["*ddragon.leagueoflegends.com/cdn/*/img/champion/Ekko.png"]})
        abre("retrato")
        d = rf.js("desenhar(%s)" % json.dumps(base, ensure_ascii=False))
        rede["retrato"] = {"faltou": d["faltou"], "arte": d["arte"], "incompleta": cards.falta_algo(base, d)}
        # a folha do Google Fonts que nunca responde: o molde abre do mesmo jeito (ela não segura os
        # scripts) e o desenho sai no prazo, sem as fontes
        rf.envia("Network.setBlockedURLs", {"urls": []})
        rf.site_falso = lambda url: None
        rf.envia("Fetch.enable", {"patterns": [{"urlPattern": "https://fonts.googleapis.com/*", "requestStage": "Request"}]})
        t0 = time.time()
        rf.envia("Page.navigate", {"url": s.url + "data/robo/card.html?pendurado"})
        while time.time() - t0 < 8 and not rf.js("typeof window.desenhar === 'function'"):
            time.sleep(0.2)
        abriu = round(time.time() - t0, 1)
        tenta("pendurado", {"abriu": abriu})
        fontes["pendurado"]["desenhou"] = round(time.time() - t0, 1)
    finally:
        rf.fechar()
    p.conta("card do Discord", "a rede: sem a folha do Google Fonts, sem o arquivo da fonte, só sem o itálico da Alegreya ou com a folha que nunca responde, o molde abre e o desenho sai no prazo, marcado \"sem as fontes\" (o robô o dá por incompleto); um endereço que não responde vira falha no prazo, sem pendurar o desenho",
            prazo == {"v": False} and all(f["erro"] is None and f["fontes"] is False for f in fontes.values()) and len(fontes) == 4 and fontes["italico"]["arquivos"] > 0
            and fontes["pendurado"]["abriu"] < 5 and fontes["pendurado"].get("desenhou", 99) < 40,
            "prazo %s · sem fontes %s" % (prazo, fontes))
    hb, rt = rede.get("habilidades") or {}, rede.get("retrato") or {}
    p.conta("card do Discord", "a rede: as habilidades do campeão que não vêm (o JSON do Data Dragon bloqueado) — o desenho sai, com as letras no lugar dos ícones e nada quebrado, \"faltou\" diz \"habilidades\" e o robô a dá por incompleta; o retrato que não vem, o mesmo",
            hb.get("faltou") == ["habilidades"] and hb.get("arte") and hb.get("fontes") and hb.get("quebradas") == 0 and hb.get("cabe") and hb.get("letras") == 3 and hb.get("incompleta") is True
            and rt.get("faltou") == ["retrato"] and rt.get("arte") and rt.get("incompleta") is True,
            "habilidades %s · retrato %s" % (hb, rt))

    # (e) a página gerada
    ass = "f" * 24
    malvado = {"id": "abc123", "nome": 'Nome "aspas" <script>alert(1)</script>', "autor": "QA", "descricao": "d" * 400}
    pg = cards.pagina(malvado, {"quem": "Ekko · Selva"}, ass, "0123456789")
    pg_sem = cards.pagina(dict(malvado, autor="", descricao=""), {"quem": "Ekko"}, ass)
    pg_html = cards.pagina(dict(malvado, nome="X", autor="<b>QA</b>", descricao="<img src=x onerror=alert(1)>"), {"quem": "Ekko"}, ass)
    desc = re.search(r'<meta property="og:description" content="([^"]*)">', pg)
    ok_pg = ("<script>alert" not in pg and "&lt;script&gt;" in pg and "&quot;aspas&quot;" in pg
             and '<meta property="og:image" content="%sb/abc123/card.jpg?v=0123456789">' % cards.SITE in pg
             and '<meta property="og:url" content="%sb/abc123/">' % cards.SITE in pg
             and '<meta property="og:image:width" content="1200">' in pg and '<meta name="twitter:card" content="summary_large_image">' in pg
             and 'url=../../#build/abc123"' in pg and 'location.replace("../../#build/abc123")' in pg and '<meta name="forja:assinatura" content="%s">' % ass in pg
             and desc is not None and len(desc.group(1)) <= 200 and desc.group(1).startswith("Ekko · Selva · por QA — ddd") and desc.group(1).endswith("…")
             and '<meta property="og:description" content="Ekko">' in pg_sem
             and "<b>" not in pg_html and "<img" not in pg_html and "&lt;img src=x" in pg_html)
    p.conta("card do Discord", "a página b/<id>/: o nome, o autor e a descrição escapados, a imagem e o endereço com o site inteiro (a imagem com ?v= da assinatura), 1200×630, summary_large_image, a descrição de até 200 letras (sem \"por\" quando não há autor) e o caminho para o #build/<id>",
            ok_pg, "descrição %r · sem autor %r" % (desc.group(1)[:50] if desc else None, re.search(r'og:description" content="([^"]*)"', pg_sem).group(1)))

    # (f) a assinatura: muda com o que o card mostra, não com o que ele não mostra; o \r\n do Windows não conta
    b0 = {"id": "abc124", "nome": "X", "autor": "", "caixas": [], "runas": runas, "habilidades": ordem_qew, "engajamentos": 1, "atualizado_em": "a"}
    s0 = cards.assinatura(b0, "base")
    tmp = tempfile.mkdtemp(prefix="qa-card-")
    raiz_de_verdade = cards.RAIZ
    try:
        with open(os.path.join(tmp, "lf.txt"), "wb") as f:
            f.write(b"a\nb\n")
        with open(os.path.join(tmp, "crlf.txt"), "wb") as f:
            f.write(b"a\r\nb\r\n")
        mesmo_texto = cards.ler_texto(os.path.join(tmp, "lf.txt")) == cards.ler_texto(os.path.join(tmp, "crlf.txt"))
        # a base acompanha data/runas.js (a Ficha mostra os ícones das runas): numa cópia da pasta data
        os.makedirs(os.path.join(tmp, "data"))
        for arq in ("catalog.js", "runas.js"):
            shutil.copy(os.path.join(RAIZ, "data", arq), os.path.join(tmp, "data", arq))
        cards.RAIZ = tmp
        base0 = cards.base_da_assinatura()
        with open(os.path.join(tmp, "data", "runas.js"), "a", encoding="utf-8") as f:
            f.write("\n// runas novas\n")
        base_runas = cards.base_da_assinatura()
    finally:
        cards.RAIZ = raiz_de_verdade
        shutil.rmtree(tmp, ignore_errors=True)
    outras_runas = dict(runas, assinatura=runas["slots"][0])
    p.conta("card do Discord", "a assinatura muda com o nome, o autor, as caixas, as runas, a ordem das habilidades e a base (molde, catálogo, runas, robô); não muda com a popularidade nem a hora; o arquivo com \\r\\n (Windows) e com \\n (o robô) dá o mesmo texto; o servidor é lido com as runas e as habilidades",
            s0 == cards.assinatura(dict(b0, engajamentos=9, atualizado_em="b"), "base") and s0 != cards.assinatura(dict(b0, nome="Y"), "base")
            and s0 != cards.assinatura(dict(b0, autor="Z"), "base") and s0 != cards.assinatura(dict(b0, caixas=[{"kind": "comum"}]), "base")
            and s0 != cards.assinatura(dict(b0, runas=outras_runas), "base") and s0 != cards.assinatura(dict(b0, runas=None), "base")
            and s0 != cards.assinatura(dict(b0, habilidades=list(reversed(ordem_qew))), "base") and s0 != cards.assinatura(dict(b0, habilidades=[]), "base")
            and s0 != cards.assinatura(b0, "outra base") and base0 != base_runas and mesmo_texto
            and "runas" in cards.CAMPOS and "habilidades" in cards.CAMPOS,
            "assinatura %s · base com runas %s · \\r\\n igual %s · campos %s" % (s0, base0 != base_runas, mesmo_texto, ",".join(cards.CAMPOS)))

    # (g) a rodada do robô, numa pasta temporária, com o Chrome de verdade
    tmp = tempfile.mkdtemp(prefix="qa-cards-")
    try:
        os.makedirs(os.path.join(tmp, "abc123"))          # a página de uma build que saiu
        os.makedirs(os.path.join(tmp, "notas"))           # pasta que não é de build: o robô não mexe
        with open(os.path.join(tmp, "LEIAME.txt"), "w") as f:
            f.write("x")
        bq = {"id": "abc124", "nome": "Card QA", "autor": "roteiro", "campeao": {"id": "Ekko", "name": "Ekko"}, "modo": "Summoner's Rift",
              "rota": "selva", "patch": patch, "caixas": caixas, "descricao": "", "runas": runas, "habilidades": ordem_qew}
        e0 = cards.rodar([], tmp)
        sobrou0 = os.path.isdir(os.path.join(tmp, "abc123"))
        e1 = cards.rodar([bq], tmp)
        jpg = open(os.path.join(tmp, "abc124", "card.jpg"), "rb").read()
        tam = _jpeg_tamanho(jpg)
        gravada = cards.assinatura_gravada(os.path.join(tmp, "abc124"))
        import hashlib
        versao_de = lambda pasta: (re.search(r'card\.jpg\?v=([0-9a-f]{10})"', open(os.path.join(tmp, pasta, "index.html"), encoding="utf-8").read()) or [None, None])[1]
        v1 = versao_de("abc124")
        e2 = cards.rodar([bq], tmp)
        e3 = cards.rodar([dict(bq, nome="Card QA novo")], tmp)
        e3r = cards.rodar([dict(bq, nome="Card QA novo", habilidades=list(reversed(ordem_qew)))], tmp)
        os.makedirs(os.path.join(tmp, "abc125"))
        e4 = cards.rodar([dict(bq, nome="Card QA novo")], tmp, so={"abc124"})
        sobrou4 = os.path.isdir(os.path.join(tmp, "abc125"))
        bx = dict(bq, id="abc126", campeao={"id": "CampeaoQueNaoExiste", "name": "Ninguém"})
        e5 = cards.rodar([dict(bq, nome="Card QA novo"), bx], tmp)
        g5 = cards.assinatura_gravada(os.path.join(tmp, "abc126")) or ""
        e6 = cards.rodar([dict(bq, nome="Card QA novo"), bx], tmp)
        jpg6 = open(os.path.join(tmp, "abc126", "card.jpg"), "rb").read()
        v6 = versao_de("abc126")
        e7 = cards.rodar([dict(bq, nome="Card QA novo"), dict(bx, nome="Card QA renomeada")], tmp)
        pg7 = open(os.path.join(tmp, "abc126", "index.html"), encoding="utf-8").read()
        jpg7 = open(os.path.join(tmp, "abc126", "card.jpg"), "rb").read()
        v7 = versao_de("abc126")
        resto = sorted(os.listdir(tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    p.conta("card do Discord", "a rodada do robô: o servidor vazio não apaga nada; a build nova ganha a página e um JPEG 1200×630 com a assinatura (e o ?v= da imagem tirado dos bytes dela); de novo, igual (sem foto); mudou o nome ou a ordem das habilidades, refaz; a página da build que saiu é apagada, a pasta que não é de build fica; com --so, nada é apagado",
            not e0["apagadas"] and sobrou0 and e1["novas"] == ["abc124"] and e1["apagadas"] == ["abc123"] and tam == (1200, 630)
            and v1 == hashlib.sha256(jpg).hexdigest()[:10] and not e1["incompletas"]
            and gravada == cards.assinatura(bq, cards.base_da_assinatura()) and e2["iguais"] == 1 and not e2["novas"] and not e2["refeitas"]
            and e3["refeitas"] == ["abc124"] and e3r["refeitas"] == ["abc124"] and sobrou4 and not e4["apagadas"] and "notas" in resto and "LEIAME.txt" in resto,
            "vazio %s · 1ª %s · %s · igual %s · mudou %s · a ordem %s · --so %s · pasta %s" % (
                e0["apagadas"], {k: e1[k] for k in ("novas", "apagadas", "incompletas")}, tam, e2["iguais"], e3["refeitas"], e3r["refeitas"], e4["apagadas"], resto))
    p.conta("card do Discord", "a build cujo campeão o Data Dragon não deu fica \"incompleta\": ganha a página (o card sem arte), mas com a assinatura marcada — a próxima rodada tenta de novo (e, sem arte outra vez, fica o card que já estava)",
            e5["incompletas"] == ["abc126"] and "abc126" in e5["novas"] and g5.startswith("incompleta-") and e6["incompletas"] == ["abc126"] and not e6["refeitas"] and e6["iguais"] == 1
            and e7["incompletas"] == ["abc126"] and '<meta property="og:title" content="Card QA renomeada">' in pg7 and jpg7 == jpg6 and v7 == v6 and v6 is not None,
            "1ª %s · assinatura %s… · 2ª %s · renomeada: título %s, card igual %s" % ({k: e5[k] for k in ("novas", "incompletas")}, g5[:16], {k: e6[k] for k in ("incompletas", "iguais")},
                                                                                  "Card QA renomeada" in pg7, jpg7 == jpg6))

    # (h) cada build por si: a que quebra fica de fora, o Chrome é reaberto e as outras seguem; a foto
    # sem as fontes é incompleta; a que o molde diz que faltou algo (as habilidades) também. Um
    # fotógrafo de mentira faz o papel do Chrome (o quebrado continua quebrado)
    class FotoFalsa:
        criadas = 0
        pagina_sem_fonte = None
        tentativas_205 = 0

        def __init__(self):
            FotoFalsa.criadas += 1
            self.quebrada = False

        def card(self, b):
            if self.quebrada:
                raise RuntimeError("a conversa com o Chrome parou no meio")
            if b["id"] == "abc201":
                self.quebrada = True
                raise RuntimeError("o desenho quebrou")
            if b["id"] == "abc204":     # a fonte falhou nesta página: nela, falha sempre; num Chrome novo, vem
                if FotoFalsa.pagina_sem_fonte is None:
                    FotoFalsa.pagina_sem_fonte = self
                return {"arte": True, "fontes": self is not FotoFalsa.pagina_sem_fonte, "quebradas": 0, "faltou": [], "quem": "QA"}, b"\xff\xd8 card 204"
            if b["id"] == "abc205":     # F13-T98: as habilidades do campeão não vieram (as duas vezes)
                FotoFalsa.tentativas_205 += 1
                return {"arte": True, "fontes": True, "quebradas": 0, "faltou": ["habilidades"], "quem": "QA"}, b"\xff\xd8 card 205"
            return {"arte": True, "fontes": b["id"] != "abc203", "quebradas": 0, "faltou": [], "quem": "QA"}, b"\xff\xd8 card de mentira"

        def fechar(self):
            pass

    tmp = tempfile.mkdtemp(prefix="qa-cards-")
    foto_de_verdade = cards.Fotografo
    cards.Fotografo = FotoFalsa
    try:
        try:
            f1 = cards.rodar([dict(bq, id="abc200"), dict(bq, id="abc201"), dict(bq, id="abc202"), dict(bq, id="abc203"), dict(bq, id="abc204"), dict(bq, id="abc205")], tmp)
            f1_erro = None
        except Exception as e:
            f1, f1_erro = {}, "%s: %s" % (type(e).__name__, str(e)[:80])
        g203 = cards.assinatura_gravada(os.path.join(tmp, "abc203")) or ""
        g205 = cards.assinatura_gravada(os.path.join(tmp, "abc205")) or ""
        feitas = sorted(d for d in os.listdir(tmp) if os.path.exists(os.path.join(tmp, d, "index.html")))
    finally:
        cards.Fotografo = foto_de_verdade
        shutil.rmtree(tmp, ignore_errors=True)
    p.conta("card do Discord", "a rodada não cai por uma build: a que quebra fica de fora (anotada em falhas), o Chrome é reaberto e as outras seguem; a foto sem as fontes tenta de novo num Chrome novo (a falha fica na página) e, faltando ainda, fica incompleta; a que saiu sem as habilidades tenta de novo e fica incompleta",
            f1_erro is None and len(f1.get("falhas", [])) == 1 and f1["falhas"][0].startswith("abc201") and feitas == ["abc200", "abc202", "abc203", "abc204", "abc205"]
            and FotoFalsa.criadas == 4 and f1["incompletas"] == ["abc203", "abc205"] and g203.startswith("incompleta-") and g205.startswith("incompleta-")
            and FotoFalsa.tentativas_205 == 2,
            "erro %s · falhas %s · feitas %s · Chromes %d · incompletas %s · tentativas sem as habilidades %d" % (
                f1_erro, f1.get("falhas"), feitas, FotoFalsa.criadas, f1.get("incompletas"), FotoFalsa.tentativas_205))

    # (h2) a rede pendurada deixa cada foto lenta: passou do orçamento, o que falta fica para a próxima
    # rodada (sem apagar a página que já existia) e o que ficou pronto é gravado
    class FotoLenta:
        def __init__(self):
            pass

        def card(self, b):
            time.sleep(0.4)
            return {"arte": True, "fontes": True, "quebradas": 0, "faltou": [], "quem": "QA"}, b"\xff\xd8 card lento"

        def fechar(self):
            pass

    tmp = tempfile.mkdtemp(prefix="qa-cards-")
    os.makedirs(os.path.join(tmp, "abc214"))
    with open(os.path.join(tmp, "abc214", "index.html"), "w", encoding="utf-8") as f:
        f.write("a página da rodada anterior")
    cards.Fotografo = FotoLenta
    try:
        o1 = cards.rodar([dict(bq, id="abc21%d" % k) for k in range(5)], tmp, orcamento=1.0)
        velha = open(os.path.join(tmp, "abc214", "index.html"), encoding="utf-8").read()
    finally:
        cards.Fotografo = foto_de_verdade
        shutil.rmtree(tmp, ignore_errors=True)
    p.conta("card do Discord", "a rodada tem orçamento de tempo: passou, as builds que faltam ficam para a próxima (anotadas, sem apagar a página que já tinham) e as feitas vão para o commit",
            bool(o1["adiadas"]) and o1["novas"] + o1["adiadas"] == ["abc21%d" % k for k in range(5)] and o1["adiadas"][-1] == "abc214"
            and velha == "a página da rodada anterior" and not o1["apagadas"],
            "feitas %s · adiadas %s · a página antiga %s" % (o1["novas"], o1["adiadas"], "ficou" if velha.startswith("a página") else "sumiu"))

    # (i) a lista vem inteira, de página em página (o servidor corta em 1000, ou menos); resposta torta para tudo
    import io
    todas = [{"id": "%06x" % k} for k in range(2500)]
    respostas = {"modo": "lista", "select": None}

    def urlopen_falso(pedido, timeout=None):
        u = pedido.full_url
        respostas["select"] = (re.search(r"select=([^&]+)", u) or [None, None])[1]
        if respostas["modo"] == "erro":
            return io.BytesIO(json.dumps({"message": "erro do servidor"}).encode())
        off = int(re.search(r"offset=(\d+)", u).group(1)) if "offset=" in u else 0
        lim = int(re.search(r"limit=(\d+)", u).group(1)) if "limit=" in u else 10 ** 9
        return io.BytesIO(json.dumps(todas[off:off + min(lim, 700)]).encode())

    urlopen_de_verdade = cards.urllib.request.urlopen
    cards.urllib.request.urlopen = urlopen_falso
    try:
        lidas = cards.buscar_publicas()
        select = (respostas["select"] or "").split(",")
        respostas["modo"] = "erro"
        try:
            cards.buscar_publicas()
            torta = "passou"
        except RuntimeError as e:
            torta = str(e)[:60]
    finally:
        cards.urllib.request.urlopen = urlopen_de_verdade
    p.conta("card do Discord", "a lista das públicas vem inteira, de página em página, mesmo com o servidor cortando em menos de 1000 (antes, acima de 1000 o robô apagava a página das que ficavam fora), pedindo as runas e as habilidades; a resposta que não é lista interrompe a rodada",
            len(lidas) == 2500 and len({b["id"] for b in lidas}) == 2500 and torta.startswith("o servidor não devolveu") and "runas" in select and "habilidades" in select,
            "lidas %d · select %s · resposta torta: %s" % (len(lidas), ",".join(select), torta))

    # (j) o molde que não abre: o robô desiste com o motivo e não deixa o Chrome aberto
    tmp = tempfile.mkdtemp(prefix="qa-cards-")
    procs = []
    popen_de_verdade, molde_de_verdade, espera_de_verdade = cards.subprocess.Popen, cards.MOLDE, cards.ESPERA_MOLDE

    def popen_anotado(*a, **k):
        pr = popen_de_verdade(*a, **k)
        procs.append(pr)
        return pr

    vazio = os.path.join(tmp, "molde_vazio.html")
    with open(vazio, "w", encoding="utf-8") as f:
        f.write("<!doctype html><title>sem desenho</title>")
    cards.subprocess.Popen, cards.MOLDE, cards.ESPERA_MOLDE = popen_anotado, vazio, 1
    try:
        try:
            cards.Fotografo().fechar()
            motivo = "abriu"
        except RuntimeError as e:
            motivo = str(e)
        time.sleep(0.5)
        vivos = [pr for pr in procs if pr.poll() is None]
    finally:
        cards.subprocess.Popen, cards.MOLDE, cards.ESPERA_MOLDE = popen_de_verdade, molde_de_verdade, espera_de_verdade
        for pr in procs:
            if pr.poll() is None:
                pr.kill()
        shutil.rmtree(tmp, ignore_errors=True)
    p.conta("card do Discord", "o molde que não abre: o robô desiste dizendo o motivo e fecha o Chrome que abriu (nada fica rodando com a porta de depuração aberta)",
            "não carregou" in motivo and len(procs) == 1 and not vivos,
            "motivo %r · Chromes abertos %d · ainda vivos %d" % (motivo[:50], len(procs), len(vivos)))


def _link_curto_lento(s, p, ID, NOME):
    """F13-T91, revisão do cético (30/10/2026): a build do link a CAMINHO. Servidor simulado LENTO — a
    pública do link responde depois de `__atraso` ms (a lista vem na hora, só com "Outra QA", bbb222).
    Sem a demora, o cancelamento nunca é exercido: o grupo passava 5/5 com ele arrancado. Todo gesto
    é clique de verdade (o voltar do navegador é o history.back, que é o que o botão faz)."""
    OUTRA = "bbb222"
    falso = r"""(() => {
      const ID = '%s', NOME = '%s', OUTRA = '%s';
      window.__atraso = Number(new URLSearchParams(location.search).get('atraso') || 0);
      const linha = (id, nome) => { const C = window.CATALOG;
        return { id, nome, descricao: 'pública lenta do roteiro', campeao: null, modo: '', marcadores: [],
          caixas: [{ name: 'Núcleo', kind: 'comum', items: C.items.filter(i => i.tier === 'Lendário').slice(0, 3).map(i => ({ itemId: i.slug })) }],
          versao: 2, atualizado_em: new Date().toISOString(), patch: C.meta.patch, autor: 'roteiro', engajamentos: 0,
          pop_dia: 0, popular_semana: false, dias_no_top: 0, layout: null, runas: null, habilidades: null }; };
      window.__copiado = [];
      const f = window.fetch;
      window.fetch = function (u, ...a) {
        const t = String(u && u.url || u);
        if (!t.includes('supabase.co')) return f.call(this, u, ...a);
        const ok = (c) => new Response(JSON.stringify(c), { status: 200, headers: { 'Content-Type': 'application/json' } });
        if (!t.includes('/rest/v1/builds_publicas')) return Promise.resolve(ok(null));
        if (t.includes('id=eq.' + ID)) return new Promise(r => setTimeout(() => r(ok([linha(ID, NOME)])), window.__atraso));
        if (t.includes('id=eq.' + OUTRA)) return Promise.resolve(ok([linha(OUTRA, 'Outra QA')]));
        if (t.includes('id=eq.') || t.includes('id=in.')) return Promise.resolve(ok([]));
        return Promise.resolve(ok([linha(OUTRA, 'Outra QA')]));
      };
      try { navigator.clipboard.writeText = (x) => { window.__copiado.push(String(x)); return Promise.resolve(); }; } catch (e) {}
    })();""" % (ID, NOME, OUTRA)
    estado = """(() => ({ hash: location.hash, aba: document.querySelector('.tab-btn.active') ? document.querySelector('.tab-btn.active').dataset.tab : null,
      forja: !document.getElementById('build-editor').hidden, lista: !document.getElementById('build-index').hidden, view: biView,
      temp: !!build.temp, origem: build.pubOrigem || null, nome: build.name, pend: linkCurto.pendente, aberto: linkCurto.aberto,
      sel: biSelected, linhaSel: (document.querySelector('.bi-row.sel') || { dataset: {} }).dataset.id || null,
      resumo: (document.getElementById('bi-detail').innerText || '').slice(0, 160), sujo: rascunho.sujo,
      dialogo: !document.getElementById('save-dialog').hidden }))()"""
    r = Sessao(s.url)

    def espera(expr, limite=8.0):
        fim = time.time() + limite
        while time.time() < fim:
            try:
                if r.js(expr):
                    return True
            except RuntimeError:
                pass
            time.sleep(0.2)
        return False

    def recarregar():
        r.envia("Page.reload", {})
        fim = time.time() + 30
        while time.time() < fim:
            msg = json.loads(r.ws.recv())
            r._anota(msg)
            if msg.get("method") == "Page.loadEventFired":
                break
        time.sleep(1.5)

    def link_a_caminho(atraso=2500):
        """Põe o link no endereço (como colar na barra) e espera a lista das Públicas com a placa."""
        r.js("(() => { window.__atraso = %d; location.hash = '#build/%s'; return 1; })()" % (atraso, ID))
        espera("linkCurto.pendente === '%s' && !!document.querySelector('.bi-row[data-pub=\"%s\"]')" % (ID, OUTRA), 5)
        time.sleep(0.4)

    def curto(q):
        return {k: q[k] for k in ("hash", "aba", "forja", "view", "temp", "nome", "pend", "aberto", "sel")}

    try:
        r.envia("Page.addScriptToEvaluateOnNewDocument", {"source": falso})
        r.tela(1600, 900)
        r.erros.clear()

        # (e) a espera tem cara: a placa "Abrindo a build <id>" e nenhuma linha escolhida sozinha
        r.abrir("?lento=1#catalogo"); r.entrar()
        link_a_caminho()
        e0 = r.js(estado)
        p.conta("link curto", "servidor lento: enquanto a build do link vem, o resumo mostra a placa \"Abrindo a build <id>\" e a lista das Públicas não escolhe outra build sozinha",
                e0["pend"] == ID and e0["view"] == "publicas" and "Abrindo a build" in e0["resumo"] and ID in e0["resumo"]
                and e0["sel"] is None and e0["linhaSel"] is None and "Outra QA" not in e0["resumo"],
                "%s · linha escolhida %r · resumo %r" % (curto(e0), e0["linhaSel"], e0["resumo"][:70]))

        # (f) achado 3: durante a espera, a aba Minhas, uma linha das Públicas e a busca cancelam
        r.clicar('.bi-row[data-pub="%s"]' % OUTRA, 0.3)
        time.sleep(2.8)
        f1 = r.js(estado)
        r.abrir("?lento=2#catalogo"); r.entrar()
        link_a_caminho()
        r.clicar('.bi-tab[data-view="minhas"]', 0.3)
        time.sleep(2.8)
        f2 = r.js(estado)
        r.abrir("?lento=3#catalogo"); r.entrar()
        link_a_caminho()
        r.clicar("#bi-search", 0.2)
        r.envia("Input.insertText", {"text": "Outra"})
        time.sleep(2.8)
        f3 = r.js(estado)
        r.js("(() => { const b = document.getElementById('bi-search'); b.value = ''; b.dispatchEvent(new Event('input')); return 1; })()")
        ok_f = (not f1["temp"] and f1["pend"] is None and f1["hash"] == "#builds" and f1["sel"] == "pub:" + OUTRA and "Outra QA" in f1["resumo"]
                and not f2["temp"] and f2["pend"] is None and f2["view"] == "minhas" and f2["hash"] == "#builds" and "Abrindo" not in f2["resumo"]
                and not f3["temp"] and f3["pend"] is None and f3["hash"] == "#builds" and "Abrindo" not in f3["resumo"])
        p.conta("link curto", "servidor lento: durante a espera, clicar numa linha das Públicas, na aba Minhas ou digitar na busca cancela — a build do link não abre por cima e o # vira #builds",
                ok_f, "linha %s · Minhas %s · busca %s" % (curto(f1), curto(f2), curto(f3)))

        # (g) achado 1: o voltar do navegador durante a espera cancela (a pública não toma a forja)
        r.nova_build()
        r.js("(() => { build.name = 'Minha QA'; gravarBuild(); renderBuildAll(); return 1; })()")
        time.sleep(0.4)
        g0 = r.js(estado)
        link_a_caminho()
        r.js("history.back(); 1")
        time.sleep(3.0)
        g1 = r.js(estado)
        p.conta("link curto", "servidor lento: o voltar do navegador durante a espera cancela — a forja fica com a build de antes, o # volta a #forja e a resposta que chega depois não reescreve nada",
                g0["hash"] == "#forja" and g1["hash"] == "#forja" and g1["forja"] and not g1["temp"] and g1["nome"] == "Minha QA"
                and g1["pend"] is None and g1["aberto"] is None,
                "antes %s · depois %s" % (curto(g0), curto(g1)))

        # (h) achado 2: sair da pública do link pelo "Copiar e editar" ou pelo ×: o # é o da tela e o F5 abre a da forja
        r.abrir("?lento=4&atraso=1500#build/" + ID)
        espera("build.temp && build.pubOrigem === '%s' && !document.getElementById('build-editor').hidden" % ID, 6)
        time.sleep(0.6)
        h0 = r.js(estado)
        r.clicar("#temp-copiar", 0.8)
        h1 = r.js(estado)
        recarregar()
        h2 = r.js(estado)
        r.abrir("?lento=5&atraso=1500#build/" + ID)
        espera("build.temp && build.pubOrigem === '%s' && !document.getElementById('build-editor').hidden" % ID, 6)
        time.sleep(0.6)
        r.clicar("#bg-fechar", 0.8)
        h3 = r.js(estado)
        recarregar()
        h4 = r.js(estado)
        ok_h = (h0["temp"] and h0["hash"] == "#build/" + ID
                and h1["hash"] == "#forja" and not h1["temp"] and h1["aberto"] is None and h1["nome"] == NOME
                and h2["hash"] == "#forja" and not h2["temp"] and h2["nome"] == NOME
                and not h3["hash"].startswith("#build/") and not h3["temp"] and h3["aberto"] is None
                and not h4["temp"] and not h4["hash"].startswith("#build/"))
        p.conta("link curto", "servidor lento: na pública aberta pelo link, \"Copiar e editar\" e o × da plaqueta esquecem o link — o # vira o da tela e o F5 abre a build que está na forja, não a pública",
                ok_h, "aberta %s · Copiar e editar %s · F5 %s · × %s · F5 %s" % (curto(h0)["hash"], curto(h1), curto(h2), curto(h3), curto(h4)))

        # (i) achado 4: rascunho sujo + link, "Continuar editando": tudo como antes do link
        espera("!!build.id && !document.getElementById('build-editor').hidden", 3)
        if not r.js("document.getElementById('entrada').classList.contains('fechada')"):
            r.entrar()
        r.js("(() => { rascunho.sujo = true; refletirSalvar(); return 1; })()")
        time.sleep(0.3)
        i0 = r.js(estado)
        r.js("(() => { window.__atraso = 1500; location.hash = '#build/%s'; return 1; })()" % ID)
        espera("!document.getElementById('save-dialog').hidden", 6)
        time.sleep(0.4)
        i1 = r.js(estado)
        if i1["dialogo"]:   # sem diálogo, a falha fica na checagem
            r.clicar('[data-sd="voltar"]', 0.8)
        i2 = r.js(estado)
        p.conta("link curto", "servidor lento: com rascunho sujo, abrir o link e escolher \"Continuar editando\" deixa tudo como antes — a forja na tela, o # dela, o rascunho e nada marcado",
                i1["dialogo"] and i2["forja"] and i2["aba"] == "build" and i2["hash"] == i0["hash"] == "#forja" and i2["nome"] == i0["nome"]
                and not i2["temp"] and i2["sujo"] and i2["aberto"] is None and i2["pend"] is None and i2["sel"] != "pub:" + ID and not i2["dialogo"],
                "antes %s · diálogo %s · depois %s" % (curto(i0), i1["dialogo"], curto(i2)))
        r.js("(() => { descartarAlteracoes(); return 1; })()")

        # (j) a publicada SEM caixas: o Copiar link da forja sai pelo curto; a não publicada sem caixas segue recusando
        r.js("""(() => { const b = library.builds.find(x => x.id === build.id); b.cats = []; build.cats = []; b.pubId = build.pubId = '%s'; b.pubVersao = build.pubVersao = 2;
          gravarBiblioteca(); renderBuildAll(); window.__copiado = []; return 1; })()""" % ID)
        time.sleep(0.4)
        if not r.js("document.getElementById('io-panel').classList.contains('show')"):
            r.clicar("#toggle-io", 0.5)
        r.clicar("#link-btn", 0.6)
        j1 = r.js("({ ult: window.__copiado[window.__copiado.length - 1] || null, msg: document.getElementById('io-msg').textContent, base: location.href.split('#')[0] })")
        r.js("""(() => { const b = library.builds.find(x => x.id === build.id); b.pubId = build.pubId = null; b.pubVersao = build.pubVersao = 0;
          gravarBiblioteca(); renderBuildAll(); window.__copiado = []; return 1; })()""")
        time.sleep(0.3)
        r.clicar("#link-btn", 0.6)
        j2 = r.js("({ n: window.__copiado.length, msg: document.getElementById('io-msg').textContent })")
        p.conta("link curto", "Copiar link da forja numa build publicada sem caixas copia o link curto (a recusa \"ainda não tem categorias\" fica só para o #b= da não publicada)",
                j1["ult"] == ((SITE + "b/%s/" % ID) if j1["base"].startswith(SITE) else j1["base"] + "#build/" + ID) and "Link curto copiado" in j1["msg"] and j2["n"] == 0 and "ainda não tem categorias" in j2["msg"],
                "publicada %r / %r · não publicada %r" % (j1["ult"], j1["msg"][:50], j2))

        # (k) F13-T92, o 1º caso raro do cético: rascunho sujo + link + o VOLTAR do navegador com o
        # "Salvar e sair?" aberto. Antes o diálogo ficava na tela e o Descartar abria a pública que o
        # jogador tinha deixado para trás; agora o voltar vale "Continuar editando".
        def sujo_com_link():
            r.js("(() => { rascunho.sujo = true; refletirSalvar(); window.__atraso = 300; location.hash = '#build/%s'; return 1; })()" % ID)
            espera("!document.getElementById('save-dialog').hidden", 6)
            time.sleep(0.4)
            return r.js(estado)
        r.abrir("?lento=6#catalogo"); r.entrar()
        r.nova_build()
        r.js("(() => { build.name = 'Suja QA'; build.cats[0].items.push({ itemId: CATALOG.items.find(i => i.tier === 'Épico').slug, note: '' }); gravarBuild(); renderBuildAll(); return 1; })()")
        time.sleep(0.4)
        k0 = r.js(estado)
        k1 = sujo_com_link()
        r.js("history.back(); 1")
        time.sleep(0.8)
        k2 = r.js(estado)
        if k2["dialogo"]:   # o diálogo que ficou (o defeito): o clique de verdade no Descartar mostra o que ele faz
            r.clicar('[data-sd="descartar"]', 0.8)
        k3 = r.js(estado)
        p.conta("link curto", "rascunho sujo + link: o voltar do navegador com o \"Salvar e sair?\" aberto vale \"Continuar editando\" — o diálogo fecha, a forja fica com a build e o rascunho, o # é #forja e a pública não abre",
                k0["hash"] == "#forja" and k1["dialogo"] and not k2["dialogo"] and k3["hash"] == "#forja" and k3["forja"] and k3["nome"] == "Suja QA"
                and k3["sujo"] and not k3["temp"] and k3["aberto"] is None and k3["pend"] is None,
                "antes %s · diálogo %s · depois do voltar %s (diálogo ainda aberto: %s)" % (curto(k0), k1["dialogo"], curto(k3), k2["dialogo"]))
        # o # de destino vale mesmo quando não é a tela de antes do link: voltar duas casas de uma vez
        r.js("(() => { descartarAlteracoes(); return 1; })()")
        r.clicar('.tab-btn[data-tab="runas"]', 0.6)
        r.clicar('.tab-btn[data-tab="build"]', 0.6)   # a aba Builds volta à forja, a tela em que se estava
        k4 = sujo_com_link()
        r.js("history.go(-2); 1")
        time.sleep(0.8)
        k5 = r.js(estado)
        # o caminho antigo, que agora passa pela mesma função: o Esc com o diálogo aberto
        r.js("(() => { descartarAlteracoes(); return 1; })()")
        r.clicar('.tab-btn[data-tab="build"]', 0.6)
        k6 = sujo_com_link()
        for tipo in ("rawKeyDown", "keyUp"):
            r.envia("Input.dispatchKeyEvent", {"type": tipo, "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27})
        time.sleep(0.6)
        k7 = r.js(estado)
        p.conta("link curto", "rascunho sujo + link: voltar duas casas com o diálogo aberto fecha o diálogo e abre a tela de destino com o # dela (#runas); o Esc continua valendo \"Continuar editando\"",
                k4["dialogo"] and not k5["dialogo"] and k5["hash"] == "#runas" and k5["aba"] == "runas" and k5["sujo"] and not k5["temp"] and k5["aberto"] is None
                and k6["dialogo"] and not k7["dialogo"] and k7["hash"] == "#forja" and k7["forja"] and k7["sujo"] and not k7["temp"] and k7["aberto"] is None,
                "duas casas %s (diálogo %s) · Esc %s (diálogo %s)" % (curto(k5), k5["dialogo"], curto(k7), k7["dialogo"]))
        r.js("(() => { descartarAlteracoes(); return 1; })()")

        # (l) F13-T92, o 2º caso raro: o voltar durante a espera devolve a tela de antes do link — a aba
        # Minhas com a linha que estava escolhida (antes ficavam as Públicas, sem nada escolhido). Página
        # nova: a pública que (k) abriu fica na memória da página e abriria na hora, sem espera
        r.abrir("?lento=8#catalogo"); r.entrar()
        r.js("""(() => { switchTab('build'); showBuildScreen('lista'); mostrarListaDe('minhas');
          biSelected = library.builds.find(b => b.name === 'Suja QA').id; renderBuildIndex(); return 1; })()""")
        time.sleep(0.5)
        l0 = r.js(estado)
        link_a_caminho()
        l1 = r.js(estado)
        r.js("history.back(); 1")
        time.sleep(3.0)   # a resposta lenta (2,5 s) chega depois do voltar e não pode mexer em nada
        l2 = r.js(estado)
        p.conta("link curto", "servidor lento: o voltar durante a espera devolve a aba Minhas com a linha que estava escolhida, e o # #builds",
                l0["hash"] == "#builds" and l0["view"] == "minhas" and l0["linhaSel"] and l1["pend"] == ID and l1["view"] == "publicas"
                and l2["hash"] == "#builds" and l2["lista"] and l2["view"] == "minhas" and l2["sel"] == l0["sel"] and l2["linhaSel"] == l0["linhaSel"]
                and l2["pend"] is None and not l2["temp"] and "Abrindo" not in l2["resumo"],
                "antes %s · a caminho %s · depois %s (linha %r → %r)" % (curto(l0), curto(l1), curto(l2), l0["linhaSel"], l2["linhaSel"]))

        # (m) o # de antes que não é tela: o #b= de um link de build. O voltar durante a espera devolve
        # a forja com a build desse link, e o # continua o #b= (antes ficava a lista das Públicas)
        longo = r.js("buildParaLink(library.builds.find(b => b.name === 'Suja QA'))")
        r.abrir("?lento=9#" + longo.split("#", 1)[1])
        espera("typeof build !== 'undefined' && build.name === 'Suja QA' && !document.getElementById('build-editor').hidden", 6)
        if not r.js("document.getElementById('entrada').classList.contains('fechada')"):
            r.entrar()
        time.sleep(0.4)
        m0 = r.js(estado)
        link_a_caminho()
        m1 = r.js(estado)
        r.js("history.back(); 1")
        time.sleep(3.0)
        m2 = r.js(estado)
        p.conta("link curto", "servidor lento: aberto por um link #b=, o voltar durante a espera devolve a forja com a build do #b= e o # dele",
                m0["hash"].startswith("#b=") and m0["forja"] and m1["pend"] == ID and not m1["forja"]
                and m2["hash"] == m0["hash"] and m2["forja"] and m2["aba"] == "build"
                and m2["nome"] == m0["nome"] == "Suja QA" and not m2["temp"] and m2["pend"] is None and m2["aberto"] is None,
                "antes %s · depois %s" % (curto(m0), curto(m2)))

        # (n) F13-T92, o achado do cético: durante a espera, o gesto que pergunta ("Nova build", o × da
        # plaqueta, "parar de editar") também cancela. Antes a resposta chegava com o diálogo aberto,
        # trocava o "depois" dele, e o Descartar ou o "Salvar e sair" abria a pública do link.
        def gesto_na_espera(n, sel, botao):
            r.abrir("?lento=%d#catalogo" % n); r.entrar()
            r.js("""(() => { activateBuild(library.builds.find(b => b.name === 'Suja QA').id); switchTab('build'); showBuildScreen('forja');
              window.ligarEdicao(true); rascunho.sujo = true; refletirSalvar(); return 1; })()""")
            time.sleep(0.4)
            q0 = r.js(estado); q0["nb"] = r.js("library.builds.filter(b => !b.temp).length")
            link_a_caminho()
            r.clicar(sel, 0.3)
            time.sleep(3.0)   # a resposta lenta (2,5 s) chega com o diálogo aberto
            q1 = r.js(estado)
            if q1["dialogo"]:
                r.clicar('[data-sd="%s"]' % botao, 0.8)
            q2 = r.js(estado); q2["nb"] = r.js("library.builds.filter(b => !b.temp).length")
            q2["editando"] = r.js("document.getElementById('edit-toggle') ? document.getElementById('edit-toggle').checked : null")
            return q0, q1, q2
        n_novo = gesto_na_espera(10, "#bi-new", "descartar")
        n_fecha = gesto_na_espera(11, "#bg-fechar", "descartar")
        n_parar = gesto_na_espera(12, "#bg-parar", "salvar")
        n_fica = gesto_na_espera(13, "#bi-new", "voltar")
        ok_n = all(q1["dialogo"] and q1["pend"] is None and q1["hash"] == "#builds" and not q1["temp"] and not q2["temp"]
                   and q2["aberto"] is None and q2["origem"] is None and not q2["dialogo"]
                   for (_, q1, q2) in (n_novo, n_fecha, n_parar, n_fica))
        q0, _, q2 = n_novo
        ok_n = ok_n and q2["forja"] and q2["hash"] == "#forja" and q2["nb"] == q0["nb"] + 1 and q2["nome"] != "Suja QA"
        _, _, q2 = n_fecha
        ok_n = ok_n and q2["lista"] and not q2["forja"] and q2["hash"] == "#builds"
        _, _, q2 = n_parar
        ok_n = ok_n and q2["nome"] == "Suja QA" and not q2["sujo"] and q2["editando"] is False
        _, _, q2 = n_fica
        ok_n = ok_n and q2["lista"] and q2["view"] == "publicas" and q2["sujo"] and q2["hash"] == "#builds" and "Abrindo" not in q2["resumo"]
        p.conta("link curto", "servidor lento: o gesto que pergunta durante a espera (Nova build, o × da plaqueta, \"parar de editar\") cancela o link — o Descartar, o \"Salvar e sair\" e o \"Continuar editando\" fazem o que o gesto pediu, e a pública não abre",
                ok_n, " · ".join("%s→%s %s" % (nome, b, curto(q[2])) for nome, b, q in
                                 (("Nova build", "descartar", n_novo), ("×", "descartar", n_fecha), ("parar", "salvar", n_parar), ("Nova build", "voltar", n_fica))))
        erros = list(r.erros)
        p.conta("link curto", "servidor lento: nenhuma exceção no console em todo o caminho do link a caminho", not erros, "%s" % erros[:2])
    finally:
        r.fechar()


# ---------------------------------------------------------------- principal
def checar_dicas(s, p):
    """F13-T101 (Leo, 02/11/2026: a opção 2 do tour — "o tour não deve ser algo massante", "pensando
    para um leigo"): a dica na hora. "Próxima"/"Entendi" passam, o ×, o Esc e o clique fora fecham (e o
    clique fora segue para onde foi dado); a leva vista não repete; "Sem dicas" desliga as automáticas; o
    "?" mostra as da tela de novo. F13-T103 ("muito pobre de conteúdo"; "deve ensinar os principais
    funcionamentos do montador"): 24 dicas (25 com a da estante, F13-T104) — as de chegada (até 4 por tela) e as da hora (o primeiro item,
    o Editar ligado, o primeiro Salvar, o Montar, a segunda visita); quem viu as da T101 não as revê.
    O resto do roteiro roda com as dicas desligadas (a barreira da Sessao); aqui elas ligam."""
    print("\n%sDICAS%s" % (AMARELO, FIM))
    s.tela(1440, 900)
    s.js("sessionStorage.setItem('qa.dicas', '1'); sessionStorage.removeItem('dicas.sessao'); 'ok'")
    s.limpar_memoria()
    estado = "({ ab: Dicas.aberta(), h3: (document.querySelector('.dn-balao h3') || {}).textContent || '', vistas: JSON.parse(localStorage.getItem('dicas.vistas') || '[]'), des: localStorage.getItem('dicas.desligadas') })"
    ab = lambda r: (r["ab"] or {}).get("id")

    def passa_todas():
        return s.js("""(async () => { const v = []; for (let k = 0; k < 12 && Dicas.aberta(); k++) { v.push(Dicas.aberta().id);
          document.querySelector('.dn-ok').click(); await new Promise(r => setTimeout(r, 120)); } return v; })()""")
    try:
        # 1. a entrada de pé não mostra dica; ao fechar, as 4 da loja aparecem, uma de cada vez, e a leva fica vista
        pre = s.js("({ de_pe: document.documentElement.classList.contains('com-entrada'), dica: !!document.querySelector('.dn-balao'), des: localStorage.getItem('dicas.desligadas') })")
        time.sleep(0.9)
        pre2 = s.js("!!document.querySelector('.dn-balao')")
        s.entrar()
        time.sleep(1.0)
        a = s.js(estado)
        p.conta("dicas", "com a entrada de pé nenhuma dica aparece; ao fechar, a 1ª das 4 da loja aparece e a leva fica vista",
                pre["de_pe"] and not pre["dica"] and not pre2 and pre["des"] is None and a["ab"] == {"tela": "loja", "i": 0, "total": 4, "id": "loja.shift"}
                and a["vistas"] == ["loja.shift", "loja.nucleo", "loja.filtros", "loja.levar"],
                "antes %s/%s · depois %s" % (pre, pre2, a))

        # 2. "Próxima" passa; o clique fora fecha e segue (a busca ganha o foco; a aba Runas abre e mostra a dela)
        s.clicar(".dn-ok", 0.4)
        b1 = s.js(estado)
        s.clicar("#search-input", 0.4)
        b0 = s.js("Object.assign(%s, { foco: document.activeElement && document.activeElement.id })" % estado)
        s.js("document.activeElement.blur(); Dicas.mostrar(); 'ok'")
        time.sleep(0.3)
        s.clicar('.tab-btn[data-tab="runas"]', 1.2)
        b2 = s.js("Object.assign(%s, { aba: document.querySelector('.tab-btn.active').dataset.tab })" % estado)
        p.conta("dicas", "\"Próxima\" passa para a 2ª; o clique fora do balão fecha a dica e segue para onde foi dado (a busca ganha o foco; a aba Runas abre e mostra a dela)",
                ab(b1) == "loja.nucleo" and b0["ab"] is None and b0["foco"] == "search-input"
                and b2["aba"] == "runas" and b2["ab"] == {"tela": "runas", "i": 0, "total": 2, "id": "runas.ler"},
                "%s · %s · %s" % (b1, b0, b2))

        # 3. o Esc fecha (a leva inteira fica vista); recarregando na mesma aba, nada volta
        s.envia("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
        s.envia("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
        time.sleep(0.3)
        c1 = s.js(estado)
        s.abrir()
        time.sleep(0.6)
        s.entrar()
        time.sleep(1.0)
        c2 = s.js(estado)
        s.js("switchTab('runas'); 'ok'")
        time.sleep(1.0)
        c3 = s.js(estado)
        p.conta("dicas", "o Esc fecha a leva inteira (a 2ª das runas também fica vista); recarregando na mesma aba (a mesma visita), a loja e as runas não mostram nada",
                c1["ab"] is None and c2["ab"] is None and c3["ab"] is None and "runas.trilhas" in c3["vistas"] and "volta" not in c3["vistas"],
                "%s · %s · %s" % (c1, c2, c3))

        # 4. "Sem dicas" desliga as automáticas; o "?" ainda mostra as da tela
        s.js("switchTab('calc'); 'ok'")
        time.sleep(1.0)
        d1 = s.js(estado)
        s.clicar(".dn-sem", 0.4)
        d2 = s.js(estado)
        s.js("switchTab('build'); showBuildScreen('lista'); 'ok'")
        time.sleep(1.2)
        d3 = s.js(estado)
        s.clicar("#dicas-btn", 0.5)
        d4 = s.js(estado)
        s.clicar(".dn-x", 0.3)
        x_fecha = s.js("Dicas.aberta() === null")
        p.conta("dicas", "\"Sem dicas\" fecha e desliga as automáticas (a lista de builds, nunca vista, fica sem); o \"?\" mostra as dela (3) mesmo assim; o × fecha",
                ab(d1) == "calc.puxar" and d2["ab"] is None and d2["des"] == "1" and d3["ab"] is None
                and d4["ab"] == {"tela": "builds", "i": 0, "total": 3, "id": "builds.oque"} and x_fecha,
                "%s · %s · %s · %s · × %s" % (d1, d2, d3, d4, x_fecha))

        # 5. os momentos: com tudo ligado de novo e uma aba nova (a 2ª visita), cada dica da hora chega no seu momento
        s.js("localStorage.removeItem('dicas.desligadas'); localStorage.removeItem('dicas.vistas'); sessionStorage.removeItem('dicas.sessao'); 'ok'")
        s.abrir()
        time.sleep(0.6)
        s.entrar()
        time.sleep(1.0)
        m_loja = passa_todas()
        s.nova_build()
        time.sleep(0.4)
        m_forja = passa_todas()
        s.clicar("#edit-switch", 1.2)
        m_editar = passa_todas()
        s.js("Dicas.fechar(); switchTab('catalog'); window.scrollTo(0, 0); build.selectedCatId = build.cats[0].id; renderBuildAll(); 'ok'")
        time.sleep(1.0)
        s.clicar("#grid .card", 1.2)
        m_item = passa_todas()
        s.js("switchTab('build'); showBuildScreen('forja'); window.scrollTo(0, 0); 'ok'")
        time.sleep(1.2)
        m_totais = passa_todas()
        s.clicar("#save-btn", 1.2)
        m_salvar = passa_todas()
        s.js("showBuildScreen('lista'); 'ok'")
        time.sleep(1.2)
        m_lista = passa_todas()
        # as 3 de chegada da lista já passaram: a nova_build atravessa a lista, e o clique no "+ Nova build" fecha a leva
        vistas_lista = s.js("JSON.parse(localStorage.getItem('dicas.vistas') || '[]')")
        s.js("switchTab('runas'); 'ok'")
        time.sleep(1.0)
        m_runas = passa_todas()
        s.clicar('.runas-modo[data-modo="montar"]', 1.2)
        m_montar = passa_todas()
        momentos = {"loja (2ª visita)": m_loja, "forja": m_forja, "Editar": m_editar, "item na loja": m_item, "forja com item": m_totais,
                    "Salvar": m_salvar, "lista": m_lista, "runas": m_runas, "Montar": m_montar}
        p.conta("dicas", "os momentos: a 2ª visita, o Editar ligado, o primeiro item (na loja e na forja), o primeiro Salvar (na forja e na lista) e o Montar trazem cada um as suas dicas, na hora",
                m_loja == ["loja.shift", "loja.nucleo", "loja.filtros", "loja.levar", "volta"]
                and m_forja == ["forja.caixas", "forja.campeao", "forja.ver", "forja.editar"]
                and m_editar == ["forja.arrastar", "forja.estante", "forja.papel", "forja.runashabs"] and m_item == ["loja.faixa"] and m_totais == ["forja.totais"]
                and m_salvar == ["forja.salvar"] and m_lista == ["builds.publicar"] and all(x in vistas_lista for x in ("builds.oque", "builds.importar", "builds.publicas"))
                and m_runas == ["runas.ler", "runas.trilhas"] and m_montar == ["runas.montar"],
                "%s" % momentos)

        # 6. nas três resoluções, cada uma das 26 dicas (com os momentos valendo) fica inteira na janela e não
        #    cobre o que aponta; e a "Caixa vazia" da forja (.slot-vazio.dica, de antes) segue intacta
        s.js("Dicas.fechar(); switchTab('build'); showBuildScreen('forja'); window.scrollTo(0, 0); 'ok'")
        time.sleep(0.9)
        vazia = s.js("(() => { Dicas.mostrar(); const v = document.querySelector('.build-cat .slot-vazio.dica'); const c = v && getComputedStyle(v); const r = v ? { pos: c.position, bg: c.backgroundImage.slice(0, 20), w: Math.round(v.getBoundingClientRect().width) } : null; Dicas.fechar(); return r; })()")
        mede = r"""(async () => {
          const out = []; if (!Dicas.mostrar()) return ['nada'];
          for (let k = 0; k < 12 && Dicas.aberta(); k++) {
            await new Promise(r => setTimeout(r, 120));
            const d = Dicas.atual(), b = document.querySelector('.dn-balao').getBoundingClientRect();
            const alvo = document.querySelector(d.alvo).getBoundingClientRect();
            const cobre = !(b.right <= alvo.left || b.left >= alvo.right || b.bottom <= alvo.top || b.top >= alvo.bottom);
            const dentro = b.left >= 0 && b.top >= 0 && b.right <= innerWidth && b.bottom <= innerHeight;
            const an = document.querySelector('.dn-anel').getBoundingClientRect();
            const torto = Math.abs(an.left - alvo.left + 6) > 2 || Math.abs(an.top - alvo.top + 6) > 2;
            out.push(d.id + (dentro ? '' : ':fora') + (cobre ? ':cobre' : '') + (torto ? ':anel' : ''));
            document.querySelector('.dn-ok').click();
          }
          return out; })()"""
        ruins, vistos = [], set()
        n_medidas = 0
        for w, h in ((1440, 900), (1920, 1080), (1600, 900)):
            s.tela(w, h)
            for passo in ("switchTab('catalog')", "switchTab('build'); showBuildScreen('lista')", "switchTab('build'); showBuildScreen('forja')",
                          "switchTab('runas')", "switchTab('mapa')", "switchTab('calc')"):
                s.js("Dicas.fechar(); window.scrollTo(0, 0); %s; 'ok'" % passo)
                time.sleep(0.9)
                r = s.js(mede)
                n_medidas += len(r)
                vistos |= {x.split(":")[0] for x in r}
                ruins += ["%dx%d %s" % (w, h, x) for x in r if ":" in x or x == "nada"]
        # a tela que entra animada (a forja sobe ao trocar de aba) move o alvo depois do primeiro quadro: o anel
        # e o balão seguem — mostrada logo na troca, a dica está no lugar quando a tela assenta
        s.tela(1440, 900)
        s.js("Dicas.fechar(); switchTab('catalog'); 'ok'")
        time.sleep(0.8)
        segue = s.js("""(async () => { switchTab('build'); showBuildScreen('lista'); Dicas.mostrar(); const d0 = Dicas.atual();
          await new Promise(r => setTimeout(r, 1300)); const d = Dicas.atual(); if (!d) return null;
          const a = document.querySelector('.dn-anel').getBoundingClientRect(), t = document.querySelector(d.alvo).getBoundingClientRect();
          return { id: d.id, dx: Math.round(a.left - t.left + 6), dy: Math.round(a.top - t.top + 6) }; })()""")
        s.js("Dicas.fechar(); 'ok'")
        p.conta("dicas", "a dica mostrada enquanto a tela ainda entra animada segue o alvo: quando a tela assenta, o anel está em volta dele",
                bool(segue) and abs(segue["dx"]) <= 2 and abs(segue["dy"]) <= 2, "%s" % segue)
        todas = s.js("Dicas.DICAS.map(d => d.id)")
        faltam = [x for x in todas if x not in vistos]
        p.conta("dicas", "nas três resoluções, cada uma das %d dicas fica inteira na janela e não cobre o que aponta; a \"Caixa vazia\" da forja segue intacta com o balão aberto" % len(todas),
                len(todas) == 26 and not faltam and not ruins and n_medidas == 78
                and bool(vazia) and vazia["pos"] == "static" and "url(" not in vazia["bg"] and vazia["w"] <= 90,
                "%d medidas · faltaram: %s · ruins: %s · caixa vazia %s" % (n_medidas, faltam or "nenhuma", ", ".join(ruins[:6]) or "nenhuma", vazia))
        s.tela(1440, 900)

        # 7. quem viu as dicas da T101 (que marcavam a tela inteira) só ganha as novas
        s.js("Dicas.fechar(); localStorage.setItem('dicas.vistas', JSON.stringify(['loja', 'forja', 'builds', 'runas', 'calc'])); switchTab('catalog'); 'ok'")
        time.sleep(1.0)
        mig = passa_todas()
        mig_v = s.js("JSON.parse(localStorage.getItem('dicas.vistas'))")
        p.conta("dicas", "quem já tinha visto as dicas da T101 não as revê: na loja só chegam as novas, e a memória antiga vira a das dicas",
                mig == ["loja.nucleo", "loja.filtros", "loja.faixa", "volta"] and "loja" not in mig_v and "loja.shift" in mig_v and "calc.puxar" in mig_v,
                "%s · %s" % (mig, mig_v))

        # 8. menos movimento para o anel; e nenhum número nos textos (dado de item não entra em dica)
        s.js("Dicas.fechar(); switchTab('catalog'); document.body.classList.add('ac-movimento'); Dicas.mostrar(); 'ok'")
        time.sleep(0.3)
        anim = s.js("getComputedStyle(document.querySelector('.dn-anel')).animationName")
        s.js("Dicas.fechar(); document.body.classList.remove('ac-movimento'); 'ok'")
        s.envia("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
        s.js("Dicas.mostrar(); 'ok'")
        time.sleep(0.3)
        anim_sis = s.js("getComputedStyle(document.querySelector('.dn-anel')).animationName")
        s.envia("Emulation.setEmulatedMedia", {"features": []})
        s.js("Dicas.fechar(); 'ok'")
        digitos = s.js("Dicas.DICAS.filter(d => /\\d/.test(d.titulo + d.texto.replace(/Ctrl\\+S|Escolha 1/g, ''))).map(d => d.id)")
        p.conta("dicas", "com \"Menos movimento\" (o da loja e o do sistema) o anel não pulsa; nenhum texto de dica traz número (nada de dado de item)",
                anim == "none" and anim_sis == "none" and digitos == [], "anel %s / sistema %s · com número: %s" % (anim, anim_sis, digitos))
    finally:
        s.js("try { Dicas.fechar(); sessionStorage.removeItem('qa.dicas'); localStorage.setItem('dicas.desligadas', '1'); } catch (e) {} 'ok'")
        s.envia("Emulation.setEmulatedMedia", {"features": []})
        s.tela(1440, 900)


def checar_mapa(p):
    """F13-T105: o data/mapa.js (a forma de Summoner's Rift para o mapa da build) — gerado do jogo pelo
    data/gerar_mapa.py, nunca à mão. Sem navegador: o arquivo decodifica no tamanho da grade, as proporções
    de parede e arbusto são de mapa, e, com o LoL instalado, gerar de novo dá o mesmo arquivo."""
    print("\n%sMAPA%s" % (AMARELO, FIM))
    caminho = os.path.join(RAIZ, "data", "mapa.js")
    txt = open(caminho, encoding="utf-8").read()
    corpo = txt[txt.index("{"):txt.rindex("}") + 1]
    campo = lambda k: re.search(r"\b%s: *([^,\n]+)" % k, corpo).group(1).strip().strip("\"'")
    nx, nz, cel = int(campo("nx")), int(campo("nz")), float(campo("celula"))
    n = nx * nz
    conta = {}
    for k in ("paredes", "arbustos", "soPasso"):
        b = base64.b64decode(re.search(r'%s: *"([^"]*)"' % k, corpo).group(1))
        conta[k] = (len(b), sum(bin(x).count("1") for x in b))
    tam_ok = all(t_ == (n + 7) // 8 for t_, _ in conta.values())
    par, arb = conta["paredes"][1] / float(n), conta["arbustos"][1] / float(n)
    p.conta("mapa", "o data/mapa.js decodifica na grade inteira (uma célula por bit) e tem proporções de mapa: parede 25–45%, arbusto 1–4%",
            "GERADO por data/gerar_mapa.py" in txt and tam_ok and 0.25 <= par <= 0.45 and 0.01 <= arb <= 0.04 and cel == 50.0,
            "%d × %d de %.0f · parede %.1f%% · arbusto %.1f%% · %s" % (nx, nz, cel, 100 * par, 100 * arb, conta))
    wad = r"C:\Riot Games\League of Legends\Game\DATA\FINAL\Maps\Shipping\Map11.wad.client"
    if not os.path.exists(wad):
        print("  %s(sem o LoL nesta máquina: a conferência com o jogo fica de fora)%s" % (CINZA, FIM))
        return
    tmp = os.path.join(tempfile.mkdtemp(), "mapa.js")
    r = subprocess.run([sys.executable, "-X", "utf8", "-c",
                        "import sys; sys.argv=['x']; sys.path.insert(0, %r); import gerar_mapa as g; g.SAIDA=%r; g.main()" % (os.path.join(RAIZ, "data"), tmp)],
                       capture_output=True, text=True, encoding="utf-8")
    igual = os.path.exists(tmp) and open(tmp, encoding="utf-8").read() == txt
    p.conta("mapa", "gerado de novo do jogo instalado, o data/mapa.js sai igual (está em dia com o mapa do patch)",
            r.returncode == 0 and igual, (r.stdout + r.stderr).strip().splitlines()[-1][:120] if (r.stdout + r.stderr).strip() else "sem saída")


def checar_tracker(s, p):
    """F13-T114 (Leo, 05/11/2026: "algo visual para as atualizações do robô para mostrar quais itens e o que foi
    alterado… o nome do bot para Update Tracker"; a opção B da amostra "como aqueles quadros de velho oeste onde
    ficam os cartazes de procurado"): o Update Tracker. O botão do topo abre o quadro; um cartaz por item do
    "detalhe" do data/mudancas.js (o histórico do catálogo), o patch mais novo primeiro; o preço na "Recompensa",
    do antes ao preço de hoje; o clique abre o antes e o depois; com patch novo na camada, ele vem primeiro, com o
    que já foi aplicado e o que se confere; o Esc fecha; o mural abre o quadro."""
    print("\n%sUPDATE TRACKER%s" % (AMARELO, FIM))
    s.tela(1440, 900)
    s.abrir("")
    s.entrar()
    time.sleep(0.5)
    try:
        # 0. o registro: o "detalhe" de cada versão casa com os itens e os campos dela
        reg = s.js("""(() => { const vs = (window.MUDANCAS || {}).versoes || [];
          return vs.map(v => ({ patch: v.patch, ok: !!v.detalhe && Object.keys(v.detalhe).join() === Object.keys(v.itens).join()
            && Object.entries(v.detalhe).every(([sl, l]) => l.map(x => x[0]).join() === v.itens[sl].join() && l.every(x => Array.isArray(x[1]) && Array.isArray(x[2]))) })); })()""")
        p.conta("update tracker", "o data/mudancas.js leva, em cada versão, o antes e o depois de cada campo que mudou (os mesmos itens e campos que desatualizam as builds)",
                bool(reg) and all(r["ok"] for r in reg), "%s" % reg)

        # 1. o botão abre o quadro: um cartaz por item (e por item que saiu) do patch mais novo, as abas do mais novo ao mais velho
        s.clicar("#tracker-btn", 0.6)
        q = s.js("""(() => { const vs = MUDANCAS.versoes, u = vs[vs.length - 1];
          return { aberto: !document.getElementById('tracker').hidden, exp: document.getElementById('tracker-btn').getAttribute('aria-expanded'),
                   cartazes: [...document.querySelectorAll('.tk-cartaz')].map(c => c.dataset.slug),
                   esperado: Object.keys(u.detalhe).concat(u.removidos || []),
                   nomes: [...document.querySelectorAll('.tk-nome')].map(x => x.textContent),
                   nomesCat: Object.keys(u.detalhe).concat(u.removidos || []).map(sl => byId[sl] ? byId[sl].namePt : sl),
                   abas: [...document.querySelectorAll('[data-tk-patch]')].map(b => b.textContent), patches: vs.map(v => 'Patch ' + v.patch).reverse() }; })()""")
        p.conta("update tracker", "o botão do topo abre o quadro: um cartaz por item que mudou no patch mais novo, com o nome do catálogo; as abas vão do patch mais novo ao mais velho",
                q["aberto"] and q["exp"] == "true" and q["cartazes"] == q["esperado"] and q["nomes"] == q["nomesCat"] and q["abas"] == q["patches"], "%s" % q)

        # 2. a Recompensa: o preço de antes riscado e o de hoje (o do catálogo)
        r = s.js("""(() => { const u = MUDANCAS.versoes[MUDANCAS.versoes.length - 1];
          const sl = Object.keys(u.detalhe).find(k => u.detalhe[k].some(x => x[0] === 'preço')); if (!sl) return null;
          const c = document.querySelector('.tk-cartaz[data-slug="' + sl + '"] .tk-recompensa'), pr = u.detalhe[sl].find(x => x[0] === 'preço');
          return { sl: sl, antes: c && c.querySelector('.tk-antes').textContent, depois: c && c.querySelector('.tk-depois').textContent,
                   esperaAntes: fmtNum(Number(pr[1][0])) + ' g', esperaDepois: fmtNum(byId[sl].priceGold) + ' g',
                   caro: c && c.querySelector('.tk-depois').classList.contains(Number(pr[2][0]) > Number(pr[1][0]) ? 'piorou' : 'melhorou') }; })()""")
        p.conta("update tracker", "no cartaz de preço, a Recompensa mostra o preço de antes riscado e o de hoje (o do catálogo), com a cor de mais caro ou mais barato",
                bool(r) and r["antes"] == r["esperaAntes"] and r["depois"] == r["esperaDepois"] and r["caro"], "%s" % r)

        # 2b. as cores (Leo, 05/11/2026: "vermelho se é uma mudança negativa, verde para positiva e amarelo para ajuste
        #     ou reformulação"; "percebi pelo Quebra-Bastião PERDENDO letalidade e estando verde"): o atributo que cai é
        #     vermelho; na recarga, o número que cai é verde; o texto trocado sem número é amarelo
        tm = s.js("""(() => { const u = MUDANCAS.versoes[MUDANCAS.versoes.length - 1];
          const cai = Object.keys(u.detalhe).find(k => u.detalhe[k].some(x => x[0] === 'atributos' && x[1].some((a, i) => {
            const b = x[2][i], va = a && Number((a.match(/\\d+(?:,\\d+)?/) || [])[0]), vb = b && Number((b.match(/\\d+(?:,\\d+)?/) || [])[0]);
            return a && b && a.replace(/[\\d,+]/g, '') === b.replace(/[\\d,+]/g, '') && vb < va; })));
          const c = cai && document.querySelector('.tk-cartaz[data-slug="' + cai + '"]');
          const li = c && [...c.querySelectorAll('.tk-resumo li')].find(x => x.textContent.includes('→'));
          const t = (a, b) => Tracker.difPalavras(a, b).tons.join();
          return { cai: cai, li: li ? li.className : null, ins: c ? [...c.querySelectorAll('.tk-detalhe p')].filter(p => /Atributos/i.test(p.querySelector('b').textContent)).map(p => [...p.querySelectorAll('ins')].map(i => i.className).join()).join() : null,
                   dano: t('causa 50 de dano', 'causa 40 de dano'), recarga: t('Recarga de 20s.', 'Recarga de 15s.'), custo: t('custo de 60 de Mana', 'custo de 80 de Mana'),
                   texto: t('Abates concedem Glória', 'Eliminações concedem Glória'), sobe: t('+30 de Vida', '+45 de Vida'),
                   junta: [Tracker.juntaTom(['piorou', 'ajuste']), Tracker.juntaTom(['piorou', 'melhorou']), Tracker.juntaTom(['ajuste']), Tracker.juntaTom(['melhorou', 'melhorou'])] }; })()""")
        p.conta("update tracker", "as cores do tom: o atributo que cai sai vermelho (o Quebra-Bastião perdendo Letalidade), o que sobe verde; na recarga e no custo é o contrário; o texto trocado sem número é amarelo; no cartaz, os números decidem quando vão todos para o mesmo lado (sem número, ou uns subindo e outros descendo, é ajuste)",
                bool(tm["cai"]) and tm["li"] == "piorou" and tm["ins"] == "piorou" and tm["dano"] == "piorou" and tm["recarga"] == "melhorou"
                and tm["custo"] == "piorou" and tm["texto"] == "ajuste" and tm["sobe"] == "melhorou" and tm["junta"] == ["piorou", "ajuste", "ajuste", "melhorou"], "%s" % tm)

        # 3. o clique abre o antes e o depois: o que saiu riscado, o que entrou realçado, o texto de hoje da Mecânica
        d = s.js("""(() => { const u = MUDANCAS.versoes[MUDANCAS.versoes.length - 1];
          const sl = Object.keys(u.detalhe).find(k => u.detalhe[k].some(x => x[0] === 'habilidades')); if (!sl) return null;
          const c = document.querySelector('.tk-cartaz[data-slug="' + sl + '"]'); c.click();
          const det = c.querySelector('.tk-detalhe'), vis = getComputedStyle(det).display !== 'none';
          const txt = det.textContent.replace(/\\s+/g, ' '), ins = [...det.querySelectorAll('ins')].map(x => x.textContent), del = [...det.querySelectorAll('del')].map(x => x.textContent);
          const hoje = (byId[sl].abilities || []).map(h => (h.mechanics || h.description || '').replace(/\\\\n/g, ' ').replace(/\\s+/g, ' '));
          const semDel = (() => { const cl = det.cloneNode(true); cl.querySelectorAll('del').forEach(x => x.remove()); return cl.textContent.replace(/\\s+/g, ' '); })();
          return { sl: sl, aberto: c.classList.contains('aberto') && vis, ins: ins.length, del: del.length, hoje: hoje.every(h => semDel.includes(h.slice(0, 60))) }; })()""")
        p.conta("update tracker", "o clique no cartaz abre o antes e o depois: o que saiu riscado, o que entrou realçado; sem o riscado, fica o texto de hoje da Mecânica",
                bool(d) and d["aberto"] and d["ins"] > 0 and d["del"] > 0 and d["hoje"], "%s" % d)

        # 4. o Esc fecha; o mural abre o quadro
        s.envia("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
        s.envia("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
        time.sleep(0.3)
        fechou = s.js("document.getElementById('tracker').hidden")
        s.clicar("#notas-btn", 0.5)
        s.clicar("#mural [data-abrir-tracker]", 0.6)
        mural = s.js("({ tracker: !document.getElementById('tracker').hidden, mural: !document.getElementById('mural').hidden })")
        p.conta("update tracker", "o Esc fecha o quadro; no mural da loja, o \"Ver os cartazes\" abre o quadro (e fecha o mural)",
                fechou is True and mural == {"tracker": True, "mural": False}, "Esc %s · mural %s" % (fechou, mural))

        # 5. com patch novo na camada: ele vem primeiro, com o que já foi aplicado (de → para) e o que se confere
        n = s.js("""(() => { ROBO.ativo = true; ROBO.de = CATALOG.meta.patch; ROBO.para = '99.1.1';
          ROBO.itens = { 'doran-s-blade': { aplicados: ['priceGold'], recusados: [], contaVelha: [], mudou: [{ campo: 'preço', de: 450, para: 500, fonte: 'wiki e Data Dragon' }] } };
          ROBO.aConferir = { 'long-sword': [{ campo: 'atributos', porque: 'a wiki diz outro número' }] };
          Tracker.abrir(true);
          return { abas: [...document.querySelectorAll('[data-tk-patch]')].map(b => b.textContent), titulos: [...document.querySelectorAll('.tk-procurado')].map(x => x.textContent), fina: (document.querySelector('.tk-cartaz[data-slug="doran-s-blade"] .tk-linha-fina') || {}).textContent || '',
                   rec: (document.querySelector('.tk-cartaz[data-slug="doran-s-blade"] .tk-recompensa') || {}).textContent || '',
                   conf: (document.querySelector('.tk-cartaz[data-slug="long-sword"] .tk-resumo') || {}).textContent || '' }; })()""")
        p.conta("update tracker", "com patch novo na camada, a aba dele vem primeiro: o cartaz do patch novo (\"patch novo · …\", e o título pelo tom: o preço subiu, \"Piorou\") com o preço de → para, e o \"A conferir\" com o motivo",
                n["abas"][:1] == ["Patch 99.1.1 · novo"] and n["titulos"] == ["Piorou", "A conferir"] and n["fina"] == "patch novo · 99.1.1" and "450 g" in n["rec"] and "500 g" in n["rec"]
                and "a wiki diz outro número" in n["conf"], "%s" % n)
    finally:
        s.abrir("")   # a camada de mentira não fica para os outros grupos
        time.sleep(0.4)


def checar_mesa(s, p):
    """F13-T107 (Leo, 02/11/2026: a opção A da F13-T106, e "é para ser uma aba à parte, como a calculadora"):
    a mesa de guerra — o mapa de Summoner's Rift na aba Mapa, com o balão "Novidade" (a adição mais recente);
    o endereço #mapa; a linha de quem é o mapa (a build aberta; a de ARAM avisa); o map11.png do patch do
    catálogo; a roda aproxima em volta do cursor sem rolar a página; o arrasto move sem deixar o mapa sair da
    janela; + − 0 e as setas; "Mapa inteiro"; nas três resoluções, a janela inteira na tela."""
    print("\n%sMESA DE GUERRA%s" % (AMARELO, FIM))
    s.tela(1440, 900)
    s.limpar_memoria()
    s.entrar()
    s.nova_build()
    s.js("switchTab('mapa'); 'ok'")
    time.sleep(0.6)
    est = "Mesa.estado()"

    def mouse(tipo, x, y, **k):
        d = {"type": tipo, "x": x, "y": y}
        d.update(k)
        s.envia("Input.dispatchMouseEvent", d)

    def janela():
        return s.js("(() => { const r = document.getElementById('mesa-janela').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; })()")

    def ponto_no_mapa(px, py):   # o ponto do mapa (0..1) sob um ponto da janela
        e = s.js(est)
        return ((px - e["x"]) / (e["lado"] * e["z"]), (py - e["y"]) / (e["lado"] * e["z"]))

    abre_mapa = "(() => { switchTab('mapa'); window.scrollTo(0, 0); return 1; })()"
    try:
        # 1. a aba: o clique abre a tela do mapa e o endereço vira #mapa; o balão "Novidade" é um só, na adição mais
        #    recente (desde a F13-T114, o botão do Update Tracker);
        #    a linha diz de quem é o mapa — e a build de ARAM avisa que o mapa é o de Summoner's Rift
        s.clicar('.tab-btn[data-tab="mapa"]', 1.0)
        a = s.js("""(() => { const v = document.getElementById('view-mapa'), n = [...document.querySelectorAll('.novidade')];
          return { vis: !v.classList.contains('hidden') && v.getBoundingClientRect().height > 0, hash: location.hash,
                   aba: document.querySelector('.tab-btn.active').dataset.tab, novidades: n.length,
                   ondeNov: n.map(x => x.closest('[data-tab]') ? x.closest('[data-tab]').dataset.tab : (x.parentElement.id || '?')),
                   novTxt: n.map(x => x.textContent.trim()), novVis: n.every(x => x.getBoundingClientRect().width > 0),
                   dona: document.getElementById('mesa-dona').textContent.trim(), nome: build.name,
                   src: document.getElementById('mesa-img').src, patch: CATALOG.meta.patch, w: document.getElementById('mesa-img').naturalWidth }; })()""")
        modos = s.js("[...document.getElementById('build-mode').options].map(o => o.value)")
        aram = next((m for m in modos if "ARAM" in m), None)
        s.js("switchTab('build'); showBuildScreen('forja'); 'ok'")
        time.sleep(0.5)
        s.clicar("#edit-switch", 0.6)   # o modo só muda com o Editar (Leo, 23/10/2026)
        s.js("(() => { const sel = document.getElementById('build-mode'); sel.value = %s; sel.dispatchEvent(new Event('change', { bubbles: true })); return 1; })()" % json.dumps(aram))
        time.sleep(0.4)
        s.js(abre_mapa)
        time.sleep(0.5)
        dona_aram = s.js("document.getElementById('mesa-dona').textContent.trim()")
        s.js("switchTab('build'); (() => { const sel = document.getElementById('build-mode'); sel.value = ''; sel.dispatchEvent(new Event('change', { bubbles: true })); })(); 'ok'")
        time.sleep(0.4)
        s.js(abre_mapa)
        time.sleep(0.5)
        j = janela()
        p.conta("mesa", "a aba Mapa abre a mesa (endereço #mapa); o balão \"Novidade\" é um só, no Update Tracker (a adição mais recente); a linha diz de qual build é o mapa e, na de ARAM, que o mapa é o de Summoner's Rift; o map11.png do patch, numa janela quadrada",
                a["vis"] and a["hash"] == "#mapa" and a["aba"] == "mapa" and a["novidades"] == 1 and a["ondeNov"] == ["tracker-btn"] and a["novTxt"] == ["Novidade"] and a["novVis"]
                and a["nome"] in a["dona"] and "ARAM" in dona_aram and "Summoner's Rift" in dona_aram
                and a["src"].endswith("/cdn/%s/img/map/map11.png" % a["patch"]) and a["w"] > 0 and abs(j["w"] - j["h"]) < 1.5,
                "%s · ARAM: %s · janela %s" % (a, dona_aram, j))

        # 2. a roda aproxima em volta do cursor e a página não rola; fora do mapa, a roda rola a página
        s.js(abre_mapa + "; Mesa.inteiro(); window.scrollTo(0, 60); 'ok'")   # um pouco rolada: a roda para cima teria para onde rolar
        time.sleep(0.3)
        j = janela()
        cx, cy = j["x"] + j["w"] * 0.3, j["y"] + j["h"] * 0.6
        antes_pt = ponto_no_mapa(cx - j["x"], cy - j["y"])
        y0 = s.js("scrollY")
        mouse("mouseMoved", cx, cy)
        mouse("mouseWheel", cx, cy, deltaX=0, deltaY=-100)
        time.sleep(0.3)
        e1 = s.js(est)
        depois_pt = ponto_no_mapa(cx - j["x"], cy - j["y"])
        y1 = s.js("scrollY")
        mouse("mouseWheel", j["x"] + j["w"] + 400, cy, deltaX=0, deltaY=300)
        time.sleep(0.4)
        y2 = s.js("scrollY")
        p.conta("mesa", "a roda no mapa aproxima (~1,2× por clique) em volta do cursor — o ponto sob ele não sai do lugar — e a página não rola; fora do mapa, a roda rola a página",
                1.15 < e1["z"] < 1.3 and abs(antes_pt[0] - depois_pt[0]) < 0.003 and abs(antes_pt[1] - depois_pt[1]) < 0.003 and y1 == y0 and y2 > y1,
                "zoom %s · ponto %s → %s · rolagem %s → %s → %s" % (e1, antes_pt, depois_pt, y0, y1, y2))

        # 3. o arrasto move junto com o mouse; puxado além da borda, o mapa para na borda
        s.js(abre_mapa + "; Mesa.inteiro(); 'ok'")
        time.sleep(0.3)
        j = janela()
        cx, cy = j["x"] + j["w"] / 2, j["y"] + j["h"] / 2
        for _ in range(4):
            mouse("mouseWheel", cx, cy, deltaX=0, deltaY=-100)
        time.sleep(0.3)
        e2 = s.js(est)
        mouse("mouseMoved", cx, cy)
        mouse("mousePressed", cx, cy, button="left", buttons=1, clickCount=1)
        mouse("mouseMoved", cx - 20, cy - 10, buttons=1)
        mouse("mouseMoved", cx - 40, cy - 30, buttons=1)
        mouse("mouseReleased", cx - 40, cy - 30, button="left", buttons=0, clickCount=1)
        time.sleep(0.3)
        e3 = s.js(est)
        # de um canto ao outro sem sair da janela (o Chrome do roteiro não repassa o movimento de fora dela;
        # com o mouse de verdade, a captura segue fora — conferido no navegador embutido): com o mapa
        # aproximado, isso já puxa além da borda. Uma pausa entre os gestos e o movimento em passos, como a mão
        time.sleep(0.7)
        ax, ay, bx, by = j["x"] + 12, j["y"] + 12, j["x"] + j["w"] - 12, j["y"] + j["h"] - 12
        mouse("mouseMoved", ax, ay)
        mouse("mousePressed", ax, ay, button="left", buttons=1, clickCount=1)
        for k in range(1, 11):
            mouse("mouseMoved", ax + (bx - ax) * k / 10, ay + (by - ay) * k / 10, buttons=1)
        mouse("mouseReleased", bx, by, button="left", buttons=0, clickCount=1)
        time.sleep(0.3)
        e4 = s.js(est)
        sel = s.js("String(getSelection()).length")
        p.conta("mesa", "o arrasto move o mapa junto com o mouse; puxado além da borda, ele para na borda (o canto não entra na janela) e nada fica selecionado",
                e2["z"] > 2 and abs((e3["x"] - e2["x"]) + 40) < 1.5 and abs((e3["y"] - e2["y"]) + 30) < 1.5 and e4["x"] == 0 and e4["y"] == 0 and sel == 0,
                "%s → %s → %s · seleção %s" % (e2, e3, e4, sel))

        # 4. o teclado (+ − 0 e as setas, com a janela em foco); o zoom para em 6×; "Mapa inteiro" volta
        s.js("document.getElementById('mesa-janela').focus(); Mesa.inteiro(); 'ok'")
        tecla = lambda k, cod: (s.envia("Input.dispatchKeyEvent", {"type": "keyDown", "key": k, "code": cod}), s.envia("Input.dispatchKeyEvent", {"type": "keyUp", "key": k, "code": cod}))
        for _ in range(12):
            tecla("+", "Equal")
        e5 = s.js(est)
        tecla("ArrowLeft", "ArrowLeft")
        e6 = s.js(est)
        tecla("0", "Digit0")
        e7 = s.js(est)
        tecla("+", "Equal")
        s.clicar("#mesa-inteiro", 0.3)
        e8 = s.js(est)
        p.conta("mesa", "com a janela em foco, + aproxima até 6× e não passa, a seta move, 0 volta ao mapa inteiro; o botão \"Mapa inteiro\" também",
                abs(e5["z"] - 6) < 1e-6 and e6["x"] > e5["x"] and e7["z"] == 1 and e7["x"] == 0 and e8["z"] == 1 and e8["x"] == 0 and e8["y"] == 0,
                "%s · %s · %s · %s" % (e5, e6, e7, e8))

        # 5. o link direto #mapa abre na tela do mapa
        s.abrir("?r=107#mapa")   # endereço novo: trocar só o # não recarrega o documento
        time.sleep(0.6)
        s.entrar()
        time.sleep(0.4)
        d = s.js("({ aba: document.querySelector('.tab-btn.active').dataset.tab, vis: !document.getElementById('view-mapa').classList.contains('hidden'), hash: location.hash })")
        p.conta("mesa", "o link direto #mapa abre na tela do mapa", d["aba"] == "mapa" and d["vis"] and d["hash"] == "#mapa", "%s" % d)

        # 6. nas três resoluções: a janela do mapa, quadrada, cabe inteira na tela (do topo), sem rolagem de lado
        ruins = []
        for w, h in ((1440, 900), (1920, 1080), (1600, 900)):
            s.tela(w, h)
            time.sleep(0.4)
            s.js(abre_mapa)
            time.sleep(0.3)
            m = s.js("(() => { const a = document.getElementById('mesa').getBoundingClientRect(), j = document.getElementById('mesa-janela').getBoundingClientRect(); return { dir: a.right, larg: innerWidth, alt: innerHeight, rola: document.documentElement.scrollWidth > innerWidth + 1, w: j.width, h: j.height, fundo: j.bottom }; })()")
            if m["dir"] > m["larg"] or m["rola"] or abs(m["w"] - m["h"]) > 1.5 or m["w"] < 340 or m["fundo"] > m["alt"]:
                ruins.append("%dx%d %s" % (w, h, m))
        p.conta("mesa", "nas três resoluções a janela do mapa é quadrada e cabe inteira na tela, sem rolagem de lado", not ruins, ", ".join(ruins) or "ok")
    finally:
        s.tela(1440, 900)


def checar_sentinelas(s, p):
    """F13-T108 (Leo, 02/11/2026: "ao posicionar o ícone da ward ela concede visão expulsando a névoa de
    guerra, revelando o alcance e o que ela revela e o que não revela"; "o raio de visão deve ser equivalente
    à escala… um círculo ciano"): as sentinelas na aba Mapa. O raio e o ícone vêm do catálogo; sem o Editar
    nada muda; a névoa abre na visão de verdade (a parede barra, o arbusto só de dentro); o raio em ciano
    acompanha o zoom; a névoa e o raio se desligam (lembrado); as marcas ficam na build (salvar, recarregar,
    duplicar). F13-T112 (a névoa viva): arrastar do botão põe, arrastar a sentinela a leva (a névoa abre no
    novo lugar e volta a fechar no velho), soltar fora do mapa tira, arrastar o mapa só move; o Enter no botão
    põe uma no meio; a Alteração Vidente vê por cima da parede, porque o texto do item diz."""
    print("\n%sSENTINELAS%s" % (AMARELO, FIM))
    s.tela(1440, 900)
    s.limpar_memoria()
    s.entrar()
    s.nova_build()
    s.js("switchTab('mapa'); window.scrollTo(0, 0); 'ok'")
    time.sleep(0.8)

    def mouse(tipo, x, y, **k):
        d = {"type": tipo, "x": x, "y": y}
        d.update(k)
        s.envia("Input.dispatchMouseEvent", d)

    def clique(x, y):
        mouse("mouseMoved", x, y)
        mouse("mousePressed", x, y, button="left", buttons=1, clickCount=1)
        mouse("mouseReleased", x, y, button="left", buttons=0, clickCount=1)
        time.sleep(0.7)

    jan = lambda: s.js("(() => { const r = document.getElementById('mesa-janela').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width }; })()")
    # o ponto da tela de uma posição do jogo, e a opacidade da névoa nela (0–255)
    tela_de = "(wx, wz) => { const e = Mesa.estado(), p = Mesa.paraTela(wx, wz), r = document.getElementById('mesa-janela').getBoundingClientRect(); return [r.left + e.x + p[0] * e.z, r.top + e.y + p[1] * e.z]; }"
    alfa = """(wx, wz) => { const cv = document.getElementById('mesa-nevoa'); if (cv.hidden) return -1;
      const L = cv.width, u = (wx - MAPA.min[0]) / (MAPA.nx * MAPA.celula), v = 1 - (wz - MAPA.min[1]) / (MAPA.nz * MAPA.celula);
      return cv.getContext('2d').getImageData(Math.floor(u * L), Math.floor(v * L), 1, 1).data[3]; }"""
    # achado na grade, perto do centro: um ponto de chão aberto (5×5 livres), um ponto de chão atrás de parede dentro
    # do raio (que a sentinela não vê) e uma parede a poucos passos
    achar = """(() => { const G = MAPA, T = G.celula, b = (s) => { const t = atob(s); return (i) => (t.charCodeAt(i >> 3) >> (i & 7)) & 1; };
      const par = b(G.paredes), arb = b(G.arbustos), sp = b(G.soPasso), w = (k) => G.min[0] + (k + .5) * T, zz = (z) => G.min[1] + (z + .5) * T;
      const livre = (k, z) => !par(z * G.nx + k) && !arb(z * G.nx + k) && !sp(z * G.nx + k);
      const r = Mesa.raio('sentinela'), n = Math.ceil(r / T);
      for (let d = 0; d < 120; d += 2) for (let k = 147 - d; k <= 147 + d; k += 2) for (const z of [148 - d, 148 + d]) {
        let ok = k > 3 && z > 3 && k < G.nx - 3 && z < G.nz - 3;
        for (let a = -2; a <= 2 && ok; a++) for (let c = -2; c <= 2 && ok; c++) if (!livre(k + a, z + c)) ok = false;
        if (!ok) continue;
        const vis = new Set(Mesa.visao(w(k), zz(z), r).map(c => c[0] + ',' + c[1]));
        let atras = null, parede = null;
        for (let dz = -n; dz <= n && !atras; dz++) for (let dx = -n; dx <= n && !atras; dx++) { const kk = k + dx, z2 = z + dz;
          if ((dx * dx + dz * dz) * T * T > (r * .8) * (r * .8) || !livre(kk, z2)) continue;
          let folga = true; for (let a = -2; a <= 2 && folga; a++) for (let c = -2; c <= 2 && folga; c++) if (vis.has((kk + a) + ',' + (z2 + c))) folga = false;
          if (folga) atras = [w(kk), zz(z2)]; }   // sem célula vista a 2 de distância: a borda esfumada não chega
        for (let e = 3; e < 10 && !parede; e++) for (const [a, c] of [[e, 0], [-e, 0], [0, e], [0, -e]]) { const kk = k + a, z2 = z + c; if (!parede && par(z2 * G.nx + kk)) parede = [w(kk), zz(z2), kk, z2]; }
        if (atras && parede) return { chao: [w(k), zz(z), k, z], atras, parede, r };
      }
      return null; })()"""

    # F13-T112: o arrasto de verdade (o mouse do CDP): apertar, andar em passos, soltar
    def arrasta(de, para, passos=20, solta=True):
        mouse("mouseMoved", de[0], de[1])
        mouse("mousePressed", de[0], de[1], button="left", buttons=1, clickCount=1)
        for k in range(1, passos + 1):
            mouse("mouseMoved", de[0] + (para[0] - de[0]) * k / passos, de[1] + (para[1] - de[1]) * k / passos, button="left", buttons=1)
            time.sleep(0.016)
        if solta:
            mouse("mouseReleased", para[0], para[1], button="left", buttons=0, clickCount=1)
            time.sleep(0.9)

    botao = lambda t: s.js("(() => { const r = document.querySelector('#mesa-ferras [data-ferra=\"%s\"]').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()" % t)

    try:
        # 1. as ferramentas: o ícone e o raio do catálogo (o número que o texto do item diz)
        f = s.js("""(() => { const it = (sl) => CATALOG.items.find(i => i.slug === sl);
          const txt = (sl) => JSON.stringify(it(sl)); const m1 = /raio de visão de ([\\d.]+)/.exec(txt('stealth-ward')), m2 = /visão num raio de ([\\d.]+)/.exec(txt('control-ward')),
            m3 = /raio de visão menor \\(([\\d.]+)\\)/.exec(txt('farsight-alteration'));
          return { raios: [Mesa.raio('sentinela'), Mesa.raio('controle'), Mesa.raio('vidente')],
                   doTexto: [m1 && Number(m1[1].replace(/\\./g, '')), m2 && Number(m2[1].replace(/\\./g, '')), m3 && Number(m3[1].replace(/\\./g, ''))],
                   icones: [...document.querySelectorAll('#mesa-ferras img')].map(i => i.src), doCat: [it('stealth-ward').iconUrl, it('control-ward').iconUrl, it('farsight-alteration').iconUrl],
                   rotulos: [...document.querySelectorAll('#mesa-ferras small')].map(x => x.textContent) }; })()""")
        p.conta("sentinelas", "as três ferramentas levam o ícone do catálogo e o raio que o texto do item diz (Sentinela Invisível, Sentinela de Controle e Alteração Vidente)",
                f["raios"] == f["doTexto"] and all(f["raios"]) and f["icones"] == f["doCat"] and f["rotulos"] == ["raio %d" % r for r in f["raios"]], "%s" % f)

        # 2. sem o Editar, arrastar do botão para o mapa não põe nada e a mesa oferece o "Ligar Editar"
        a = s.js(achar)
        x1, y1 = s.js("(%s)(%r, %r)" % (tela_de, a["chao"][0], a["chao"][1]))
        arrasta(botao("sentinela"), (x1, y1))
        sem = s.js("({ n: build.mapa.visao.length, editing: build.editing, btn: !!document.querySelector('#mesa-pode [data-ligar-editar]'), fantasma: !!document.querySelector('.mesa-fantasma') })")
        s.clicar("#mesa-pode [data-ligar-editar]", 0.6)
        ligado = s.js("build.editing")
        p.conta("sentinelas", "sem o Editar, arrastar do botão para o mapa não põe nada e a mesa oferece o \"Ligar Editar\", que liga",
                sem == {"n": 0, "editing": False, "btn": True, "fantasma": False} and ligado is True, "%s · depois %s" % (sem, ligado))

        # 3. com o Editar, arrastar (de verdade) do botão até o mapa põe a sentinela onde foi solta; a build fica
        #    "não salva"; a névoa abre ali e continua fechada atrás da parede, dentro do raio, e longe
        x1, y1 = s.js("(%s)(%r, %r)" % (tela_de, a["chao"][0], a["chao"][1]))
        arrasta(botao("sentinela"), (x1, y1))
        time.sleep(0.6)
        v = s.js("({ m: build.mapa.visao, sujo: rascunho.sujo, svg: document.querySelectorAll('#mesa-marcas .mm-sent').length, ic: (document.querySelector('#mesa-marcas image') || {}).getAttribute && document.querySelector('#mesa-marcas image').getAttribute('href'), fantasma: !!document.querySelector('.mesa-fantasma') })")
        al = s.js("(() => { const f = %s; return { aqui: f(%r, %r), atras: %s, longe: f(MAPA.min[0] + 400, MAPA.min[1] + MAPA.nz * MAPA.celula - 400) }; })()"
                  % (alfa, a["chao"][0], a["chao"][1], ("f(%r, %r)" % tuple(a["atras"])) if a["atras"] else "null"))
        m = v["m"][0] if v["m"] else {}
        p.conta("sentinelas", "com o Editar, arrastar do botão até o mapa põe a sentinela onde foi solta (a menos de uma célula) e a build fica \"não salva\"; a névoa abre ali e segue fechada atrás da parede (dentro do raio) e longe",
                len(v["m"]) == 1 and m.get("t") == "sentinela" and abs(m["x"] - a["chao"][0]) <= 50 and abs(m["z"] - a["chao"][1]) <= 50 and v["sujo"] and v["svg"] == 1
                and not v["fantasma"] and v["ic"] == s.js("CATALOG.items.find(i => i.slug === 'stealth-ward').iconUrl")
                and al["aqui"] is not None and al["aqui"] < 70 and al["atras"] is not None and al["atras"] > 120 and al["longe"] > 120,
                "%s · névoa %s · ponto atrás %s" % (v, al, a["atras"]))

        # 4. o raio em ciano: no mapa inteiro tem o tamanho do raio na escala do mapa; aproximado 2×, dobra
        rr = lambda: s.js("(() => { const c = document.querySelector('#mesa-marcas .mm-raio'); return c ? Number(c.getAttribute('r')) : null; })()")
        r1 = rr()
        esperado = s.js("Mesa.raio('sentinela') / (MAPA.nx * MAPA.celula) * Mesa.estado().lado")
        j = jan()
        s.js("(() => { const j = document.getElementById('mesa-janela'), r = j.getBoundingClientRect(); for (let k = 0; k < 4; k++) j.dispatchEvent(new WheelEvent('wheel', { deltaY: -86.6, clientX: r.left + r.width / 2, clientY: r.top + r.width / 2, bubbles: true, cancelable: true })); return 1; })()")
        time.sleep(0.3)
        z2 = s.js("Mesa.estado().z")
        r2 = rr()
        s.js("Mesa.inteiro(); 'ok'")
        p.conta("sentinelas", "o raio em ciano tem o tamanho do raio na escala do mapa e cresce junto com o zoom",
                r1 is not None and abs(r1 - esperado) < 0.6 and r2 is not None and abs(r2 - r1 * z2) < 1, "r %s (esperado %.1f) · zoom %.2f → %s" % (r1, esperado, z2, r2))

        # 5. arrastar o mapa (fora das sentinelas) não põe; arrastar a sentinela a leva — a névoa abre no lugar
        #    novo e volta a fechar no velho —; soltá-la fora do mapa a tira
        s.js("(() => { const j = document.getElementById('mesa-janela'), r = j.getBoundingClientRect(); j.dispatchEvent(new WheelEvent('wheel', { deltaY: -200, clientX: r.left + 100, clientY: r.top + 100, bubbles: true, cancelable: true })); return 1; })()")
        time.sleep(0.6)
        x0, y0 = jan()["x"] + 200, jan()["y"] + 200
        mouse("mouseMoved", x0, y0)
        mouse("mousePressed", x0, y0, button="left", buttons=1, clickCount=1)
        for k in range(1, 6):
            mouse("mouseMoved", x0 + 8 * k, y0 + 6 * k, buttons=1)
        mouse("mouseReleased", x0 + 40, y0 + 30, button="left", buttons=0, clickCount=1)
        time.sleep(0.6)
        n_arr = s.js("build.mapa.visao.length")
        s.js("Mesa.inteiro(); 'ok'")
        time.sleep(0.7)
        x1, y1 = s.js("(%s)(%r, %r)" % (tela_de, m["x"], m["z"]))
        arrasta((x1, y1), (x1 + 90, y1 - 70), passos=30)
        levada = s.js("build.mapa.visao")
        time.sleep(2.0)
        nv = s.js("(() => { const f = %s; return { velho: f(%r, %r), novo: f(%r, %r) }; })()" % (alfa, m["x"], m["z"], levada[0]["x"] if levada else 0, levada[0]["z"] if levada else 0))
        x2, y2 = s.js("(%s)(%r, %r)" % (tela_de, levada[0]["x"], levada[0]["z"])) if levada else (x1, y1)
        arrasta((x2, y2), (jan()["x"] + jan()["w"] + 90, y2), passos=25)
        n_tira = s.js("build.mapa.visao.length")
        p.conta("sentinelas", "arrastar o mapa não põe sentinela; arrastar a sentinela a leva (a névoa abre no lugar novo e volta a fechar no velho); soltá-la fora do mapa a tira",
                n_arr == 1 and len(levada) == 1 and math.hypot(levada[0]["x"] - m["x"], levada[0]["z"] - m["z"]) > 1500
                and nv["novo"] < 70 and nv["velho"] > 120 and n_tira == 0,
                "depois de arrastar o mapa %s · levada %s · névoa %s · depois de soltar fora %s" % (n_arr, levada, nv, n_tira))

        # 6. a Sentinela de Controle; e a solta numa parede escorrega para o chão
        xw, yw = s.js("(%s)(%r, %r)" % (tela_de, a["parede"][0], a["parede"][1]))
        arrasta(botao("controle"), (xw, yw))
        c = s.js("""(() => { const v = build.mapa.visao[0]; if (!v) return null; const G = MAPA, k = Math.floor((v.x - G.min[0]) / G.celula), z = Math.floor((v.z - G.min[1]) / G.celula);
          const t = atob(G.paredes), i = z * G.nx + k; return { t: v.t, parede: (t.charCodeAt(i >> 3) >> (i & 7)) & 1, dist: Math.hypot(v.x - %r, v.z - %r), cor: document.querySelector('#mesa-marcas .mm-sent.controle circle').getAttribute('fill') }; })()""" % (a["parede"][0], a["parede"][1]))
        p.conta("sentinelas", "a Sentinela de Controle se põe com a sua cor; a solta numa parede escorrega para o chão mais perto (não fica na parede)",
                bool(c) and c["t"] == "controle" and c["parede"] == 0 and c["dist"] <= 250 and c["cor"] == "#d8434b", "%s" % c)

        # 6b. o Enter no botão põe uma no meio do que se vê (o teclado também põe); a do teclado sai do mapa arrastada
        s.js("document.querySelector('#mesa-ferras [data-ferra=\"vidente\"]').focus(); 'ok'")
        s.envia("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "text": "\r"})
        s.envia("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
        time.sleep(0.6)
        meio = s.js("(() => { const l = build.mapa.visao, v = l[l.length - 1]; const p = Mesa.paraTela(v.x, v.z), L = Mesa.estado().lado; return { n: l.length, t: v.t, dx: Math.abs(p[0] - L / 2), dy: Math.abs(p[1] - L / 2), cor: [...document.querySelectorAll('#mesa-marcas .mm-sent.vidente circle')].map(c => c.getAttribute('fill')) }; })()")
        p.conta("sentinelas", "o Enter no botão da Alteração Vidente põe uma no meio do que se vê (perto do centro, no chão), com a cor dela",
                meio["n"] == 2 and meio["t"] == "vidente" and meio["dx"] < 30 and meio["dy"] < 30 and meio["cor"] == ["#4fa3ff"], "%s" % meio)
        mv = s.js("build.mapa.visao[1]")
        x3, y3 = s.js("(%s)(%r, %r)" % (tela_de, mv["x"], mv["z"]))
        arrasta((x3, y3), (x3, jan()["y"] - 80), passos=25)

        # 6c. a Alteração Vidente vê por cima da parede (o texto do item diz "inclusive sobre terreno e através de
        #     arbustos"): perto de uma parede, há chão atrás dela que ela vê e a Sentinela, do mesmo ponto e raio, não
        vd = s.js("""(() => { const G = MAPA, it = CATALOG.items.find(i => i.slug === 'farsight-alteration');
          const tp = atob(G.paredes), par = (i) => (tp.charCodeAt(i >> 3) >> (i & 7)) & 1;
          const diz = /inclusive sobre terreno e através de arbustos/.test(JSON.stringify(it)), r = Mesa.raio('vidente');
          // um ponto de chão, perto do meio, com chão atrás de parede dentro do raio
          const w = (k) => G.min[0] + (k + .5) * G.celula, zz = (z) => G.min[1] + (z + .5) * G.celula;
          for (let d = 0; d < 140; d += 3) for (let k = 147 - d; k <= 147 + d; k += 3) for (const z of [148 - d, 148 + d]) {
            if (k < 0 || z < 0 || k >= G.nx || z >= G.nz || par(z * G.nx + k)) continue;
            const comum = new Set(Mesa.visao(w(k), zz(z), r, false).map(c => c[0] + ',' + c[1]));
            const dela = Mesa.visao(w(k), zz(z), r, Mesa.livre('vidente'));
            const atras = dela.filter(c => !comum.has(c[0] + ',' + c[1]) && !par(c[1] * G.nx + c[0])).length;
            if (atras) return { diz: diz, livre: Mesa.livre('vidente'), livreSent: Mesa.livre('sentinela'), atras: atras, dela: dela.length, comum: comum.size, ponto: [k, z] };
          }
          return { diz: diz, livre: Mesa.livre('vidente'), livreSent: Mesa.livre('sentinela'), atras: 0 }; })()""")
        p.conta("sentinelas", "a Alteração Vidente vê por cima da parede porque o texto do item diz (do mesmo ponto e raio, chão atrás da parede que a visão comum não vê, ela vê); a Sentinela não",
                vd["diz"] and vd["livre"] is True and vd["livreSent"] is False and vd["atras"] > 0, "%s" % vd)

        # 7. o arbusto: de fora não se vê dentro; de dentro, sim (a regra, pela própria grade)
        mt = s.js("""(() => { const G = MAPA, T = G.celula, b = (s) => { const t = atob(s); return (i) => (t.charCodeAt(i >> 3) >> (i & 7)) & 1; };
          const par = b(G.paredes), arb = b(G.arbustos), w = (k) => G.min[0] + (k + .5) * T, zz = (z) => G.min[1] + (z + .5) * T;
          for (let z = 5; z < G.nz - 5; z++) for (let k = 5; k < G.nx - 5; k++) {
            if (!arb(z * G.nx + k)) continue;
            for (let d = 3; d <= 6; d++) { const fk = k + d; if (arb(z * G.nx + fk) || par(z * G.nx + fk)) continue;
              let limpo = true; for (let s2 = k + 1; s2 < fk; s2++) if (par(z * G.nx + s2)) limpo = false;
              if (!limpo) continue;
              const ve = (wx, wz) => Mesa.visao(wx, wz, Mesa.raio('sentinela')).some(c => c[0] === k && c[1] === z);
              return { de_fora: ve(w(fk), zz(z)), de_dentro: ve(w(k), zz(z)), moita: [k, z] }; } }
          return null; })()""")
        p.conta("sentinelas", "o arbusto: a sentinela de fora não vê dentro dele; a de dentro vê", bool(mt) and mt["de_fora"] is False and mt["de_dentro"] is True, "%s" % mt)

        # 8. a névoa e o raio se desligam, e ficam desligados ao recarregar
        s.clicar("#mesa-raio-on", 0.3)
        s.clicar("#mesa-nevoa-on", 0.3)
        d1 = s.js("({ raios: document.querySelectorAll('#mesa-marcas .mm-raio').length, nevoa: document.getElementById('mesa-nevoa').hidden })")
        s.js("salvarAgora(); 'ok'")   # o Salvar da forja (o Ctrl+S chama o mesmo)
        time.sleep(0.4)
        s.abrir("?r=108#mapa")
        time.sleep(0.6)
        s.entrar()
        time.sleep(0.8)
        d2 = s.js("({ raioOn: document.getElementById('mesa-raio-on').checked, nevoaOn: document.getElementById('mesa-nevoa-on').checked, nevoa: document.getElementById('mesa-nevoa').hidden, n: build.mapa.visao.length, marcas: document.querySelectorAll('#mesa-marcas .mm-sent').length })")
        p.conta("sentinelas", "a névoa e o raio em ciano se desligam (o raio some, a névoa some) e continuam desligados ao recarregar; salva, a sentinela volta com a build",
                d1 == {"raios": 0, "nevoa": True} and d2 == {"raioOn": False, "nevoaOn": False, "nevoa": True, "n": 1, "marcas": 1}, "%s · %s" % (d1, d2))
        s.js("(() => { ['mesa-raio-on', 'mesa-nevoa-on'].forEach(id => { const c = document.getElementById(id); if (!c.checked) c.click(); }); return 1; })()")

        # 9. duplicar a build leva as sentinelas
        s.js("switchTab('build'); showBuildScreen('forja'); 'ok'")
        time.sleep(0.5)
        s.js("duplicateBuild(build.id); 'ok'")
        time.sleep(0.8)
        dup = s.js("({ nome: build.name, m: build.mapa.visao })")
        p.conta("sentinelas", "duplicar a build leva as sentinelas", "(cópia)" in dup["nome"] and len(dup["m"]) == 1 and dup["m"][0]["t"] == "controle", "%s" % dup)
    finally:
        s.js("try { ['mesa-raio-on', 'mesa-nevoa-on'].forEach(id => localStorage.setItem(id === 'mesa-raio-on' ? 'mesa.raio' : 'mesa.nevoa', '1')); } catch (e) {} 'ok'")
        s.tela(1440, 900)


GRUPOS = [
    ("catálogo", checar_catalogo),
    ("ficha", checar_ficha),
    ("forja", checar_forja),
    ("marcadores", checar_marcadores),
    ("marcadores: ajuda", checar_marcadores_ajuda),
    ("notas", checar_notas),
    ("endereço por tela", checar_enderecos),
    ("autor", checar_autor),
    ("link curto", checar_link_curto),
    ("card do Discord", checar_card),
    ("card pronto", checar_card_pronto),
    ("dislexia", checar_dislexia),
    ("tags somam", checar_tags_somam),
    ("visualização", checar_visualizacao),
    ("passiva do Ornn", checar_passiva_do_ornn),
    ("teclado", checar_teclado),
    ("redesenho", checar_redesenho),
    ("importação", checar_importacao),
    ("lote e ornn", checar_lote_e_ornn),
    ("conferência", checar_conferencia),
    ("rota", checar_rota),
    ("filtro de rota", checar_filtro_rota),
    ("cadeado", checar_cadeado),
    ("reembolso e topo", checar_reembolso_e_topo),
    ("aviso", checar_aviso),
    ("cadeado: ajustes", checar_cadeado_ajustes),
    ("camada do robô", checar_camada_robo),
    ("runas", checar_runas),
    ("habilidades", checar_habilidades),
    ("texto", checar_texto),
    ("fragmento", checar_fragmento),
    ("salvar", checar_salvar),
    ("publicar", checar_publicar),
    ("exclusão", checar_exclusao),
    ("publicação órfã", checar_orfa),
    ("duas abas", checar_abas),
    ("última build", checar_ultima),
    ("atualização", checar_atualizacao),
    ("rascunho", checar_rascunho),
    ("troca", checar_troca),
    ("falta publicar", checar_falta_publicar),
    ("bigorna", checar_bigorna),
    ("fechar", checar_fechar),
    ("entrada", checar_entrada),
    ("entrada da loja", checar_entrada_loja),
    ("dicas", checar_dicas),
    ("update tracker", checar_tracker),
    ("mesa de guerra", checar_mesa),
    ("sentinelas", checar_sentinelas),
    ("desatualizadas", checar_desatualizadas),
    ("mudanças", checar_mudancas),
    ("acessibilidade", checar_acessibilidade),
    ("resoluções", checar_resolucoes),
    ("calculadora", checar_calculadora),
    ("som", checar_som),
    # Por último de propósito: com as 38 builds publicadas na tela, o navegador
    # fica pesado, e daí em diante qualquer medida sai contaminada.
    ("públicas", checar_publicas),
]


def main():
    ap = argparse.ArgumentParser(description="Roteiro de QA do Montador de Itens")
    ap.add_argument("--site", action="store_true", help="roda contra o GitHub Pages em vez desta pasta")
    ap.add_argument("--offline", action="store_true", help="pula o que precisa do servidor das builds")
    ap.add_argument("-k", metavar="PALAVRA", help="só os grupos cujo nome contém a palavra")
    ap.add_argument("--captura", metavar="ARQUIVO", help="salva uma captura do catálogo no fim")
    args = ap.parse_args()

    p = Placar()
    servidor = None
    if args.site:
        url = SITE
        print("Alvo: %s%s%s" % (CINZA, url, FIM))
    else:
        servidor = Servidor()
        url = servidor.url
        print("Alvo: %sesta pasta, servida em %s%s" % (CINZA, url, FIM))
        checar_arquivos(p)
        try:   # sem navegador, mas com a mesma regra: grupo que estoura vira falha dele
            checar_robo(p)
        except Exception as e:
            p.conta("robô", "o grupo rodou até o fim", False, "%s: %s" % (type(e).__name__, str(e)[:110]))
        try:
            checar_robo_regra(p)
        except Exception as e:
            p.conta("robô", "a regra rodou até o fim", False, "%s: %s" % (type(e).__name__, str(e)[:110]))
        try:
            checar_mapa(p)
        except Exception as e:
            p.conta("mapa", "o grupo rodou até o fim", False, "%s: %s" % (type(e).__name__, str(e)[:110]))

    s = Sessao(url)
    try:
        s.abrir()
        checar_fundacao(s, p)
        for nome, fn in GRUPOS:
            if args.k and args.k.lower() not in nome.lower():
                continue
            # Grupo que estoura vira falha dele, não fim do roteiro: eu quero o
            # relatório inteiro, não o primeiro tropeço.
            try:
                if nome == "públicas":
                    fn(s, p, not args.offline)
                else:
                    fn(s, p)
            except Exception as e:
                p.conta(nome, "o grupo rodou até o fim", False,
                        "%s: %s" % (type(e).__name__, str(e)[:110]))
        checar_console(s, p)
        if args.captura:
            # A captura é cortesia: se o navegador já estiver ruim, não é ela que
            # vai decidir se o roteiro passou.
            try:
                s.js("switchTab('catalog')")
                time.sleep(0.8)
                s.captura(args.captura)
                print("\ncaptura em %s" % args.captura)
            except Exception as e:
                print("\nsem captura: %s" % str(e)[:80])
    finally:
        s.fechar()
        if servidor:
            servidor.parar()
    sys.exit(p.resumo())


if __name__ == "__main__":
    main()
