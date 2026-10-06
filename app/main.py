from fastapi import FastAPI
from .routers.usuarios import router as usuarios_router
from .routers.categorias import router as categorias_router
from .routers.transacoes import router as transacoes_router

app = FastAPI()
app.include_router(usuarios_router)
app.include_router(categorias_router)
app.include_router(transacoes_router)
