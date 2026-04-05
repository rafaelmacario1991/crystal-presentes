"""Script de deploy via SSH com paramiko."""
import paramiko, sys, time

HOST = "72.62.10.198"
USER = "root"
PASS = "4l.PJ0(Z,Yp/iCc7bk/K"

def run(client, cmd, timeout=180, ignore_error=False):
    print(f"\n$ {cmd[:100]}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    output = (out + err).strip()
    # Mostrar apenas linhas nao-W:
    for line in output.splitlines():
        if not line.startswith("W:") and line.strip():
            print(line)
    if rc != 0 and not ignore_error:
        print(f"[ERRO] exit code {rc}")
        sys.exit(rc)
    return out

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=15)
print("Conectado a VPS")

step = int(sys.argv[1]) if len(sys.argv) > 1 else 0

if step == 0 or step == 1:
    print("\n=== 1. Verificando SO ===")
    os_info = run(client, "cat /etc/os-release | head -5")
    py_check = run(client, "python3.11 --version 2>&1 || echo 'sem python3.11'")

    print("\n=== Instalando pacotes ===")
    # Adicionar deadsnakes para python3.11 se necessario
    run(client, "apt-get install -y software-properties-common -qq 2>/dev/null || true", ignore_error=True)
    run(client, "add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true", ignore_error=True)
    run(client, "apt-get update -qq 2>/dev/null || true", ignore_error=True)
    run(client, "apt-get install -y python3.11 python3.11-venv python3.11-distutils 2>/dev/null || apt-get install -y python3 python3-venv")
    run(client, "apt-get install -y git nginx certbot python3-certbot-nginx -qq")
    print("Pacotes instalados.")

if step == 0 or step == 2:
    print("\n=== 2. Usuario crystal ===")
    run(client, "id crystal 2>/dev/null || useradd -m -s /bin/bash crystal")
    print("Usuario OK.")

if step == 0 or step == 3:
    print("\n=== 3. Repositorio ===")
    run(client, "[ -d /home/crystal/repo ] || sudo -u crystal git clone https://github.com/rafaelmacario1991/crystal-presentes.git /home/crystal/repo")
    run(client, "cd /home/crystal/repo && sudo -u crystal git fetch origin && sudo -u crystal git reset --hard origin/main")
    print("Repositorio atualizado.")

if step == 0 or step == 4:
    print("\n=== 4. Venv + dependencias ===")
    # Usar python3.11 se disponivel, senao python3
    py = run(client, "python3.11 --version 2>/dev/null && echo 'python3.11' || echo 'python3'").strip().splitlines()[-1]
    run(client, f"[ -d /home/crystal/venv ] || sudo -u crystal {py} -m venv /home/crystal/venv")
    run(client, "sudo -u crystal /home/crystal/venv/bin/pip install --upgrade pip -q")
    run(client, "sudo -u crystal /home/crystal/venv/bin/pip install -r /home/crystal/repo/backend/requirements.txt -q", timeout=300)
    print("Dependencias instaladas.")

if step == 0 or step == 5:
    print("\n=== 5. Arquivo .env ===")
    env_lines = [
        "SUPABASE_URL=https://qltfwxmflygyrobvwqxw.supabase.co",
        "SUPABASE_ANON_KEY=sb_publishable_PtCxpU9f3M70teEyfS8u3A_dxSMeYi0",
        "SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsdGZ3eG1mbHlneXJvYnZ3cXh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTQwNzcyOCwiZXhwIjoyMDkwOTgzNzI4fQ.xFRAXAf9Tl5T2JVttaUKWXa605XxyQIMATjK-IryMjg",
        "ADMIN_EMAIL=lojacrystalpresentes@hotmail.com",
        r"ADMIN_PASSWORD_HASH=$2b$12$myJlRVXhevKqPRbGRLVOseND7dwJXKkBDAm.icH6E1vV3NqXfvfOq",
        "SECRET_KEY=6ae11698fbf4bb152e8cb6ebd26372300a52e7c3de11e8fdf91cb71f3fe5a2a7",
        "ACCESS_TOKEN_EXPIRE_MINUTES=480",
        "APP_ENV=production",
        "APP_HOST=0.0.0.0",
        "APP_PORT=8002",
    ]
    for line in env_lines:
        key = line.split("=")[0]
        run(client, f"sed -i '/^{key}=/d' /home/crystal/repo/backend/.env 2>/dev/null || true", ignore_error=True)
    # Escrever .env via python para evitar problemas de escape
    env_content = "\n".join(env_lines) + "\n"
    sftp = client.open_sftp()
    with sftp.open("/home/crystal/repo/backend/.env", "w") as f:
        f.write(env_content)
    sftp.close()
    run(client, "chown crystal:crystal /home/crystal/repo/backend/.env && chmod 600 /home/crystal/repo/backend/.env")
    print(".env gravado.")

if step == 0 or step == 6:
    print("\n=== 6. Servico systemd ===")
    service = """[Unit]
Description=Crystal Presentes FastAPI
After=network.target

[Service]
User=crystal
WorkingDirectory=/home/crystal/repo/backend
ExecStart=/home/crystal/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 2
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    sftp = client.open_sftp()
    with sftp.open("/etc/systemd/system/crystalpresentes.service", "w") as f:
        f.write(service)
    sftp.close()
    run(client, "systemctl daemon-reload && systemctl enable crystalpresentes && systemctl restart crystalpresentes")
    time.sleep(4)
    status = run(client, "systemctl is-active crystalpresentes", ignore_error=True)
    if "active" in status:
        print("Servico: ATIVO")
    else:
        print("Servico com problema — verificando logs:")
        run(client, "journalctl -u crystalpresentes -n 30 --no-pager", ignore_error=True)
        sys.exit(1)

if step == 0 or step == 7:
    print("\n=== 7. Nginx ===")
    nginx_conf = """server {
    listen 80;
    server_name crystalpresentes.com.br www.crystalpresentes.com.br;
    client_max_body_size 10M;

    location /static/ {
        alias /home/crystal/repo/backend/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
"""
    sftp = client.open_sftp()
    with sftp.open("/etc/nginx/sites-available/crystalpresentes", "w") as f:
        f.write(nginx_conf)
    sftp.close()
    run(client, "ln -sf /etc/nginx/sites-available/crystalpresentes /etc/nginx/sites-enabled/crystalpresentes")
    run(client, "nginx -t && systemctl reload nginx")
    print("Nginx OK.")

if step == 0 or step == 8:
    print("\n=== 8. Converter imagens para WebP ===")
    run(client, "sudo -u crystal /home/crystal/venv/bin/pip install Pillow -q")
    run(client, "cd /home/crystal/repo/backend && sudo -u crystal /home/crystal/venv/bin/python convert_images.py", timeout=60)

print("\nDeploy concluido! Acesse: http://crystalpresentes.com.br")
client.close()
