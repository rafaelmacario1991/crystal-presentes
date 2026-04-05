"""
API REST para o agente de IA (n8n).
Autenticação via header X-Agent-Key (service key do Supabase).
Retorna JSON com campos completos incluindo preço atacado.
"""

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel

from app import database as db
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/agent", tags=["agent"])


def _verify_agent_key(x_agent_key: str | None):
    """Valida que a requisição vem do n8n com a service key."""
    if not x_agent_key or x_agent_key != settings.supabase_service_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# ============================================================
# Consulta de produtos
# ============================================================

@router.get("/products")
async def agent_get_products(
    niche: str | None = Query(None),
    age_range: str | None = Query(None),
    gender: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    x_agent_key: str | None = Header(None),
):
    _verify_agent_key(x_agent_key)
    products = db.get_products_for_agent(
        niche=niche,
        age_range=age_range,
        gender=gender,
        search=q,
        limit=limit,
    )
    return {"products": products, "total": len(products)}


# ============================================================
# Criação de pré-pedido
# ============================================================

class PreOrderItem(BaseModel):
    product_id: str
    name: str
    qty: int
    unit_price: float


class PreOrderCreate(BaseModel):
    customer_name: str | None = None
    customer_phone: str
    customer_type: str  # 'varejo' | 'atacado'
    items: list[PreOrderItem]
    total_retail: float | None = None
    total_wholesale: float | None = None
    notes: str | None = None


@router.post("/pre-orders", status_code=status.HTTP_201_CREATED)
async def agent_create_pre_order(
    payload: PreOrderCreate,
    x_agent_key: str | None = Header(None),
):
    _verify_agent_key(x_agent_key)

    data = {
        "customer_name": payload.customer_name,
        "customer_phone": payload.customer_phone,
        "customer_type": payload.customer_type,
        "items": [item.model_dump() for item in payload.items],
        "total_retail": payload.total_retail,
        "total_wholesale": payload.total_wholesale,
        "notes": payload.notes,
        "status": "pending",
    }

    order = db.create_pre_order(data)
    return {"order_id": order["id"], "status": "pending"}
