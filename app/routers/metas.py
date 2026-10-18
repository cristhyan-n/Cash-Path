import math
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db_connection
from ..schemas import (
    MetaCreate,
    MetaUpdate,
    MetaMovimentoCreate,
    MetaMovimentoResponse,
    MetaProgressoResponse,
    MetaResponse,
)
from ..security import verify_jwt_token

router = APIRouter()


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Data inválida para {field_name}.")


def _saldo_meta(cursor, meta_id: int, usuario_id: int) -> int:
    cursor.execute(
        """SELECT COALESCE(SUM(CASE WHEN tipo = 'aporte' THEN valor ELSE -valor END), 0)
        FROM meta_movimento WHERE meta_id = ? AND usuario_id = ?""",
        (meta_id, usuario_id),
    )
    return cursor.fetchone()[0]


def _criar_resposta_progresso(
    meta_id: int,
    tipo: str,
    valor_alvo: int,
    data_alvo: str | None,
    valor_atual: int,
    hoje: date,
) -> MetaProgressoResponse:
    valor_restante = max(valor_alvo - valor_atual, 0)
    aporte_mensal = None
    if data_alvo:
        prazo = date.fromisoformat(data_alvo)
        if prazo >= hoje:
            meses = max(1, (prazo.year - hoje.year) * 12 + prazo.month - hoje.month + 1)
            aporte_mensal = math.ceil(valor_restante / meses)

    return MetaProgressoResponse(
        meta_id=meta_id,
        tipo=tipo,
        valor_alvo=valor_alvo,
        valor_atual=valor_atual,
        valor_restante=valor_restante,
        aporte_mensal_sugerido=aporte_mensal,
        percentual_concluido=round(valor_atual / valor_alvo * 100, 2) if valor_alvo else 0.0,
        status="concluido" if valor_atual >= valor_alvo else "ativo",
    )


def _validar_categoria_economia(cursor, categoria_id: int, usuario_id: int):
    cursor.execute(
        """SELECT id, nome FROM categoria
        WHERE id = ? AND grupo = 'economia' AND ativa = 1
            AND (usuario_id IS NULL OR usuario_id = ?)""",
        (categoria_id, usuario_id),
    )
    categoria = cursor.fetchone()
    if not categoria:
        raise HTTPException(
            status_code=422,
            detail="Escolha uma categoria ativa de Economia/Investimentos para a meta.",
        )
    return categoria


@router.post("/metas", response_model=MetaResponse)
def criar_meta(
    dados: MetaCreate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    data_inicio = _parse_date(dados.data_inicio, "início da meta")
    if data_inicio > date.today():
        raise HTTPException(status_code=422, detail="O início da meta não pode estar no futuro.")
    if dados.data_alvo:
        data_alvo = _parse_date(dados.data_alvo, "prazo da meta")
        if data_alvo < date.today():
            raise HTTPException(status_code=422, detail="O prazo da meta não pode estar no passado.")
        if data_alvo < data_inicio:
            raise HTTPException(status_code=422, detail="O prazo precisa ser posterior ao início da meta.")
    cursor = conexao.cursor()
    categoria = _validar_categoria_economia(
        cursor, dados.categoria_id, usuario_id
    )
    cursor.execute(
        """INSERT INTO meta
        (nome, tipo, categoria_id, valor_alvo, data_inicio, data_alvo, usuario_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (dados.nome.strip(), dados.tipo, dados.categoria_id, dados.valor_alvo,
         dados.data_inicio, dados.data_alvo, usuario_id),
    )
    conexao.commit()
    novo_id = cursor.lastrowid
    return MetaResponse(
        id=novo_id,
        nome=dados.nome.strip(),
        tipo=dados.tipo,
        categoria_id=categoria[0],
        categoria_nome=categoria[1],
        valor_alvo=dados.valor_alvo,
        data_inicio=dados.data_inicio,
        data_alvo=dados.data_alvo,
        status="ativo",
        usuario_id=usuario_id,
    )


@router.get("/metas", response_model=List[MetaResponse])
def listar_metas(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """SELECT m.id, m.nome, m.tipo, m.categoria_id, c.nome,
        m.valor_alvo, m.data_inicio, m.data_alvo, m.status, m.usuario_id
        FROM meta m JOIN categoria c ON c.id = m.categoria_id
        WHERE m.usuario_id = ? ORDER BY m.status, m.data_alvo, m.id DESC""",
        (usuario_id,),
    )
    return [
        MetaResponse(
            id=row[0], nome=row[1], tipo=row[2], categoria_id=row[3],
            categoria_nome=row[4], valor_alvo=row[5], data_inicio=row[6],
            data_alvo=row[7], status=row[8], usuario_id=row[9],
        )
        for row in cursor.fetchall()
    ]


@router.get("/metas/progresso", response_model=List[MetaProgressoResponse])
def listar_progresso_metas(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """SELECT m.id, m.tipo, m.valor_alvo, m.data_alvo,
        COALESCE(SUM(CASE WHEN mm.tipo = 'aporte' THEN mm.valor ELSE -mm.valor END), 0)
        FROM meta m LEFT JOIN meta_movimento mm
          ON mm.meta_id = m.id AND mm.usuario_id = m.usuario_id
        WHERE m.usuario_id = ? GROUP BY m.id ORDER BY m.id""",
        (usuario_id,),
    )
    hoje = date.today()
    return [
        _criar_resposta_progresso(
            meta_id, tipo, valor_alvo, data_alvo, valor_atual, hoje
        )
        for meta_id, tipo, valor_alvo, data_alvo, valor_atual in cursor.fetchall()
    ]


@router.put("/metas/{meta_id}", response_model=MetaResponse)
def atualizar_meta(
    meta_id: int,
    dados: MetaUpdate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT data_inicio FROM meta WHERE id = ? AND usuario_id = ?",
        (meta_id, usuario_id),
    )
    meta = cursor.fetchone()
    if not meta:
        raise HTTPException(status_code=404, detail="Meta não encontrada.")
    categoria = _validar_categoria_economia(
        cursor, dados.categoria_id, usuario_id
    )
    data_alvo = None
    if dados.data_alvo:
        data_alvo = _parse_date(dados.data_alvo, "prazo da meta")
        if data_alvo < date.fromisoformat(meta[0]):
            raise HTTPException(status_code=422, detail="O prazo não pode ser anterior ao início da meta.")
    saldo = _saldo_meta(cursor, meta_id, usuario_id)
    cursor.execute(
        "UPDATE meta SET nome = ?, categoria_id = ?, valor_alvo = ?, data_alvo = ?, status = ? WHERE id = ? AND usuario_id = ?",
        (dados.nome.strip(), dados.categoria_id, dados.valor_alvo, dados.data_alvo,
         "concluido" if saldo >= dados.valor_alvo else "ativo", meta_id, usuario_id),
    )
    conexao.commit()
    cursor.execute(
        """SELECT m.id, m.nome, m.tipo, m.categoria_id, c.nome,
        m.valor_alvo, m.data_inicio, m.data_alvo, m.status, m.usuario_id
        FROM meta m JOIN categoria c ON c.id = m.categoria_id
        WHERE m.id = ? AND m.usuario_id = ?""",
        (meta_id, usuario_id),
    )
    row = cursor.fetchone()
    return MetaResponse(
        id=row[0], nome=row[1], tipo=row[2], categoria_id=row[3],
        categoria_nome=row[4], valor_alvo=row[5], data_inicio=row[6],
        data_alvo=row[7], status=row[8], usuario_id=row[9],
    )


@router.delete("/metas/{meta_id}")
def excluir_meta(
    meta_id: int,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM meta WHERE id = ? AND usuario_id = ?", (meta_id, usuario_id))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Meta não encontrada.")
    conexao.commit()
    return {"removida": True}


@router.get("/metas/{meta_id}/progresso", response_model=MetaProgressoResponse)
def obter_progresso_meta(
    meta_id: int,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT tipo, valor_alvo, data_alvo FROM meta WHERE id = ? AND usuario_id = ?",
        (meta_id, usuario_id),
    )
    meta = cursor.fetchone()
    if not meta:
        raise HTTPException(status_code=404, detail="Meta não encontrada.")

    tipo, valor_alvo, data_alvo = meta
    valor_atual = _saldo_meta(cursor, meta_id, usuario_id)
    return _criar_resposta_progresso(
        meta_id, tipo, valor_alvo, data_alvo, valor_atual, date.today()
    )


@router.post("/metas/{meta_id}/movimentos", response_model=MetaMovimentoResponse)
def registrar_movimento_meta(
    meta_id: int,
    dados: MetaMovimentoCreate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    data_movimento = _parse_date(dados.data, "movimentação")
    if data_movimento > date.today():
        raise HTTPException(status_code=422, detail="A data do movimento não pode estar no futuro.")
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT valor_alvo, data_inicio FROM meta WHERE id = ? AND usuario_id = ?",
        (meta_id, usuario_id),
    )
    meta = cursor.fetchone()
    if not meta:
        raise HTTPException(status_code=404, detail="Meta não encontrada.")
    if data_movimento < date.fromisoformat(meta[1]):
        raise HTTPException(
            status_code=400,
            detail="A movimentação não pode ser anterior ao início da meta.",
        )

    if dados.tipo == "retirada" and dados.valor > _saldo_meta(cursor, meta_id, usuario_id):
        raise HTTPException(
            status_code=400,
            detail="A retirada não pode ser maior que o valor acumulado nesta meta.",
        )

    cursor.execute(
        """INSERT INTO meta_movimento (meta_id, usuario_id, tipo, valor, data)
        VALUES (?, ?, ?, ?, ?)""",
        (meta_id, usuario_id, dados.tipo, dados.valor, dados.data),
    )
    movimento_id = cursor.lastrowid
    saldo = _saldo_meta(cursor, meta_id, usuario_id)
    cursor.execute(
        "UPDATE meta SET status = ? WHERE id = ? AND usuario_id = ?",
        ("concluido" if saldo >= meta[0] else "ativo", meta_id, usuario_id),
    )
    conexao.commit()
    return MetaMovimentoResponse(
        id=movimento_id,
        meta_id=meta_id,
        tipo=dados.tipo,
        valor=dados.valor,
        data=dados.data,
    )


@router.get("/metas/{meta_id}/movimentos", response_model=List[MetaMovimentoResponse])
def listar_movimentos_meta(
    meta_id: int,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute("SELECT 1 FROM meta WHERE id = ? AND usuario_id = ?", (meta_id, usuario_id))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Meta não encontrada.")
    cursor.execute(
        """SELECT id, meta_id, tipo, valor, data FROM meta_movimento
        WHERE meta_id = ? AND usuario_id = ? ORDER BY data DESC, id DESC""",
        (meta_id, usuario_id),
    )
    return [
        MetaMovimentoResponse(
            id=row[0], meta_id=row[1], tipo=row[2], valor=row[3], data=row[4]
        )
        for row in cursor.fetchall()
    ]


@router.delete("/metas/{meta_id}/movimentos/{movimento_id}")
def excluir_movimento_meta(
    meta_id: int,
    movimento_id: int,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        "DELETE FROM meta_movimento WHERE id = ? AND meta_id = ? AND usuario_id = ?",
        (movimento_id, meta_id, usuario_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada.")
    saldo = _saldo_meta(cursor, meta_id, usuario_id)
    cursor.execute(
        "SELECT valor_alvo FROM meta WHERE id = ? AND usuario_id = ?",
        (meta_id, usuario_id),
    )
    meta = cursor.fetchone()
    if meta:
        cursor.execute(
            "UPDATE meta SET status = ? WHERE id = ? AND usuario_id = ?",
            ("concluido" if saldo >= meta[0] else "ativo", meta_id, usuario_id),
        )
    conexao.commit()
    return {"removida": True}
