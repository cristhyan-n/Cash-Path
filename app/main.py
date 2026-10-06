from fastapi import FastAPI
from .routers.usuarios import router as usuarios_router
from .routers.category import router as categorias_router

app = FastAPI()
app.include_router(usuarios_router)
app.include_router(categorias_router)
