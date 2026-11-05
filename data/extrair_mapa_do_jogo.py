#!/usr/bin/env python3
"""
extrair_mapa_do_jogo.py — Capítulo 2, F13-T113 (o mapa de hoje; Leo, 05/11/2026: "tem algo que não está
certo… na saída do rio tem um arbusto no meio, não na borda, isso é antigo… e tem as alterações das almas
dos dragões no mapa"). Tira do jogo instalado o que o mapa do app precisa para ser o de hoje, sem mudar nada lá:

  - as imagens do minimapa de agora (o map11.png do Data Dragon é a arte antiga): uma por alma e por forma do
    covil do Barão (2dlevelminimap_<alma>_baron<n>.tex), em assets/mapa/;
  - as camadas de navegação que o jogo põe por cima da grade (NavGrid_*.ngrid_overlay): as almas que mudam
    parede ou arbusto e as formas do covil do Barão, em data/mapa_camadas.json. O covil do Atakhan fica de fora:
    o Atakhan saiu do jogo (Leo, 05/11/2026: "o atakhan foi removido"), embora os arquivos dele continuem lá.

A grade de base é a do data/gerar_mapa.py. Nenhum dado é digitado: tudo sai dos arquivos.

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
CAMADAS = os.path.join(AQUI, "mapa_camadas.json")
# só as almas que mudam o terreno (Leo, 05/11/2026: "eu quero as almas que realmente afetam o mapa… o Hextec só
# adiciona portais"): a Nuvem e a Hextec ficam de fora; a Quimtec não tem imagem própria (a de base, com a camada dela)
ALMAS = ["base", "infernal", "mountain", "ocean"]
# as camadas que o map11.bin cita (as de Map90, as de regiões e as do Atakhan, que saiu do jogo, ficam de fora)
NOMES_CAMADAS = ["Infernal_SEASONAL", "Mountain_SEASONAL", "Ocean_SEASONAL", "Chemtech", "Cup_Base", "Tunnel_Base"]


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
    with open(CAMADAS, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"_gerado_por": "data/extrair_mapa_do_jogo.py — não editar à mão", "camadas": camadas}, f, separators=(",", ":"))
    print("imagens (%d) em %s: %s" % (len(feitas), IMAGENS, ", ".join(feitas)))
    print("camadas (%d) em %s: %s" % (len(camadas), CAMADAS, ", ".join("%s (%d regiões)" % (k, len(v)) for k, v in camadas.items())))


if __name__ == "__main__":
    main()
