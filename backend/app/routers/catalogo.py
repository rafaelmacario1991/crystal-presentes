"""
Rotas públicas do catálogo — sem autenticação.
Fase 3: implementação completa das templates.
"""

import json
import httpx
from fastapi import APIRouter, Form, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import database as db
from app.config import NICHOS, FAIXAS_ETARIAS, FAIXAS_ETARIAS_LABEL, GENEROS, get_settings

router = APIRouter(tags=["catalogo"])
templates = Jinja2Templates(directory="app/templates")

_VALID_GENDERS = {"meninos", "meninas", "ambos"}


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    featured = db.get_products_public(page=1, per_page=8)
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "products": featured["data"],
        "nichos": NICHOS,
    })


@router.get("/catalogo", response_class=HTMLResponse)
async def catalogo(
    request: Request,
    niche: str | None = Query(None),
    age_range: str | None = Query(None),
    gender: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    # Sanitize filter params — ignore unknown values to prevent injection
    if niche and niche not in NICHOS:
        niche = None
    if age_range and age_range not in FAIXAS_ETARIAS:
        age_range = None
    if gender and gender not in _VALID_GENDERS:
        gender = None
    result = db.get_products_public(
        niche=niche,
        age_range=age_range,
        gender=gender,
        search=q,
        page=page,
    )
    return templates.TemplateResponse("catalogo.html", {
        "request": request,
        "result": result,
        "nichos": NICHOS,
        "faixas": FAIXAS_ETARIAS,
        "faixas_label": FAIXAS_ETARIAS_LABEL,
        "generos": GENEROS,
        "filters": {"niche": niche, "age_range": age_range, "gender": gender, "q": q},
    })


@router.get("/produto/{product_id}", response_class=HTMLResponse)
async def produto_detalhe(request: Request, product_id: str):
    product = db.get_product_public(product_id)
    if not product:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("produto.html", {
        "request": request,
        "product": product,
        "faixas_label": FAIXAS_ETARIAS_LABEL,
    })


@router.post("/pedidos", response_class=HTMLResponse)
async def criar_pedido(
    request: Request,
    customer_name: str = Form(""),
    customer_phone: str = Form(...),
    customer_type: str = Form("varejo"),
    notes: str = Form(""),
    items_json: str = Form(...),
    source: str = Form("web"),
):
    try:
        items = json.loads(items_json)
    except Exception:
        items = []

    if not items:
        return RedirectResponse("/catalogo", status_code=302)

    total = sum(i.get("price", 0) * i.get("qty", 1) for i in items)

    order_items = [
        {
            "product_id": i.get("id", ""),
            "name": i.get("name", ""),
            "qty": i.get("qty", 1),
            "unit_price": i.get("price", 0),
        }
        for i in items
    ]

    pre_order = db.create_pre_order({
        "customer_name": customer_name.strip() or None,
        "customer_phone": customer_phone.strip(),
        "customer_type": customer_type,
        "items": order_items,
        "total_retail": round(total, 2),
        "status": "pending",
        "notes": notes.strip() or None,
        "source": source,
    })

    # Webhook n8n — fire and forget
    settings = get_settings()
    if settings.n8n_webhook_url:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(settings.n8n_webhook_url, json={
                    "event": "new_pre_order",
                    "source": source,
                    "order_id": pre_order.get("id"),
                    "customer_name": customer_name,
                    "customer_phone": customer_phone,
                    "customer_type": customer_type,
                    "items": order_items,
                    "total": round(total, 2),
                    "notes": notes,
                })
        except Exception:
            pass  # nunca bloqueia a resposta

    return templates.TemplateResponse("pedido_confirmado.html", {
        "request": request,
        "order": pre_order,
        "customer_name": customer_name,
        "total": total,
        "items": order_items,
    })
