import sqlite3

DB = "data.db"

STONE_SIZES = [
    "1.00","1.25","1.50","1.75","2.00","2.25","2.50","2.75",
    "3.00","3.50","3.80","4.00","4.30","4.50","5.00","5.50",
    "6.00","6.50","7.00","7.50","8.00"
]

STONE_TYPES = ["diamond","cvd","moissanite","zircon"]

FIXED_METALS = [
    "Срібло 925",
    "Золото 375",
    "Золото 585",
    "Золото 750",
    "Платина 950"
]

JEWELER_TYPES = ["platinum","premium","premium_plus"]

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS metals(
        name TEXT PRIMARY KEY,
        price REAL DEFAULT 0
    )
    """)
    for m in FIXED_METALS:
        cur.execute("INSERT OR IGNORE INTO metals VALUES(?,0)", (m,))

    cur.execute("""
    CREATE TABLE IF NOT EXISTS jeweler(
        type TEXT PRIMARY KEY,
        price REAL DEFAULT 0
    )
    """)
    for t in JEWELER_TYPES:
        cur.execute("INSERT OR IGNORE INTO jeweler VALUES(?,0)", (t,))

    # USD rate
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        id INTEGER PRIMARY KEY,
        usd REAL DEFAULT 40,
        background_file TEXT DEFAULT 'background.png'
    )
    """)

    settings_cols = [row[1] for row in cur.execute("PRAGMA table_info(settings)")]
    if "background_file" not in settings_cols:
        cur.execute("ALTER TABLE settings ADD COLUMN background_file TEXT DEFAULT 'background.png'")

    cur.execute("INSERT OR IGNORE INTO settings(id, usd, background_file) VALUES(1,40,'background.png')")
    cur.execute("UPDATE settings SET background_file='background.png' WHERE background_file IS NULL OR background_file=''")

    # stones in USD
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stones(
        size TEXT PRIMARY KEY,
        diamond REAL DEFAULT 0,
        cvd REAL DEFAULT 0,
        moissanite REAL DEFAULT 0,
        zircon REAL DEFAULT 0
    )
    """)
    for s in STONE_SIZES:
        cur.execute("INSERT OR IGNORE INTO stones(size) VALUES(?)",(s,))

    cur.execute("""
    CREATE TABLE IF NOT EXISTS profiles(name TEXT PRIMARY KEY, price REAL DEFAULT 0)
    """)
    cur.execute("INSERT OR IGNORE INTO profiles VALUES('Comfort fit',0)")
    cur.execute("INSERT OR IGNORE INTO profiles VALUES('Стандартний',0)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS engravings(name TEXT PRIMARY KEY, price REAL DEFAULT 0)
    """)
    cur.execute("INSERT OR IGNORE INTO engravings VALUES('Просте',0)")
    cur.execute("INSERT OR IGNORE INTO engravings VALUES('Складне',0)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS coatings(name TEXT PRIMARY KEY, price REAL DEFAULT 0)
    """)
    cur.execute("INSERT OR IGNORE INTO coatings VALUES('Родій',0)")
    cur.execute("INSERT OR IGNORE INTO coatings VALUES('Рутеній',0)")

    conn.commit()
    conn.close()
