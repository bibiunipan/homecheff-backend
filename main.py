from fastapi import FastAPI, Query, HTTPException
from typing import List, Optional
import json
import os

app = FastAPI()

# Caminho do arquivo JSON com as receitas (ajuste se precisar)
ARQUIVO_RECEITAS = os.path.join(os.path.dirname(__file__), 'receitas.json')

# Carregar o JSON com as receitas na inicialização da API
with open(ARQUIVO_RECEITAS, 'r', encoding='utf-8') as f:
    receitas = json.load(f)

@app.get("/")
def raiz():
    return {"mensagem": "API Home Cheff funcionando!"}

@app.get("/receitas")
def buscar_receitas(
    nome: Optional[str] = Query(None, description="Nome (ou parte) da receita"),
    ingredientes: Optional[List[str]] = Query(None, description="Lista de ingredientes separados, ex: ?ingredientes=arroz&ingredientes=feijao"),
    tempo_max: Optional[int] = Query(None, description="Tempo máximo de preparo em minutos")
):
    resultados = receitas
    
    # Filtrar por nome
    if nome:
        resultados = [r for r in resultados if nome.lower() in r['nome'].lower()]
    
    # Filtrar por ingredientes (todas as ingredientes da query precisam estar na receita)
    if ingredientes:
        ingredientes = [ing.lower() for ing in ingredientes]
        def tem_ingredientes(r):
            receita_ings = [i.lower() for i in r['ingredientes']]
            return all(ing in receita_ings for ing in ingredientes)
        resultados = [r for r in resultados if tem_ingredientes(r)]
    
    # Filtrar por tempo máximo
    if tempo_max is not None:
        resultados = [r for r in resultados if r['tempo'] <= tempo_max]
    
    # Retornar só nome e tempo para lista resumida
    lista_resumida = [{"nome": r['nome'], "tempo": r['tempo']} for r in resultados]
    
    return lista_resumida

@app.get("/receitas/{nome_receita}")
def detalhes_receita(nome_receita: str):
    for r in receitas:
        if r['nome'].lower() == nome_receita.lower():
            return r
    raise HTTPException(status_code=404, detail="Receita não encontrada")
