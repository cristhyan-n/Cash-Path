import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db_connection
from ..schemas import OrcamentoCreate, OrcamentoResponse
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
