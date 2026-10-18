import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db_connection
from ..schemas import (
    AlertaOrcamentoResponse,
    OrcamentoCreate,
    OrcamentoGrupoCreate,
    OrcamentoGruposCreate,
    OrcamentoGrupoResponse,
    OrcamentoResponse,
    OrcamentoSugestao,
)
from ..security import verify_jwt_token

router = APIRouter()

GRUPOS_ORCAMENTO = ("necessidade", "desejo", "economia")


@router.get("/orcamentos/grupos", response_model=List[OrcamentoGrupoResponse])
def listar_orcamentos_por_grupo(
    periodo: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    periodo_consulta = periodo or datetime.now().strftime("%Y-%m")
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT grupo, valor_limite FROM orcamento_grupo WHERE usuario_id = ?",
        (usuario_id,),
    )
    limites = {grupo: valor for grupo, valor in cursor.fetchall()}

    realizados = {grupo: 0 for grupo in GRUPOS_ORCAMENTO}
    cursor.execute(
        """
        SELECT c.grupo, COALESCE(SUM(t.valor), 0)
        FROM transacao t
        JOIN categoria c ON c.id = t.categoria_id
        WHERE t.usuario_id = ? AND t.tipo = 'despesa'
            AND substr(t.data, 1, 7) = ?
            AND c.grupo IN ('necessidade', 'desejo')
            AND c.ativa = 1
            AND (c.usuario_id IS NULL OR c.usuario_id = ?)
        GROUP BY c.grupo
        """,
        (usuario_id, periodo_consulta, usuario_id),
    )
    realizados.update(dict(cursor.fetchall()))
    cursor.execute(
        """SELECT COALESCE(SUM(CASE WHEN tipo = 'aporte' THEN valor ELSE -valor END), 0)
        FROM meta_movimento WHERE usuario_id = ? AND substr(data, 1, 7) = ?""",
        (usuario_id, periodo_consulta),
    )
    realizados["economia"] = cursor.fetchone()[0]

    return [
        OrcamentoGrupoResponse(
            grupo=grupo,
            valor_limite=limites.get(grupo, 0),
            valor_realizado=realizados[grupo],
        )
        for grupo in GRUPOS_ORCAMENTO
    ]


@router.put("/orcamentos/grupos", response_model=OrcamentoGrupoResponse)
def definir_orcamento_por_grupo(
    dados: OrcamentoGrupoCreate,
    periodo: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        """
        INSERT INTO orcamento_grupo (usuario_id, grupo, valor_limite)
        VALUES (?, ?, ?)
        ON CONFLICT(usuario_id, grupo)
        DO UPDATE SET valor_limite = excluded.valor_limite
        """,
        (usuario_id, dados.grupo, dados.valor_limite),
    )
    conexao.commit()
    resumo = listar_orcamentos_por_grupo(
        periodo=periodo,
        usuario_id=usuario_id,
        conexao=conexao,
    )
    return next(item for item in resumo if item.grupo == dados.grupo)


@router.put("/orcamentos/grupos/divisao", response_model=List[OrcamentoGrupoResponse])
def definir_divisao_orcamento_por_grupo(
    dados: OrcamentoGruposCreate,
    periodo: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    itens = dados.itens
    grupos_enviados = [item.grupo for item in itens]
    if len(itens) != len(GRUPOS_ORCAMENTO) or set(grupos_enviados) != set(GRUPOS_ORCAMENTO):
        raise HTTPException(
            status_code=422,
            detail="Informe exatamente um orçamento para cada um dos três grupos.",
        )

    with conexao:
        conexao.executemany(
            """
            INSERT INTO orcamento_grupo (usuario_id, grupo, valor_limite)
            VALUES (?, ?, ?)
            ON CONFLICT(usuario_id, grupo)
            DO UPDATE SET valor_limite = excluded.valor_limite
            """,
            [
                (usuario_id, item.grupo, item.valor_limite)
                for item in itens
            ],
        )

    return listar_orcamentos_por_grupo(
        periodo=periodo,
        usuario_id=usuario_id,
        conexao=conexao,
    )


@router.delete("/orcamentos/grupos")
def resetar_orcamentos_por_grupo(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute(
        "DELETE FROM orcamento_grupo WHERE usuario_id = ?",
        (usuario_id,),
    )
    conexao.commit()
    return {"removidos": cursor.rowcount}


@router.delete("/orcamentos/categorias")
def resetar_orcamentos_por_categoria(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM orcamento WHERE usuario_id = ?", (usuario_id,))
    conexao.commit()
    return {"removidos": cursor.rowcount}


@router.get("/orcamentos/sugestoes", response_model=List[OrcamentoSugestao])
def sugerir_orcamentos(
    renda_periodo: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    if renda_periodo:
        cursor.execute("SELECT valor_renda FROM perfil_financeiro WHERE usuario_id = ? AND renda_periodo = ?", (usuario_id, renda_periodo))
    else:
        cursor.execute("SELECT valor_renda FROM perfil_financeiro WHERE usuario_id = ? ORDER BY renda_periodo DESC LIMIT 1", (usuario_id,))
    renda = cursor.fetchone()
    if not renda:
        raise HTTPException(status_code=400, detail="Informe sua renda mensal antes de gerar sugestões.")
    cursor.execute("""SELECT id, nome, grupo FROM categoria
        WHERE ativa = 1 AND grupo IN ('necessidade', 'desejo', 'economia')
        AND (usuario_id IS NULL OR usuario_id = ?) ORDER BY grupo, id""", (usuario_id,))
    categorias = cursor.fetchall()
    grupos = {"necessidade": [], "desejo": [], "economia": []}
    for categoria in categorias:
        grupos[categoria[2]].append(categoria)
    if any(not grupo for grupo in grupos.values()):
        raise HTTPException(status_code=409, detail="É necessário manter ao menos uma categoria ativa em necessidades, desejos e economia.")
    renda_centavos = renda[0]
    hoje = datetime.now()
    primeiro_mes_atual = hoje.replace(day=1)
    primeiro_mes_tres_atras = primeiro_mes_atual
    for _ in range(3):
        primeiro_mes_tres_atras = (primeiro_mes_tres_atras - timedelta(days=1)).replace(day=1)
    cursor.execute(
        """SELECT t.categoria_id, COALESCE(SUM(t.valor), 0)
        FROM transacao t JOIN categoria c ON c.id = t.categoria_id
        WHERE t.usuario_id = ? AND t.tipo = 'despesa'
          AND t.data >= ? AND t.data < ? AND c.grupo IN ('necessidade', 'desejo')
          AND c.ativa = 1 AND (c.usuario_id IS NULL OR c.usuario_id = ?)
        GROUP BY t.categoria_id""",
        (usuario_id, primeiro_mes_tres_atras.strftime("%Y-%m-%d"), primeiro_mes_atual.strftime("%Y-%m-%d"), usuario_id),
    )
    gastos_historicos = {categoria_id: valor for categoria_id, valor in cursor.fetchall()}
    sugestoes = []
    for nome_grupo, percentual in (("necessidade", .50), ("desejo", .30), ("economia", .20)):
        grupo = grupos[nome_grupo]
        total = round(renda_centavos * percentual)
        pesos = [gastos_historicos.get(cat_id, 0) if nome_grupo != "economia" else 0 for cat_id, _, _ in grupo]
        soma_pesos = sum(pesos)
        # Combina 70% do histórico recente com 30% de uma divisão igual.
        # Sem histórico, mantém a divisão igual como ponto de partida.
        if soma_pesos:
            denominador = 10 * len(grupo) * soma_pesos
            numeradores = [3 * soma_pesos + 7 * len(grupo) * peso for peso in pesos]
            divisao = [divmod(total * numerador, denominador) for numerador in numeradores]
            valores = [inteiro for inteiro, _ in divisao]
            resto = total - sum(valores)
            ordem = sorted(range(len(grupo)), key=lambda i: divisao[i][1], reverse=True)
            for i in ordem[:resto]:
                valores[i] += 1
        else:
            base, resto = divmod(total, len(grupo))
            valores = [base + (1 if i < resto else 0) for i in range(len(grupo))]
        sugestoes.extend(
            OrcamentoSugestao(categoria_id=cat_id, categoria_nome=nome, grupo=nome_grupo,
                              valor_sugerido=valores[i])
            for i, (cat_id, nome, _) in enumerate(grupo)
        )
    return sugestoes


@router.post("/orcamentos", response_model=OrcamentoResponse)
def criar_ou_atualizar_orcamento(
    dados: OrcamentoCreate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute("""SELECT grupo FROM categoria WHERE id = ? AND ativa = 1
        AND (usuario_id IS NULL OR usuario_id = ?)""", (dados.categoria_id, usuario_id))
    categoria = cursor.fetchone()
    if not categoria or categoria[0] not in ("necessidade", "desejo", "economia"):
        raise HTTPException(status_code=404, detail="Categoria de orçamento não encontrada.")

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
        SELECT o.id, o.categoria_id, o.valor_limite, o.usuario_id
        FROM orcamento o
        JOIN categoria c ON c.id = o.categoria_id
        WHERE o.usuario_id = ? AND c.ativa = 1
            AND c.grupo IN ('necessidade', 'desejo', 'economia')
            AND (c.usuario_id IS NULL OR c.usuario_id = ?)
        """,
        (usuario_id, usuario_id),
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


def calcular_status_orcamento(
    valor_realizado: int, valor_limite: int, grupo: str = "necessidade"
) -> str:
    if grupo == "economia":
        if valor_realizado >= valor_limite:
            return "meta_alcancada"
        if valor_limite and valor_realizado / valor_limite >= LIMITE_ATENCAO / 100:
            return "atencao"
        return "ok"
    if valor_realizado > valor_limite:
        return "estourado"
    if valor_limite and (valor_realizado / valor_limite * 100) >= LIMITE_ATENCAO:
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
            c.grupo,
            CASE WHEN c.grupo = 'economia' THEN COALESCE((
                SELECT SUM(CASE WHEN mm.tipo = 'aporte' THEN mm.valor ELSE -mm.valor END)
                FROM meta m
                JOIN meta_movimento mm ON mm.meta_id = m.id AND mm.usuario_id = m.usuario_id
                WHERE m.categoria_id = c.id
                    AND m.usuario_id = o.usuario_id
                    AND substr(mm.data, 1, 7) = ?
            ), 0) ELSE COALESCE(SUM(t.valor), 0) END AS valor_realizado
        FROM orcamento o
        JOIN categoria c ON c.id = o.categoria_id
        LEFT JOIN transacao t
            ON t.categoria_id = o.categoria_id
            AND t.usuario_id = o.usuario_id
            AND t.tipo = 'despesa'
            AND substr(t.data, 1, 7) = ?
        WHERE o.usuario_id = ?
            AND c.ativa = 1
            AND c.grupo IN ('necessidade', 'desejo', 'economia')
            AND (c.usuario_id IS NULL OR c.usuario_id = o.usuario_id)
        GROUP BY o.id, c.grupo
        """,
        (periodo_consulta, periodo_consulta, usuario_id),
    )
    resultados = cursor.fetchall()

    alertas = []
    for categoria_id, categoria_nome, valor_limite, grupo, valor_realizado in resultados:
        percentual = (valor_realizado / valor_limite * 100) if valor_limite else 0.0
        alertas.append(
            AlertaOrcamentoResponse(
                categoria_id=categoria_id,
                categoria_nome=categoria_nome,
                grupo=grupo,
                valor_limite=valor_limite,
                valor_realizado=valor_realizado,
                percentual_utilizado=round(percentual, 2),
                status=calcular_status_orcamento(valor_realizado, valor_limite, grupo),
            )
        )
    return alertas
