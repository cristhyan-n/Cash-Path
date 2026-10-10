from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db_connection
from ..schemas import MetaCreate, MetaProgressoResponse, MetaResponse
from ..security import verify_jwt_token

router = APIRouter()


@router.post("/metas", response_model=MetaResponse)
def criar_meta(
    dados: MetaCreate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """
        INSERT INTO meta (tipo, valor_alvo, data_inicio, usuario_id)
        VALUES (?, ?, ?, ?)
        """,
        (dados.tipo, dados.valor_alvo, dados.data_inicio, usuario_id),
    )
    conexao.commit()
    novo_id = cursor.lastrowid

    cursor.execute("SELECT status FROM meta WHERE id = ?", (novo_id,))
    status_atual = cursor.fetchone()[0]

    return MetaResponse(
        id=novo_id,
        tipo=dados.tipo,
        valor_alvo=dados.valor_alvo,
        data_inicio=dados.data_inicio,
        status=status_atual,
        usuario_id=usuario_id,
    )


@router.get("/metas", response_model=List[MetaResponse])
def listar_metas(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT id, tipo, valor_alvo, data_inicio, status, usuario_id
        FROM meta
        WHERE usuario_id = ?
        """,
        (usuario_id,),
    )
    resultados = cursor.fetchall()

    return [
        MetaResponse(
            id=linha[0],
            tipo=linha[1],
            valor_alvo=linha[2],
            data_inicio=linha[3],
            status=linha[4],
            usuario_id=linha[5],
        )
        for linha in resultados
    ]


@router.get("/metas/{meta_id}/progresso", response_model=MetaProgressoResponse)
def obter_progresso_meta(
    meta_id: int,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT tipo, valor_alvo, data_inicio, status
        FROM meta
        WHERE id = ? AND usuario_id = ?
        """,
        (meta_id, usuario_id),
    )
    meta_encontrada = cursor.fetchone()

    if not meta_encontrada:
        raise HTTPException(status_code=404, detail="Meta não encontrada.")

    tipo, valor_alvo, data_inicio, status_atual = meta_encontrada

    cursor.execute(
        """
        SELECT COALESCE(SUM(
            CASE WHEN tipo = 'receita' THEN valor ELSE -valor END
        ), 0)
        FROM transacao
        WHERE usuario_id = ? AND data >= ?
        """,
        (usuario_id, data_inicio),
    )
    valor_atual = cursor.fetchone()[0]

    percentual = (max(valor_atual, 0) / valor_alvo * 100) if valor_alvo else 0.0

    return MetaProgressoResponse(
        meta_id=meta_id,
        tipo=tipo,
        valor_alvo=valor_alvo,
        valor_atual=valor_atual,
        percentual_concluido=round(percentual, 2),
        status=status_atual,
    )
