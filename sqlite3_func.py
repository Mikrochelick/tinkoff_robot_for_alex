import sqlite3 as sq


def create_base():
    with sq.connect('Bot_Base.db') as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
        figi TEXT,
        name TEXT,
        cv REAL,
        cn REAL,
        cd REAL,
        cv_lus REAL,
        cn_plus REAL,
        mode INTEGER,
        count INTEGER,
        cmax INTEGER,
        nmax INTEGER,
        kmax INTEGER,
        qmin INTEGER,
        lmax INTEGER,
        g INTEGER,
        count_buy INTEGER
        )
        """)

def install_config():
    pass