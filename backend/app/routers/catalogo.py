"""
Rotas públicas do catálogo — sem autenticação.
Fase 3: implementação completa das templates.
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import database as db
from app.config import NICHOS, FAIXAS_ETARIAS, FAIXAS_ETARIAS_LABEL, GENEROS

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
