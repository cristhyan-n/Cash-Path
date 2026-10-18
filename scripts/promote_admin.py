"""Promove uma conta existente a administradora do CashPath."""

import sqlite3
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/promote_admin.py email@exemplo.com")
        return 2
    email = sys.argv[1].strip().lower()
    db_path = Path(__file__).resolve().parents[1] / "financas.db"
    with sqlite3.connect(db_path) as conexao:
        cursor = conexao.execute(
            "UPDATE usuario SET role = 'admin' WHERE lower(email) = ?", (email,)
        )
        if cursor.rowcount == 0:
            print("Conta não encontrada. Cadastre-a primeiro no aplicativo.")
            return 1
    print(f"{email} agora é administradora do sistema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
