import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db_connection
from ..permissions import get_admin_usuario_id
from ..schemas import CategoriaCreate, CategoriaFixaCreate, CategoriaResponse, CategoriaUpdate
from ..security import verify_jwt_token

router = APIRouter()


def _categoria(linha):
    return CategoriaResponse(
        id=linha[0],
        nome=linha[1],
        grupo=linha[2],
        ativa=bool(linha[3]),
        personalizada=linha[4] is not None,
    )


@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(
    usuario_id: int = Depends(verify_jwt_token), conexao=Depends(get_db_connection)
):
    cursor = conexao.cursor()
    cursor.execute(
        """SELECT id, nome, grupo, ativa, usuario_id FROM categoria
        WHERE ativa = 1 AND (usuario_id IS NULL OR usuario_id = ?) ORDER BY grupo, nome""",
        (usuario_id,),
    )
    return [_categoria(linha) for linha in cursor.fetchall()]


@router.get("/categorias/admin", response_model=List[CategoriaResponse])
def listar_categorias_fixadas(
    conexao=Depends(get_db_connection),
    usuario_id: int = Depends(get_admin_usuario_id),
):
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, nome, grupo, ativa, usuario_id FROM categoria WHERE usuario_id IS NULL ORDER BY grupo, nome"
    )
    return [_categoria(linha) for linha in cursor.fetchall()]


@router.get("/categorias/minhas", response_model=List[CategoriaResponse])
def listar_categorias_personalizadas(
    usuario_id: int = Depends(verify_jwt_token), conexao=Depends(get_db_connection)
):
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, nome, grupo, ativa, usuario_id FROM categoria WHERE usuario_id = ? ORDER BY ativa DESC, grupo, nome",
        (usuario_id,),
    )
    return [_categoria(linha) for linha in cursor.fetchall()]


@router.post("/categorias", response_model=CategoriaResponse)
def criar_categoria_personalizada(
    dados: CategoriaCreate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT 1 FROM categoria WHERE usuario_id = ? AND lower(nome) = lower(?)",
        (usuario_id, dados.nome.strip()),
    )
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Você já possui uma categoria com esse nome.")
    try:
        cursor.execute(
            "INSERT INTO categoria (nome, grupo, usuario_id) VALUES (?, ?, ?)",
            (dados.nome.strip(), dados.grupo, usuario_id),
        )
        conexao.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Não foi possível criar a categoria.")
    return CategoriaResponse(
        id=cursor.lastrowid,
        nome=dados.nome.strip(),
        grupo=dados.grupo,
        personalizada=True,
    )


@router.post("/categorias/fixas", response_model=CategoriaResponse)
def criar_categoria_fixa(
    dados: CategoriaFixaCreate,
    conexao=Depends(get_db_connection),
    usuario_id: int = Depends(get_admin_usuario_id),
):
    cursor = conexao.cursor()
    try:
        cursor.execute(
            "INSERT INTO categoria (nome, grupo) VALUES (?, ?)",
            (dados.nome.strip(), dados.grupo),
        )
        conexao.commit()
        return CategoriaResponse(
            id=cursor.lastrowid,
            nome=dados.nome.strip(),
            grupo=dados.grupo,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Categoria fixa já existe.")


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    dados: CategoriaUpdate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT usuario_id FROM categoria WHERE id = ?", (categoria_id,)
    )
    atual = cursor.fetchone()
    if not atual:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    if atual[0] is None:
        admin_id = get_admin_usuario_id(usuario_id, conexao)
        if admin_id != usuario_id:
            raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    elif atual[0] != usuario_id:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    elif dados.grupo == "receita":
        raise HTTPException(status_code=400, detail="Categorias pessoais devem pertencer a um grupo do orçamento.")
    try:
        cursor.execute(
            """UPDATE categoria SET nome = ?, grupo = ?, ativa = ? WHERE id = ?""",
            (dados.nome.strip(), dados.grupo, int(dados.ativa), categoria_id),
        )
        conexao.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Já existe uma categoria com esse nome.")
    cursor.execute(
        "SELECT id, nome, grupo, ativa, usuario_id FROM categoria WHERE id = ?",
        (categoria_id,),
    )
    return _categoria(cursor.fetchone())
