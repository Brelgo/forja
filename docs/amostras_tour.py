"""Captura das duas opções do tour (F13-T101, 02/11/2026).

Abre o app de verdade no Chrome do QA (mudo, sem tocar no servidor das builds),
injeta docs/amostras/fase13-t101-tour.js e fotografa, em 1440×900:
  Opção 1 — o tour curto: 6 passos no primeiro acesso, a tela escurecida;
  Opção 2 — a dica na hora: 1 ou 2 balões na primeira visita a cada tela, sem escurecer.
Nada disso é código do app. Saída: docs/screenshots/fase13-t101-tour-opcoes.png
Uso: python docs/amostras_tour.py
"""
import base64
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import qa_roteiro as q  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

RAIZ = os.path.dirname(AQUI)
JS = open(os.path.join(AQUI, "amostras", "fase13-t101-tour.js"), encoding="utf-8").read()

PASSOS = {
    "1-loja": (1, "loja", "#grid .card", {
        "sec": "A loja · 1 de 6", "titulo": "Bem-vindo à loja", "passo": 1, "total": 6, "lado": "direita",
        "texto": "@N Passe o mouse num item para ver o que ele faz. Segure <b>Shift</b> para ler a ficha inteira."}),
    "1-forja": (1, "forja", ".build-cat", {
        "sec": "A forja · 4 de 6", "titulo": "Sua build mora aqui", "passo": 4, "total": 6, "lado": "direita",
        "texto": "Uma build é a lista do que comprar numa partida. Os itens que você clica na loja caem nestas caixas. Arraste para mudar a ordem."}),
    "2-loja": (2, "loja", "#grid .card", {
        "sec": "Dica", "titulo": "Clique para levar", "passo": 1, "total": 2, "lado": "direita",
        "texto": "Clicou num item, ele vai para a sua build. Clique de novo para tirar."}),
    "2-forja": (2, "forja", ".build-cat", {
        "sec": "Dica", "titulo": "As caixas da build", "passo": 1, "total": 2, "lado": "direita",
        "texto": "Cada caixa é uma etapa da partida: o começo, o principal, o fim. Arraste os itens entre elas."}),
}


def foto(s):
    dados = s.envia("Page.captureScreenshot", {"format": "png"})["data"]
    return Image.open(io.BytesIO(base64.b64decode(dados))).convert("RGB")


def mostra(s, chave):
    op, tema, alvo, d = PASSOS[chave]
    d = dict(d)
    texto = json.dumps(d.pop("texto"), ensure_ascii=False).replace("@N", "Aqui estão os \" + CATALOG.items.length + \" itens do jogo.")
    r = s.js("window.scrollTo(0, 0); amostraTour(%d, %s, %s, Object.assign(%s, { texto: %s }))"
             % (op, json.dumps(tema), json.dumps(alvo), json.dumps(d, ensure_ascii=False), texto))
    assert r == "ok", r
    time.sleep(0.5)
    return foto(s)


srv = q.Servidor()
s = q.Sessao(srv.url)
fotos = {}
try:
    s.abrir()
    s.tela(1440, 900)
    s.limpar_memoria()
    s.entrar()
    s.js(JS + "; 'ok'")
    s.js("switchTab('catalog'); 'ok'")
    time.sleep(0.6)
    fotos["1-loja"] = mostra(s, "1-loja")
    fotos["2-loja"] = mostra(s, "2-loja")
    s.js("amostraTourLimpa(); 'ok'")
    s.nova_build()
    fotos["1-forja"] = mostra(s, "1-forja")
    fotos["2-forja"] = mostra(s, "2-forja")
finally:
    s.fechar()
    srv.parar()

# a prancha: duas colunas (as opções), duas linhas (loja e forja), a metade do tamanho
W, H = 720, 450
TOPO, MARGEM, ROT = 70, 24, 30
img = Image.new("RGB", (MARGEM * 3 + W * 2, TOPO + (ROT + H) * 2 + MARGEM * 2), "#120c08")
dr = ImageDraw.Draw(img)
try:
    f1 = ImageFont.truetype("georgiab.ttf", 22)
    f2 = ImageFont.truetype("georgia.ttf", 15)
except OSError:
    f1 = f2 = ImageFont.load_default()
cabecas = [("Opção 1 — o tour curto", "6 passos no primeiro acesso; a tela escurece; Próximo, Pular tour, ×"),
           ("Opção 2 — a dica na hora", "1 ou 2 balões na 1ª visita a cada tela; nada escurece; Entendi")]
for c, (t, sub) in enumerate(cabecas):
    x = MARGEM + c * (W + MARGEM)
    dr.text((x, 14), t, fill="#e8d3a2", font=f1)
    dr.text((x, 44), sub, fill="#b89a66", font=f2)
    for l, onde in enumerate(("loja", "forja")):
        y = TOPO + l * (ROT + H + MARGEM)
        dr.text((x, y + 4), "na loja" if onde == "loja" else "na forja", fill="#d9c08a", font=f2)
        img.paste(fotos["%d-%s" % (c + 1, onde)].resize((W, H), Image.LANCZOS), (x, y + ROT))
saida = os.path.join(RAIZ, "docs", "screenshots", "fase13-t101-tour-opcoes.png")
img.save(saida)
print("ok", saida)
