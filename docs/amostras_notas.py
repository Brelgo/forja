"""Amostra F13-T80: as duas opções das notas de atualização, desenhadas dentro do app de verdade
(docs/amostras/fase13-notas.js) e capturadas em docs/screenshots/fase13-t80-notas-opcoes.png.

As notas vêm dos commits de tarefa (F13-T…: <frase>), dos dois últimos dias; a divisão em
Adicionado · Ajustado · Removido aqui é só um esboço (a regra é decisão do Leo)."""
import base64, io, json, os, re, subprocess, sys, time
sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import qa_roteiro as q
from PIL import Image, ImageDraw, ImageFont

log = subprocess.run(["git", "-C", RAIZ, "log", "--format=%ad|%s", "--date=short"], capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
por_dia = {}
for linha in log:
    data, _, assunto = linha.partition("|")
    m = re.match(r"F13-T\d+[a-z]?: (.+)", assunto)
    if m:
        por_dia.setdefault(data, []).append(m.group(1))
dias = sorted(por_dia, reverse=True)[:2]
AJUSTE = re.compile(r"conserto|corrig|ajuste|não |sem |vira|fecha|some|volta|só |cabe", re.I)
datas = []
for d in dias:
    a, j = [], []
    for x in por_dia[d]:
        x = x[0].upper() + x[1:]
        (j if AJUSTE.search(x) else a).append(x)
    datas.append({"data": "%s/%s/%s" % (d[8:10], d[5:7], d[:4]), "add": a, "aj": j, "rem": []})
# o roteiro, na língua de quem usa (sem número de tarefa nem data)
embreve = [
    ["Catálogo e Builds em abas", "cada tela com o seu link, para abrir as duas lado a lado e mandar o endereço direto"],
    ["A entrada da loja e o tour", "a fachada de uma região a cada visita, e um passeio guiado pelo Montador"],
    ["Mapa interativo", "onde pôr a visão e as rotas da selva e do farm"],
    ["Calculadora de armadura", "quanto o tanque aguenta, na forja"],
    ["Comparar duas builds", "lado a lado, atributo por atributo"],
    ["Campeões e o Bestiário", "as fichas dos campeões e dos monstros, e a calculadora dos épicos"],
]
NOTAS = {"datas": datas, "embreve": embreve}


def foto(s):
    d = s.envia("Page.captureScreenshot", {"format": "png"})["data"]
    return Image.open(io.BytesIO(base64.b64decode(d))).convert("RGB")


js = open(os.path.join(AQUI, "amostras", "fase13-notas.js"), encoding="utf-8").read()
fotos = {}
srv = q.Servidor(); s = q.Sessao(srv.url)
try:
    s.abrir(); s.tela(1600, 900); s.entrar()
    s.js("(() => { window.ATUALIZACAO = ATUALIZACAO; window.__NOTAS = %s; return 1; })()" % json.dumps(NOTAS, ensure_ascii=False))
    s.js(js + "; 1")
    s.js("(() => { switchTab('catalog'); window.scrollTo(0, 0); return 1; })()"); time.sleep(0.6)
    icone = s.js("(() => { const b = document.getElementById('notas-btn').getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom].map(Math.round); })()")
    fotos["limpa"] = foto(s)
    s.js("(() => { __notasAmostra.opcaoA('novidades'); return 1; })()"); time.sleep(0.9)
    fotos["A1"] = foto(s)
    s.js("(() => { __notasAmostra.opcaoA('embreve'); return 1; })()"); time.sleep(0.5)
    fotos["A2"] = foto(s)
    s.js("(() => { document.getElementById('overlay').classList.remove('show'); __notasAmostra.opcaoB(); return 1; })()"); time.sleep(0.6)
    fotos["B"] = foto(s)
    print("erros:", s.erros[:3])
finally:
    s.fechar(); srv.parar()

f_t = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 24)
f_p = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 17)
esc_ = 0.6
peq = {k: v.resize((int(v.width * esc_), int(v.height * esc_))) for k, v in fotos.items() if k != "limpa"}
x0, y0 = 40, 100
W = x0 * 2 + peq["A1"].width * 2 + 30
H = y0 + peq["A1"].height + 60 + peq["B"].height + 50
img = Image.new("RGB", (W, H), (22, 17, 13)); d = ImageDraw.Draw(img)
d.text((40, 22), "F13-T80 — as notas de atualização: duas opções (o ícone do pergaminho fica ao lado da Acessibilidade)", font=f_t, fill=(233, 179, 106))
d.text((40, 60), "A — o pergaminho, como a ficha do item: duas abas, Novidades (por data: Adicionado · Ajustado · Removido) e O que vem por aí", font=f_p, fill=(207, 194, 173))
img.paste(peq["A1"], (x0, y0)); img.paste(peq["A2"], (x0 + peq["A1"].width + 30, y0))
y = y0 + peq["A1"].height + 20
d.text((40, y), "B — o mural da loja: um quadro de madeira com bilhetes pregados, deslizando da direita; o \u201cEm breve\u201d pregado no alto", font=f_p, fill=(207, 194, 173))
img.paste(peq["B"], (x0, y + 32))
# o ícone, ampliado, ao lado do mural
ic = fotos["limpa"].crop((icone[0] - 150, icone[1] - 14, icone[2] + 90, icone[3] + 16))
ic = ic.resize((ic.width * 3, ic.height * 3))
img.paste(ic, (x0 + peq["B"].width + 40, y + 60))
d.text((x0 + peq["B"].width + 40, y + 60 + ic.height + 10), "o ícone (ampliado), com o número da atualização", font=f_p, fill=(207, 194, 173))
img.save(os.path.join(RAIZ, "docs", "screenshots", "fase13-t80-notas-opcoes.png"))
print("salvo", img.size)
