import sqlite3


def get_connection():
    conexao = sqlite3.connect("financas.db")

    # Habilitando validação de Foreign Key
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao
