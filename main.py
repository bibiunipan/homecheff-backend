from fastapi import FastAPI, Query, HTTPException
from typing import List, Optional
import json
import os
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client

# Substitua pelas suas chaves do projeto Supabase
SUPABASE_URL = "https://<seu-projeto>.supabase.co"
SUPABASE_KEY = "<sua-anon-key>"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

class Cadastro(BaseModel):
    email: str
    senha: str
    nome: str
    restricoes: str
@app.post("/cadastro")
def cadastrar_usuario(dados: Cadastro):
    # 1. Criar usuário no auth (email e senha)
    resp = supabase.auth.sign_up({
        "email": dados.email,
        "password": dados.senha
    })

    if not resp.user:
        raise HTTPException(status_code=400, detail="Erro ao criar usuário")

    user_id = resp.user.id  # pega o ID criado no auth.users

    # 2. Criar perfil na sua tabela personalizada
    perfil = {
        "id": user_id,
        "nome": dados.nome,
        "restricoes": dados.restricoes
    }

    supabase.table("perfis").insert(perfil).execute()

    return {"mensagem": "Usuário cadastrado com sucesso"}

ARQUIVO_RECEITAS = os.path.join(os.path.dirname(__file__), "receitas.json")

# Função para converter "1 hora e 20 minutos" ou "40 minutos" em minutos inteiros
def tempo_para_minutos(tempo_str: str) -> int:
    tempo_str = tempo_str.lower()
    horas = 0
    minutos = 0

    # Pega quantidades de horas (ex: "1 hora" ou "2 horas")
    match_horas = re.search(r"(\d+)\s*hora", tempo_str)
    if match_horas:
        horas = int(match_horas.group(1))

    # Pega quantidades de minutos (ex: "20 minutos", "14 min")
    match_minutos = re.search(r"(\d+)\s*min", tempo_str)
    if match_minutos:
        minutos = int(match_minutos.group(1))

    return horas * 60 + minutos

# Carregar receitas da lista dentro do JSON
with open(ARQUIVO_RECEITAS, 'r', encoding='utf-8') as f:
    data = json.load(f)
    receitas = data["receitas"]

@app.get("/buscar_receitas")
def buscar_receitas(
    nome: Optional[str] = Query(None, description="Nome parcial para busca"),
    ingrediente: Optional[str] = Query(None, description="Ingrediente para busca parcial"),
    tempo_max: Optional[int] = Query(None, description="Tempo máximo de preparo em minutos"),
):
    filtradas = []
    for r in receitas:
        # Checa nome (parcial, case insensitive)
        if nome and nome.lower() not in r['nome'].lower():
            continue

        # Checa ingrediente parcial
        if ingrediente:
            lista_ingredientes = [i.strip() for i in ingrediente.split(",")]
            if not all(
                any(ing.lower() in i.lower() for i in r.get('ingredientes', []))
                for ing in lista_ingredientes
            ):
                continue

        # Checa tempo de preparo convertendo para minutos
        if tempo_max:
            tempo_receita = tempo_para_minutos(r.get('tempo_preparo', '0'))
            if tempo_receita > tempo_max:
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
