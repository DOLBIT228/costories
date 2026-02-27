import streamlit as st
import pandas as pd
import requests
from pathlib import Path
import shutil
from database import get_conn, init_db, STONE_SIZES, STONE_TYPES
from pdf_engine import generate_pdf


init_db()
conn = get_conn()

ASSETS_DIR = Path("assets")
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)


def list_background_files():
    allowed = {".png", ".jpg", ".jpeg"}
    files = sorted([f.name for f in BACKGROUNDS_DIR.iterdir() if f.is_file() and f.suffix.lower() in allowed])

    legacy = Path("background.png")
    if legacy.exists() and "background.png" not in files:
        files.insert(0, "background.png")

    return files


def get_background_path(filename):
    if filename == "background.png":
        return "background.png"

    candidate = BACKGROUNDS_DIR / filename
    if candidate.exists():
        return str(candidate)

    return "background.png"

st.set_page_config(layout="wide")
st.title("💍 Кошторис обручок")

tab1, tab2 = st.tabs(["Менеджер","Адмін"])

# ================= ADMIN =================
with tab2:

    st.header("Адмін панель")

    def editable_table(title, table):
        st.subheader(title)
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
        edited = st.data_editor(df, use_container_width=True, num_rows="fixed")
        if st.button(f"Зберегти {table}"):
            for _, r in edited.iterrows():
                cols = ",".join([f"{c}=?" for c in df.columns[1:]])
                conn.execute(
                    f"UPDATE {table} SET {cols} WHERE {df.columns[0]}=?",
                    list(r[1:]) + [r[0]]
                )
            conn.commit()
            st.success("Збережено")

    editable_table("Метали ₴/г","metals")
    editable_table("Робота ювеліра ₴/г","jeweler")
    editable_table("Каміння (USD матриця)","stones")
    editable_table("Профілі","profiles")
    editable_table("Гравіювання","engravings")
    editable_table("Покриття","coatings")

    st.subheader("Курс USD")

    settings = pd.read_sql("SELECT usd, background_file FROM settings WHERE id=1",conn).iloc[0]
    usd = settings["usd"]
    selected_background = settings["background_file"]
    new_usd = st.number_input("USD → UAH",value=float(usd))

    if st.button("Зберегти курс"):
        conn.execute("UPDATE settings SET usd=? WHERE id=1",(new_usd,))
        conn.commit()

    if st.button("Оновити з НБУ"):
        r = requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json")
        rate = r.json()[0]["rate"]
        conn.execute("UPDATE settings SET usd=? WHERE id=1",(rate,))
        conn.commit()
        st.success(f"Оновлено: {rate}")

    st.subheader("Фони для PDF")

    uploaded_backgrounds = st.file_uploader(
        "Завантажити фони (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="background_uploads",
    )

    if st.button("Зберегти фони"):
        if uploaded_backgrounds:
            saved = 0
            for bg in uploaded_backgrounds:
                safe_name = Path(bg.name).name
                target = BACKGROUNDS_DIR / safe_name
                with target.open("wb") as f:
                    shutil.copyfileobj(bg, f)
                saved += 1
            st.success(f"Збережено фонів: {saved}")
        else:
            st.info("Спочатку оберіть хоча б один файл.")

    backgrounds = list_background_files()
    current_background = pd.read_sql("SELECT background_file FROM settings WHERE id=1", conn).iloc[0]["background_file"]
    if current_background not in backgrounds:
        current_background = backgrounds[0] if backgrounds else "background.png"

    selected_background = st.selectbox(
        "Фон для формування PDF",
        options=backgrounds if backgrounds else ["background.png"],
        index=(backgrounds.index(current_background) if backgrounds else 0),
        key="selected_background",
    )

    if st.button("Зберегти фон для PDF"):
        conn.execute("UPDATE settings SET background_file=? WHERE id=1", (selected_background,))
        conn.commit()
        st.success(f"Активний фон: {selected_background}")

# ================= MANAGER =================
with tab1:

    metals = pd.read_sql("SELECT * FROM metals",conn)
    jeweler = pd.read_sql("SELECT * FROM jeweler",conn)
    stones = pd.read_sql("SELECT * FROM stones",conn)
    profiles = pd.read_sql("SELECT * FROM profiles",conn)
    engr = pd.read_sql("SELECT * FROM engravings",conn)
    coat = pd.read_sql("SELECT * FROM coatings",conn)
    settings = pd.read_sql("SELECT usd, background_file FROM settings WHERE id=1",conn).iloc[0]
    usd = settings["usd"]
    selected_background = settings["background_file"]

    col1,col2 = st.columns(2)

    photo1 = st.file_uploader("Фото жіночої",type=["png","jpg"],key="p1")
    photo2 = st.file_uploader("Фото чоловічої",type=["png","jpg"],key="p2")

    def ring(prefix,title):
        st.subheader(title)

        size = st.text_input("Розмір",key=f"{prefix}s")
        width = st.text_input("Ширина мм",key=f"{prefix}w")
        thickness = st.text_input("Товщина мм",key=f"{prefix}t")
        weight = st.number_input("Вага г",0.0,key=f"{prefix}wg")

        metal = st.selectbox("Метал",metals.name,key=f"{prefix}m")
        jew = st.selectbox("Тип роботи",jeweler.type,key=f"{prefix}j")

        metal_price = float(metals[metals.name == metal].price.values[0])
        jeweler_price = float(jeweler[jeweler.type == jew].price.values[0])

        st.markdown("#### Знижки менеджера")
        d1, d2 = st.columns(2)
        with d1:
            metal_discount = st.number_input(
                "Знижка на метали ₴/г",
                min_value=0.0,
                value=0.0,
                step=10.0,
                key=f"{prefix}dm",
            )
            profile_discount = st.number_input(
                "Знижка на профіль %",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=1.0,
                key=f"{prefix}dp",
            )
        with d2:
            jeweler_discount = st.number_input(
                "Знижка на роботу ювелірів %",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=1.0,
                key=f"{prefix}dj",
            )
            engraving_discount = st.number_input(
                "Знижка на гравіювання %",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=1.0,
                key=f"{prefix}de",
            )

        pricing_rows = []

        def add_row(category, item, unit_price, qty, discount, unit, discount_type="percent"):
            base = unit_price * qty

            if discount_type == "per_unit":
                discounted_unit_price = max(unit_price - discount, 0)
                final = discounted_unit_price * qty
                discount_label = f"-{discount:.0f} ₴/{unit}"
            else:
                final = base * (1 - discount / 100)
                discount_label = f"{discount:.0f}%"

            pricing_rows.append(
                {
                    "Категорія": category,
                    "Товар/послуга": item,
                    "Ціна": f"{unit_price:.0f} ₴",
                    "К-сть": f"{qty:.2f} {unit}",
                    "Знижка": discount_label,
                    "Сума": f"{final:.0f} ₴",
                }
            )
            return final

        total = 0.0
        total += add_row("Метал", metal, metal_price, weight, metal_discount, "г", "per_unit")
        total += add_row("Робота ювеліра", jew, jeweler_price, weight, jeweler_discount, "г")

        stones_txt = profile_txt = engr_txt = coat_txt = combo_txt = ""

        if st.checkbox("Каміння",key=f"{prefix}k"):
            t = st.selectbox("Тип",STONE_TYPES,key=f"{prefix}kt")
            sz = st.selectbox("Розмір",STONE_SIZES,key=f"{prefix}ks")
            q = st.number_input("Кількість",0,key=f"{prefix}kq")

            usd_price = stones[stones["size"]==sz][t].values[0]
            stone_price = float(usd_price * usd)
            total += add_row("Каміння", f"{t} {sz}мм", stone_price, q, 0.0, "шт")
            stones_txt = f"{t} {sz}мм x{q}"

        if st.checkbox("Профіль",key=f"{prefix}p"):
            p = st.selectbox("Тип",profiles.name,key=f"{prefix}pp")
            profile_price = float(profiles[profiles.name == p].price.values[0])
            total += add_row("Профіль", p, profile_price, 1, profile_discount, "шт")
            profile_txt = p

        if st.checkbox("Гравіювання",key=f"{prefix}e"):
            e = st.selectbox("Тип",engr.name,key=f"{prefix}ee")
            engraving_price = float(engr[engr.name == e].price.values[0])
            total += add_row("Гравіювання", e, engraving_price, 1, engraving_discount, "шт")
            engr_txt = e

        if st.checkbox("Покриття",key=f"{prefix}c"):
            c = st.selectbox("Тип",coat.name,key=f"{prefix}cc")
            coating_price = float(coat[coat.name == c].price.values[0])
            total += add_row("Покриття", c, coating_price, 1, 0.0, "шт")
            coat_txt = c

        if st.checkbox("Поєднання кольорів",key=f"{prefix}x"):
            cx = st.number_input("Сума ₴",0.0,key=f"{prefix}xx")
            total += add_row("Поєднання кольорів", "Додаткова послуга", cx, 1, 0.0, "шт")
            combo_txt = f"{cx:.0f} ₴"

        if pricing_rows:
            st.markdown("#### Ціноутворення")
            st.dataframe(pd.DataFrame(pricing_rows), use_container_width=True, hide_index=True)

        st.markdown(f"### 💰 {total:.2f} ₴")

        return {
            "size":size,
            "width":width,
            "thickness":thickness,
            "metal":metal,
            "weight":weight,
            "total":total,
            "pricing_rows":pricing_rows,
            "stones":stones_txt,
            "profile":profile_txt,
            "engraving":engr_txt,
            "coating":coat_txt,
            "combo":combo_txt
        }

    with col1:
        woman = ring("w","Жіноча")

    with col2:
        man = ring("m","Чоловіча")

    pair_total = woman["total"] + man["total"]

    st.divider()
    st.markdown(f"# 🧾 Разом: {pair_total:.2f} ₴")

    if st.button("📄 Згенерувати PDF"):

        data = {
            "photo1":photo1,
            "photo2":photo2,

            "w_size":woman["size"],
            "m_size":man["size"],
            "w_width":woman["width"],
            "m_width":man["width"],
            "w_thickness":woman["thickness"],
            "m_thickness":man["thickness"],
            "w_metal":woman["metal"],
            "m_metal":man["metal"],
            "w_weight":woman["weight"],
            "m_weight":man["weight"],
            "w_pricing_rows":woman["pricing_rows"],
            "m_pricing_rows":man["pricing_rows"],

            "w_total":woman["total"],
            "m_total":man["total"],
            "pair_total":pair_total,

            "w_stones":woman["stones"],
            "m_stones":man["stones"],
            "w_profile":woman["profile"],
            "m_profile":man["profile"],
            "w_engraving":woman["engraving"],
            "m_engraving":man["engraving"],
            "w_coating":woman["coating"],
            "m_coating":man["coating"],
            "w_combo":woman["combo"],
            "m_combo":man["combo"]
        }

        out = generate_pdf(get_background_path(selected_background),data)

        with open(out,"rb") as f:
            st.download_button("⬇️ Завантажити PDF",f,file_name="koshtorys.pdf")
