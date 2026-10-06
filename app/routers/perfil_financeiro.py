import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db_connection
from ..schemas import PerfilFinanceiroCreate, PerfilFinanceiroResponse
from ..security import verify_jwt_token

router = APIRouter()


@router.post("/perfil-financeiro", response_model=PerfilFinanceiroResponse)
def criar_perfil_financeiro(
    dados: PerfilFinanceiroCreate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO perfil_financeiro (valor_renda, renda_periodo, usuario_id)
            VALUES (?, ?, ?)
            """,
            (dados.valor_renda, dados.renda_periodo, usuario_id),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Renda já informada para esse período.",
        )

    return PerfilFinanceiroResponse(
        id=novo_id,
        valor_renda=dados.valor_renda,
        renda_periodo=dados.renda_periodo,
        usuario_id=usuario_id,
    )


@router.get("/perfil-financeiro", response_model=List[PerfilFinanceiroResponse])
def listar_perfil_financeiro(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT id, valor_renda, renda_periodo, usuario_id
        FROM perfil_financeiro
        WHERE usuario_id = ?
        """,
        (usuario_id,),
    )
    resultados = cursor.fetchall()

    return [
        PerfilFinanceiroResponse(
            id=linha[0],
            valor_renda=linha[1],
            renda_periodo=linha[2],
            usuario_id=linha[3],
        )
        for linha in resultados
    ]
