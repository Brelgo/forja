#!/usr/bin/env python3
"""
gerar_mapa.py — Capítulo 2, F13-T105 (o mapa interativo, item 9 do roteiro)
A forma de Summoner's Rift para o mapa da build: onde há parede e onde há arbusto,
célula por célula, e os limites do mapa em unidades do jogo (a escala do zoom, do
raio de visão e do círculo ciano). Grava data/mapa.js (window.MAPA).

A fonte é a grade de navegação do próprio jogo — ASSETS/Maps/NavGrid/Map11/
AIPath_SRX_2.aimesh_ngrid, a que o map11.bin liga às configurações de Summoner's
Rift de hoje —, lida de dentro do Map11.wad.client da instalação do LoL, sem mudar
nada lá. Nenhum dado é digitado: tudo sai do arquivo.

Uso:  python gerar_mapa.py [pasta do LoL]
      Sem argumento, procura em C:\\Riot Games\\League of Legends. Rodar de novo
      quando um patch mexer no mapa. Precisa do pacote zstandard (o .wad guarda os
      arquivos compactados em zstd).

O formato (lido e conferido nesta tarefa; nada copiado de outro programa):
  .wad (versão 3): "RW", versão, 256 bytes de assinatura, 8 de checksum, o número
  de entradas e, por entrada, 32 bytes — o xxHash64 do caminho em minúsculas,
  posição, tamanho compactado, tamanho, tipo (3 = zstd), duplicado, subpedaço,
  checksum.
  .aimesh_ngrid (versão 7): versão maior (1 byte) e menor (2), o canto mínimo e o
  máximo (3 floats cada; x, altura, z), o tamanho da célula, as células em x e em z;
  depois 48 bytes por célula, e então um short de marcas por célula (o bitfield
  de visão e caminho): 1 arbusto, 2 parede, 4 parede de estrutura, 64 parede
  transparente (bloqueia o passo, não a visão). A célula (x, z) é a de índice
  z * nx + x e cobre [min + x * célula, min + (x + 1) * célula).

A saída não tem data: rodar duas vezes sobre o mesmo jogo dá o mesmo arquivo.
"""
import base64
import os
import struct
import sys

import zstandard

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "mapa.js")
LOL = sys.argv[1] if len(sys.argv) > 1 else r"C:\Riot Games\League of Legends"
WAD = os.path.join(LOL, "Game", "DATA", "FINAL", "Maps", "Shipping", "Map11.wad.client")
GRADE = "ASSETS/Maps/NavGrid/Map11/AIPath_SRX_2.aimesh_ngrid"
BYTES_POR_CELULA = 48
ARBUSTO, PAREDE, PAREDE_ESTRUTURA, PAREDE_TRANSPARENTE = 1, 2, 4, 64

# ---------------------------------------------------------------- xxHash64 (semente 0)
M64 = (1 << 64) - 1
P1, P2, P3, P4, P5 = 11400714785074694791, 14029467366897019727, 1609587929392839161, 9650029242287828579, 2870177450012600261


def _rotl(x, r):
    return ((x << r) | (x >> (64 - r))) & M64


def _rodada(acc, v):
    return (_rotl((acc + v * P2) & M64, 31) * P1) & M64


def xxh64(b):
    n, i = len(b), 0
    if n >= 32:
        v = [(P1 + P2) & M64, P2, 0, (-P1) & M64]
        while i + 32 <= n:
            for k in range(4):
                v[k] = _rodada(v[k], int.from_bytes(b[i + 8 * k:i + 8 * k + 8], "little"))
            i += 32
        h = (_rotl(v[0], 1) + _rotl(v[1], 7) + _rotl(v[2], 12) + _rotl(v[3], 18)) & M64
        for x in v:
            h = ((h ^ _rodada(0, x)) * P1 + P4) & M64
    else:
        h = P5
    h = (h + n) & M64
    while i + 8 <= n:
        h = (_rotl(h ^ _rodada(0, int.from_bytes(b[i:i + 8], "little")), 27) * P1 + P4) & M64
        i += 8
    if i + 4 <= n:
        h = (_rotl(h ^ ((int.from_bytes(b[i:i + 4], "little") * P1) & M64), 23) * P2 + P3) & M64
        i += 4
    while i < n:
        h = (_rotl(h ^ ((b[i] * P5) & M64), 11) * P1) & M64
        i += 1
    h ^= h >> 33
    h = (h * P2) & M64
    h ^= h >> 29
    h = (h * P3) & M64
    return h ^ (h >> 32)


assert xxh64(b"") == 0xEF46DB3751D8E999   # o valor de referência do xxHash64 vazio


# ---------------------------------------------------------------- o .wad
def ler_do_wad(caminho_wad, caminho):
    alvo = xxh64(caminho.lower().encode())
    with open(caminho_wad, "rb") as f:
        cab = f.read(4)
        if cab[:2] != b"RW" or cab[2] != 3:
            sys.exit("%s não é um .wad versão 3 (cabeçalho %r)" % (caminho_wad, cab))
        f.seek(4 + 256 + 8)
        (n,) = struct.unpack("<I", f.read(4))
        for _ in range(n):
            h, pos, comp, tam, tipo, _dup, _sub, _chk = struct.unpack("<QIIIBBHQ", f.read(32))
            if h != alvo:
                continue
            f.seek(pos)
            bruto = f.read(comp)
            tipo &= 0xF
            if tipo == 0:
                return bruto
            if tipo == 3:
                return zstandard.ZstdDecompressor().decompress(bruto, max_output_size=tam)
            sys.exit("%s está guardado no tipo %d, que este leitor não abre" % (caminho, tipo))
    sys.exit("%s não está no %s" % (caminho, caminho_wad))


# ---------------------------------------------------------------- a grade
def ler_grade(b):
    maior, menor = b[0], struct.unpack_from("<H", b, 1)[0]
    if maior != 7:
        sys.exit("grade versão %d.%d: este leitor conhece a 7" % (maior, menor))
    mx, my, mz, Mx, My, Mz, celula = struct.unpack_from("<7f", b, 3)
    nx, nz = struct.unpack_from("<2i", b, 31)
    n = nx * nz
    ini = 39 + n * BYTES_POR_CELULA
    marcas = struct.unpack_from("<%dH" % n, b, ini)
    return {"versao": "%d.%d" % (maior, menor), "min": (mx, mz), "max": (Mx, Mz), "celula": celula,
            "nx": nx, "nz": nz, "marcas": marcas}


def bits(lista):
    """Uma célula por bit, na ordem z * nx + x, em base64."""
    out = bytearray((len(lista) + 7) // 8)
    for i, v in enumerate(lista):
        if v:
            out[i >> 3] |= 1 << (i & 7)
    return base64.b64encode(bytes(out)).decode()


def main():
    if not os.path.exists(WAD):
        sys.exit("não achei o mapa do jogo em %s (passe a pasta do LoL como argumento)" % WAD)
    g = ler_grade(ler_do_wad(WAD, GRADE))
    m = g["marcas"]
    n = g["nx"] * g["nz"]
    # parede que esconde: a parede sem a marca de transparente. A transparente (a borda fina das paredes,
    # conferida por cima do map11.png) e a de estrutura (torres, inibidores, nexo) param o passo, mas a
    # visão passa. Arbusto dentro de parede conta como parede
    transp = PAREDE_TRANSPARENTE | PAREDE_ESTRUTURA
    parede = [bool(v & PAREDE) and not (v & transp) for v in m]
    arbusto = [bool(v & ARBUSTO) and not (v & PAREDE) for v in m]
    so_passo = [bool(v & transp) for v in m]
    conta = lambda l: sum(1 for x in l if x)
    print("grade %s · %d × %d células de %.0f · x %.1f…%.1f · z %.1f…%.1f"
          % (g["versao"], g["nx"], g["nz"], g["celula"], g["min"][0], g["max"][0], g["min"][1], g["max"][1]))
    print("parede %d (%.1f%%) · arbusto %d (%.1f%%) · só bloqueia o passo %d"
          % (conta(parede), 100.0 * conta(parede) / n, conta(arbusto), 100.0 * conta(arbusto) / n, conta(so_passo)))
    js = ("// GERADO por data/gerar_mapa.py - nao editar a mao.\n"
          "// A forma de Summoner's Rift lida da grade de navegacao do jogo (%s, versao %s):\n"
          "// celula de `celula` unidades; a celula (x, z) e o bit z * nx + x; min/max em unidades do jogo.\n"
          "// paredes: a visao nao passa; arbustos: quem esta dentro so e visto por quem tem visao do arbusto;\n"
          "// soPasso: parede transparente e de estrutura (para o passo, nao a visao).\n"
          "// A imagem do mapa (img/map/map11.png do Data Dragon) cobre de min a min + n * celula: conferido\n"
          "// na F13-T105, o melhor encaixe da grade sobre ela fica a menos de 2 px (1 px = ~29 unidades).\n"
          "window.MAPA = {\n"
          "  fonte: %r,\n"
          "  celula: %r, nx: %d, nz: %d,\n"
          "  min: [%.3f, %.3f], max: [%.3f, %.3f],\n"
          "  paredes: \"%s\",\n"
          "  arbustos: \"%s\",\n"
          "  soPasso: \"%s\"\n"
          "};\n") % (GRADE, g["versao"], GRADE, g["celula"], g["nx"], g["nz"],
                     g["min"][0], g["min"][1], g["max"][0], g["max"][1], bits(parede), bits(arbusto), bits(so_passo))
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write(js)
    print("gravado %s (%d KB)" % (SAIDA, len(js) // 1024))


if __name__ == "__main__":
    main()
