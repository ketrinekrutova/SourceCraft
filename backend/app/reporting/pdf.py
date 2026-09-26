"""Выгрузка отчёта в PDF. Рендерит тот же RepositoryDetail, что и страница и Markdown-отчёт.

Нужен TTF-шрифт с кириллицей: PDF_FONT_PATH / PDF_FONT_BOLD_PATH или один из стандартных путей
(DejaVu в Docker-образе - пакет fonts-dejavu-core, Arial на Windows, Liberation/DejaVu в Linux)."""

import os
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

from ..schemas.analysis import Metric, RepositoryDetail
from .markdown import CATEGORY_TITLES, NO_DATA, PRIORITY_TITLES

FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
]
PRIORITY_COLORS = {"HIGH": (198, 91, 91), "MEDIUM": (200, 163, 73), "LOW": (111, 156, 118)}


class PdfFontMissing(RuntimeError):
    pass


def _fonts() -> tuple[str, str]:
    regular, bold = os.environ.get("PDF_FONT_PATH"), os.environ.get("PDF_FONT_BOLD_PATH")
    if regular and Path(regular).exists():
        return regular, bold if bold and Path(bold).exists() else regular
    for reg, bld in FONT_CANDIDATES:
        if Path(reg).exists():
            return reg, bld if Path(bld).exists() else reg
    raise PdfFontMissing("Не найден TTF-шрифт с кириллицей для PDF (задайте PDF_FONT_PATH)")


def _score_color(score: int | None) -> tuple[int, int, int]:
    if score is None:
        return (160, 160, 160)
    if score >= 70:
        return (160, 170, 60)
    if score >= 40:
        return (215, 170, 50)
    return (192, 43, 85)


class _Report(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("main", size=8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, f"SourceCraft Repo Health · стр. {self.page_no()}", align="C")


def render_pdf_report(detail: RepositoryDetail) -> bytes:
    regular, bold = _fonts()
    pdf = _Report(format="A4")
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_font("main", "", regular)
    pdf.add_font("main", "B", bold)
    pdf.set_margins(16, 16, 16)
    pdf.add_page()
    width = pdf.epw

    def text(value: str, size: float = 10, style: str = "", color=(45, 45, 45), h: float = 5.2):
        pdf.set_font("main", style, size)
        pdf.set_text_color(*color)
        pdf.multi_cell(width, h, value, align="L", new_x="LMARGIN", new_y="NEXT")

    def heading(value: str, size: float = 14):
        pdf.ln(4)
        text(value, size, "B", h=7)
        pdf.ln(1)

    # --- шапка ---
    text(detail.full_name, 20, "B", h=9)
    pdf.set_font("main", "B", 28)
    pdf.set_text_color(*_score_color(detail.health_score))
    score = "-" if detail.health_score is None else f"{detail.health_score}/100"
    pdf.cell(pdf.get_string_width(score) + 4, 14, score)
    pdf.set_font("main", "", 13)
    pdf.set_text_color(45, 45, 45)
    pdf.cell(0, 14, detail.verdict, new_x="LMARGIN", new_y="NEXT")
    meta = [
        f"Ссылка: {detail.url}",
        f"Дата анализа: {detail.last_analyzed_at:%Y-%m-%d %H:%M} UTC" if detail.last_analyzed_at else "Дата анализа: -",
        f"Основной язык: {detail.language or '-'}",
        "Режим: " + ("личный анализ по PAT владельца (включая AppSec)" if detail.scope == "personal"
                     else "публичный анализ (открытые данные)"),
        f"Полнота данных: {round(detail.coverage * 100)}% веса методики"
        + (f" · методика v{detail.methodology_version}" if detail.methodology_version else ""),
    ]
    for line in meta:
        text(line, 9.5, color=(90, 90, 90), h=4.8)

    if detail.metrics is None:
        text("Анализ ещё не выполнялся.", 11)
        return bytes(pdf.output())
    metrics = detail.metrics.model_dump()

    # --- категории ---
    heading("Оценки по категориям")
    pdf.set_font("main", size=9)
    heading_style = FontFace(emphasis="BOLD", fill_color=(235, 235, 235))
    with pdf.table(col_widths=(26, 20, 26, 18, 88), line_height=5, headings_style=heading_style,
                   text_align=("LEFT", "CENTER", "CENTER", "CENTER", "LEFT")) as table:
        table.row(["Категория", "Оценка", "Вес: исходный → факт.", "Вклад", "Пояснение"])
        for key, title in CATEGORY_TITLES.items():
            m = Metric(**metrics[key])
            no_data = m.status == "NO_DATA"
            table.row([
                title,
                NO_DATA if no_data else f"{m.score}/100",
                f"{round(m.base_weight * 100)}% → {round(m.weight * 100)}%",
                "-" if no_data else f"{m.contribution:.1f}",
                m.summary or "",
            ])
    pdf.ln(2)
    text("Repo Health Score = Σ(оценка категории × вес) по категориям с данными. Веса категорий "
         "«Нет данных» перераспределяются между остальными - отсутствие данных не снижает оценку.", 8.5,
         color=(90, 90, 90), h=4.4)

    # --- сильные / слабые стороны ---
    if detail.strengths or detail.weaknesses:
        heading("Сильные и слабые стороны")
        for s in detail.strengths:
            text(f"+  {s}", 10, color=(63, 122, 74))
        for w in detail.weaknesses:
            text(f"–  {w}", 10, color=(162, 59, 59))

    # --- рекомендации ---
    heading("Рекомендации")
    if not detail.recommendations:
        text("Критичных рекомендаций нет.", 10)
    for i, rec in enumerate(detail.recommendations, start=1):
        pdf.set_font("main", "B", 8)
        pdf.set_fill_color(*PRIORITY_COLORS[rec.priority])
        pdf.set_text_color(255, 255, 255)
        label = f" {PRIORITY_TITLES[rec.priority].upper()} "
        pdf.cell(pdf.get_string_width(label) + 2, 5.5, label, fill=True)
        pdf.set_fill_color(255, 255, 255)  # иначе цвет плашки «протекает» в таблицы ниже
        pdf.cell(3, 5.5, "")
        pdf.set_font("main", "B", 10.5)
        pdf.set_text_color(45, 45, 45)
        pdf.multi_cell(0, 5.5, f"{i}. {rec.title}", align="L", new_x="LMARGIN", new_y="NEXT")
        text(f"Почему важно: {rec.why_it_matters}", 9.5)
        if rec.facts:
            text(f"Факты: {rec.facts}", 9.5)
        text(f"Что сделать: {rec.action}", 9.5)
        if rec.impact:
            text(f"Ожидаемый эффект: {rec.impact}", 9.5, "B")
        if rec.evidence:
            text("Подтверждения: " + "; ".join(e.ref for e in rec.evidence[:6]), 8.5, color=(100, 100, 100), h=4.4)
        pdf.ln(2)

    # --- объяснение расчёта ---
    heading("Объяснение расчёта")
    for key, title in CATEGORY_TITLES.items():
        m = Metric(**metrics[key])
        text(f"{title}: {NO_DATA if m.status == 'NO_DATA' else f'{m.score}/100'}", 11, "B", h=6)
        if m.status == "NO_DATA":
            text(f"{m.summary}. Категория исключена из расчёта и не снижает Score.", 9, color=(90, 90, 90))
            pdf.ln(1)
            continue
        if m.components:
            pdf.set_font("main", size=8.5)
            with pdf.table(col_widths=(80, 60, 30), line_height=4.6, headings_style=heading_style,
                           text_align=("LEFT", "LEFT", "RIGHT")) as table:
                table.row(["Показатель", "Значение", "Баллы"])
                for c in m.components:
                    if c.points is None:
                        points = "не измерено"
                    elif c.max_points:
                        points = f"{c.points:.1f} из {c.max_points:g}"
                    else:
                        points = f"{c.points:.0f}"
                    table.row([c.label, c.value, points])
        pdf.ln(2)

    return bytes(pdf.output())
