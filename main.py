from fastapi import FastAPI, Query, HTTPException
from typing import Optional
import json
import os
import re
import unicodedata
import httpx
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Permitindo o frontend do GitHub Pages
origins = [
    "https://bibiunipan.github.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/{rest_of_path:path}")
async def preflight_handler():
    return {}

# Caminho do JSON
ARQUIVO_RECEITAS = os.path.join(os.path.dirname(__file__), "receitas.json")

# Leitura do JSON
with open(ARQUIVO_RECEITAS, 'r', encoding='utf-8') as f:
    data = json.load(f)
    receitas = data["receitas"]

# Funções auxiliares
def tempo_para_minutos(tempo_str: str) -> int:
    tempo_str = tempo_str.lower()
    horas = 0
    minutos = 0
    match_horas = re.search(r"(\d+)\s*hora", tempo_str)
    if match_horas:
        horas = int(match_horas.group(1))
    match_minutos = re.search(r"(\d+)\s*min", tempo_str)
    if match_minutos:
        minutos = int(match_minutos.group(1))
    return horas * 60 + minutos

def normalizar(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()

# Supabase
SUPABASE_URL = "https://ytztgkuzvdmlnbzelmct.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl0enRna3V6dmRtbG5iemVsbWN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkwODAyODEsImV4cCI6MjA2NDY1NjI4MX0.UFLTaoKbkenLhL_xu8Zdi3Zv73qR0t9M-KE_Jym4r3k"

SUBSTITUICOES = {
    "lactose": {
        "leite": "leite vegetal",
        "queijo": "queijo vegano",
        "manteiga": "margarina vegetal",
        "creme de leite": "creme vegetal"
    },
    "gluten": {
        "farinha de trigo": "farinha de arroz",
        "pão": "pão sem glúten",
        "macarrão": "macarrão sem glúten"
    },
    "vegano": {
        "carne": "proteína vegetal",
        "ovo": "ovo de linhaça",
        "leite": "leite vegetal",
        "mel": "melado"
    },
    "vegetariano": {
        "carne": "soja texturizada",
        "frango": "tofu",
        "peixe": "palmito"
    }
}

async def buscar_restricao_usuario(email: str) -> Optional[str]:
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/usuarios?email=eq.{email}",
            headers=headers
        )
    if response.status_code == 200 and response.json():
        return response.json()[0].get("restricao")
    return None

# Endpoint principal de busca com filtro inteligente
@app.get("/buscar_receitas")
async def buscar_receitas(
    nome: Optional[str] = Query(None, description="Nome parcial da receita"),
    ingrediente: Optional[str] = Query(None, description="Ingrediente parcial"),
    tempo_max: Optional[int] = Query(None, description="Tempo máximo de preparo em minutos"),
    email: Optional[str] = Query(None, description="Email do usuário para aplicar restrições")
):
    restricao = None
    substituicoes = {}

    if email:
        restricao = await buscar_restricao_usuario(email)
        if restricao:
            substituicoes = SUBSTITUICOES.get(restricao.lower(), {})

    filtradas = []

    for r in receitas:
        if nome and nome.lower() not in r['nome'].lower():
            continue

        if ingrediente:
            lista_ingredientes = [i.strip() for i in ingrediente.split(",")]
            if not all(
                any(normalizar(ing) in normalizar(i) for i in r.get('ingredientes', []))
                for ing in lista_ingredientes
            ):
                continue

        if tempo_max:
            tempo_receita = tempo_para_minutos(r.get('tempo_preparo', '0'))
            if tempo_receita > tempo_max:
                continue

        sugestoes = []
        if substituicoes:
            for ing in r["ingredientes"]:
                ing_norm = normalizar(ing)
                for proibido, alternativo in substituicoes.items():
                    pattern = r'\b' + re.escape(proibido) + r'\b'
                    if re.search(pattern, ing_norm):
                        substituicao_sugestao = re.sub(pattern, alternativo, ing, flags=re.IGNORECASE)
                        sugestoes.append({
                            "ingrediente_original": ing,
                            "sugestao_substituicao": substituicao_sugestao
                        })
                        break

        filtradas.append({
            "nome": r["nome"],
            "ingredientes": r["ingredientes"],
            "tempo_preparo": r.get("tempo_preparo", ""),
            "sugestoes_substituicoes": sugestoes
        })

    if not filtradas:
        raise HTTPException(status_code=404, detail="Nenhuma receita encontrada com os filtros.")

    return filtradas

@app.get("/detalhes_receita")
async def detalhes_receita(nome: str = Query(..., description="Nome exato da receita"), email: Optional[str] = None):
    restricao = None
    substituicoes_dict = {}

    if email:
        restricao = await buscar_restricao_usuario(email)
        if restricao:
            substituicoes_dict = SUBSTITUICOES.get(restricao.lower(), {})

    for r in receitas:
        if r["nome"].lower() == nome.lower():
            detalhes = r.copy()

            substituicoes = []
            if substituicoes_dict:
                for ing in detalhes["ingredientes"]:
                    ing_norm = normalizar(ing)
                    substituido = None
                    for proibido, alternativo in substituicoes_dict.items():
                        pattern = r'\b' + re.escape(proibido) + r'\b'
                        if re.search(pattern, ing_norm):
                            substituido = re.sub(pattern, alternativo, ing, flags=re.IGNORECASE)
                            print(f"Substituindo '{ing}' por '{substituido}' para restrição '{restricao}'")
                            break
                    substituicoes.append(substituido or ing)

            detalhes["substituicoes"] = substituicoes
            return detalhes

    raise HTTPException(status_code=404, detail="Receita não encontrada.")

# Execução local (opcional)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
