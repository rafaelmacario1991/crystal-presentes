from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # Admin
    admin_email: str
    admin_password_hash: str

    # JWT
    secret_key: str
    access_token_expire_minutes: int = 480

    # App
    app_env: str = "production"
    app_host: str = "0.0.0.0"
    app_port: int = 8001

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ============================================================
# Domínio e configuração do catálogo
# ============================================================
SITE_URL = "https://crystalpresentes.com.br"

NICHOS = [
    "Educativo",
    "Jogos",
    "Bonecas",
    "Cartelados",
    "Festividades",
    "Puzzle",
]

FAIXAS_ETARIAS = [
    "0-3",
    "3-6",
    "7-10",
    "10-12",
    "12+",
]

FAIXAS_ETARIAS_LABEL = {
    "0-3":   "0 a 3 anos",
    "3-6":   "3 a 6 anos",
    "7-10":  "7 a 10 anos",
    "10-12": "10 a 12 anos",
    "12+":   "12 anos ou mais",
}

GENEROS = ["meninos", "meninas", "ambos"]

STATUS_PRODUTO = ["active", "inactive", "featured"]

STATUS_LABEL = {
    "active":   "Ativo",
    "inactive": "Inativo",
    "featured": "Destaque",
}

STATUS_PEDIDO = ["pending", "attended", "closed"]

STATUS_PEDIDO_LABEL = {
    "pending":  "Pendente",
    "attended": "Atendido",
    "closed":   "Encerrado",
}

# Campos NUNCA retornados ao público (aplicado no database.py)
CAMPOS_RESTRITOS = ["wholesale_price", "min_wholesale_qty", "supplier"]
