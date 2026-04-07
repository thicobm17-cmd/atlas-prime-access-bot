import sqlite3
from contextlib import closing

DB_NAME = "atlas_prime.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT,
                    telefone TEXT,
                    email TEXT UNIQUE,
                    telegram_id INTEGER,
                    plano TEXT,
                    ciclo TEXT,
                    origem TEXT,
                    regiao TEXT,
                    status TEXT,
                    validacao_documental TEXT,
                    data_compra TEXT,
                    ultimo_pagamento TEXT,
                    vigencia_ate TEXT,
                    data_liberacao TEXT,
                    observacoes TEXT
                )
            """)


def add_or_update_cliente(
    nome,
    telefone,
    email,
    plano,
    ciclo,
    status,
    data_compra,
    ultimo_pagamento,
    vigencia_ate,
    origem=None,
    regiao=None,
    telegram_id=None,
    validacao_documental=None,
    data_liberacao=None,
    observacoes=None
):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("""
                INSERT INTO clientes (
                    nome, telefone, email, telegram_id, plano, ciclo, origem, regiao,
                    status, validacao_documental, data_compra, ultimo_pagamento,
                    vigencia_ate, data_liberacao, observacoes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    nome=excluded.nome,
                    telefone=excluded.telefone,
                    plano=excluded.plano,
                    ciclo=excluded.ciclo,
                    origem=excluded.origem,
                    regiao=excluded.regiao,
                    status=excluded.status,
                    validacao_documental=excluded.validacao_documental,
                    data_compra=excluded.data_compra,
                    ultimo_pagamento=excluded.ultimo_pagamento,
                    vigencia_ate=excluded.vigencia_ate,
                    data_liberacao=excluded.data_liberacao,
                    observacoes=excluded.observacoes
            """, (
                nome, telefone, email.lower(), telegram_id, plano, ciclo, origem, regiao,
                status, validacao_documental, data_compra, ultimo_pagamento,
                vigencia_ate, data_liberacao, observacoes
            ))


def get_cliente_by_email(email):
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM clientes WHERE email = ?",
            (email.lower(),)
        )
        return cur.fetchone()


def get_cliente_by_telegram_id(telegram_id):
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM clientes WHERE telegram_id = ?",
            (telegram_id,)
        )
        return cur.fetchone()


def update_cliente_field(email, field, value):
    allowed_fields = {
        "nome", "telefone", "telegram_id", "plano", "ciclo", "origem", "regiao",
        "status", "validacao_documental", "data_compra", "ultimo_pagamento",
        "vigencia_ate", "data_liberacao", "observacoes"
    }

    if field not in allowed_fields:
        raise ValueError(f"Campo não permitido: {field}")

    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                f"UPDATE clientes SET {field} = ? WHERE email = ?",
                (value, email.lower())
            )


def list_clientes():
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM clientes")
        return cur.fetchall()