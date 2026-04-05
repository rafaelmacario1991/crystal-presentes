# ============================================================
# Crystal Presentes — Ativar SSL com Let's Encrypt
# Executar após o domínio apontar para a VPS
# Uso: .\deploy\ssl.ps1
# ============================================================

$VPS_IP   = "72.62.10.198"
$VPS_USER = "root"
$DOMAIN   = "crystalpresentes.com.br"
$EMAIL    = "lojacrystalpresentes@hotmail.com"

Write-Host "=== Crystal Presentes — SSL ===" -ForegroundColor Cyan
Write-Host "Domínio: $DOMAIN" -ForegroundColor Gray

$REMOTE = @"
set -e
certbot --nginx \
  -d $DOMAIN \
  -d www.$DOMAIN \
  --non-interactive \
  --agree-tos \
  --email $EMAIL \
  --redirect
echo "✅ SSL ativo! Site disponível em https://$DOMAIN"
"@

ssh "${VPS_USER}@${VPS_IP}" $REMOTE
