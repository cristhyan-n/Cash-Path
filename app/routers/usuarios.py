import sqlite3

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from ..security import hash_password
from ..database import get_db_connection
from ..schemas import CadastroUsuario, UsuarioResponse  # type: ignore[import-not-found]

router = APIRouter()


@router.post("/usuarios", response_model=UsuarioResponse)
def criar_usuario(dados_usuario: CadastroUsuario, conexao=Depends(get_db_connection)):
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "INSERT INTO usuario (nome, email, senha) VALUES (?, ?, ?)",
            (
                dados_usuario.nome,
                dados_usuario.email,
                hash_password(dados_usuario.senha),
            ),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email já cadastrado.")

    return {"id": novo_id, "nome": dados_usuario.nome, "email": dados_usuario.email}
