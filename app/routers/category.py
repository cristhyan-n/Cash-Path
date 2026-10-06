from fastapi import Depends, APIRouter
from ..schemas import CategoriaResponse
from ..database import get_db_connection
from typing import List

router = APIRouter()


@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(conexao=Depends(get_db_connection)):
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome FROM categoria")
    resultados = cursor.fetchall()

    categorias = [CategoriaResponse(id=id, nome=nome) for id, nome in resultados]
    return categorias
