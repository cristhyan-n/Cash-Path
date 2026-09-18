from fastapi import FastAPI  # type: ignore[import-not-found]

app = FastAPI()


@app.get("/")
def nome_da_funcao():
    return {"mensagem": "algo aqui"}
