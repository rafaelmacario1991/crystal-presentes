"""
Todas as operações com o Supabase.
- Cliente público (anon key): leitura do catálogo
- Cliente admin (service key): painel + agente
"""

from supabase import create_client, Client
from app.config import get_settings, CAMPOS_RESTRITOS

settings = get_settings()

# Cliente público — catálogo (respeita RLS)
supabase_public: Client = create_client(
    settings.supabase_url,
    settings.supabase_anon_key,
)

# Cliente admin — painel e agente (bypassa RLS)
supabase_admin: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key,
)

# ============================================================
# Helpers
# ============================================================

def _strip_restricted(product: dict) -> dict:
    """Remove campos restritos de um produto para exibição pública."""
    return {k: v for k, v in product.items() if k not in CAMPOS_RESTRITOS}


# ============================================================
# PRODUTOS — leitura pública
# ============================================================

def get_products_public(
    niche: str | None = None,
    age_range: str | None = None,
    gender: str | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Retorna produtos ativos/destaque sem campos restritos. Com filtros e paginação."""
    offset = (page - 1) * per_page

    query = supabase_public.table("products").select(
        "id, name, age_range, gender, description, niche, retail_price, "
        "photos, status, availability, created_at",
        count="exact",
    ).in_("status", ["active", "featured"])

    if niche:
        query = query.eq("niche", niche)
    if age_range:
        query = query.eq("age_range", age_range)
    if gender and gender != "ambos":
        query = query.in_("gender", [gender, "ambos"])
    if search:
        query = query.text_search("search_vector", search, config="portuguese")

    result = query.order("status", desc=True).order("created_at", desc=True).range(offset, offset + per_page - 1).execute()

    return {
        "data": result.data,
        "total": result.count,
        "page": page,
        "per_page": per_page,
        "pages": -(-result.count // per_page) if result.count else 0,
    }


def get_product_public(product_id: str) -> dict | None:
    """Retorna um produto público pelo ID."""
    result = supabase_public.table("products").select(
        "id, name, age_range, gender, description, niche, retail_price, "
        "photos, status, availability, created_at"
    ).eq("id", product_id).in_("status", ["active", "featured"]).maybe_single().execute()
    return result.data


# ============================================================
# PRODUTOS — painel admin (campos completos)
# ============================================================

def get_products_admin(
    status: str | None = None,
    niche: str | None = None,
    page: int = 1,
    per_page: int = 30,
) -> dict:
    offset = (page - 1) * per_page
    query = supabase_admin.table("products").select("*", count="exact")

    if status:
        query = query.eq("status", status)
    if niche:
        query = query.eq("niche", niche)

    result = query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()

    return {
        "data": result.data,
        "total": result.count,
        "page": page,
        "per_page": per_page,
        "pages": -(-result.count // per_page) if result.count else 0,
    }


def get_product_admin(product_id: str) -> dict | None:
    result = supabase_admin.table("products").select("*").eq("id", product_id).maybe_single().execute()
    return result.data


def create_product(data: dict) -> dict:
    result = supabase_admin.table("products").insert(data).execute()
    return result.data[0]


def update_product(product_id: str, data: dict) -> dict:
    result = supabase_admin.table("products").update(data).eq("id", product_id).execute()
    return result.data[0]


def delete_product(product_id: str) -> None:
    supabase_admin.table("products").delete().eq("id", product_id).execute()


def upload_product_image(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Faz upload de imagem para Supabase Storage e retorna a URL pública."""
    path = f"products/{filename}"
    supabase_admin.storage.from_("product-images").upload(
        path, file_bytes, {"content-type": content_type, "upsert": "true"}
    )
    public_url = supabase_admin.storage.from_("product-images").get_public_url(path)
    return public_url


def delete_product_image(path: str) -> None:
    supabase_admin.storage.from_("product-images").remove([path])


# ============================================================
# PRÉ-PEDIDOS
# ============================================================

def get_pre_orders(status: str | None = None, page: int = 1, per_page: int = 30) -> dict:
    offset = (page - 1) * per_page
    query = supabase_admin.table("pre_orders").select("*", count="exact")

    if status:
        query = query.eq("status", status)

    result = query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()

    return {
        "data": result.data,
        "total": result.count,
        "page": page,
        "per_page": per_page,
        "pages": -(-result.count // per_page) if result.count else 0,
    }


def get_pre_order(order_id: str) -> dict | None:
    result = supabase_admin.table("pre_orders").select("*").eq("id", order_id).maybe_single().execute()
    return result.data


def create_pre_order(data: dict) -> dict:
    result = supabase_admin.table("pre_orders").insert(data).execute()
    return result.data[0]


def update_pre_order_status(order_id: str, status: str, notes: str | None = None) -> dict:
    payload = {"status": status}
    if notes:
        payload["notes"] = notes
    result = supabase_admin.table("pre_orders").update(payload).eq("id", order_id).execute()
    return result.data[0]


# ============================================================
# AGENTE — leitura completa de produtos (service key)
# ============================================================

def get_products_for_agent(
    niche: str | None = None,
    age_range: str | None = None,
    gender: str | None = None,
    search: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Retorna produtos com campos completos (incluindo preço atacado) para o agente."""
    query = supabase_admin.table("products").select(
        "id, name, age_range, gender, description, niche, retail_price, "
        "wholesale_price, min_wholesale_qty, photos, availability"
    ).in_("status", ["active", "featured"]).eq("availability", "disponivel")

    if niche:
        query = query.eq("niche", niche)
    if age_range:
        query = query.eq("age_range", age_range)
    if gender and gender != "ambos":
        query = query.in_("gender", [gender, "ambos"])
    if search:
        query = query.text_search("search_vector", search, config="portuguese")

    result = query.limit(limit).execute()
    return result.data
