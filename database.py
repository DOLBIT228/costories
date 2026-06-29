import sqlite3
import re
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "data.db"
BACKUP_FILE = BASE_DIR / "data_backup.json"

STONE_SIZES = [
    "1.00","1.25","1.50","1.75","2.00","2.25","2.50","2.75",
    "3.00","3.50","3.80","4.00","4.30","4.50","5.00","5.50",
    "6.00","6.50","7.00","7.50","8.00"
]

STONE_TYPE_TO_COLUMN = {
    "Діамант": "diamond",
    "CVD": "cvd",
    "Муассаніт": "moissanite",
    "Цирконій": "zircon",
}
STONE_TYPES = list(STONE_TYPE_TO_COLUMN.keys())

FIXED_METALS = [
    "Срібло 925",
    "Золото 375",
    "Золото 585",
    "Золото 750",
    "Платина 950"
]

JEWELER_TYPES = ["Платина","Преміум","Преміум+"]
DEFAULT_TEXT_COLOR = "#000000"
DEFAULT_BACKGROUND_FILE = "full_white.png"

BACKUP_TABLES = {
    "metals": ("name", ["price"]),
    "jeweler": ("type", ["price"]),
    "stones": ("size", ["diamond", "cvd", "moissanite", "zircon"]),
    "profiles": ("name", ["price"]),
    "engravings": ("name", ["price"]),
    "coatings": ("name", ["price"]),
    "settings": ("id", ["usd", "background_file", "text_color"]),
}


def normalize_text_color(value):
    if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?", value.strip()):
        return value.strip().lower()
    return DEFAULT_TEXT_COLOR


def normalize_background_file(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_BACKGROUND_FILE

def get_conn():
    conn = sqlite3.connect(str(DB), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def build_database_backup(conn):
    backup = {}
    for table, (key_col, value_cols) in BACKUP_TABLES.items():
        columns = [key_col] + value_cols
        rows = conn.execute(
            f"SELECT {', '.join(columns)} FROM {table} ORDER BY {key_col}"
        ).fetchall()
        backup[table] = [dict(zip(columns, row)) for row in rows]
    return backup


def write_backup_file(backup):
    tmp_file = BACKUP_FILE.with_suffix(".tmp")
    with tmp_file.open("w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, BACKUP_FILE)


def backup_database(conn=None):
    close_conn = conn is None
    if conn is None:
        conn = get_conn()

    backup = build_database_backup(conn)
    write_backup_file(backup)

    if close_conn:
        conn.close()

    return backup


def apply_backup_data(conn, backup):
    if not isinstance(backup, dict):
        return False

    for table, (key_col, value_cols) in BACKUP_TABLES.items():
        rows = backup.get(table, [])
        if not isinstance(rows, list):
            continue

        for row in rows:
            if not isinstance(row, dict) or key_col not in row:
                continue

            columns = [key_col] + value_cols
            values = [row.get(col) for col in columns]
            placeholders = ", ".join(["?"] * len(columns))
            update_cols = ", ".join([f"{col}=excluded.{col}" for col in value_cols])
            conn.execute(
                f"""
                INSERT INTO {table} ({', '.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT({key_col}) DO UPDATE SET {update_cols}
                """,
                values,
            )

    conn.commit()
    return True


def restore_database_from_backup(conn):
    if not BACKUP_FILE.exists():
        return False

    try:
        with BACKUP_FILE.open("r", encoding="utf-8") as f:
            backup = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False

    return apply_backup_data(conn, backup)

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

    jeweler_type_aliases = {
        "platinum": "Платина",
        "premium": "Преміум",
        "premium_plus": "Преміум+",
    }
    for old_type, new_type in jeweler_type_aliases.items():
        existing = cur.execute("SELECT price FROM jeweler WHERE type=?", (old_type,)).fetchone()
        if existing:
            existing_new = cur.execute("SELECT price FROM jeweler WHERE type=?", (new_type,)).fetchone()
            if not existing_new:
                cur.execute("INSERT INTO jeweler(type, price) VALUES(?, ?)", (new_type, existing[0]))
            elif existing_new[0] == 0 and existing[0] != 0:
                cur.execute("UPDATE jeweler SET price=? WHERE type=?", (existing[0], new_type))
            cur.execute("DELETE FROM jeweler WHERE type=?", (old_type,))

    for t in JEWELER_TYPES:
        cur.execute("INSERT OR IGNORE INTO jeweler VALUES(?,0)", (t,))

    # USD rate
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        id INTEGER PRIMARY KEY,
        usd REAL DEFAULT 40,
        background_file TEXT DEFAULT 'full_white.png'
    )
    """)

    settings_cols = [row[1] for row in cur.execute("PRAGMA table_info(settings)")]
    if "background_file" not in settings_cols:
        cur.execute("ALTER TABLE settings ADD COLUMN background_file TEXT DEFAULT 'full_white.png'")
    if "text_color" not in settings_cols:
        cur.execute("ALTER TABLE settings ADD COLUMN text_color TEXT DEFAULT '#000000'")

    cur.execute(
        "INSERT OR IGNORE INTO settings(id, usd, background_file, text_color) VALUES(1,40,?,?)",
        (DEFAULT_BACKGROUND_FILE, DEFAULT_TEXT_COLOR),
    )
    current_background = cur.execute("SELECT background_file FROM settings WHERE id=1").fetchone()[0]
    normalized_background = normalize_background_file(current_background)
    if current_background != normalized_background:
        cur.execute("UPDATE settings SET background_file=? WHERE id=1", (normalized_background,))
    current_color = cur.execute("SELECT text_color FROM settings WHERE id=1").fetchone()[0]
    normalized_color = normalize_text_color(current_color)
    if current_color != normalized_color:
        cur.execute("UPDATE settings SET text_color=? WHERE id=1", (normalized_color,))

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
    restore_database_from_backup(conn)
    conn.close()
