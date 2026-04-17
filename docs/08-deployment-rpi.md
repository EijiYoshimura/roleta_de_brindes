# 08 — Deploy no Raspberry Pi 4B

## Pré-requisitos de Hardware

- Raspberry Pi 4B (2GB RAM ou mais)
- Cartão microSD ≥ 16GB (Classe 10 / A1)
- Monitor/TV com HDMI
- Teclado e mouse (apenas para configuração inicial)
- Fonte de alimentação oficial RPi 4 (5V / 3A USB-C)

---

## Sistema Operacional Recomendado

**Raspberry Pi OS (64-bit) com desktop** — "Bookworm" ou posterior.

> **Não use** a versão Lite (sem desktop) — o Chromium em kiosk precisa do ambiente gráfico X11.

Download: [https://www.raspberrypi.com/software/](https://www.raspberrypi.com/software/) (use o Raspberry Pi Imager)

Configurações no Imager antes de gravar:
- Hostname: `roleta`
- Username: `pi` / Senha: escolha uma segura
- Wi-Fi: opcional (a app é offline, mas útil para configuração inicial via SSH)
- Enable SSH: recomendado para manutenção remota

---

## Instalação Automática (`setup_rpi.sh`)

Após clonar o repositório, este script instala tudo:

```bash
cd /home/pi
git clone <url-do-repositorio> roleta
cd roleta
chmod +x setup_rpi.sh
./setup_rpi.sh
```

### O que o script faz (detalhado):

```bash
#!/bin/bash
set -e

echo "=== Roleta Virtual — Setup RPi ==="

# 1. Atualizar pacotes do sistema
sudo apt update
sudo apt install -y python3-pip python3-venv git chromium-browser unclutter

# 2. Criar ambiente virtual Python
cd /home/pi/roleta
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar dependências Python
pip install --upgrade pip
pip install -r requirements.txt

# 4. Criar pastas necessárias
mkdir -p instance
mkdir -p app/static/uploads

# 5. Inicializar banco de dados com seed
python migrations/init_db.py

# 6. Instalar serviços systemd
sudo cp roleta.service /etc/systemd/system/
sudo cp roleta-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable roleta.service
sudo systemctl enable roleta-kiosk.service

# 7. Desabilitar screensaver/blanking
mkdir -p /home/pi/.config/lxsession/LXDE-pi/
echo "@xset s off
@xset -dpms
@xset s noblank" >> /home/pi/.config/lxsession/LXDE-pi/autostart

# 8. Configurar Chromium para não perguntar sobre sessão anterior
mkdir -p /home/pi/.config/chromium/Default/
echo '{"profile":{"exit_type":"Normal","exited_cleanly":true}}' \
    > /home/pi/.config/chromium/Default/Preferences

echo ""
echo "=== Instalação concluída! ==="
echo "Reinicie o RPi com: sudo reboot"
```

---

## Serviços systemd

### `roleta.service` — Servidor Flask (Gunicorn)

```ini
[Unit]
Description=Roleta Virtual — Servidor Web
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/roleta
ExecStart=/home/pi/roleta/.venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 2 \
    --timeout 30 \
    --access-logfile /home/pi/roleta/logs/access.log \
    --error-logfile /home/pi/roleta/logs/error.log \
    wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> **Nota:** `--bind 127.0.0.1:5000` (loopback only) — o servidor **não** é acessível fora do RPi. Isso é intencional: sem exposição à rede.

### `roleta-kiosk.service` — Chromium em modo kiosk

```ini
[Unit]
Description=Roleta Virtual — Chromium Kiosk
Requires=roleta.service
After=roleta.service graphical-session.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --no-first-run \
    --disable-translate \
    --no-default-browser-check \
    --user-data-dir=/home/pi/.config/chromium-kiosk \
    http://localhost:5000
Restart=always
RestartSec=10

[Install]
WantedBy=graphical-session.target
```

> **Por que `ExecStartPre=/bin/sleep 5`?** O Gunicorn pode levar alguns segundos para inicializar. O sleep garante que o servidor esteja pronto antes do Chromium abrir.

---

## Acesso ao Painel Admin no RPi

Como o Chromium está em kiosk (modo fullscreen travado em `/`), para acessar o admin:

### Opção A — Teclado conectado ao RPi
1. Pressionar `Alt+F4` para fechar o kiosk
2. Abrir o Chromium normalmente: `chromium-browser http://localhost:5000/admin`
3. Após configurar, fechar o browser
4. O roleta-kiosk.service reiniciará o kiosk automaticamente em 10 segundos

### Opção B — SSH + port forward (manutenção remota)
```bash
ssh -L 8080:localhost:5000 pi@roleta.local
# No seu PC: abrir http://localhost:8080/admin
```

### Opção C — Segundo monitor/browser
Se o RPi tiver dois monitores ou uma tela secundária conectada.

---

## Gerenciamento dos Serviços

```bash
# Status
sudo systemctl status roleta.service
sudo systemctl status roleta-kiosk.service

# Reiniciar
sudo systemctl restart roleta.service
sudo systemctl restart roleta-kiosk.service

# Ver logs em tempo real
sudo journalctl -u roleta.service -f
sudo journalctl -u roleta-kiosk.service -f

# Parar tudo
sudo systemctl stop roleta-kiosk.service
sudo systemctl stop roleta.service

# Iniciar manualmente
sudo systemctl start roleta.service
sudo systemctl start roleta-kiosk.service
```

---

## Estrutura de Pastas no RPi

```
/home/pi/roleta/
├── .venv/               ← ambiente virtual Python (não versionar)
├── instance/
│   └── roleta.db        ← banco SQLite (FAZER BACKUP!)
├── app/static/uploads/  ← imagens dos brindes (FAZER BACKUP!)
├── logs/
│   ├── access.log
│   └── error.log
└── ... (restante do projeto)
```

---

## Backup e Restauração

### Backup automático diário (crontab)

```bash
crontab -e
# Adicionar linha:
0 3 * * * cp /home/pi/roleta/instance/roleta.db /home/pi/backups/roleta_$(date +\%Y\%m\%d).db
```

### Backup manual completo

```bash
tar -czf ~/roleta_backup_$(date +%Y%m%d).tar.gz \
    /home/pi/roleta/instance/ \
    /home/pi/roleta/app/static/uploads/
```

---

## Performance no RPi 4B

O RPi 4B com 2GB RAM é suficiente para esta aplicação. Métricas esperadas:

| Métrica | Valor estimado |
|---|---|
| Uso de RAM | ~80MB (Flask + Gunicorn + SQLite) |
| Tempo de boot até kiosk | ~25–35 segundos |
| Tempo de resposta `/api/spin` | < 100ms |
| Tempo de geração de PDF (500 sorteios) | < 2 segundos |

Se o RPi esquentar muito em ambiente fechado, considerar:
```bash
# Verificar temperatura
vcgencmd measure_temp

# Adicionar dissipadores de calor ou cooler se > 70°C
```

---

## Atualização da Aplicação

```bash
cd /home/pi/roleta
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart roleta.service
# O kiosk reiniciará automaticamente
```

> **Atenção:** Se houver mudanças no schema do banco (novos campos), execute:
> ```bash
> python migrations/init_db.py  # adiciona campos faltantes sem apagar dados
> ```
