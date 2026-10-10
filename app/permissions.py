from fastapi import Depends, HTTPException

from .database import get_db_connection
from .security import verify_jwt_token


def get_admin_usuario_id(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
) -> int:
    cursor = conexao.cursor()
    cursor.execute("SELECT role FROM usuario WHERE id = ?", (usuario_id,))
    linha = cursor.fetchone()

    if not linha or linha[0] != "admin":
        raise HTTPException(
            status_code=403, detail="Acesso restrito a administradores."
        )

    return usuario_id
