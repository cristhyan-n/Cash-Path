from pydantic import BaseModel
from typing import Literal


class CadastroUsuario(BaseModel):
    nome: str
    email: str
    senha: str


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str

    class Config:
        from_attributes = True


class UsuarioLogin(BaseModel):
    email: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CategoriaResponse(BaseModel):
    id: int
    nome: str

    class Config:
        from_attributes = True


class CategoriaCreate(BaseModel):
    nome: str


class TransacaoCreate(BaseModel):
    valor: int
    data: str
    tipo: Literal["receita", "despesa"]
    categoria_id: int


class TransacaoResponse(BaseModel):
    id: int
    valor: int
    data: str
    tipo: str
    categoria_id: int
    usuario_id: int

    class Config:
        from_attributes = True


class MetaCreate(BaseModel):
    tipo: Literal["economizar", "investir"]
    valor_alvo: int
    data_inicio: str


class MetaResponse(BaseModel):
    id: int
    tipo: str
    valor_alvo: int
    data_inicio: str
    status: str
    usuario_id: int

    class Config:
        from_attributes = True


class PerfilFinanceiroCreate(BaseModel):
    valor_renda: int
    renda_periodo: str


class PerfilFinanceiroResponse(BaseModel):
    id: int
    valor_renda: int
    renda_periodo: str
    usuario_id: int

    class Config:
        from_attributes = True


class OrcamentoCreate(BaseModel):
    categoria_id: int
    valor_limite: int


class OrcamentoResponse(BaseModel):
    id: int
    categoria_id: int
    valor_limite: int
    usuario_id: int

    class Config:
        from_attributes = True
