import sqlite3
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db_connection
from ..schemas import AlertaOrcamentoResponse, OrcamentoCreate, OrcamentoResponse
from ..security import verify_jwt_token

router = APIRouter()


@router.post("/orcamentos", response_model=OrcamentoResponse)
def criar_ou_atualizar_orcamento(
    dados: OrcamentoCreate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO orcamento (usuario_id, categoria_id, valor_limite)
            VALUES (?, ?, ?)
            """,
            (usuario_id, dados.categoria_id, dados.valor_limite),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
    except sqlite3.IntegrityError as erro:
        mensagem_erro = str(erro)

        if "UNIQUE" in mensagem_erro:
            # já existe orçamento pra essa combinação usuário+categoria: atualiza o valor vigente
            cursor.execute(
                """
                UPDATE orcamento
                SET valor_limite = ?
                WHERE usuario_id = ? AND categoria_id = ?
                """,
                (dados.valor_limite, usuario_id, dados.categoria_id),
            )
            conexao.commit()

            cursor.execute(
                "SELECT id FROM orcamento WHERE usuario_id = ? AND categoria_id = ?",
                (usuario_id, dados.categoria_id),
            )
            novo_id = cursor.fetchone()[0]
        elif "FOREIGN KEY" in mensagem_erro:
            raise HTTPException(
                status_code=404, detail="Categoria informada não existe."
            )
        else:
            raise

    return OrcamentoResponse(
        id=novo_id,
        categoria_id=dados.categoria_id,
        valor_limite=dados.valor_limite,
        usuario_id=usuario_id,
    )


@router.get("/orcamentos", response_model=List[OrcamentoResponse])
def listar_orcamentos(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT id, categoria_id, valor_limite, usuario_id
        FROM orcamento
        WHERE usuario_id = ?
        """,
        (usuario_id,),
    )
    resultados = cursor.fetchall()

    return [
        OrcamentoResponse(
            id=linha[0],
            categoria_id=linha[1],
            valor_limite=linha[2],
            usuario_id=linha[3],
        )
        for linha in resultados
    ]


LIMITE_ATENCAO = 80.0


def calcular_status_orcamento(valor_gasto: int, valor_limite: int) -> str:
    if valor_gasto > valor_limite:
        return "estourado"
    if valor_limite and (valor_gasto / valor_limite * 100) >= LIMITE_ATENCAO:
        return "atencao"
    return "ok"


@router.get("/orcamentos/alertas", response_model=List[AlertaOrcamentoResponse])
def listar_alertas_orcamento(
    periodo: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    periodo_consulta = periodo or datetime.now().strftime("%Y-%m")

    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT
            o.categoria_id,
            c.nome,
            o.valor_limite,
            COALESCE(SUM(t.valor), 0) AS valor_gasto
        FROM orcamento o
        JOIN categoria c ON c.id = o.categoria_id
        LEFT JOIN transacao t
            ON t.categoria_id = o.categoria_id
            AND t.usuario_id = o.usuario_id
            AND t.tipo = 'despesa'
            AND substr(t.data, 1, 7) = ?
        WHERE o.usuario_id = ?
        GROUP BY o.id
        """,
        (periodo_consulta, usuario_id),
    )
    resultados = cursor.fetchall()

    alertas = []
    for categoria_id, categoria_nome, valor_limite, valor_gasto in resultados:
        percentual = (valor_gasto / valor_limite * 100) if valor_limite else 0.0
        alertas.append(
            AlertaOrcamentoResponse(
                categoria_id=categoria_id,
                categoria_nome=categoria_nome,
                valor_limite=valor_limite,
                valor_gasto=valor_gasto,
                percentual_utilizado=round(percentual, 2),
                status=calcular_status_orcamento(valor_gasto, valor_limite),
            )
        )
    return alertas
