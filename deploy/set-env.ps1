# ============================================================
# Crystal Presentes — Configura variável no .env da VPS
# Uso: .\deploy\set-env.ps1 NOME_VAR "valor"
# Exemplo: .\deploy\set-env.ps1 SECRET_KEY "abc123"
# ============================================================

param(
    [Parameter(Mandatory=$true)][string]$VarName,
    [Parameter(Mandatory=$true)][string]$VarValue
)

$VPS_IP   = "72.62.10.198"
$VPS_USER = "root"
$ENV_FILE = "/home/crystal/backend/.env"

$REMOTE = @"
# Remove linha existente e adiciona nova
sed -i "/^${VarName}=/d" ${ENV_FILE}
echo '${VarName}=${VarValue}' >> ${ENV_FILE}
echo "✅ ${VarName} atualizado."
systemctl restart crystalpresentes
"@

Write-Host "Atualizando $VarName na VPS..." -ForegroundColor Cyan
ssh "${VPS_USER}@${VPS_IP}" $REMOTE
