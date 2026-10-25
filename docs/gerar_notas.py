"""As notas de atualização (F13-T80): lê os commits de tarefa (F13-T…) desde docs/notas.json → "desde"
e grava data/notas.js (window.NOTAS), que o mural da loja mostra. Sem digitar nada à mão no app.

De cada commit de tarefa, as linhas "Notas: Adicionado|Ajustado|Removido — <frase para quem usa>"
(o jeito escolhido pelo Leo em 25/10/2026); as tarefas de antes disso vêm de docs/notas.json →
"antigas". O "Em breve" (o roteiro na língua de quem usa) vem de docs/notas.json → "embreve".
Sem hora nem data de geração no arquivo: rodar de novo sem commit novo não muda nada.

Uso:  python docs/gerar_notas.py           (grava data/notas.js)
      python docs/gerar_notas.py --conferir (só diz se o arquivo está em dia e quais tarefas estão sem nota)
"""
import json, os, re, subprocess, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SAIDA = os.path.join(RAIZ, "data", "notas.js")
CATEGORIAS = {"Adicionado": "add", "Ajustado": "aj", "Removido": "rem"}
LINHA = re.compile(r"^Notas:\s*(Adicionado|Ajustado|Removido)\s*[—–-]\s*(.+?)\s*$", re.M)


def notas():
    fonte = json.load(open(os.path.join(AQUI, "notas.json"), encoding="utf-8"))
    bruto = subprocess.run(["git", "-C", RAIZ, "log", "--since=%s 00:00" % fonte["desde"], "--date=short", "--format=%x1e%ad%x1f%s%x1f%b"],
                           capture_output=True, text=True, encoding="utf-8").stdout
    por_dia, sem_nota = {}, []
    for registro in bruto.split("\x1e"):
        if not registro.strip():
            continue
        data, assunto, corpo = (registro.split("\x1f") + ["", ""])[:3]
        m = re.match(r"(F\d+-T\d+[a-z]?):", assunto)
        if not m or data < fonte["desde"]:
            continue
        tarefa = m.group(1)
        linhas = [[c, f] for c, f in LINHA.findall(corpo)] or fonte["antigas"].get(tarefa)
        if not linhas:
            sem_nota.append(tarefa)
            continue
        dia = por_dia.setdefault(data, {"add": [], "aj": [], "rem": []})
        for cat, frase in reversed(linhas):          # o log vem do mais novo; dentro do dia, a ordem das tarefas
            dia[CATEGORIAS[cat]].insert(0, frase)
    datas = [{"data": "%s/%s/%s" % (d[8:10], d[5:7], d[:4]), **por_dia[d]} for d in sorted(por_dia, reverse=True)]
    return {"datas": datas, "embreve": fonte["embreve"]}, sem_nota


def texto(n):
    return ("// Gerado por docs/gerar_notas.py a partir dos commits de tarefa (F13-T80). Não editar à mão.\n"
            "window.NOTAS = " + json.dumps(n, ensure_ascii=False, indent=1) + ";\n")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    n, sem_nota = notas()
    if "--conferir" in sys.argv:
        atual = open(SAIDA, encoding="utf-8").read() if os.path.exists(SAIDA) else ""
        print("em dia" if atual == texto(n) else "desatualizado", "· sem nota:", sem_nota or "nenhuma")
        return
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto(n))
    print("%d dias · %d notas · data/notas.js%s" % (len(n["datas"]), sum(len(d[k]) for d in n["datas"] for k in ("add", "aj", "rem")),
                                                 " · SEM NOTA: %s" % sem_nota if sem_nota else ""))


if __name__ == "__main__":
    main()
