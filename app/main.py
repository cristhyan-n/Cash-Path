from fastapi import FastAPI
from .routers.usuarios import router as usuarios_router
from .routers.categorias import router as categorias_router
from .routers.transacoes import router as transacoes_router
from .routers.metas import router as metas_router
from .routers.perfil_financeiro import router as perfil_financeiro_router
from .routers.orcamentos import router as orcamentos_router
from .routers.projecoes import router as projecoes_router

app = FastAPI()
app.include_router(usuarios_router)
app.include_router(categorias_router)
app.include_router(transacoes_router)
app.include_router(metas_router)
app.include_router(perfil_financeiro_router)
app.include_router(orcamentos_router)
app.include_router(projecoes_router)
