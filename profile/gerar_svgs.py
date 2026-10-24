"""Gera os SVGs do README de perfil (claro e escuro), com o texto convertido
em contornos: imagem de README não carrega fonte externa, então a letra vai
desenhada no próprio arquivo."""
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
        cartao="#FFFFFF", sombra="#1E1828", chip="#EEE8F7",
    ),
    "dark": dict(
        fundo="#17121F", grade="#231C2E", borda="#2F2640", tinta="#F3EFFA",
        suave="#ABA1BE", roxo="#7B5CB0", roxo_txt="#BDA4EC", laranja="#FF8A3D",
        cartao="#211A2C", sombra="#000000", chip="#2A2238",
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

    frase = ("Construo pipelines com dados públicos brasileiros, da coleta à página "
             "publicada, com a LGPD dentro do projeto desde o começo.")
    y = 272
    for linha in TEXTO.quebrar(frase, 17, 560):
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


# ---------------------------------------------------------------- projetos
PROJETOS = [
    ("energia", "Energia Desperdiçada", "ONS · 2021–2026", "37,2 TWh",
     "de energia eólica e solar cortada pelo ONS em 2025, 21% do que as usinas poderiam gerar.",
     ["Airflow", "dbt", "DuckDB"]),
    ("golpe", "O golpe que o Brasil não sabe contar", "ANUÁRIO FBSP · 2023–2026", "21,1% → 11,1%",
     "Alta do estelionato eletrônico em 2025: a publicada, e a dos 18 estados que informam desde 2021.",
     ["dbt", "DuckDB", "ECharts"]),
    ("ferrovias", "Carga nas Ferrovias", "ANTT · 2006–2026", "−22%",
     "foi a queda da carga da MRS em 2019, depois de Brumadinho. Em 2025, ela levou 153,2 mi t.",
     ["PostGIS", "dbt", "Comex Stat"]),
    ("queimadas", "Monitor de Queimadas", "INPE · ATUALIZA TODO DIA", "278.299",
     "focos de calor em 2024, o pior ano da série. Cada foco ligado ao município por spatial join.",
     ["PostGIS", "dbt", "GitHub Actions"]),
    ("indices", "Consultor de índices", "INSTACART · 33,8 MI DE ITENS", "170 s → 13,9 s",
     "de consulta por hora com os 2 índices que o algoritmo escolheu entre 35 candidatos.",
     ["PostgreSQL", "HypoPG", "Python"]),
    ("salarios", "Salários em dados", "STATE OF DATA · 2019–2025", "−6,6%",
     "no salário real do mesmo perfil entre 2021 e 2025, enquanto a mediana bruta subiu 20%.",
     ["Python", "Jupyter", "regressão"]),
    ("bcb", "Pipeline BCB", "BANCO CENTRAL · TODO DIA ÚTIL", "21 meses",
     "de juro real negativo entre jul/2020 e abr/2022. Testado contra o IPCA oficial do IBGE.",
     ["PostgreSQL", "dbt", "Docker"]),
    ("enem", "Análise do ENEM 2023", "INEP · MICRODADOS", "28,0%",
     "da variação da nota é explicada por renda familiar e tipo de escola, juntos.",
     ["DuckDB", "Python"]),
]


def cartao_projeto(t, titulo, fonte, numero, legenda, stack):
    W, H = 480, 300
    p = [f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{t["fundo"]}" stroke="{t["borda"]}"/>']
    x = 28
    p.append(asterisco(x + 6, 40, 6, t["laranja"], 2.4))
    p.append(MONO.path(fonte.upper(), x + 20, 44.5, 11.5, t["laranja"], espaco=0.08))
    tam_t = 23
    while TITULO.largura(titulo, tam_t) > W - 2 * x:
        tam_t -= 1
    p.append(TITULO.path(titulo, x, 82, tam_t, t["tinta"]))
    tam_n = 54
    while DISPLAY.largura(numero, tam_n, -0.02) > W - 2 * x:
        tam_n -= 2
    p.append(DISPLAY.path(numero, x - 2, 150, tam_n, t["roxo_txt"], espaco=-0.02))
    y = 184
    for linha in TEXTO.quebrar(legenda, 15.5, W - 2 * x)[:3]:
        p.append(TEXTO.path(linha, x, y, 15.5, t["suave"]))
        y += 22
    cx = x
    for s in stack:
        c, w = chip(cx, H - 50, s, t, 12)
        p.append(c)
        cx += w + 8
    p.append(MONO.path("código ↗", W - x, H - 32, 12.5, t["roxo_txt"], ancora="end"))
    return svg(W, H, "".join(p), f"{titulo}: {numero} {legenda}")


# ---------------------------------------------------------------- stack
STACK = [
    ("Orquestração e transformação", ["Airflow", "dbt", "Apache Spark", "ETL/ELT", "arquitetura medalhão"]),
    ("Bancos e análise", ["PostgreSQL", "PostGIS", "DuckDB", "SQL", "Python", "pandas", "Jupyter"]),
    ("Entrega e operação", ["Docker", "GitHub Actions", "GitHub Pages", "Grafana", "Streamlit", "Linux"]),
    ("Governança", ["LGPD", "minimização", "retenção", "controle de acesso", "anonimização"]),
]


def stack(t):
    W = 1000
    p, y = [], 36
    for grupo, itens in STACK:
        p.append(MONO.path(grupo.upper(), 40, y + 18, 12, t["laranja"], espaco=0.08))
        x = 300
        for it in itens:
            w = MONO.largura(it, 13.5) + 24
            if x + w > W - 40:
                x = 300
                y += 40
            c, w = chip(x, y, it, t, 13.5, fundo=t["chip"], cor=t["tinta"])
            p.append(c)
            x += w + 10
        y += 56
    H = y - 8
    fundo = (f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" '
             f'fill="{t["fundo"]}" stroke="{t["borda"]}"/>')
    return svg(W, H, fundo + "".join(p), "Stack: " + "; ".join(
        f"{g}: {', '.join(i)}" for g, i in STACK))


# ---------------------------------------------------------------- formação
FORMACAO = [
    ("Engenharia de Software", "Universidade Estácio de Sá", "2025–2029"),
    ("Direito", "Universidade Salgado de Oliveira", "2022–2027"),
    ("Gestão de Segurança Pública e Privada", "Faculdade Aliança de Itaberaí · sequencial", "840 h"),
]
CERTS = [
    ("Inglês C1 Advanced · 61/100", "EF SET", "2025"),
    ("Engenharia de Dados e IA para Gestores de TIC — Eixo 1", "ENAP · nota 100", "44 h"),
    ("Como implementar a LGPD", "ENAP", "25 h"),
    ("Fundamentos de Engenharia de Dados", "Data Science Academy", "24 h"),
    ("Python do Básico a Aplicações de IA", "Data Science Academy", "96 h"),
    ("Python para Análise de Dados, Data Science e ML", "Data Science Academy", "64 h"),
    ("Inteligência Artificial I: redes neurais", "IFTM", "40 h"),
    ("Introdução à IA Generativa", "MIT Professional Education", "2025"),
]


def formacao(t):
    W = 1000
    p = []
    p.append(MONO.path("FORMAÇÃO", 40, 54, 12, t["laranja"], espaco=0.08))
    y = 92
    for nome, inst, quando in FORMACAO:
        for i, linha in enumerate(TITULO.quebrar(nome, 19, 300)):
            p.append(TITULO.path(linha, 40, y + i * 24, 19, t["tinta"]))
        y += 24 * (len(TITULO.quebrar(nome, 19, 300)) - 1)
        p.append(TEXTO.path(inst, 40, y + 23, 14, t["suave"]))
        p.append(MONO.path(quando, 40, y + 44, 12.5, t["roxo_txt"]))
        y += 82
    p.append(f'<path d="M392 40V{y - 30}" stroke="{t["borda"]}"/>')

    xc = 430
    p.append(MONO.path("CERTIFICAÇÕES", xc, 54, 12, t["laranja"], espaco=0.08))
    yc = 92
    for nome, inst, carga in CERTS:
        p.append(TEXTO_B.path(nome, xc, yc, 15.5, t["tinta"]))
        p.append(TEXTO.path(inst, xc, yc + 21, 13.5, t["suave"]))
        p.append(MONO.path(carga, W - 40, yc, 13, t["roxo_txt"], ancora="end"))
        yc += 50
    H = max(y, yc) - 10
    fundo = (f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" '
             f'fill="{t["fundo"]}" stroke="{t["borda"]}"/>')
    desc = "Formação: " + "; ".join(f"{a}, {b}" for a, b, _ in FORMACAO) + \
        ". Certificações: " + "; ".join(f"{a}, {b}" for a, b, _ in CERTS)
    return svg(W, H, fundo + "".join(p), desc)


for nome_tema, t in TEMAS.items():
    (SAIDA / f"header-{nome_tema}.svg").write_text(cabecalho(t))
    (SAIDA / f"stack-{nome_tema}.svg").write_text(stack(t))
    (SAIDA / f"formacao-{nome_tema}.svg").write_text(formacao(t))
    for slug, *dados in PROJETOS:
        (SAIDA / f"{slug}-{nome_tema}.svg").write_text(cartao_projeto(t, *dados))
print("ok", len(list(SAIDA.glob("*.svg"))), "svgs")
