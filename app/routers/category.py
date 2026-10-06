import sqlite3
from fastapi import Depends, APIRouter, HTTPException
from ..security import verify_jwt_token
from ..schemas import CategoriaCreate, CategoriaResponse
from ..database import get_db_connection
from typing import List

router = APIRouter()


@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(conexao=Depends(get_db_connection)):
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome FROM categoria")
    resultados = cursor.fetchall()

    categorias = [CategoriaResponse(id=id, nome=nome) for id, nome in resultados]
    return categorias


@router.post("/categorias", response_model=CategoriaResponse)
def criar_categoria(
    dados: CategoriaCreate,
    conexao=Depends(get_db_connection),
    usuario_id: int = Depends(verify_jwt_token),
):
    cursor = conexao.cursor()
    try:
        cursor.execute("INSERT INTO categoria (nome) VALUES (?)", (dados.nome,))
        conexao.commit()
        novo_id = cursor.lastrowid
        return CategoriaResponse(id=novo_id, nome=dados.nome)
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail="Categoria já existe")
