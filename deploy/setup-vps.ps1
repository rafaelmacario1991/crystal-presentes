# ============================================================
# Crystal Presentes — Setup inicial da VPS
# Executar UMA VEZ antes do primeiro deploy
# Uso: .\deploy\setup-vps.ps1
# ============================================================

$VPS_IP   = "72.62.10.198"
$VPS_USER = "root"
$APP_USER = "crystal"
$APP_DIR  = "/home/crystal"
$REPO_URL = "https://github.com/rafaelmacario1991/crystal-presentes.git"
$PORT     = "8002"
$DOMAIN   = "crystalpresentes.com.br"

Write-Host "=== Crystal Presentes — Setup VPS ===" -ForegroundColor Cyan

$REMOTE = @"
set -e

# ── 1. Criar usuário da aplicação ──────────────────────────
if ! id crystal &>/dev/null; then
  useradd -m -s /bin/bash crystal
  echo "Usuário crystal criado."
fi

# ── 2. Instalar dependências do sistema ────────────────────
apt-get update -qq
apt-get install -y -qq python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx

# ── 3. Clonar repositório ──────────────────────────────────
if [ ! -d "$APP_DIR/backend" ]; then
  sudo -u crystal git clone $REPO_URL $APP_DIR/repo
  ln -s $APP_DIR/repo/backend $APP_DIR/backend
  echo "Repositório clonado."
fi

# ── 4. Criar venv e instalar dependências Python ──────────
sudo -u crystal python3.11 -m venv $APP_DIR/venv
sudo -u crystal $APP_DIR/venv/bin/pip install --upgrade pip -q
sudo -u crystal $APP_DIR/venv/bin/pip install -r $APP_DIR/backend/requirements.txt -q
echo "Dependências instaladas."

# ── 5. Criar .env vazio (preencher com set-env.ps1) ───────
if [ ! -f "$APP_DIR/backend/.env" ]; then
  touch $APP_DIR/backend/.env
  chown crystal:crystal $APP_DIR/backend/.env
  chmod 600 $APP_DIR/backend/.env
  echo ".env criado (vazio — use set-env.ps1 para preencher)."
fi

# ── 6. Systemd service ────────────────────────────────────
cat > /etc/systemd/system/crystalpresentes.service << 'SERVICE'
[Unit]
Description=Crystal Presentes — FastAPI
After=network.target

[Service]
User=crystal
WorkingDirectory=/home/crystal/backend
ExecStart=/home/crystal/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 2
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable crystalpresentes
echo "Serviço systemd configurado."

# ── 7. Nginx server block ─────────────────────────────────
cat > /etc/nginx/sites-available/crystalpresentes << 'NGINX'
server {
    listen 80;
    server_name crystalpresentes.com.br www.crystalpresentes.com.br;

    client_max_body_size 10M;

    location /static/ {
        alias /home/crystal/backend/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        gzip_static on;
    }

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/crystalpresentes /etc/nginx/sites-enabled/crystalpresentes
nginx -t && systemctl reload nginx
echo "Nginx configurado."

echo ""
echo "✅ Setup concluído!"
echo "Próximos passos:"
echo "  1. Preencher .env com: ./deploy/set-env.ps1"
echo "  2. Fazer primeiro deploy: ./deploy/update-vps.ps1"
echo "  3. Ativar SSL: ./deploy/ssl.ps1"
"@

ssh "${VPS_USER}@${VPS_IP}" $REMOTE
