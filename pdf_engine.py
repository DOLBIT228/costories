from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from PIL import Image
import tempfile

pdfmetrics.registerFont(TTFont("Montserrat", "Montserrat-Regular.ttf"))
pdfmetrics.registerFont(TTFont("MontserratBold", "Montserrat-Bold.ttf"))


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


def append_pricing_rows(table, rows, ring_title):
    table.append([ring_title, "", "", "", ""])
    for r in rows:
        table.append([
            r["Товар/послуга"],
            r["Ціна"],
            r["К-сть"],
            r["Знижка"],
            r["Сума"],
        ])


def generate_pdf(background, data, out="final.pdf"):

    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    elements = []

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
    elements.append(Spacer(1, 95*mm))

    table = []

    table.append(["ПАРАМЕТРИ","ЖІНОЧА","ЧОЛОВІЧА", "", ""])
    table += [["Розмір",data["w_size"],data["m_size"], "", ""]]
    table += [["Ширина",data["w_width"],data["m_width"], "", ""]]
    table += [["Товщина",data["w_thickness"],data["m_thickness"], "", ""]]

    table.append(["ЦІНОУТВОРЕННЯ", "", "", "", ""])
    table.append(["Товар/послуга", "Ціна", "К-сть", "Знижка", "Вартість"])

    append_pricing_rows(table, data["w_pricing_rows"], "Жіноча")
    append_pricing_rows(table, data["m_pricing_rows"], "Чоловіча")

    table.append(["ЗАГАЛЬНА ВАРТІСТЬ", "", "", "", ""])

    idx_w = len(table)
    table.append(["Жіноча", "", "", "", f'{data["w_total"]:.0f} ₴'])

    idx_m = len(table)
    table.append(["Чоловіча", "", "", "", f'{data["m_total"]:.0f} ₴'])

    idx_pair = len(table)
    table.append(["Ціна за пару", "", "", "", f'{data["pair_total"]:.0f} ₴'])

    tbl = Table(table, colWidths=[48*mm,30*mm,28*mm,28*mm,36*mm])

    style = [
        ("GRID",(0,0),(-1,-1),0.4,colors.white),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2b3149")),
        ("FONT",(0,0),(-1,0),"MontserratBold",11),

        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),

        ("FONT",(0,1),(-1,-1),"Montserrat",10),
        ("TEXTCOLOR",(0,0),(-1,-1),colors.white),
    ]

    for i,r in enumerate(table):
        if r[1]=="" and r[2]=="" and r[3]=="" and r[4]=="":
            style.append(("SPAN",(0,i),(-1,i)))
            style.append(("BACKGROUND",(0,i),(-1,i),colors.HexColor("#3b4158")))
            style.append(("FONT",(0,i),(-1,i),"MontserratBold",11))

    pricing_header_idx = None
    for i, r in enumerate(table):
        if r[0] == "Товар/послуга":
            pricing_header_idx = i
            break
    if pricing_header_idx is not None:
        style.append(("BACKGROUND", (0, pricing_header_idx), (-1, pricing_header_idx), colors.HexColor("#4d556f")))
        style.append(("FONT", (0, pricing_header_idx), (-1, pricing_header_idx), "MontserratBold", 10))

    style += [
        ("FONT",(0,idx_pair),(-1,idx_pair),"MontserratBold",12),
        ("ALIGN",(4,1),(4,-1),"RIGHT"),
    ]

    tbl.setStyle(TableStyle(style))

    elements.append(tbl)

    doc.build(elements, onFirstPage=draw_bg)

    return out
