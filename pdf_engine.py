from reportlab.lib.pagesizes import A4
from reportlab.platypus import KeepInFrame, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from PIL import Image
import tempfile

pdfmetrics.registerFont(TTFont("EUkraineRegular", "e-Ukraine-UltraLight.otf"))
pdfmetrics.registerFont(TTFont("EUkraineBold", "e-Ukraine-Bold.otf"))


def get_pdf_color(data):
    value = str(data.get("text_color", "#fff")).strip().lower()
    if value.startswith("#") and len(value) in (4, 7) and all(ch in "0123456789abcdef" for ch in value[1:]):
        return colors.HexColor(value)
    return colors.HexColor("#fff")


def save_uploaded(upload):
    if not upload:
        return None
    img = Image.open(upload).convert("RGBA")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name


def section(title):
    return [[title, "", ""]]


def row(label, w, m):
    return [[label, str(w), str(m)]]


VISIBLE_PRICE_COLS = [0, 2, 4, 6, 8]
PRICE_GAP_COLS = [1, 3, 5, 7]


def pricing_row(col_1="", col_2="", col_3="", col_4="", col_5=""):
    return [col_1, "", col_2, "", col_3, "", col_4, "", col_5]


def pricing_summary_row(label, value):
    # Keep the first column untouched and place the total value into one merged block
    # built from visual columns 2-5.
    return pricing_row(label, value)


def append_pricing_rows(table, rows, ring_title):
    table.append(pricing_row(ring_title))
    table.append(pricing_row("Товар/послуга", "Ціна", "К-сть", "Знижка", "Вартість"))
    for r in rows:
        table.append(pricing_row(
            r["Товар/послуга"],
            r["Ціна"],
            r["К-сть"],
            r["Знижка"],
            r["Сума"],
        ))


def append_split_row_line(style, row_idx, line_type, thickness, color, columns):
    for col_idx in columns:
        style.append((line_type, (col_idx, row_idx), (col_idx, row_idx), thickness, color))


def draw_footer(canvas_obj, doc, data):
    couple_names = data.get("couple_names")
    agreement_number = data.get("agreement_number")

    footer_lines = []
    if couple_names:
        footer_lines.append(f"Ім'я нареченого та нареченої: {couple_names}")
    if agreement_number:
        footer_lines.append(f"Номер угоди: {agreement_number}")

    if not footer_lines:
        return

    canvas_obj.saveState()
    canvas_obj.setFont("EUkraineRegular", 8)
    canvas_obj.setFillColor(get_pdf_color(data))

    x = doc.leftMargin
    y = 10 * mm
    line_gap = 4 * mm

    for i, line in enumerate(footer_lines):
        canvas_obj.drawString(x, y + (len(footer_lines) - i - 1) * line_gap, line)

    canvas_obj.restoreState()


def generate_pdf(data, out="final.pdf"):

    background = data.get("background_path", "background.png")

    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    elements = []
    pdf_color = get_pdf_color(data)

    pricing_rows_total = len(data["w_pricing_rows"]) + len(data["m_pricing_rows"])
    is_compact_layout = pricing_rows_total >= 12

    body_font_size = 8 if is_compact_layout else 9
    section_font_size = 10 if is_compact_layout else 11
    header_font_size = 7 if is_compact_layout else 8

    row_top_padding = 2 if is_compact_layout else 3
    row_bottom_padding = 3 if is_compact_layout else 5
    section_top_padding = 6 if is_compact_layout else 8
    section_bottom_padding = 4 if is_compact_layout else 5
    title_bottom_padding = 5 if is_compact_layout else 6

    # ================= BACKGROUND + PHOTOS =================
    def draw_bg(canvas, doc):

        PAGE_W, PAGE_H = A4
        canvas.drawImage(background, 0, 0, PAGE_W, PAGE_H)

        # ===== SAFE ZONE ПІД ЛОГО =====
        LOGO_SAFE = 55 * mm

        PHOTO_W = 50 * mm
        PHOTO_H = 50 * mm
        GAP = 15 * mm
        RADIUS = 10

        photo_y = PAGE_H - LOGO_SAFE - PHOTO_H

        # ===== ФУНКЦІЯ ОКРУГЛЕННЯ =====
        def rounded(img, x, y):
            canvas.saveState()

            path = canvas.beginPath()
            path.roundRect(x, y, PHOTO_W, PHOTO_H, RADIUS)

            canvas.clipPath(path, stroke=0, fill=0)

            canvas.drawImage(
                img,
                x,
                y,
                PHOTO_W,
                PHOTO_H,
                preserveAspectRatio=False,
                mask="auto"
            )

            canvas.restoreState()

        # ===== ЗБІР ФОТО =====
        photos = []

        if data["photo1"]:
            photos.append(save_uploaded(data["photo1"]))

        if data["photo2"]:
            photos.append(save_uploaded(data["photo2"]))

        count = len(photos)

        # ===== 1 ФОТО =====
        if count == 1:
            x = (PAGE_W - PHOTO_W) / 2
            rounded(photos[0], x, photo_y)

        # ===== 2 ФОТО =====
        elif count == 2:
            total_width = PHOTO_W * 2 + GAP
            start_x = (PAGE_W - total_width) / 2

            rounded(photos[0], start_x, photo_y)
            rounded(photos[1], start_x + PHOTO_W + GAP, photo_y)

    # таблиця завжди під фото
    table_top_offset = 95 * mm
    elements.append(Spacer(1, table_top_offset))

    params_table = [
        ["ПАРАМЕТРИ", "", "Жіноча", "", "Чоловіча"],
        ["Розмір", "", data["w_size"], "", data["m_size"]],
        ["Ширина", "", data["w_width"], "", data["m_width"]],
        ["Товщина", "", data["w_thickness"], "", data["m_thickness"]],
        ["Вага", "", f'{data["w_weight"]:.2f} г', "", f'{data["m_weight"]:.2f} г'],
    ]

    params_col_widths = [58 * mm, 4 * mm, 52 * mm, 4 * mm, 52 * mm]
    params_tbl = Table(params_table, colWidths=params_col_widths)
    params_tbl.hAlign = "CENTER"

    params_style = [
        ("FONT", (0, 0), (-1, -1), "EUkraineRegular", body_font_size),
        ("FONT", (0, 0), (-1, 0), "EUkraineBold", section_font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), pdf_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), pdf_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (2, 0), (4, -1), "LEFT"),
        ("ALIGN", (2, 0), (4, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), row_top_padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), row_bottom_padding),
        ("BOTTOMPADDING", (0, 0), (-1, 0), title_bottom_padding),
        ("LEFTPADDING", (1, 0), (1, -1), 0),
        ("RIGHTPADDING", (1, 0), (1, -1), 0),
        ("LEFTPADDING", (3, 0), (3, -1), 0),
        ("RIGHTPADDING", (3, 0), (3, -1), 0),
        ("LINEBELOW", (0, 0), (0, 0), 1, pdf_color),
        ("LINEBELOW", (2, 0), (2, 0), 1, pdf_color),
        ("LINEBELOW", (4, 0), (4, 0), 1, pdf_color),
    ]

    for row_idx in range(1, len(params_table)):
        params_style.append(("LINEBELOW", (0, row_idx), (0, row_idx), 0.3, pdf_color))
        params_style.append(("LINEBELOW", (2, row_idx), (2, row_idx), 0.3, pdf_color))
        params_style.append(("LINEBELOW", (4, row_idx), (4, row_idx), 0.3, pdf_color))

    params_tbl.setStyle(TableStyle(params_style))

    table = []

    table.append(pricing_row("ЦІНОУТВОРЕННЯ"))

    append_pricing_rows(table, data["w_pricing_rows"], "Жіноча")
    append_pricing_rows(table, data["m_pricing_rows"], "Чоловіча")

    idx_summary_header = len(table)
    table.append(pricing_summary_row("ЗАГАЛЬНА ВАРТІСТЬ", ""))

    idx_w = len(table)
    table.append(pricing_summary_row("Жіноча", f'{data["w_total"]:.0f} ₴'))

    idx_m = len(table)
    table.append(pricing_summary_row("Чоловіча", f'{data["m_total"]:.0f} ₴'))

    idx_pair = len(table)
    table.append(pricing_summary_row("Загальна вартість", f'{data["pair_total"]:.0f} ₴'))

    pricing_col_widths = [64 * mm, 3 * mm, 24 * mm, 3 * mm, 20 * mm, 3 * mm, 20 * mm, 3 * mm, 30 * mm]
    tbl = Table(table, colWidths=pricing_col_widths)
    tbl.hAlign = "CENTER"

    style = [
        ("FONT", (0, 0), (-1, -1), "EUkraineRegular", body_font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), pdf_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (2, 0), (8, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), row_top_padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), row_bottom_padding),
        ("FONT", (0, 0), (-1, 0), "EUkraineBold", section_font_size),
        ("ALIGN", (2, 0), (8, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), title_bottom_padding),
        ("TEXTCOLOR", (0, 0), (-1, 0), pdf_color),
        ("SPAN", (2, idx_summary_header), (8, idx_summary_header)),
        ("SPAN", (2, idx_w), (8, idx_w)),
        ("SPAN", (2, idx_m), (8, idx_m)),
        ("SPAN", (2, idx_pair), (8, idx_pair)),
    ]

    for gap_col in PRICE_GAP_COLS:
        style.append(("LEFTPADDING", (gap_col, 0), (gap_col, -1), 0))
        style.append(("RIGHTPADDING", (gap_col, 0), (gap_col, -1), 0))

    append_split_row_line(style, 0, "LINEBELOW", 1, pdf_color, VISIBLE_PRICE_COLS)

    for row_idx in range(1, len(table)):
        append_split_row_line(style, row_idx, "LINEBELOW", 0.3, pdf_color, VISIBLE_PRICE_COLS)

    for i,r in enumerate(table):
        if all(r[col] == "" for col in VISIBLE_PRICE_COLS[1:]) and r[0] != "ЗАГАЛЬНА ВАРТІСТЬ":
            style.append(("SPAN",(0,i),(-1,i)))
            style.append(("FONT",(0,i),(-1,i),"EUkraineBold",section_font_size))
            style.append(("TEXTCOLOR", (0, i), (-1, i), pdf_color))
            style.append(("TOPPADDING", (0, i), (-1, i), section_top_padding))
            style.append(("BOTTOMPADDING", (0, i), (-1, i), section_bottom_padding))
            style.append(("LINEBELOW", (0, i), (8, i), 1, pdf_color))

    style += [
        ("FONT", (0, idx_summary_header), (8, idx_summary_header), "EUkraineBold", section_font_size),
        ("TEXTCOLOR", (0, idx_summary_header), (8, idx_summary_header), pdf_color),
        ("TOPPADDING", (0, idx_summary_header), (8, idx_summary_header), section_top_padding),
        ("BOTTOMPADDING", (0, idx_summary_header), (8, idx_summary_header), section_bottom_padding),
        ("LINEBELOW", (0, idx_summary_header), (8, idx_summary_header), 1, pdf_color),
    ]

    pricing_header_indexes = [i for i, r in enumerate(table) if r[0] == "Товар/послуга"]
    for pricing_header_idx in pricing_header_indexes:
        style.append(("FONT", (0, pricing_header_idx), (-1, pricing_header_idx), "EUkraineBold", header_font_size))
        style.append(("TEXTCOLOR", (0, pricing_header_idx), (-1, pricing_header_idx), pdf_color))
        append_split_row_line(style, pricing_header_idx, "LINEABOVE", 0.8, pdf_color, VISIBLE_PRICE_COLS)

    style += [
        ("FONT",(0,idx_pair),(-1,idx_pair),"EUkraineBold",section_font_size),
        ("FONT", (2, idx_w), (8, idx_pair), "EUkraineBold", body_font_size),
        ("ALIGN", (2, idx_w), (8, idx_pair), "LEFT"),
    ]

    # In the summary block we use merged cells on columns 2-8,
    # so draw a continuous white divider instead of split per-column lines.
    for summary_row in (idx_w, idx_m, idx_pair):
        style.append(("LINEBELOW", (2, summary_row), (8, summary_row), 0.8, pdf_color))

    tbl.setStyle(TableStyle(style))

    available_table_height = doc.height - table_top_offset
    fit_table = KeepInFrame(
        maxWidth=doc.width,
        maxHeight=available_table_height,
        content=[params_tbl, Spacer(1, 6 if is_compact_layout else 8), tbl],
        mode="shrink",
        hAlign="CENTER",
    )

    elements.append(fit_table)

    def draw_first_page(canvas_obj, page_doc):
        draw_bg(canvas_obj, page_doc)
        draw_footer(canvas_obj, page_doc, data)

    doc.build(elements, onFirstPage=draw_first_page)

    return out
