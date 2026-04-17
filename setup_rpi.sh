#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  setup_rpi.sh — Instalação da Roleta Virtual no Raspberry Pi
#  Testado em: Raspberry Pi OS (Bullseye/Bookworm), Python 3.11+
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"
SERVICE_DIR="/etc/systemd/system"
CURRENT_USER="${SUDO_USER:-$USER}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Roleta Virtual — Setup para Raspberry Pi"
echo " Diretório: $APP_DIR"
echo " Usuário:   $CURRENT_USER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Verificar dependências do sistema ──────────────────────
echo "[1/6] Verificando dependências do sistema..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv \
     chromium-browser x11-xserver-utils unclutter --no-install-recommends -qq
echo "      ✓ Dependências instaladas"

# ── 2. Criar virtualenv ────────────────────────────────────────
echo "[2/6] Criando ambiente virtual Python..."
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
echo "      ✓ Virtualenv em $VENV_DIR"

# ── 3. Instalar dependências Python ───────────────────────────
echo "[3/6] Instalando pacotes Python..."
pip install -r "$APP_DIR/requirements.txt" -q
echo "      ✓ Pacotes instalados"

# ── 4. Criar pastas necessárias ───────────────────────────────
echo "[4/6] Criando pastas e ajustando permissões..."
mkdir -p "$APP_DIR/instance"
mkdir -p "$APP_DIR/app/static/uploads"
chown -R "$CURRENT_USER":"$CURRENT_USER" "$APP_DIR"
chmod -R 755 "$APP_DIR"
echo "      ✓ Pastas configuradas"

# ── 5. Inicializar banco de dados ─────────────────────────────
echo "[5/6] Inicializando banco de dados..."
cd "$APP_DIR"
source "$VENV_DIR/bin/activate"
python - <<EOF
import sys
sys.path.insert(0, '$APP_DIR')
from app import create_app
app = create_app()
print("      ✓ Banco de dados criado e seed aplicado")
EOF

# ── 6. Instalar serviços systemd ──────────────────────────────
echo "[6/6] Configurando serviços systemd..."

# Substituir placeholders nos arquivos de serviço
sed "s|APP_DIR_PLACEHOLDER|$APP_DIR|g; s|USER_PLACEHOLDER|$CURRENT_USER|g" \
  "$APP_DIR/roleta.service" | sudo tee "$SERVICE_DIR/roleta.service" > /dev/null

sed "s|USER_PLACEHOLDER|$CURRENT_USER|g" \
  "$APP_DIR/roleta-kiosk.service" | sudo tee "$SERVICE_DIR/roleta-kiosk.service" > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable roleta.service roleta-kiosk.service
echo "      ✓ Serviços habilitados"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅ Instalação concluída!"
echo ""
echo "  Para iniciar agora:    sudo systemctl start roleta"
echo "  Para ver o status:     sudo systemctl status roleta"
echo "  Reiniciar o RPi para   iniciar modo kiosk automático"
echo ""
echo "  Painel admin:  http://localhost:5000/admin"
echo "  Roleta:        http://localhost:5000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
