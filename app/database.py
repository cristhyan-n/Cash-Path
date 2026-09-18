import sqlite3


def get_connection():
    conexao = sqlite3.connect("financas.db")

    # Habilitando validação de Foreign Key
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def get_db_connection():
    recurso = get_connection()
    try:
        yield recurso
    finally:
        recurso.close()
