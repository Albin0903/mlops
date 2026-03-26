import sqlite3
from pathlib import Path
from typing import List

DB_PATH = Path("data/tusmo_words.db")


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS words (
            word TEXT PRIMARY KEY,
            length INTEGER,
            start_letter TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_length ON words(length)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_start ON words(start_letter)")
    conn.commit()
    return conn


def import_txt_dictionary(txt_path: Path, db_path: Path) -> None:
    if not txt_path.exists():
        raise FileNotFoundError(f"{txt_path} not found")

    conn = init_db(db_path)
    records = []

    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Mots de") or line.startswith("Mots pour"):
                continue
            word = line.split()[0].lower()
            records.append((word, len(word), word[0]))

    conn.executemany("INSERT OR IGNORE INTO words (word, length, start_letter) VALUES (?, ?, ?)", records)
    conn.commit()
    conn.close()


class TusmoDictionary:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        if not self.db_path.exists():
            fallback_txt = Path("tusmo/mots.txt")
            if fallback_txt.exists():
                import_txt_dictionary(fallback_txt, self.db_path)

    def get_words(self, length: int, start_letter: str) -> List[str]:
        if not self.db_path.exists():
            return []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT word FROM words WHERE length = ? AND start_letter = ?", (length, start_letter.lower())
        )
        words = [row[0] for row in cursor.fetchall()]
        conn.close()
        return words


if __name__ == "__main__":
    txt_path = Path("tusmo/mots.txt")
    if txt_path.exists():
        print(f"Importing {txt_path} into {DB_PATH} ...")
        import_txt_dictionary(txt_path, DB_PATH)
        print("Import complete.")
