# 01 — Guia de Instalação

## Pré-requisitos

- Python 3.11+
- pip
- Git

---

## Instalação para Desenvolvimento (qualquer PC Linux/Mac/Windows)

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio> roleta
cd roleta
```

### 2. Criar ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Inicializar o banco de dados

```bash
python migrations/init_db.py
```

Isso cria o arquivo `instance/roleta.db` e insere os dados iniciais (itens "Tente Novamente" e "Não foi dessa vez").

### 5. Iniciar o servidor de desenvolvimento

```bash
python run.py
```

Acesse no browser:
- Roleta: [http://localhost:5000/](http://localhost:5000/)
- Admin: [http://localhost:5000/admin/](http://localhost:5000/admin/)

---

## Instalação no Raspberry Pi 4B (produção)

### Opção A — Automática (recomendada)

```bash
git clone <url-do-repositorio> /home/pi/roleta
cd /home/pi/roleta
chmod +x setup_rpi.sh
./setup_rpi.sh
```

O script faz tudo automaticamente. Veja [docs/08-deployment-rpi.md](08-deployment-rpi.md) para detalhes do que ele executa.

### Opção B — Manual passo a passo

#### 1. Instalar dependências do sistema

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git chromium-browser
```

#### 2. Clonar o projeto

```bash
git clone <url-do-repositorio> /home/pi/roleta
cd /home/pi/roleta
```

#### 3. Criar ambiente virtual e instalar pacotes Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Criar pastas necessárias

```bash
mkdir -p instance
mkdir -p app/static/uploads
```

#### 5. Inicializar o banco

```bash
python migrations/init_db.py
```

#### 6. Testar o servidor manualmente

```bash
.venv/bin/gunicorn --bind 0.0.0.0:5000 wsgi:app
```

Abra `http://localhost:5000` no browser do RPi para confirmar que funciona. Depois, `Ctrl+C` para parar.

#### 7. Instalar os serviços systemd

```bash
sudo cp roleta.service /etc/systemd/system/
sudo cp roleta-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable roleta.service
sudo systemctl enable roleta-kiosk.service
```

#### 8. Reiniciar o RPi

```bash
sudo reboot
```

Ao reiniciar, o Chromium abrirá automaticamente em tela cheia exibindo a roleta.

---

## Variáveis de Ambiente (opcionais)

Crie um arquivo `.env` na raiz do projeto para sobrescrever configurações:

```env
SECRET_KEY=minha-chave-secreta-aqui
FLASK_ENV=production
```

Se não criar, a aplicação usa valores padrão seguros para produção local.

---

## Atualizar o projeto no RPi

```bash
cd /home/pi/roleta
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart roleta.service
```

---

## Verificar status dos serviços

```bash
# Ver se o servidor Flask está rodando
sudo systemctl status roleta.service

# Ver logs do servidor
sudo journalctl -u roleta.service -f

# Ver se o Chromium kiosk está rodando
sudo systemctl status roleta-kiosk.service
```

---

## Solução de Problemas Comuns

### "Port 5000 already in use"
```bash
sudo fuser -k 5000/tcp
sudo systemctl restart roleta.service
```

### Chromium pedindo "Restaurar sessão"
O perfil do Chromium está configurado para evitar isso. Se ocorrer, execute:
```bash
rm -rf /home/pi/.config/chromium/Default/Preferences
sudo systemctl restart roleta-kiosk.service
```

### Banco de dados corrompido
```bash
cp instance/roleta.db instance/roleta.db.backup  # backup
rm instance/roleta.db
python migrations/init_db.py                       # recriar
```

### Imagens não aparecem
Verificar permissões:
```bash
chmod -R 755 app/static/uploads/
chown -R pi:pi app/static/uploads/
```
