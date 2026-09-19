from fastapi import FastAPI
from .routers.usuarios import router as usuarios_router

app = FastAPI()
app.include_router(usuarios_router)
