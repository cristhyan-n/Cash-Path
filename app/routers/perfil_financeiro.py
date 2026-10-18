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
            INSERT INTO perfil_financeiro (valor_renda, renda_periodo, usuario_id, objetivo)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(usuario_id, renda_periodo) DO UPDATE SET
                valor_renda = excluded.valor_renda, objetivo = excluded.objetivo
            """,
            (dados.valor_renda, dados.renda_periodo, usuario_id, dados.objetivo),
        )
        conexao.commit()
        cursor.execute("SELECT id FROM perfil_financeiro WHERE usuario_id = ? AND renda_periodo = ?", (usuario_id, dados.renda_periodo))
        novo_id = cursor.fetchone()[0]
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
        objetivo=dados.objetivo,
    )


@router.get("/perfil-financeiro", response_model=List[PerfilFinanceiroResponse])
def listar_perfil_financeiro(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT id, valor_renda, renda_periodo, usuario_id, objetivo
        FROM perfil_financeiro
        WHERE usuario_id = ?
        ORDER BY renda_periodo
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
            objetivo=linha[4],
        )
        for linha in resultados
    ]


@router.delete("/perfil-financeiro/dados")
def resetar_dados_financeiros(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    """Limpa os dados financeiros sem remover a conta nem invalidar o login."""
    with conexao:
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM transacao WHERE usuario_id = ?", (usuario_id,))
        cursor.execute("DELETE FROM meta WHERE usuario_id = ?", (usuario_id,))
        cursor.execute("DELETE FROM orcamento WHERE usuario_id = ?", (usuario_id,))
        cursor.execute("DELETE FROM orcamento_grupo WHERE usuario_id = ?", (usuario_id,))
        cursor.execute("DELETE FROM perfil_financeiro WHERE usuario_id = ?", (usuario_id,))
        cursor.execute("DELETE FROM categoria WHERE usuario_id = ?", (usuario_id,))
    return {"message": "Dados financeiros removidos. A conta permanece ativa."}
