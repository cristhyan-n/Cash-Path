from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class CadastroUsuario(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    senha: str = Field(min_length=8, max_length=128)


class UsuarioUpdate(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    senha_atual: Optional[str] = None
    nova_senha: Optional[str] = Field(default=None, min_length=8, max_length=128)


class SolicitarRecuperacao(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RedefinirSenha(BaseModel):
    token: str = Field(pattern=r"^\d{6}$")
    nova_senha: str = Field(min_length=8, max_length=128)
    confirmar_senha: str = Field(min_length=8, max_length=128)


class ConfirmarEmail(BaseModel):
    token: str = Field(pattern=r"^\d{6}$")


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    role: str = "usuario"
    provider: Literal["local", "google"] = "local"

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
    grupo: Literal["necessidade", "desejo", "economia", "receita"]
    ativa: bool = True
    personalizada: bool = False

    class Config:
        from_attributes = True


class CategoriaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=80)
    grupo: Literal["necessidade", "desejo", "economia"]


class CategoriaFixaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=80)
    grupo: Literal["necessidade", "desejo", "economia", "receita"]


class CategoriaUpdate(BaseModel):
    nome: str = Field(min_length=2, max_length=80)
    grupo: Literal["necessidade", "desejo", "economia", "receita"]
    ativa: bool


class TransacaoCreate(BaseModel):
    valor: int = Field(gt=0)
    data: str
    tipo: Literal["receita", "despesa"]
    descricao: Optional[str] = Field(default=None, max_length=100)
    categoria_id: int


class TransacaoResponse(BaseModel):
    id: int
    valor: int
    data: str
    tipo: str
    descricao: Optional[str] = None
    categoria_id: int
    usuario_id: int

    class Config:
        from_attributes = True


class MetaCreate(BaseModel):
    nome: str = Field(default="Minha meta", min_length=2, max_length=100)
    tipo: Literal["economizar", "investir"]
    categoria_id: int
    valor_alvo: int = Field(gt=0)
    data_inicio: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    data_alvo: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class MetaUpdate(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    categoria_id: int
    valor_alvo: int = Field(gt=0)
    data_alvo: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class MetaMovimentoCreate(BaseModel):
    tipo: Literal["aporte", "retirada"]
    valor: int = Field(gt=0)
    data: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class MetaMovimentoResponse(BaseModel):
    id: int
    meta_id: int
    tipo: Literal["aporte", "retirada"]
    valor: int
    data: str


class MetaResponse(BaseModel):
    id: int
    nome: str = "Minha meta"
    tipo: str
    categoria_id: int
    categoria_nome: str
    valor_alvo: int
    data_inicio: str
    data_alvo: Optional[str] = None
    status: str
    usuario_id: int

    class Config:
        from_attributes = True


class PerfilFinanceiroCreate(BaseModel):
    valor_renda: int = Field(gt=0)
    renda_periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    objetivo: Literal["economizar", "investir"] = "economizar"


class PerfilFinanceiroResponse(BaseModel):
    id: int
    valor_renda: int
    renda_periodo: str
    usuario_id: int
    objetivo: str = "economizar"


class OrcamentoSugestao(BaseModel):
    categoria_id: int
    categoria_nome: str
    grupo: Literal["necessidade", "desejo", "economia"]
    valor_sugerido: int

    class Config:
        from_attributes = True


class OrcamentoCreate(BaseModel):
    categoria_id: int
    valor_limite: int = Field(gt=0)


class OrcamentoGrupoCreate(BaseModel):
    grupo: Literal["necessidade", "desejo", "economia"]
    valor_limite: int = Field(gt=0)


class OrcamentoGruposCreate(BaseModel):
    itens: List[OrcamentoGrupoCreate]


class OrcamentoGrupoResponse(BaseModel):
    grupo: Literal["necessidade", "desejo", "economia"]
    valor_limite: int
    valor_realizado: int


class OrcamentoResponse(BaseModel):
    id: int
    categoria_id: int
    valor_limite: int
    usuario_id: int

    class Config:
        from_attributes = True


class MetaProgressoResponse(BaseModel):
    meta_id: int
    tipo: str
    valor_alvo: int
    valor_atual: int
    valor_restante: int
    aporte_mensal_sugerido: Optional[int] = None
    percentual_concluido: float
    status: str


class AlertaOrcamentoResponse(BaseModel):
    categoria_id: int
    categoria_nome: str
    grupo: Literal["necessidade", "desejo", "economia"]
    valor_limite: int
    valor_realizado: int
    percentual_utilizado: float
    status: Literal["ok", "atencao", "estourado", "meta_alcancada"]


class ProjecaoResponse(BaseModel):
    meses_considerados: int
    fonte_renda: Literal["perfil_financeiro", "media_receitas"]
    renda_base: int
    media_despesas_mensais: int
    saldo_projetado: int
    valor_meta_sugerido: int


class GoogleLogin(BaseModel):
    id_token: str
