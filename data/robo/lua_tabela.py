"""Lê uma tabela Lua de dados (o formato do Module:ItemData/data da wiki) para
Python: tabelas viram dict (com chave) ou list (sem chave), e o resto vira
str, int, float, bool ou None. Só o que um módulo de dados usa — sem expressões,
sem funções. Erro de leitura para com a linha e a coluna: tabela lida pela
metade não pode passar por tabela inteira. Chave repetida vale a última, como
no Lua, e fica anotada em `avisos` — a wiki já teve uma.
"""


class ErroLua(ValueError):
    pass


_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "\n": "\n", "a": "\a", "b": "\b", "f": "\f", "v": "\v"}


class _Leitor:
    def __init__(self, texto, avisos):
        self.t = texto
        self.i = 0
        self.avisos = avisos

    def erro(self, msg):
        linha = self.t.count("\n", 0, self.i) + 1
        coluna = self.i - (self.t.rfind("\n", 0, self.i) + 1) + 1
        raise ErroLua("%s (linha %d, coluna %d)" % (msg, linha, coluna))

    def pula(self):
        t = self.t
        while self.i < len(t):
            c = t[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif t.startswith("--", self.i):
                # comentário longo: --[[ … ]] e também com nível, --[=[ … ]=] (revisão da
                # T74: o com nível era lido como comentário de uma linha só, e o resto
                # do bloco comentado entrava como dado)
                j = self.i + 3
                while t.startswith("=", j):
                    j += 1
                if t.startswith("--[", self.i) and t.startswith("[", j):
                    fecha = "]" + "=" * (j - self.i - 3) + "]"
                    fim = t.find(fecha, j + 1)
                    if fim < 0:
                        self.erro("comentário longo sem fim")
                    self.i = fim + len(fecha)
                else:
                    fim = t.find("\n", self.i)
                    self.i = len(t) if fim < 0 else fim + 1
            else:
                break

    def ve(self):
        self.pula()
        return self.t[self.i] if self.i < len(self.t) else ""

    def espera(self, s):
        self.pula()
        if not self.t.startswith(s, self.i):
            self.erro("esperava %r" % s)
        self.i += len(s)

    def texto(self):
        aspa = self.t[self.i]
        self.i += 1
        out = []
        while True:
            if self.i >= len(self.t):
                self.erro("texto sem fim")
            c = self.t[self.i]
            if c == aspa:
                self.i += 1
                return "".join(out)
            if c == "\\":
                n = self.t[self.i + 1]
                if n in _ESCAPES:
                    out.append(_ESCAPES[n])
                    self.i += 2
                elif n.isdigit():
                    j = self.i + 1
                    while j < self.i + 4 and self.t[j].isdigit():
                        j += 1
                    out.append(chr(int(self.t[self.i + 1:j])))
                    self.i = j
                else:
                    self.erro("escape desconhecido \\%s" % n)
            elif c == "\n":
                self.erro("quebra de linha dentro de texto")
            else:
                out.append(c)
                self.i += 1

    def texto_longo(self):
        # [[...]] ou [==[...]==]
        j = self.i + 1
        while self.t[j] == "=":
            j += 1
        if self.t[j] != "[":
            self.erro("texto longo malformado")
        fecha = "]" + "=" * (j - self.i - 1) + "]"
        fim = self.t.find(fecha, j + 1)
        if fim < 0:
            self.erro("texto longo sem fim")
        s = self.t[j + 1:fim]
        self.i = fim + len(fecha)
        return s[1:] if s.startswith("\n") else s

    def nome(self):
        j = self.i
        while j < len(self.t) and (self.t[j].isalnum() or self.t[j] == "_"):
            j += 1
        if j == self.i:
            self.erro("esperava um nome")
        s = self.t[self.i:j]
        self.i = j
        return s

    def numero(self):
        j = self.i
        if self.t[j] in "+-":
            j += 1
        if self.t.startswith(("0x", "0X"), j):
            k = j + 2
            while k < len(self.t) and self.t[k] in "0123456789abcdefABCDEF":
                k += 1
            v = int(self.t[j:k], 16)
            v = -v if self.t[self.i] == "-" else v
            self.i = k
            return v
        k = j
        while k < len(self.t) and (self.t[k].isdigit() or self.t[k] in ".eE" or (self.t[k] in "+-" and self.t[k - 1] in "eE")):
            k += 1
        s = self.t[self.i:k]
        try:
            v = float(s) if any(x in s for x in ".eE") else int(s)
        except ValueError:
            self.erro("número malformado %r" % s)
        self.i = k
        return v

    def valor(self):
        c = self.ve()
        if not c:          # o fim do texto ("" está dentro de qualquer texto: sem isto passava por aspa)
            self.erro("o texto acabou antes do valor")
        if c == "{":
            return self.tabela()
        if c in "\"'":
            return self.texto()
        if c == "[" and self.t[self.i + 1] in "[=":
            return self.texto_longo()
        if c.isdigit() or c in "+-." or (c == "-" and self.t[self.i + 1].isdigit()):
            return self.numero()
        if c.isalpha() or c == "_":
            n = self.nome()
            if n == "true":
                return True
            if n == "false":
                return False
            if n == "nil":
                return None
            self.erro("valor desconhecido %r" % n)
        self.erro("esperava um valor")

    def repetida(self, chave):
        linha = self.t.count("\n", 0, self.i) + 1
        self.avisos.append("chave repetida %r na linha %d (vale a última, como no Lua)" % (chave, linha))

    def guarda(self, tabela, chave, valor):
        # no Lua, "chave = nil" não cria a chave (e apaga a que havia) — antes ela ficava
        # com None, e quem lia com .get(chave, padrão) recebia None em vez do padrão
        if valor is None:
            tabela.pop(chave, None)
        else:
            tabela[chave] = valor

    def tabela(self):
        self.espera("{")
        com_chave, lista = {}, []
        while True:
            c = self.ve()
            if not c:
                self.erro("o texto acabou com a tabela aberta")
            if c == "}":
                self.i += 1
                break
            if c == "[" and self.t[self.i + 1] not in "[=":
                self.i += 1
                chave = self.valor()
                self.espera("]")
                self.espera("=")
                if chave in com_chave:
                    self.repetida(chave)
                self.guarda(com_chave, chave, self.valor())
            elif (c.isalpha() or c == "_") and self._e_atribuicao():
                chave = self.nome()
                self.espera("=")
                if chave in com_chave:
                    self.repetida(chave)
                self.guarda(com_chave, chave, self.valor())
            else:
                lista.append(self.valor())
            c = self.ve()
            if c and c in ",;":
                self.i += 1
            elif c != "}":
                self.erro("esperava ',' ou '}'")
        if com_chave and lista:
            self.erro("tabela mistura chave e lista")
        return com_chave if com_chave or not lista else lista

    def _e_atribuicao(self):
        j = self.i
        while j < len(self.t) and (self.t[j].isalnum() or self.t[j] == "_"):
            j += 1
        while j < len(self.t) and self.t[j] in " \t\r\n":
            j += 1
        return j < len(self.t) and self.t[j] == "=" and self.t[j + 1:j + 2] != "="


def ler_modulo(texto, avisos=None):
    """O módulo inteiro: comentários, `return { ... }` e mais nada."""
    r = _Leitor(texto, [] if avisos is None else avisos)
    r.pula()
    if not texto.startswith("return", r.i):
        r.erro("esperava 'return'")
    r.i += len("return")
    v = r.valor()
    r.pula()
    if r.i != len(texto):
        r.erro("sobrou texto depois da tabela")
    return v
