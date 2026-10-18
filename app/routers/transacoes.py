import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db_connection
from ..schemas import TransacaoCreate, TransacaoResponse
from ..security import verify_jwt_token

router = APIRouter()


@router.post("/transacoes", response_model=TransacaoResponse)
def criar_transacao(
    dados: TransacaoCreate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """SELECT grupo FROM categoria WHERE id = ? AND ativa = 1
        AND (usuario_id IS NULL OR usuario_id = ?)""",
        (dados.categoria_id, usuario_id),
    )
    categoria = cursor.fetchone()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    grupo = categoria[0]
    if dados.tipo == "despesa" and grupo not in ("necessidade", "desejo"):
        raise HTTPException(status_code=400, detail="Despesas só podem usar categorias de necessidades ou desejos.")
    if dados.tipo == "receita" and grupo != "receita":
        raise HTTPException(status_code=400, detail="Receitas devem usar uma categoria de renda.")
    try:
        cursor.execute(
            """
            INSERT INTO transacao (valor, data, tipo, descricao, usuario_id, categoria_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                dados.valor,
                dados.data,
                dados.tipo,
                dados.descricao,
                usuario_id,
                dados.categoria_id,
            ),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=404, detail="Categoria informada não existe.")

    return TransacaoResponse(
        id=novo_id,
        valor=dados.valor,
        data=dados.data,
        tipo=dados.tipo,
        descricao=dados.descricao,
        categoria_id=dados.categoria_id,
        usuario_id=usuario_id,
    )


@router.get("/transacoes", response_model=List[TransacaoResponse])
def listar_transacoes(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT id, valor, data, tipo, descricao, usuario_id, categoria_id
        FROM transacao
        WHERE usuario_id = ?
        """,
        (usuario_id,),
    )
    resultados = cursor.fetchall()

    return [
        TransacaoResponse(
            id=linha[0],
            valor=linha[1],
            data=linha[2],
            tipo=linha[3],
            descricao=linha[4],
            usuario_id=linha[5],
            categoria_id=linha[6],
        )
        for linha in resultados
    ]


@router.delete("/transacoes/{transacao_id}")
def excluir_transacao(
    transacao_id: int,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        "DELETE FROM transacao WHERE id = ? AND usuario_id = ?",
        (transacao_id, usuario_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Transação não encontrada.")
    conexao.commit()
    return {"removida": True}
