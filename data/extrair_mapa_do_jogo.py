#!/usr/bin/env python3
"""
extrair_mapa_do_jogo.py — Capítulo 2, F13-T113 (o mapa de hoje; Leo, 05/11/2026: "tem algo que não está
certo… na saída do rio tem um arbusto no meio, não na borda, isso é antigo… e tem as alterações das almas
dos dragões no mapa"). Tira do jogo instalado o que o mapa do app precisa para ser o de hoje, sem mudar nada lá:

  - as imagens do minimapa de agora (o map11.png do Data Dragon é a arte antiga): uma por alma e por forma do
    covil do Barão (2dlevelminimap_<alma>_baron<n>.tex), em assets/mapa/;
  - as malhas de colisão (Leo, 05/11/2026: "e as malhas de colisões?"), prontas como o app lê, em
    data/mapa_variantes.js (window.MAPA_HOJE): a grade de base de hoje, a AIPath_SRX_3 (a que casa com o
    minimapa de agora; o data/gerar_mapa.py ainda lê a SRX_2), no mesmo formato do data/mapa.js; e, por variante,
    as regiões que a camada de navegação do jogo (NavGrid_*.ngrid_overlay) troca por cima dela — as almas que
    mudam o terreno e as formas do covil do Barão. O covil do Atakhan fica de fora: o Atakhan saiu do jogo (Leo,
    05/11/2026: "o atakhan foi removido"), embora os arquivos dele continuem lá.

Nenhum dado é digitado: tudo sai dos arquivos.

Uso:  python extrair_mapa_do_jogo.py [pasta do LoL]
      Precisa do zstandard e do Pillow (o Pillow lê a textura DXT5).

Os formatos (lidos e conferidos nesta tarefa; nada copiado de outro programa):
  .wad: a entrada de tipo 4 é zstd em pedaços — vários quadros zstd seguidos (e, se um pedaço não comprimiu,
  os bytes crus); a soma tem o tamanho que a entrada diz.
  .tex: "TEX\\0", largura e altura (2 bytes cada), 1 byte, o formato (12 = DXT5), 1 byte, as marcas (1 = com
  mipmaps); os mipmaps vêm do menor ao maior, e o tamanho cheio é o último bloco do arquivo.
  .ngrid_overlay: versão (1 byte), o número de regiões (1 byte) e, por região, x, z, largura e altura em
  células (4 inteiros de 4 bytes) e então largura × altura marcas de 2 bytes, linha a linha (z), a mesma
  marca da grade de base (1 arbusto, 2 parede, 4 estrutura, 64 transparente, 128 rio), que substitui a da
  base naquela célula; sobra 1 byte no fim do arquivo.
"""
import io
import json
import os
import struct
import sys

import zstandard
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import gerar_mapa as gm   # o xxHash64, a leitura da grade e o caminho do Map11.wad.client

LOL = sys.argv[1] if len(sys.argv) > 1 else r"C:\Riot Games\League of Legends"
WAD = os.path.join(LOL, "Game", "DATA", "FINAL", "Maps", "Shipping", "Map11.wad.client")
IMAGENS = os.path.join(RAIZ, "assets", "mapa")
SAIDA = os.path.join(AQUI, "mapa_variantes.js")
GRADE_HOJE = "ASSETS/Maps/NavGrid/Map11/AIPath_SRX_3.aimesh_ngrid"
# só as almas que mudam o terreno (Leo, 05/11/2026: "eu quero as almas que realmente afetam o mapa… o Hextec só
# adiciona portais"): a Nuvem e a Hextec ficam de fora; a Quimtec não tem imagem própria (a de base, com a camada dela)
ALMAS = ["base", "infernal", "mountain", "ocean"]
# as camadas que o map11.bin cita (as de Map90, as de regiões e as do Atakhan, que saiu do jogo, ficam de fora)
NOMES_CAMADAS = ["Infernal_SEASONAL", "Mountain_SEASONAL", "Ocean_SEASONAL", "Chemtech", "Cup_Base", "Tunnel_Base"]
# a variante no app → a camada do jogo. A forma 2 do covil do Barão é a Tunnel e a 3 é a Cup (conferido pela
# diferença entre as imagens baron2/baron3 e a de base: 356 de 454 e 118 de 136 células dentro da camada)
VARIANTES = {"infernal": "Infernal_SEASONAL", "montanha": "Mountain_SEASONAL", "oceano": "Ocean_SEASONAL",
             "quimtec": "Chemtech", "barao2": "Tunnel_Base", "barao3": "Cup_Base"}


def tipo(v):
    """A célula como o app a usa, pelas regras do gerar_mapa.py: 1 parede que esconde, 2 arbusto, 4 só para o passo."""
    transp = gm.PAREDE_TRANSPARENTE | gm.PAREDE_ESTRUTURA
    return ((1 if v & gm.PAREDE and not v & transp else 0) | (2 if v & gm.ARBUSTO and not v & gm.PAREDE else 0)
            | (4 if v & transp else 0))


def indice(wad):
    with open(wad, "rb") as f:
        cab = f.read(4)
        if cab[:2] != b"RW" or cab[2] != 3:
            sys.exit("%s não é um .wad versão 3 (cabeçalho %r)" % (wad, cab))
        f.seek(4 + 256 + 8)
        (n,) = struct.unpack("<I", f.read(4))
        return {h: (pos, comp, tam, tipo) for h, pos, comp, tam, tipo, _d, _s, _c in
                (struct.unpack("<QIIIBBHQ", f.read(32)) for _ in range(n))}


def ler(wad, idx, caminho):
    pos, comp, tam, tipo = idx[gm.xxh64(caminho.lower().encode())]
    with open(wad, "rb") as f:
        f.seek(pos)
        b = f.read(comp)
    tipo &= 0xF
    if tipo == 0:
        return b
    if tipo == 3:
        return zstandard.ZstdDecompressor().decompress(b, max_output_size=tam)
    if tipo != 4:
        sys.exit("%s está guardado no tipo %d, que este leitor não abre" % (caminho, tipo))
    out = bytearray()
    while b:
        if b[:4] != b"\x28\xb5\x2f\xfd":   # o pedaço que não comprimiu
            out += b
            break
        d = zstandard.ZstdDecompressor().decompressobj()
        out += d.decompress(b)
        b = d.unused_data
    if len(out) != tam:
        sys.exit("%s: abriu com %d bytes, a entrada diz %d" % (caminho, len(out), tam))
    return bytes(out)


def textura(b):
    if b[:4] != b"TEX\0":
        sys.exit("não é uma textura .tex")
    w, h, _u, fmt, _r, _marcas = struct.unpack_from("<HHBBBB", b, 4)
    if fmt != 12:
        sys.exit("textura no formato %d: este leitor conhece o 12 (DXT5)" % fmt)
    tam = ((w + 3) // 4) * ((h + 3) // 4) * 16
    return Image.frombytes("RGBA", (w, h), b[len(b) - tam:], "bcn", 3)


def camada(b):
    ver, n = b[0], b[1]
    if ver != 1:
        sys.exit("camada versão %d: este leitor conhece a 1" % ver)
    p, regioes = 2, []
    for _ in range(n):
        x, z, w, h = struct.unpack_from("<4i", b, p)
        p += 16
        regioes.append({"x": x, "z": z, "w": w, "h": h, "marcas": list(struct.unpack_from("<%dH" % (w * h), b, p))})
        p += 2 * w * h
    if len(b) - p != 1:
        sys.exit("camada com %d bytes sobrando (o formato conhecido deixa 1)" % (len(b) - p))
    return regioes


def main():
    if not os.path.exists(WAD):
        sys.exit("não achei o mapa do jogo em %s (passe a pasta do LoL como argumento)" % WAD)
    idx = indice(WAD)
    tem = lambda c: gm.xxh64(c.lower().encode()) in idx
    os.makedirs(IMAGENS, exist_ok=True)
    feitas = []
    for alma in ALMAS:
        for n in (1, 2, 3):
            c = "assets/maps/info/map11/2dlevelminimap_%s_baron%d.tex" % (alma, n)
            if tem(c):
                nome = "%s_baron%d.png" % (alma, n)
                textura(ler(WAD, idx, c)).save(os.path.join(IMAGENS, nome), optimize=True)
                feitas.append(nome)
    camadas = {}
    for nome in NOMES_CAMADAS:
        c = "ASSETS/Maps/NavGrid/NavGrid_%s.ngrid_overlay" % nome
        if tem(c):
            camadas[nome] = camada(ler(WAD, idx, c))
    # a malha de base de hoje, no formato do data/mapa.js
    g = gm.ler_grade(ler(WAD, idx, GRADE_HOJE))
    tipos = [tipo(v) for v in g["marcas"]]
    hoje = {"fonte": GRADE_HOJE, "versao": g["versao"], "celula": g["celula"], "nx": g["nx"], "nz": g["nz"],
            "min": [round(g["min"][0], 3), round(g["min"][1], 3)], "max": [round(g["max"][0], 3), round(g["max"][1], 3)],
            "paredes": gm.bits([t & 1 for t in tipos]), "arbustos": gm.bits([t & 2 for t in tipos]),
            "soPasso": gm.bits([t & 4 for t in tipos]), "variantes": {}}
    # por variante: [x, z, largura, altura, os tipos das células linha a linha (z), um algarismo de 0 a 7 por célula]
    for chave, nome in VARIANTES.items():
        if nome not in camadas:
            continue
        for r in camadas[nome]:
            if r["x"] < 0 or r["z"] < 0 or r["x"] + r["w"] > g["nx"] or r["z"] + r["h"] > g["nz"]:
                sys.exit("a camada %s sai da grade" % nome)
        hoje["variantes"][chave] = {"camada": "ASSETS/Maps/NavGrid/NavGrid_%s.ngrid_overlay" % nome,
                                    "regioes": [[r["x"], r["z"], r["w"], r["h"], "".join(str(tipo(v)) for v in r["marcas"])]
                                                for r in camadas[nome]]}
    js = ("// GERADO por data/extrair_mapa_do_jogo.py - nao editar a mao (F13-T113).\n"
          "// A malha de colisao de hoje (AIPath_SRX_3) no formato do data/mapa.js e, por variante (as almas que mudam o\n"
          "// terreno e as formas do covil do Barao), as regioes que a camada de navegacao do jogo troca por cima dela:\n"
          "// [x, z, largura, altura, tipos], um algarismo por celula, linha a linha: 1 parede, 2 arbusto, 4 so para o passo.\n"
          "window.MAPA_HOJE = " + json.dumps(hoje, separators=(",", ":")) + ";\n")
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write(js)
    conta = lambda b: sum(1 for x in tipos if x & b)
    print("imagens (%d) em %s: %s" % (len(feitas), IMAGENS, ", ".join(feitas)))
    print("malha de hoje %s: %d × %d · parede %d · arbusto %d · só o passo %d"
          % (GRADE_HOJE.rsplit("/", 1)[1], g["nx"], g["nz"], conta(1), conta(2), conta(4)))
    print("variantes em %s (%d KB): %s" % (SAIDA, len(js) // 1024,
          ", ".join("%s (%d regiões)" % (k, len(v["regioes"])) for k, v in hoje["variantes"].items())))


if __name__ == "__main__":
    main()
