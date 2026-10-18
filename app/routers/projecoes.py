from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db_connection
from ..schemas import ProjecaoResponse
from ..security import verify_jwt_token

router = APIRouter()

PERCENTUAL_POUPANCA = 0.20


def calcular_valor_meta_sugerido(renda_base: int, saldo_projetado: int) -> int:
    teto_pela_renda = renda_base * PERCENTUAL_POUPANCA
    return int(min(teto_pela_renda, max(saldo_projetado, 0)))


@router.get("/projecao", response_model=ProjecaoResponse)
def obter_projecao(
    meses: int = Query(default=3, ge=1, le=12),
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    mes_atual = datetime.now().strftime("%Y-%m")
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            substr(data, 1, 7) AS mes,
            SUM(CASE WHEN tipo = 'receita' THEN valor ELSE 0 END),
            SUM(CASE WHEN tipo = 'despesa' THEN valor ELSE 0 END)
        FROM transacao
        WHERE usuario_id = ? AND substr(data, 1, 7) < ?
        GROUP BY mes
        ORDER BY mes DESC
        LIMIT ?
        """,
        (usuario_id, mes_atual, meses),
    )
    historico = cursor.fetchall()

    if not historico:
        raise HTTPException(
            status_code=400,
            detail="Histórico insuficiente: registre transações de ao menos um mês anterior.",
        )

    meses_considerados = len(historico)
    media_receitas = sum(linha[1] for linha in historico) / meses_considerados
    media_despesas = round(sum(linha[2] for linha in historico) / meses_considerados)

    cursor.execute(
        """
        SELECT valor_renda
        FROM perfil_financeiro
        WHERE usuario_id = ?
        ORDER BY renda_periodo DESC
        LIMIT 1
        """,
        (usuario_id,),
    )
    perfil_recente = cursor.fetchone()

    if perfil_recente:
        renda_base = perfil_recente[0]
        fonte_renda = "perfil_financeiro"
    else:
        renda_base = round(media_receitas)
        fonte_renda = "media_receitas"

    saldo_projetado = renda_base - media_despesas

    return ProjecaoResponse(
        meses_considerados=meses_considerados,
        fonte_renda=fonte_renda,
        renda_base=renda_base,
        media_despesas_mensais=media_despesas,
        saldo_projetado=saldo_projetado,
        valor_meta_sugerido=calcular_valor_meta_sugerido(renda_base, saldo_projetado),
    )
