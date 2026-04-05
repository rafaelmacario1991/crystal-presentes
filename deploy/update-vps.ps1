# ============================================================
# Crystal Presentes — Deploy / Atualização da VPS
# Uso: .\deploy\update-vps.ps1
# ============================================================

$VPS_IP   = "72.62.10.198"
$VPS_USER = "root"
$APP_DIR  = "/home/crystal"

Write-Host "=== Crystal Presentes — Deploy ===" -ForegroundColor Cyan
Write-Host "VPS: $VPS_IP" -ForegroundColor Gray

$REMOTE = @"
set -e
cd $APP_DIR/repo

echo "→ Atualizando código..."
git pull origin main

echo "→ Instalando dependências..."
$APP_DIR/venv/bin/pip install -r backend/requirements.txt -q

echo "→ Convertendo imagens para WebP..."
cd $APP_DIR/backend
$APP_DIR/venv/bin/python convert_images.py 2>/dev/null || echo "  (Pillow não instalado ou imagens já convertidas)"

echo "→ Reiniciando serviço..."
systemctl restart crystalpresentes
sleep 2
systemctl is-active --quiet crystalpresentes && echo "✅ Serviço ativo!" || (echo "❌ Erro no serviço:" && journalctl -u crystalpresentes -n 20 --no-pager && exit 1)
"@

ssh "${VPS_USER}@${VPS_IP}" $REMOTE
Write-Host ""
Write-Host "Deploy concluído: https://crystalpresentes.com.br" -ForegroundColor Green
