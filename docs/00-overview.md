# 00 — Visão Geral do Projeto Roleta Virtual

## O que é

Uma aplicação web local que simula uma roleta de premiação para eventos. Ela roda **100% offline** em um Raspberry Pi 4B, sem qualquer dependência de internet. O participante pressiona um botão na tela, a roleta gira e exibe o resultado. Um painel de administração permite cadastrar brindes, definir quantidades e configurar os pesos do sorteio.

---

## Stack Tecnológico

| Camada | Tecnologia | Versão | Motivo |
|---|---|---|---|
| Backend | Python + Flask | Python 3.11, Flask 3.0 | Pré-instalado no RPi OS, leve, sem overhead |
| ORM | SQLAlchemy | 2.0 | Abstração segura do banco, migrations simples |
| Banco | SQLite | 3.x (embutido) | Zero configuração, arquivo único, ideal para eventos |
| Frontend | HTML5 + CSS3 + Vanilla JS | — | Sem build step, funciona offline imediatamente |
| Animação | Canvas API (HTML5) | — | Nativo do browser, sem biblioteca externa |
| Imagens | Pillow | 10.x | Redimensionamento seguro de fotos de brindes |
| PDF | ReportLab | 4.x | Biblioteca Python pura, gera PDF offline |
| Servidor prod | Gunicorn | 21.x | WSGI estável para rodar via systemd |
| Kiosk | Chromium `--kiosk` | presente no RPi OS | Abre tela cheia automaticamente |
| Autostart | systemd | — | Inicia app + Chromium ao ligar o RPi |

---

## Arquitetura

```
┌─────────────────────────────────────────────┐
│              Raspberry Pi 4B                │
│                                             │
│  ┌─────────────┐    HTTP     ┌───────────┐  │
│  │  Chromium   │◄──────────►│  Gunicorn │  │
│  │  --kiosk    │  localhost  │  :5000    │  │
│  │  (fullscreen│    :5000    └─────┬─────┘  │
│  │  roleta)    │                   │        │
│  └─────────────┘              ┌────▼─────┐  │
│                               │  Flask   │  │
│  ┌─────────────┐              │  App     │  │
│  │  Browser    │◄────────────►│          │  │
│  │  /admin     │              └────┬─────┘  │
│  │  (painel)   │                   │        │
│  └─────────────┘              ┌────▼─────┐  │
│                               │  SQLite  │  │
│                               │  roleta  │  │
│                               │  .db     │  │
│                               └──────────┘  │
└─────────────────────────────────────────────┘
```

- **`/`** → Tela da roleta (modo kiosk, tela cheia)
- **`/admin`** → Painel de administração (CRUD de brindes, configurações, histórico)
- **`/api/wheel`** → JSON com segmentos da roda (consultado pelo JS)
- **`/api/spin`** → Executa o sorteio, retorna vencedor

---

## Fluxo Principal

```
[Participante clica GIRAR]
        │
        ▼
[JS: POST /api/spin]
        │
        ▼
[Backend: algoritmo de peso]
   ├── prize (qty > 0): peso = quantity
   ├── prize (qty = 0, hide_weight): peso = 0 → nunca sorteado
   ├── prize (qty = 0, act_as_retry): peso = 1 → retorna "Tente Novamente"
   ├── retry: peso = weight% × total_prizes
   └── no_win: peso = weight% × total_prizes
        │
        ▼
[Backend: decrementa quantity se prize real ganhou]
        │
        ▼
[Backend: grava Draw no banco]
        │
        ▼
[JS: anima roleta até segmento vencedor]
        │
        ▼
[JS: exibe overlay com resultado]
        │
        ▼
[JS: recarrega roda (atualiza visual de esgotados)]
```

---

## Estrutura de Arquivos

```
/home/pi/roleta/          ← raiz do projeto
├── app/
│   ├── __init__.py       ← Flask app factory (create_app)
│   ├── models.py         ← Prize, Draw, Setting (SQLAlchemy)
│   ├── config.py         ← Configurações centralizadas
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── admin.py      ← Painel admin (CRUD + settings + history)
│   │   ├── roulette.py   ← Tela roleta + API /api/wheel, /api/spin
│   │   └── reports.py    ← Exportação CSV e PDF
│   ├── static/
│   │   ├── css/
│   │   │   ├── admin.css
│   │   │   └── roulette.css
│   │   ├── js/
│   │   │   ├── admin.js
│   │   │   └── roulette.js
│   │   └── uploads/      ← Fotos dos brindes (não versionadas)
│   └── templates/
│       ├── base.html
│       ├── admin/
│       │   ├── index.html
│       │   ├── form.html
│       │   ├── settings.html
│       │   └── history.html
│       └── roulette/
│           └── index.html
├── instance/
│   └── roleta.db         ← SQLite (gerado automaticamente)
├── migrations/
│   └── init_db.py        ← Cria tabelas + seed inicial
├── docs/                 ← Esta pasta
├── requirements.txt
├── run.py                ← Entry point desenvolvimento
├── wsgi.py               ← Entry point produção (Gunicorn)
├── setup_rpi.sh          ← Instalação automática no RPi
├── roleta.service        ← systemd: inicia servidor Flask
└── roleta-kiosk.service  ← systemd: inicia Chromium kiosk
```

---

## Decisões de Arquitetura

### Por que Flask e não Django?
Django é excessivo para uma aplicação de página única offline. Flask tem menor footprint de memória, inicializa mais rápido no RPi e não requer configuração de banco de dados além do SQLite.

### Por que Vanilla JS e não React/Vue?
Frameworks JS modernos exigem Node.js, npm e build step. No RPi offline, isso adicionaria complexidade de manutenção sem benefício real. A animação da roleta via Canvas é implementável com ~150 linhas de JavaScript puro.

### Por que SQLite e não PostgreSQL/MySQL?
Uma aplicação de eventos locais nunca terá concorrência de escrita. SQLite é embutido, o banco é um arquivo único (`roleta.db`) que pode ser copiado e restaurado trivialmente.

### Por que sem autenticação no admin?
A aplicação roda em evento físico controlado com acesso físico ao dispositivo. Adicionar autenticação adicionaria fricção operacional sem benefício de segurança real. Se necessário no futuro, Flask-HTTPAuth pode ser adicionado em horas.

### Segmentos esgotados nunca somem da roda
O layout visual da roda deve ser **estável** durante todo o evento. Quando um brinde se esgota, o segmento permanece visível com indicador de "ESGOTADO", mas o administrador escolhe o comportamento do sorteio:
- `hide_weight`: segmento visível, nunca sorteado
- `act_as_retry`: segmento visível, se cair exibe "Tente Novamente"

---

## URLs da Aplicação

| URL | Descrição |
|---|---|
| `http://localhost:5000/` | Tela da roleta (modo kiosk) |
| `http://localhost:5000/admin/` | Lista de brindes |
| `http://localhost:5000/admin/prizes/new` | Cadastrar brinde |
| `http://localhost:5000/admin/prizes/<id>/edit` | Editar brinde |
| `http://localhost:5000/admin/settings` | Configurações gerais |
| `http://localhost:5000/admin/history` | Histórico de sorteios |
| `http://localhost:5000/admin/reports/csv` | Download CSV |
| `http://localhost:5000/admin/reports/pdf` | Download PDF |
| `http://localhost:5000/api/wheel` | JSON: segmentos da roda |
| `http://localhost:5000/api/spin` | POST: executar sorteio |
