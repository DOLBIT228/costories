import streamlit as st
import pandas as pd
import requests
from database import get_conn, init_db, STONE_SIZES, STONE_TYPES
from pdf_engine import generate_pdf
from tempfile import NamedTemporaryFile

init_db()
conn = get_conn()

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

    usd = pd.read_sql("SELECT usd FROM settings WHERE id=1",conn).iloc[0][0]
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

# ================= MANAGER =================
with tab1:

    metals = pd.read_sql("SELECT * FROM metals",conn)
    jeweler = pd.read_sql("SELECT * FROM jeweler",conn)
    stones = pd.read_sql("SELECT * FROM stones",conn)
    profiles = pd.read_sql("SELECT * FROM profiles",conn)
    engr = pd.read_sql("SELECT * FROM engravings",conn)
    coat = pd.read_sql("SELECT * FROM coatings",conn)
    usd = pd.read_sql("SELECT usd FROM settings WHERE id=1",conn).iloc[0][0]

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

        total = (
            weight * metals[metals.name==metal].price.values[0] +
            weight * jeweler[jeweler.type==jew].price.values[0]
        )

        stones_txt = profile_txt = engr_txt = coat_txt = combo_txt = ""

        if st.checkbox("Каміння",key=f"{prefix}k"):
            t = st.selectbox("Тип",STONE_TYPES,key=f"{prefix}kt")
            sz = st.selectbox("Розмір",STONE_SIZES,key=f"{prefix}ks")
            q = st.number_input("Кількість",0,key=f"{prefix}kq")

            usd_price = stones[stones["size"]==sz][t].values[0]
            total += usd_price * usd * q
            stones_txt = f"{t} {sz}мм x{q}"

        if st.checkbox("Профіль",key=f"{prefix}p"):
            p = st.selectbox("Тип",profiles.name,key=f"{prefix}pp")
            total += profiles[profiles.name==p].price.values[0]
            profile_txt = p

        if st.checkbox("Гравіювання",key=f"{prefix}e"):
            e = st.selectbox("Тип",engr.name,key=f"{prefix}ee")
            total += engr[engr.name==e].price.values[0]
            engr_txt = e

        if st.checkbox("Покриття",key=f"{prefix}c"):
            c = st.selectbox("Тип",coat.name,key=f"{prefix}cc")
            total += coat[coat.name==c].price.values[0]
            coat_txt = c

        if st.checkbox("Поєднання кольорів",key=f"{prefix}x"):
            cx = st.number_input("Сума ₴",0.0,key=f"{prefix}xx")
            total += cx
            combo_txt = f"{cx:.0f} ₴"

        st.markdown(f"### 💰 {total:.2f} ₴")

        return {
            "size":size,
            "width":width,
            "thickness":thickness,
            "metal":metal,
            "weight":weight,
            "total":total,
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

        out = generate_pdf("background.png",data)

        with open(out,"rb") as f:
            st.download_button("⬇️ Завантажити PDF",f,file_name="koshtorys.pdf")