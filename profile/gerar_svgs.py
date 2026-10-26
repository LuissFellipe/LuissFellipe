"""Gera os SVGs do README de perfil (claro e escuro), com o texto convertido
em contornos: imagem de README não carrega fonte externa, então a letra vai
desenhada no próprio arquivo."""
import re
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONTES = Path(sys.argv[1])
SAIDA = Path(sys.argv[2])
SAIDA.mkdir(parents=True, exist_ok=True)


class Fonte:
    def __init__(self, arquivo):
        self.tt = TTFont(FONTES / arquivo)
        self.upm = self.tt["head"].unitsPerEm
        self.cmap = self.tt.getBestCmap()
        self.glifos = self.tt.getGlyphSet()
        self.hmtx = self.tt["hmtx"]

    def _glifo(self, ch):
        nome = self.cmap.get(ord(ch))
        if nome is None:
            raise SystemExit(f"glifo ausente: {ch!r} em {self.tt}")
        return nome

    def largura(self, texto, tam, espaco=0.0):
        s = tam / self.upm
        return sum(self.hmtx[self._glifo(c)][0] * s + espaco * tam for c in texto) - espaco * tam

    def path(self, texto, x, y, tam, cor, espaco=0.0, ancora="start"):
        if ancora == "end":
            x -= self.largura(texto, tam, espaco)
        elif ancora == "middle":
            x -= self.largura(texto, tam, espaco) / 2
        s = tam / self.upm
        pen = SVGPathPen(self.glifos, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        for c in texto:
            nome = self._glifo(c)
            self.glifos[nome].draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
            x += self.hmtx[nome][0] * s + espaco * tam
        d = pen.getCommands()
        return f'<path fill="{cor}" d="{d}"/>' if d else ""

    def quebrar(self, texto, tam, largura_max):
        linhas, atual = [], ""
        for palavra in texto.split():
            teste = f"{atual} {palavra}".strip()
            if self.largura(teste, tam) <= largura_max or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        return linhas + [atual]


DISPLAY = Fonte("brico800.ttf")
TITULO = Fonte("brico600.ttf")
ITALICO = Fonte("fraunces-i.ttf")
MONO = Fonte("plexmono500.ttf")
TEXTO = Fonte("plexsans400.ttf")
TEXTO_B = Fonte("plexsans600.ttf")

# Roxo da marca (5B4282) e laranja de acento, como nas capas do Canva.
# Neutros puxados para o roxo, para não ler cinza ao lado dele.
TEMAS = {
    "light": dict(
        fundo="#F7F4FC", grade="#E9E3F3", borda="#E2DAEF", tinta="#1E1828",
        suave="#5F5672", roxo="#5B4282", roxo_txt="#4B3470", laranja="#E2620E",
        cartao="#FFFFFF", sombra="#1E1828", chip="#EEE8F7", ladrilho="#FFFFFF",
    ),
    "dark": dict(
        fundo="#17121F", grade="#231C2E", borda="#2F2640", tinta="#F3EFFA",
        suave="#ABA1BE", roxo="#7B5CB0", roxo_txt="#BDA4EC", laranja="#FF8A3D",
        cartao="#211A2C", sombra="#000000", chip="#2A2238", ladrilho="#F3EFFA",
    ),
}


def svg(w, h, corpo, titulo):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>{titulo}</title>{corpo}</svg>\n'
    )


def asterisco(cx, cy, r, cor, espessura):
    # seis braços, o asterisco laranja das capas
    import math
    partes = []
    for i in range(3):
        a = math.pi / 3 * i + math.pi / 2
        dx, dy = math.cos(a) * r, math.sin(a) * r
        partes.append(
            f'<line x1="{cx - dx:.1f}" y1="{cy - dy:.1f}" x2="{cx + dx:.1f}" y2="{cy + dy:.1f}" '
            f'stroke="{cor}" stroke-width="{espessura}" stroke-linecap="round"/>'
        )
    return "".join(partes)


def chip(x, y, texto, t, tam=12.5, fundo=None, cor=None):
    w = MONO.largura(texto, tam) + 20
    h = tam + 13
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" '
        f'fill="{fundo or t["chip"]}"/>'
        + MONO.path(texto, x + 10, y + h / 2 + tam * 0.36, tam, cor or t["suave"])
    ), w


# ---------------------------------------------------------------- cabeçalho
def cabecalho(t):
    W, H = 1000, 360
    p = [f'<rect width="{W}" height="{H}" rx="18" fill="{t["fundo"]}"/>']
    # papel quadriculado
    linhas = "".join(f"M{x} 0V{H}" for x in range(24, W, 24)) + "".join(
        f"M0 {y}H{W}" for y in range(24, H, 24)
    )
    p.append(f'<path d="{linhas}" stroke="{t["grade"]}" stroke-width="1" fill="none"/>')
    p.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{t["borda"]}"/>')

    x0 = 48
    p.append(asterisco(x0 + 9, 62, 9, t["laranja"], 3.2))
    p.append(MONO.path("ENGENHARIA E GOVERNANÇA DE DADOS", x0 + 28, 67, 14, t["laranja"], espaco=0.08))
    p.append(DISPLAY.path("Luis Felipe", x0 - 4, 158, 92, t["tinta"], espaco=-0.025))
    p.append(ITALICO.path("Dias Gomes", x0, 228, 64, t["roxo_txt"]))

    frase = ("Sou Analista de Dados, graduando em Engenharia de Software e em Direito, "
             "e trabalho com Engenharia e Governança de Dados.")
    linhas = TEXTO.quebrar(frase, 17, 575)
    assert len(linhas) <= 2, linhas  # a terceira linha cairia em cima da linhagem
    y = 272
    for linha in linhas:
        p.append(TEXTO.path(linha, x0, y, 17, t["suave"]))
        y += 25

    # a linhagem que todo projeto do perfil segue
    etapas = ["fonte pública", "raw", "dbt", "marts", "página no ar"]
    x, yb = x0, 314
    for i, e in enumerate(etapas):
        ultimo = i == len(etapas) - 1
        c, w = chip(x, yb, e, t, 13, fundo=t["roxo"] if ultimo else t["chip"],
                    cor="#FFFFFF" if ultimo else t["suave"])
        p.append(c)
        x += w
        if not ultimo:
            p.append(MONO.path("→", x + 7, yb + 18, 14, t["laranja"]))
            x += 30

    # dois cartões sobrepostos: as duas graduações
    def cartao(x, y, rot, fundo, rotulo, nome, sub, cor_txt, cor_sub):
        g = [f'<g transform="rotate({rot} {x + 150} {y + 60})">',
             f'<rect x="{x + 6}" y="{y + 8}" width="300" height="120" rx="16" fill="{t["sombra"]}" opacity="0.14"/>',
             f'<rect x="{x}" y="{y}" width="300" height="120" rx="16" fill="{fundo}" stroke="{t["borda"]}"/>',
             MONO.path(rotulo, x + 22, y + 36, 12, cor_sub, espaco=0.08),
             TITULO.path(nome, x + 22, y + 74, 30, cor_txt),
             MONO.path(sub, x + 22, y + 101, 12.5, cor_sub),
             "</g>"]
        return "".join(g)

    p.append(cartao(636, 62, -4, t["cartao"], "BACHARELADO", "Eng. de Software",
                    "Estácio · 2025–2029", t["tinta"], t["suave"]))
    p.append(cartao(668, 200, 3, t["roxo"], "BACHARELADO", "Direito",
                    "Universo · 2022–2027", "#FFFFFF", "#E4DAF5"))
    p.append(asterisco(948, 300, 16, t["laranja"], 5))
    return svg(W, H, "".join(p), "Luis Felipe Dias Gomes — Engenharia e Governança de Dados")


# ---------------------------------------------------------------- stack
LOGOS = Path(sys.argv[3]) if len(sys.argv) > 3 else None

# None = desenhado aqui (SQL, governança); o resto é logotipo do devicon
STACK = [
    ("Linguagens", [("Python", "python-original"), ("SQL", "sql"), ("JavaScript", "javascript-original"),
                    ("TypeScript", "typescript-original"), ("Ruby", "ruby-original"),
                    ("Rails", "rails-plain")]),
    ("Dados", [("PostgreSQL", "postgresql-original"), ("DuckDB", "duckdb-original"), ("dbt", "dbt-original"),
               ("Apache Spark", "apachespark-original"), ("Pandas", "pandas-original"),
               ("Jupyter", "jupyter-original"), ("Grafana", "grafana-original"),
               ("Streamlit", "streamlit-original")]),
    ("Orquestração", [("Apache Airflow", "apacheairflow-original"), ("Docker", "docker-original"),
                      ("GitHub Actions", "githubactions-original"), ("Git", "git-original"),
                      ("Linux", "linux-plain")]),
    ("Governança", [("LGPD", "asterisco"), ("Minimização", "asterisco"), ("Retenção", "asterisco"),
                    ("Controle de acesso", "asterisco"), ("Anonimização", "asterisco"),
                    ("Arquitetura medalhão", "asterisco")]),
]


def logo(nome, x, y, tam, n, t):
    # o SVG do logotipo vai embutido: imagem de README não carrega arquivo externo
    bruto = (LOGOS / f"{nome}.svg").read_text()
    vb = re.search(r'viewBox="([^"]+)"', bruto).group(1)
    corpo = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", bruto, flags=re.S)
    corpo = re.sub(r'id="([^"]+)"', rf'id="l{n}-\1"', corpo)
    corpo = re.sub(r"url\(#([^)]+)\)", rf"url(#l{n}-\1)", corpo)
    corpo = re.sub(r'href="#([^"]+)"', rf'href="#l{n}-\1"', corpo)
    # logotipos escuros somem no tema escuro: clareia o azul do pandas e
    # inverte o pato do DuckDB (círculo amarelo, ponto escuro)
    if t["nome"] == "dark":
        corpo = corpo.replace("#130754", t["tinta"])
        corpo = corpo.replace("#000000", "@@").replace("#fff100", t["fundo"]).replace("@@", "#fff100")
    raiz = re.search(r'<svg[^>]*?\sfill="([^"]+)"', bruto)
    cor = f' fill="{t["tinta"]}"' if nome == "linux-plain" else (f' fill="{raiz.group(1)}"' if raiz else "")
    return f'<svg x="{x:.1f}" y="{y:.1f}" width="{tam}" height="{tam}" viewBox="{vb}"{cor}>{corpo}</svg>'


def icone(arq, x, y, tam, n, t):
    if arq == "asterisco":
        return asterisco(x + tam / 2, y + tam / 2, tam * 0.36, t["laranja"], 2.4)
    if arq == "sql":
        # cilindro de banco de dados
        cx, rx, ry, h = x + tam / 2, tam * 0.38, tam * 0.13, tam * 0.7
        y0 = y + tam * 0.16
        c = t["roxo_txt"]
        return (f'<g fill="none" stroke="{c}" stroke-width="2">'
                f'<ellipse cx="{cx}" cy="{y0}" rx="{rx}" ry="{ry}"/>'
                f'<path d="M{cx - rx} {y0}V{y0 + h}A{rx} {ry} 0 0 0 {cx + rx} {y0 + h}V{y0}"/>'
                f'<path d="M{cx - rx} {y0 + h / 2}A{rx} {ry} 0 0 0 {cx + rx} {y0 + h / 2}"/></g>')
    return logo(arq, x, y, tam, n, t)


def stack(t):
    W, x_rot, x_ini, ico, tam, gap, alt = 1000, 0, 160, 24, 17, 26, 38
    p, y, n = [], 0, 0
    for g, (grupo, itens) in enumerate(STACK):
        if g:
            p.append(f'<path d="M0 {y}H{W}" stroke="{t["borda"]}"/>')
        y += 6
        p.append(MONO.path(grupo.upper(), x_rot, y + alt / 2 + 5, 14, t["laranja"], espaco=0.08))
        x = x_ini
        for rotulo, arq in itens:
            w = ico + 11 + MONO.largura(rotulo, tam)
            if x + w > W - 40:
                x = x_ini
                y += alt
            p.append(icone(arq, x, y + (alt - ico) / 2, ico, n, t))
            n += 1
            p.append(MONO.path(rotulo, x + ico + 11, y + alt / 2 + tam * 0.36, tam, t["tinta"]))
            x += w + gap
        y += alt + 6
    H = y
    fundo = ""  # sem painel: a lista fica direto no fundo do GitHub
    desc = "Stack — " + ". ".join(f"{g}: {', '.join(r for r, _ in i)}" for g, i in STACK)
    return svg(W, H, fundo + "".join(p), desc)


# ---------------------------------------------------------------- formação
FORMACAO = [
    ("Engenharia de Software", "Universidade Estácio de Sá", "2025–2029"),
    ("Direito", "Universidade Salgado de Oliveira", "2022–2027"),
    ("Gestão de Segurança Pública e Privada", "Faculdade Aliança de Itaberaí", "sequencial · 840 h"),
]
CERT_TEC = [
    ("Engenharia de Dados e IA para Gestores de TIC", "ENAP · Eixo 1 · nota 100", "44 h"),
    ("Fundamentos de Engenharia de Dados", "Data Science Academy", "24 h"),
    ("Python do Básico a Aplicações de IA", "Data Science Academy", "96 h"),
    ("Python para Análise de Dados, Data Science e ML", "Data Science Academy", "64 h"),
    ("Inteligência Artificial I: redes neurais", "IFTM", "40 h"),
    ("Java Básico", "Loiane Training", "30 h"),
    ("Introdução à IA Generativa", "MIT Professional Education", "8 h"),
]
CERT_DIR = [
    ("Como implementar a LGPD", "ENAP", "25 h"),
    ("Direito Administrativo", "IFRS", "40 h"),
    ("Direito do Trabalho", "IFRS", "40 h"),
    ("Direito Empresarial", "IFRS", "30 h"),
    ("Direito e Legislação Ambiental", "IFRS", "30 h"),
    ("Direito Público", "IFRS", "20 h"),
]
IDIOMA = [("Inglês C1 Advanced · 61/100", "EF SET", "2025")]


def lista_cert(t, p, x, y, largura, rotulo, itens):
    p.append(MONO.path(rotulo, x, y, 13, t["laranja"], espaco=0.08))
    y += 40
    for nome, inst, carga in itens:
        linhas = TEXTO_B.quebrar(nome, 17, largura - 40)
        for i, l in enumerate(linhas):
            p.append(TEXTO_B.path(l, x, y + i * 22, 17, t["tinta"]))
        p.append(MONO.path(carga, x + largura, y, 14, t["roxo_txt"], ancora="end"))
        y += 22 * (len(linhas) - 1)
        p.append(TEXTO.path(inst, x, y + 22, 14.5, t["suave"]))
        y += 52
    return y


def formacao(t):
    W = 1000
    p = [MONO.path("FORMAÇÃO", 40, 50, 13, t["laranja"], espaco=0.08)]
    col = (W - 80) / 3
    yf = 0
    for i, (nome, inst, quando) in enumerate(FORMACAO):
        x, y = 40 + i * col, 92
        linhas = TITULO.quebrar(nome, 21, col - 24)
        for j, l in enumerate(linhas):
            p.append(TITULO.path(l, x, y + j * 26, 21, t["tinta"]))
        y += 26 * (len(linhas) - 1)
        p.append(TEXTO.path(inst, x, y + 26, 15, t["suave"]))
        p.append(MONO.path(quando, x, y + 50, 14, t["roxo_txt"]))
        yf = max(yf, y + 50)
    y0 = yf + 34
    p.append(f'<path d="M40 {y0}H{W - 40}" stroke="{t["borda"]}"/>')
    larg = (W - 80 - 60) / 2
    xa, xb = 40, 40 + larg + 60
    ya = lista_cert(t, p, xa, y0 + 42, larg, "TECNOLOGIA", CERT_TEC)
    yb = lista_cert(t, p, xb, y0 + 42, larg, "DIREITO", CERT_DIR)
    yb = lista_cert(t, p, xb, yb + 8, larg, "IDIOMA", IDIOMA)
    p.append(f'<path d="M{xb - 30} {y0 + 26}V{max(ya, yb) - 30}" stroke="{t["borda"]}"/>')
    H = max(ya, yb) - 6
    fundo = (f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" '
             f'fill="{t["fundo"]}" stroke="{t["borda"]}"/>')
    desc = ("Formação: " + "; ".join(f"{a}, {b}" for a, b, _ in FORMACAO)
            + ". Tecnologia: " + "; ".join(f"{a} ({b}, {c})" for a, b, c in CERT_TEC)
            + ". Direito: " + "; ".join(f"{a} ({b}, {c})" for a, b, c in CERT_DIR)
            + ". Idioma: Inglês C1 Advanced, EF SET")
    return svg(W, H, fundo + "".join(p), desc)


# ---------------------------------------------------------------- destaque
# o projeto em destaque no mesmo desenho da stack: rótulo à esquerda, fio entre linhas
ARCADIUS = [
    ("Problema", "Quem estuda para concurso monta o cronograma à mão: cruza o edital, o peso de "
                 "cada matéria e as horas livres, e refaz tudo quando a rotina muda."),
    ("O que faz", "Monta o cronograma a partir do edital e o adapta à rotina do aluno: os dias, as "
                  "horas e as matérias que ainda pesam. Tem revisão espaçada, banco de questões e "
                  "XP, ofensiva e ranking."),
    ("Trilhas", [("Policial", "asterisco"), ("Tech", "asterisco"), ("Juris", "asterisco")]),
    ("Stack", [("Ruby", "ruby-original"), ("Rails 8", "rails-plain"), ("PostgreSQL", "postgresql-original"),
               ("Redis", "redis-original"), ("Sidekiq", "asterisco"), ("Hotwire", "asterisco"),
               ("Docker", "docker-original"), ("GitHub Actions", "githubactions-original")]),
    ("No ar", [("Algumas dezenas de usuários reais", "asterisco"), ("5.327 testes automatizados", "asterisco")]),
]


def arcadius(t):
    W, x_ini, ico, tam, gap, alt = 1000, 160, 24, 17, 26, 38
    p, y, n = [], 0, 100  # n começa em 100 para os ids não colidirem com os da stack
    for g, (grupo, itens) in enumerate(ARCADIUS):
        if g:
            p.append(f'<path d="M0 {y}H{W}" stroke="{t["borda"]}"/>')
        y += 6
        p.append(MONO.path(grupo.upper(), 0, y + alt / 2 + 5, 14, t["laranja"], espaco=0.08))
        if isinstance(itens, str):
            linhas = TEXTO.quebrar(itens, tam, W - x_ini - 20)
            for k, linha in enumerate(linhas):
                p.append(TEXTO.path(linha, x_ini, y + alt / 2 + tam * 0.36 + k * 27, tam, t["tinta"]))
            y += 27 * (len(linhas) - 1)
        else:
            x = x_ini
            for rotulo, arq in itens:
                w = ico + 11 + MONO.largura(rotulo, tam)
                if x + w > W - 40:
                    x = x_ini
                    y += alt
                p.append(icone(arq, x, y + (alt - ico) / 2, ico, n, t))
                n += 1
                p.append(MONO.path(rotulo, x + ico + 11, y + alt / 2 + tam * 0.36, tam, t["tinta"]))
                x += w + gap
        y += alt + 6
    desc = "Arcadius Academy — " + ". ".join(
        f"{g}: {i if isinstance(i, str) else ', '.join(r for r, _ in i)}" for g, i in ARCADIUS)
    return svg(W, y, "".join(p), desc)


for nome_tema, t in TEMAS.items():
    t["nome"] = nome_tema
    (SAIDA / f"header-{nome_tema}-2.svg").write_text(cabecalho(t))
    (SAIDA / f"stack-{nome_tema}-compacta-2.svg").write_text(stack(t))
    (SAIDA / f"formacao-{nome_tema}-3.svg").write_text(formacao(t))
    (SAIDA / f"arcadius-{nome_tema}-lista.svg").write_text(arcadius(t))
print("ok", len(list(SAIDA.glob("*.svg"))), "svgs")
