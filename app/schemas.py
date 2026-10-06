from pydantic import BaseModel


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
