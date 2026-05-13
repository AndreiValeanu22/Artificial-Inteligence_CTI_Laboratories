# -*- coding: utf-8 -*-
"""
Actualizeaza in LAB10:
  - Bayes-Seminar.ipynb (pagini seminar ca imagini + text reflow fara diacritice + explicatii + rezolvari)
  - Bayes-Seminar-Raspunsuri.pdf
  - seminar_pages/*.png (randate din Bayes-Seminar.pdf — fisierul PDF NU este modificat)

Ruleaza din acest folder: python generate_lab10.py
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF — deschide PDF doar pentru citire / rasterizare

from _numeric_helpers import q4, q5, q6_bruteforce

# ---------------------------------------------------------------------------
# PDF sursa: NU scriem niciodata in Bayes-Seminar.pdf
# ---------------------------------------------------------------------------

_ROMANIAN_TR = str.maketrans(
    {
        "ă": "a",
        "â": "a",
        "î": "i",
        "ș": "s",
        "ț": "t",
        "Ă": "A",
        "Â": "A",
        "Î": "I",
        "Ș": "S",
        "Ț": "T",
        "ş": "s",
        "ţ": "t",
        "Ş": "S",
        "Ţ": "T",
    }
)


def strip_diacritics(s: str) -> str:
    s = s.translate(_ROMANIAN_TR)
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s) if unicodedata.category(c) != "Mn"
    )
    for ch in ("\u02d8", "\u02c6", "\u00b8"):
        s = s.replace(ch, "")
    s = s.replace("˘", "").replace("ˆ", "")
    return s


def reflow_page_body(body: str) -> str:
    """Imbina randuri rupte la PDF; paragrafe separate prin linie goala."""
    if not body.strip():
        return ""
    lines = body.split("\n")
    merged: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            merged.append("")
            continue
        if ln.endswith("-") and i + 1 < len(lines):
            nxt = lines[i + 1].lstrip()
            if nxt:
                merged.append(ln[:-1] + nxt)
                i += 2
                continue
        merged.append(ln)
        i += 1

    paras: list[str] = []
    buf: list[str] = []
    for ln in merged:
        if not ln.strip():
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        buf.append(ln.strip())
    if buf:
        paras.append(" ".join(buf))

    text = "\n\n".join(paras)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_transcript_pages(raw: str) -> list[tuple[int, str]]:
    pattern = re.compile(r"^===== PAGE (\d+) =====\n", re.MULTILINE)
    matches = list(pattern.finditer(raw))
    pages: list[tuple[int, str]] = []
    for i, m in enumerate(matches):
        n = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        pages.append((n, raw[start:end].rstrip("\n")))
    return pages


def render_pdf_pages_readonly(
    pdf_path: Path, out_dir: Path, zoom: float = 2.0, margin_frac: float = 0.022
) -> list[str]:
    """
    Citeste Bayes-Seminar.pdf (fara modificare pe disc) si salveaza PNG-uri.
    margin_frac: micsoreaza usor chenarul alb (nu e decupare manuala pe figuri).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    rels: list[str] = []
    # DOAR citire — fitz.open nu rescrie PDF-ul
    with fitz.open(pdf_path) as doc:
        for i in range(len(doc)):
            page = doc[i]
            r = page.rect
            dx = r.width * margin_frac
            dy = r.height * margin_frac
            clip = fitz.Rect(r.x0 + dx, r.y0 + dy, r.x1 - dx, r.y1 - dy)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
            fname = f"page_{i + 1:02d}.png"
            pix.save(str(out_dir / fname))
            rels.append(f"seminar_pages/{fname}")
    return rels


def seminar_page_cell(page_num: int, image_rel: str | None, body: str) -> str:
    """O pagina: imagine (daca exista) + text reflow, fara diacritice, aliniat."""
    reflowed = strip_diacritics(reflow_page_body(body))
    paras = [p.strip() for p in reflowed.split("\n\n") if p.strip()]
    paras_html = "".join(
        '<p style="margin:0 0 0.9em 0;text-align:justify;text-justify:inter-word;'
        'font-family:\'Segoe UI\',Roboto,\'Helvetica Neue\',Arial,sans-serif;'
        'font-size:15px;line-height:1.72;color:#111827;">'
        f"{html.escape(p)}</p>"
        for p in paras
    )

    img_block = ""
    if image_rel:
        img_block = (
            f'<img src="{image_rel}" alt="Seminar pagina {page_num}" '
            'style="width:100%;max-width:100%;height:auto;display:block;'
            "margin:0 auto 14px auto;border:1px solid #e5e7eb;border-radius:8px;"
            'box-shadow:0 2px 10px rgba(15,23,42,0.07);"/>'
        )

    return (
        f'<div style="margin:0 auto 36px auto;max-width:960px;">'
        f'<div style="font-size:12px;font-weight:600;color:#4b5563;margin:0 0 10px 2px;">'
        f"Pagina {page_num}</div>"
        f"{img_block}"
        f'<div style="padding:18px 20px;background:#fafafa;border:1px solid #e5e7eb;'
        f'border-radius:10px;">'
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;'
        f'color:#6b7280;margin-bottom:12px;">Text reflow (fără diacritice, pentru citire)</div>'
        f"{paras_html}</div></div>"
    )


def md_lines(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    if not lines:
        return ["\n"]
    if not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return lines


def build_solutions_markdown() -> str:
    q4_res, p_G_marg, p_F_G = q4()
    p_D, p_E, q5b = q5()
    q6 = q6_bruteforce()

    joint_binary = 2**7 - 1
    params_bn_binary = 19
    joint_ternary = 3**7 - 1
    params_bn_ternary = 90

    q3 = """| Relație | Adevărat? | Motiv (d-separare, rețeaua din Fig. 6: A,B,C→D; D→E; D→F; E,F→G) |
|---------|-------------|---------------------------------------------------------------------|
| a) A ⊥ G \\| D | **Da** | Lanțul A–D–…–G este blocat de observarea lui D (nod intermediar pe lanț). |
| b) A ⊥ B \\| F | **Nu** | A→D←B e colider; F e descendent al lui D ⇒ colider activat ⇒ A și B devin dependente (cf. Fig. 7b). |
| c) A ⊥ C | **Da** | Pe calea A–D–C, D e colider neobservat ⇒ cale blocată; alte căi lungi trec prin G neobservat (colider E→G←F) ⇒ blocate. |
| d) A ⊥ C \\| E | **Nu** | E e descendent al lui D ⇒ observarea lui E deschide coliderul în D ⇒ A și C devin dependente. |
| e) F ⊥ G \\| A | **Nu** | Există muchia directă F–G; nu există nod intermediar care să blocheze această cale. |
| f) B ⊥ C \\| G | **Nu** | Observând G (copil al lui E și F) se activează structuri convergente legate de D ⇒ B și C nu sunt d-separate. |
| g) F ⊥ C \\| G | **Nu** | Calea neorientată C–D–F e un lanț cu D **neobservat** ⇒ cale activă; F și C rămân dependente chiar dacă observăm G. |"""

    return f"""# Rezolvări — exerciții din seminar

## Întrebarea 1 și 2 (parametri)

**Variabile binare (7 noduri)**  
- Reprezentare tabulară completă a lui p(A,…,G): **{joint_binary}** valori independente (2⁷−1).  
- Rețeaua din Fig. 2 / Fig. 6 (A,B,C→D; D→E; D→F; E,F→G): **{params_bn_binary}** parametri  
  (1+1+1 pentru A,B,C; 2³ pentru D\\|A,B,C; câte 2 pentru E\\|D și F\\|D; 2² pentru G\\|E,F).

**Variabile ternare**  
- Joint complet: **{joint_ternary}** (3⁷−1).  
- Aceeași structură de rețea: **{params_bn_ternary}** parametri.

## Întrebarea 3

{q3}

## Întrebarea 4

**a) p(D\\|F,G)** — probabilități P(D=1\\|F,G) (complementul e P(D=0\\|F,G)):

{json.dumps({str(k): {str(d): round(v, 6) for d, v in dct.items()} for k, dct in q4_res.items()}, indent=2, ensure_ascii=False)}

**b) p(F\\|G)**:

{json.dumps({str(g): {str(f): round(pF, 6) for f, pF in d.items()} for g, d in p_F_G.items()}, indent=2, ensure_ascii=False)}

**Marjale p(G)**: {json.dumps({str(k): round(v, 6) for k, v in p_G_marg.items()}, ensure_ascii=False)}

## Întrebarea 5

**a) p(D\\|E)** — D și E sunt rădăcini independente ⇒ **p(D\\|E) = p(D)**:

P(D=1\\|E=1) = P(D=1\\|E=0) = **0.7**

**b) p(D\\|G,E)** — cheia (G,E) = (valoare G, valoare E):

{json.dumps({str(k): {str(d): round(v, 6) for d, v in dct.items()} for k, dct in q5b.items()}, indent=2, ensure_ascii=False)}

## Întrebarea 6

Model: p(A)p(B)p(C)p(D\\|A,B)p(E\\|C)p(F\\|D)p(G\\|D,E).

{json.dumps({k: round(v, 6) for k, v in sorted(q6.items())}, indent=2, ensure_ascii=False)}
"""


def _pdf_font_path() -> str | None:
    try:
        import matplotlib

        p = Path(matplotlib.matplotlib_fname()).parent / "fonts" / "ttf" / "DejaVuSans.ttf"
        return str(p) if p.is_file() else None
    except Exception:
        return None


def write_pdf(lab10: Path, chart_path: Path | None) -> None:
    """PDF structurat ca fisa / document, nu ca README in multi_cell."""
    from fpdf import FPDF

    q4_res, p_G_marg, p_F_G = q4()
    _p_D, _p_E, q5b = q5()
    q6 = q6_bruteforce()

    joint_binary = 2**7 - 1
    params_bn_binary = 19
    joint_ternary = 3**7 - 1
    params_bn_ternary = 90

    font_path = _pdf_font_path()
    fname = "DejaVu" if font_path else "Helvetica"
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    if font_path:
        pdf.add_font(fname, "", font_path)
        bold_p = Path(font_path).with_name("DejaVuSans-Bold.ttf")
        if bold_p.is_file():
            pdf.add_font(fname, "B", str(bold_p))
        else:
            pdf.add_font(fname, "B", font_path)

    def set_n(size: float, bold: bool = False) -> None:
        st = "B" if bold else ""
        pdf.set_font(fname, st, size)

    def rule() -> None:
        pdf.set_draw_color(200, 205, 220)
        y = pdf.get_y()
        pdf.line(18, y, pdf.w - 18, y)
        pdf.ln(4)

    def section(num: str, title: str) -> None:
        pdf.ln(6)
        set_n(13, True)
        pdf.set_text_color(30, 41, 59)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 8, f"{num}  {title}")
        pdf.set_text_color(30, 30, 30)
        set_n(10.5, False)
        rule()

    def para(text: str, h: float = 5.8) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, h, text)
        pdf.ln(1)

    pdf.add_page()
    # Antet document
    set_n(9, False)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, "LAB 10 · Rețele Bayesiene", ln=1)
    pdf.set_text_color(15, 23, 42)
    set_n(20, True)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 10, "Răspunsuri la exerciții")
    set_n(11, False)
    pdf.set_text_color(71, 85, 105)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 6, "Concordanță cu întrebările din seminar (figurile 2–10).")
    pdf.set_text_color(30, 30, 30)
    pdf.ln(8)
    rule()
    pdf.ln(2)

    # Întrebări 1–2
    section("1–2.", "Parametri (joint vs. rețea)")
    para(
        f"Variabile binare (7 noduri): reprezentare tabulară completă a lui p(A,…,G) — "
        f"{joint_binary} valori independente (2^7 - 1)."
    )
    para(
        f"Aceeași mulțime în rețeaua din Fig. 2 / Fig. 6 (A,B,C→D; D→E; D→F; E,F→G): "
        f"{params_bn_binary} parametri "
        f"(1+1+1 pentru rădăcini; 2^3 pentru D|A,B,C; câte 2 pentru E|D și F|D; 2^2 pentru G|E,F)."
    )
    para(
        f"Variabile ternare: joint complet — {joint_ternary} valori (3^7 - 1); "
        f"aceeași topologie de rețea — {params_bn_ternary} parametri."
    )

    # Întrebarea 3
    section("3.", "Independență condițională (Fig. 6)")
    q3_items = [
        ("a", "A ⊥ G | D", "Da", "D observat pe lanțul A–D–…–G → cale blocată."),
        ("b", "A ⊥ B | F", "Nu", "Colider A→D←B; F descendent al lui D → colider activat (cf. Fig. 7b)."),
        ("c", "A ⊥ C", "Da", "Colider la D neobservat; căi prin G neobservat rămân blocate."),
        ("d", "A ⊥ C | E", "Nu", "E descendent al lui D → se deschide coliderul în D."),
        ("e", "F ⊥ G | A", "Nu", "Muchie directă F–G."),
        ("f", "B ⊥ C | G", "Nu", "G copil al lui E,F; observarea lui G poate activa căi spre D."),
        ("g", "F ⊥ C | G", "Nu", "Lanțul C–D–F cu D neobservat rămâne activ."),
    ]
    for lab, rel, ans, why in q3_items:
        set_n(10.5, True)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 6, f"({lab})  {rel}")
        set_n(10.5, False)
        pdf.set_text_color(37, 99, 235)
        pdf.set_x(pdf.l_margin)
        pdf.cell(pdf.epw, 5, f"Răspuns: {ans}.", ln=1)
        pdf.set_text_color(30, 30, 30)
        para(f"Motiv: {why}")
        pdf.ln(0.5)

    # Întrebarea 4
    section("4.", "Probabilități (Fig. 8 — doar D, F, G)")
    para("a)  p(D | F, G) — valori P(D = 1 | F, G); complementul este P(D = 0 | F, G).")
    pdf.set_x(pdf.l_margin)
    wq = pdf.w - 36
    c1, c2, c3, c4 = 32, 32, (wq - 64) // 2, wq - 64 - (wq - 64) // 2
    set_n(9, True)
    pdf.cell(c1, 7, "F", border=1, align="C")
    pdf.cell(c2, 7, "G", border=1, align="C")
    pdf.cell(c3, 7, "P(D=1 | F,G)", border=1, align="C")
    pdf.cell(c4, 7, "P(D=0 | F,G)", border=1, align="C", ln=1)
    set_n(9, False)
    pdf.set_fill_color(248, 250, 252)
    for (f, g), dct in sorted(q4_res.items()):
        pdf.cell(c1, 7, str(f), border=1, align="C", fill=True)
        pdf.cell(c2, 7, str(g), border=1, align="C", fill=True)
        pdf.cell(c3, 7, f"{dct[1]:.6f}", border=1, align="C", fill=True)
        pdf.cell(c4, 7, f"{dct[0]:.6f}", border=1, align="C", fill=True, ln=1)
    pdf.ln(3)
    para(
        f"b)  p(G):  P(G=0) = {p_G_marg[0]:.6f},   P(G=1) = {p_G_marg[1]:.6f}."
    )
    para("    p(F | G):")
    pdf.set_x(pdf.l_margin)
    wf = (pdf.w - 36) / 3
    set_n(9, True)
    pdf.cell(wf, 7, "G", border=1, align="C")
    pdf.cell(wf, 7, "F=0", border=1, align="C")
    pdf.cell(wf, 7, "F=1", border=1, align="C", ln=1)
    set_n(9, False)
    for g in (0, 1):
        pdf.cell(wf, 7, str(g), border=1, align="C")
        pdf.cell(wf, 7, f"{p_F_G[g][0]:.6f}", border=1, align="C")
        pdf.cell(wf, 7, f"{p_F_G[g][1]:.6f}", border=1, align="C", ln=1)

    # Întrebarea 5
    section("5.", "Probabilități (Fig. 9 — D, E, G)")
    para("a)  D și E independente ⇒ p(D | E) = p(D).  Deci P(D=1 | E=1) = P(D=1 | E=0) = 0,7.")
    para("b)  p(D | G, E) — (G, E) în ordinea (valoare G, valoare E):")
    pdf.set_x(pdf.l_margin)
    w5 = pdf.w - 36
    gcol, ecol = 22, 22
    pcol = (w5 - gcol - ecol) // 2
    pcol2 = w5 - gcol - ecol - pcol
    set_n(9, True)
    pdf.cell(gcol, 7, "G", border=1, align="C")
    pdf.cell(ecol, 7, "E", border=1, align="C")
    pdf.cell(pcol, 7, "P(D=0 | G,E)", border=1, align="C")
    pdf.cell(pcol2, 7, "P(D=1 | G,E)", border=1, align="C", ln=1)
    set_n(9, False)
    for (g, e) in sorted(q5b.keys()):
        dct = q5b[(g, e)]
        pdf.cell(gcol, 7, str(g), border=1, align="C")
        pdf.cell(ecol, 7, str(e), border=1, align="C")
        pdf.cell(pcol, 7, f"{dct[0]:.6f}", border=1, align="C")
        pdf.cell(pcol2, 7, f"{dct[1]:.6f}", border=1, align="C", ln=1)

    # Întrebarea 6
    section("6.", "Probabilități (Fig. 10)")
    para(
        "Model factorizat: p(A)p(B)p(C)p(D|A,B)p(E|C)p(F|D)p(G|D,E)."
    )
    for k, v in sorted(q6.items()):
        para(f"•  {k}  =  {v:.6f}")

    # Pagină grafic
    if chart_path and chart_path.is_file():
        pdf.add_page()
        set_n(14, True)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 9, "Anexă grafic — Întrebarea 4")
        set_n(10, False)
        pdf.set_text_color(71, 85, 105)
        para("P(D = 1 | F, G) pentru fiecare pereche (F, G).")
        pdf.set_text_color(30, 30, 30)
        pdf.ln(4)
        pdf.image(str(chart_path), x=18, w=pdf.w - 36)

    out = lab10 / "Bayes-Seminar-Raspunsuri.pdf"
    pdf.output(str(out))


def maybe_q4_chart(lab10: Path, q4_res) -> Path | None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    labels = []
    vals = []
    for (f, g), dct in sorted(q4_res.items()):
        labels.append(f"F={f}, G={g}")
        vals.append(dct[1])
    plt.figure(figsize=(7, 4))
    plt.bar(labels, vals, color=["#d946ef", "#38bdf8", "#a78bfa", "#34d399"])
    plt.ylabel("P(D = 1 | F, G)")
    plt.title("Întrebarea 4 — probabilitatea a posteriori pentru D=1")
    plt.ylim(0, 1)
    plt.tight_layout()
    p = lab10 / "_fig_q4_pd_given_fg.png"
    plt.savefig(p, dpi=150)
    plt.close()
    return p


def main() -> None:
    lab10 = Path(__file__).resolve().parent
    raw = (lab10 / "_extracted_pymupdf.txt").read_text(encoding="utf-8")
    pages = split_transcript_pages(raw)
    body_by_n = {n: b for n, b in pages}

    pdf_source = lab10 / "Bayes-Seminar.pdf"
    out_png_dir = lab10 / "seminar_pages"
    image_rels: list[str] = []
    if pdf_source.is_file():
        image_rels = render_pdf_pages_readonly(pdf_source, out_png_dir)
    else:
        print("Lipseste Bayes-Seminar.pdf — Partea I va avea doar text reflow.")

    hl = (
        '<div style="background: linear-gradient(90deg, #fff7ed, #fdf4ff); '
        "border-left: 6px solid #f97316; padding: 10px 14px; margin: 12px 0; "
        'font-family: system-ui, sans-serif; color: #1e1b4b;">\n\n'
        "**Pe scurt (începători — rețele Bayesiene):**\n\n"
    )
    hl_end = "\n\n</div>"

    explain_blocks = [
        (
            "## Explicații — probabilități de bază",
            hl
            + "- **Variabilă aleatoare**: rezultat incert înainte de observație.\n"
            + "- **p(X)**: probabilitatea evenimentului X (între 0 și 1).\n"
            + "- **Independență**: X ⊥ Y ⇒ p(X∩Y) = p(X)p(Y).\n"
            + "- **Condiționare p(X|Y)**: probabilitatea lui X după ce știm Y.\n"
            + hl_end,
        ),
        (
            "## Explicații — Teorema lui Bayes",
            hl
            + "- **Rol**: din observație (efect) inferăm cauza.\n"
            + "- **Posterior** p(cauză|efect) ∝ verosimilitate × prior (normalizat).\n"
            + "- **Numitor**: probabilitatea totală a observației; uneori se evită prin rapoarte (artificiul din seminar).\n"
            + "- **Exemplul gripei din material:** la formula (10) numitorul corect este "
            + "suma de produse p(+|Gripa)p(Gripa) + p(+|¬Gripa)p(¬Gripa), nu expresia cu `0.9 + 0.01 + …` "
            + "din tipărire (eroare de formă).\n"
            + hl_end,
        ),
        (
            "## Explicații — Rețele Bayesiene",
            hl
            + "- **Nod** = variabilă; **arc** = influență directă (de obicei cauzală).\n"
            + "- **CPT**: probabilitățile nodului condiționate de părinți.\n"
            + "- **Economie de parametri** față de tabelul joint complet.\n"
            + hl_end,
        ),
        (
            "## Explicații — Independență condițională și d-separabilitate",
            hl
            + "- **X ⊥ Z | Y**: ținând cont de Y, Z nu modifică credința despre X.\n"
            + "- **d-separare**: mulțimea observată blochează toate căile neorientate ⇒ independență condițională.\n"
            + "- **Colider** (A→C←B): blocat dacă C și descendenții nu sunt observați; se deschide la observare pe C sau descendent.\n"
            + hl_end,
        ),
    ]

    cells: list[dict] = []

    cells.append(
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": md_lines(
                "# Rețele Bayesiene — Seminar\n\n"
                "Notebook-ul conține **materialul seminarului**, **explicații** și **rezolvări** la exerciții.\n\n"
                "**Partea I:** pentru fiecare pagină — imagine din `Bayes-Seminar.pdf` "
                "(fișierul PDF sursă **nu este modificat** pe disc) și, sub ea, **text reflow** "
                "în română **fără diacritice**, aliniat pe lățime.\n\n"
                "Dacă vrei **decupaje mai strânse** (doar scheme sau figuri), înlocuiește manual "
                "PNG-urile din `seminar_pages/` cu tăieturile tale (păstrează același nume de fișier)."
            ),
        }
    )

    cells.append(
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": md_lines(
                "---\n\n# PARTEA I — Paginile seminarului\n\n"
                "Imaginile provin din citirea PDF-ului original (margini albe ușor tăiate automat). "
                "Textul de dedesubt este reorganizat pe paragrafe și **fără diacritice**, pentru lizibilitate."
            ),
        }
    )

    n_pages = max(len(image_rels), max((n for n, _ in pages), default=0), 0)
    if image_rels:
        for i, rel in enumerate(image_rels):
            pn = i + 1
            body = body_by_n.get(pn, "")
            block = seminar_page_cell(pn, rel, body) + "\n"
            cells.append(
                {
                    "cell_type": "markdown",
                    "metadata": {"tags": ["seminar-page"]},
                    "source": md_lines(block),
                }
            )
        for n, body in sorted(pages, key=lambda x: x[0]):
            if n > len(image_rels):
                block = seminar_page_cell(n, None, body) + "\n"
                cells.append(
                    {
                        "cell_type": "markdown",
                        "metadata": {"tags": ["seminar-page"]},
                        "source": md_lines(block),
                    }
                )
    else:
        for n, body in sorted(pages, key=lambda x: x[0]):
            block = seminar_page_cell(n, None, body) + "\n"
            cells.append(
                {
                    "cell_type": "markdown",
                    "metadata": {"tags": ["seminar-page"]},
                    "source": md_lines(block),
                }
            )

    for title, body in explain_blocks:
        cells.append({"cell_type": "markdown", "metadata": {}, "source": md_lines(title + "\n\n" + body)})

    sol_md = build_solutions_markdown()
    cells.append(
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": md_lines("---\n\n# PARTEA II — Rezolvări (rezumat)\n\n" + sol_md),
        }
    )

    helpers_rel = "_numeric_helpers.py"
    code = f'''# Verificare numerică (rulează din folderul LAB10)
import json
from pathlib import Path
import importlib.util

p = Path(r"{lab10.as_posix()}") / "{helpers_rel}"
spec = importlib.util.spec_from_file_location("h", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

t4, pG, pFG = m.q4()
print("Q4 p(D|F,G):", json.dumps({{str(k): v for k, v in t4.items()}}, indent=2))
print("Q4 p(G):", pG)
print("Q4 p(F|G):", json.dumps(pFG, indent=2))
_, _, q5b = m.q5()
print("Q5b p(D|G,E):", json.dumps({{str(k): v for k, v in q5b.items()}}, indent=2))
print("Q6:", json.dumps({{k: round(v, 6) for k, v in sorted(m.q6_bruteforce().items())}}, indent=2))
'''
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": md_lines(code)})

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
        },
        "cells": cells,
    }

    out_nb = lab10 / "Bayes-Seminar.ipynb"
    out_nb.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")

    q4_res, _, _ = q4()
    chart = maybe_q4_chart(lab10, q4_res)
    write_pdf(lab10, chart)

    print("Creat:", out_nb.name)
    print("Creat: Bayes-Seminar-Raspunsuri.pdf")
    if image_rels:
        print("PNG-uri:", out_png_dir, f"({len(image_rels)} fisiere)")
    if chart:
        print("Chart:", chart.name)


if __name__ == "__main__":
    main()
