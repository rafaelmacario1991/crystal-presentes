"""
Rotas do painel administrativo — requer autenticação.
Fase 2: implementação completa das templates e lógica de upload.
"""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import database as db
from app.auth import create_access_token, require_admin, verify_admin_credentials
from app.config import (
    NICHOS, FAIXAS_ETARIAS, FAIXAS_ETARIAS_LABEL, GENEROS,
    STATUS_PRODUTO, STATUS_LABEL, STATUS_PEDIDO, STATUS_PEDIDO_LABEL,
    get_settings,
)

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# Login / Logout
# ============================================================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if not verify_admin_credentials(email, password):
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": "E-mail ou senha incorretos.",
        })

    token = create_access_token(
        {"sub": email},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key="crystal_session",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("crystal_session")
    return response


# ============================================================
# Dashboard
# ============================================================

@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, admin=Depends(require_admin)):
    total_produtos = db.get_products_admin(page=1, per_page=1)["total"]
    total_pedidos = db.get_pre_orders(page=1, per_page=1)["total"]
    pedidos_pendentes = db.get_pre_orders(status="pending", page=1, per_page=1)["total"]
    ultimos_pedidos = db.get_pre_orders(page=1, per_page=5)["items"]

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_produtos": total_produtos,
        "total_pedidos": total_pedidos,
        "pedidos_pendentes": pedidos_pendentes,
        "ultimos_pedidos": ultimos_pedidos,
        "status_pedido_label": STATUS_PEDIDO_LABEL,
    })


# ============================================================
# Produtos — CRUD
# ============================================================

@router.get("/produtos", response_class=HTMLResponse)
async def listar_produtos(
    request: Request,
    admin=Depends(require_admin),
    status: str | None = Query(None),
    niche: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    result = db.get_products_admin(status=status, niche=niche, page=page)
    return templates.TemplateResponse("admin/produtos.html", {
        "request": request,
        "result": result,
        "nichos": NICHOS,
        "status_label": STATUS_LABEL,
        "filters": {"status": status, "niche": niche},
    })


@router.get("/produtos/novo", response_class=HTMLResponse)
async def novo_produto_page(request: Request, admin=Depends(require_admin)):
    return templates.TemplateResponse("admin/produto_form.html", {
        "request": request,
        "product": None,
        "nichos": NICHOS,
        "faixas": FAIXAS_ETARIAS,
        "faixas_label": FAIXAS_ETARIAS_LABEL,
        "generos": GENEROS,
        "status_opcoes": STATUS_PRODUTO,
        "status_label": STATUS_LABEL,
    })


@router.post("/produtos/novo")
async def criar_produto(
    request: Request,
    admin=Depends(require_admin),
    name: str = Form(...),
    supplier: str = Form(""),
    age_range: str = Form(...),
    gender: str = Form(...),
    description: str = Form(""),
    niche: str = Form(...),
    retail_price: float = Form(...),
    wholesale_price: float | None = Form(None),
    min_wholesale_qty: int | None = Form(None),
    status: str = Form("active"),
    availability: str = Form("disponivel"),
    photos: list[UploadFile] = File(default=[]),
):
    photo_urls = []
    for photo in photos:
        if photo.filename:
            content = await photo.read()
            ext = photo.filename.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4()}.{ext}"
            url = db.upload_product_image(content, filename, photo.content_type)
            photo_urls.append(url)

    data = {
        "name": name,
        "supplier": supplier or None,
        "age_range": age_range,
        "gender": gender,
        "description": description or None,
        "niche": niche,
        "retail_price": retail_price,
        "wholesale_price": wholesale_price,
        "min_wholesale_qty": min_wholesale_qty,
        "status": status,
        "availability": availability,
        "photos": photo_urls,
    }

    db.create_product(data)
    return RedirectResponse(url="/admin/produtos?created=1", status_code=303)


@router.get("/produtos/{product_id}/editar", response_class=HTMLResponse)
async def editar_produto_page(request: Request, product_id: str, admin=Depends(require_admin)):
    product = db.get_product_admin(product_id)
    if not product:
        return RedirectResponse(url="/admin/produtos", status_code=303)
    return templates.TemplateResponse("admin/produto_form.html", {
        "request": request,
        "product": product,
        "nichos": NICHOS,
        "faixas": FAIXAS_ETARIAS,
        "faixas_label": FAIXAS_ETARIAS_LABEL,
        "generos": GENEROS,
        "status_opcoes": STATUS_PRODUTO,
        "status_label": STATUS_LABEL,
    })


@router.post("/produtos/{product_id}/editar")
async def atualizar_produto(
    request: Request,
    product_id: str,
    admin=Depends(require_admin),
    name: str = Form(...),
    supplier: str = Form(""),
    age_range: str = Form(...),
    gender: str = Form(...),
    description: str = Form(""),
    niche: str = Form(...),
    retail_price: float = Form(...),
    wholesale_price: float | None = Form(None),
    min_wholesale_qty: int | None = Form(None),
    status: str = Form("active"),
    availability: str = Form("disponivel"),
    photos: list[UploadFile] = File(default=[]),
    remove_photos: list[str] = Form(default=[]),
):
    product = db.get_product_admin(product_id)
    if not product:
        return RedirectResponse(url="/admin/produtos", status_code=303)

    current_photos = product.get("photos") or []

    # Remove fotos marcadas
    current_photos = [p for p in current_photos if p not in remove_photos]

    # Upload de novas fotos
    for photo in photos:
        if photo.filename:
            content = await photo.read()
            ext = photo.filename.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4()}.{ext}"
            url = db.upload_product_image(content, filename, photo.content_type)
            current_photos.append(url)

    data = {
        "name": name,
        "supplier": supplier or None,
        "age_range": age_range,
        "gender": gender,
        "description": description or None,
        "niche": niche,
        "retail_price": retail_price,
        "wholesale_price": wholesale_price,
        "min_wholesale_qty": min_wholesale_qty,
        "status": status,
        "availability": availability,
        "photos": current_photos,
    }

    db.update_product(product_id, data)
    return RedirectResponse(url=f"/admin/produtos/{product_id}/editar?updated=1", status_code=303)


@router.post("/produtos/{product_id}/excluir")
async def excluir_produto(product_id: str, admin=Depends(require_admin)):
    db.delete_product(product_id)
    return RedirectResponse(url="/admin/produtos?deleted=1", status_code=303)


# ============================================================
# Pré-pedidos
# ============================================================

@router.get("/pedidos", response_class=HTMLResponse)
async def listar_pedidos(
    request: Request,
    admin=Depends(require_admin),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    result = db.get_pre_orders(status=status, page=page)
    return templates.TemplateResponse("admin/pedidos.html", {
        "request": request,
        "result": result,
        "status_label": STATUS_PEDIDO_LABEL,
        "filters": {"status": status},
    })


@router.post("/pedidos/{order_id}/status")
async def atualizar_status_pedido(
    order_id: str,
    admin=Depends(require_admin),
    status: str = Form(...),
    notes: str = Form(""),
):
    db.update_pre_order_status(order_id, status, notes or None)
    return RedirectResponse(url="/admin/pedidos", status_code=303)
