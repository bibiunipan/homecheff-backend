from fastapi import FastAPI, Query, HTTPException
from typing import List, Optional
import json
import os

app = FastAPI()

ARQUIVO_RECEITAS = os.path.join(os.path.dirname(__file__), "receitas.json")

with open(ARQUIVO_RECEITAS, 'r', encoding='utf-8') as f:
    receitas = json.load(f)

@app.get("/buscar_receitas")
def buscar_receitas(
    nome: Optional[str] = Query(None, description="Nome parcial para busca"),
    ingrediente: Optional[str] = Query(None, description="Ingrediente para busca parcial"),
    tempo_max: Optional[int] = Query(None, description="Tempo máximo de preparo em minutos"),
):
    filtradas = []
    for r in receitas:
        if nome and nome.lower() not in r['nome'].lower():
            continue
        if ingrediente:
            if not any(ingrediente.lower() in i.lower() for i in r.get('ingredientes', [])):
                continue
        if tempo_max and r.get('tempo_preparo', 0) > tempo_max:
            continue
        filtradas.append(r)
    
    nomes = [r["nome"] for r in filtradas]
    
    if not nomes:
        raise HTTPException(status_code=404, detail="Nenhuma receita encontrada com os filtros.")
    
    return nomes

@app.get("/detalhes_receita")
def detalhes_receita(nome: str = Query(..., description="Nome exato da receita")):
    for r in receitas:
        if r["nome"].lower() == nome.lower():
            return r
    raise HTTPException(status_code=404, detail="Receita não encontrada.")
