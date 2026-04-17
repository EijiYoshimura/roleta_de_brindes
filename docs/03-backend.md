# 03 — Backend: Rotas e API

## Estrutura de Blueprints

O Flask usa **Blueprints** para organizar as rotas:

| Blueprint | Prefixo | Arquivo |
|---|---|---|
| `roulette_bp` | `/` | `app/routes/roulette.py` |
| `admin_bp` | `/admin` | `app/routes/admin.py` |
| `reports_bp` | `/admin/reports` | `app/routes/reports.py` |

---

## Rotas da Roleta

### `GET /`
**Descrição:** Página principal — tela da roleta em fullscreen.

**Response:** HTML (`templates/roulette/index.html`)

**Comportamento:** Renderiza a página que carrega o Canvas e inicializa o JavaScript da roleta.

---

### `GET /api/wheel`
**Descrição:** Retorna os dados de todos os segmentos da roda para o frontend JavaScript.

**Response:** `application/json`

```json
{
  "segments": [
    {
      "id": 1,
      "name": "Fone de Ouvido",
      "color": "#3498db",
      "image_url": "/static/uploads/abc123.jpg",
      "item_type": "prize",
      "quantity": 5,
      "is_exhausted": false
    },
    {
      "id": 2,
      "name": "Camiseta",
      "color": "#2ecc71",
      "image_url": null,
      "item_type": "prize",
      "quantity": 0,
      "is_exhausted": true
    },
    {
      "id": 3,
      "name": "Tente Novamente",
      "color": "#e74c3c",
      "image_url": null,
      "item_type": "retry",
      "quantity": null,
      "is_exhausted": false
    }
  ]
}
```

**Nota de segurança:** Esta rota **não retorna pesos** — o algoritmo de sorteio fica exclusivamente no backend para evitar manipulação client-side.

---

### `POST /api/spin`
**Descrição:** Executa o sorteio, registra no histórico e retorna o vencedor.

**Request:** Sem body (POST vazio).

**Response:** `application/json`

```json
{
  "winner_id": 1,
  "winner_name": "Fone de Ouvido",
  "winner_type": "prize",
  "image_url": "/static/uploads/abc123.jpg",
  "is_exhausted_result": false,
  "remaining_quantity": 4
}
```

**Campos da resposta:**

| Campo | Tipo | Descrição |
|---|---|---|
| `winner_id` | int | ID do segmento vencedor (para o JS calcular ângulo) |
| `winner_name` | string | Nome a exibir no overlay |
| `winner_type` | string | `'prize'`, `'retry'`, `'no_win'` |
| `image_url` | string \| null | URL da imagem do brinde |
| `is_exhausted_result` | bool | `true` se brinde esgotado com `act_as_retry` foi sorteado |
| `remaining_quantity` | int \| null | Estoque restante após sorteio (null para retry/no_win) |

**Erros possíveis:**

```json
{ "error": "no_active_prizes", "message": "Nenhum item ativo na roda." }
```
HTTP 409 quando todos os itens com peso estão esgotados.

---

## Rotas do Admin

### `GET /admin/`
**Descrição:** Lista todos os brindes cadastrados.

**Response:** HTML — tabela com todos os `Prize` ordenados por `item_type`, depois por `name`.

**Filtros disponíveis via query string:**
- `?tipo=prize` — apenas brindes
- `?tipo=retry` — apenas "tente novamente"
- `?ativo=1` — apenas ativos
- `?ativo=0` — apenas inativos

---

### `GET /admin/prizes/new`
**Descrição:** Formulário de cadastro de novo brinde (vazio).

**Response:** HTML

---

### `POST /admin/prizes/new`
**Descrição:** Processa o formulário de cadastro.

**Request body (form-data):**

| Campo | Tipo | Obrigatório | Validação |
|---|---|---|---|
| `name` | string | Sim | 1–100 caracteres |
| `item_type` | string | Sim | `prize`, `retry`, `no_win` |
| `quantity` | int | Apenas para `prize` | ≥ 0 |
| `color` | string | Sim | Hex `#RRGGBB` |
| `weight` | float | Apenas para `retry`/`no_win` | 0.01–0.99 |
| `exhausted_behavior` | string | Apenas para `prize` | `hide_weight`, `act_as_retry` |
| `image` | file | Não | jpg, png, webp, gif; máx 5MB |

**Response em sucesso:** Redirect para `GET /admin/` com flash "Brinde cadastrado com sucesso."

**Response em erro:** Re-renderiza o formulário com mensagens de erro inline.

---

### `GET /admin/prizes/<id>/edit`
**Descrição:** Formulário de edição pré-preenchido com dados do brinde.

**Response:** HTML

**Erro 404** se o brinde não existir.

---

### `POST /admin/prizes/<id>/edit`
**Descrição:** Processa edição. Mesmos campos e validações que o cadastro.

**Comportamento especial:** Se uma nova imagem for enviada, a imagem anterior é deletada do disco.

---

### `POST /admin/prizes/<id>/delete`
**Descrição:** Exclui um brinde. Registros em `draws` que apontam para este brinde têm `prize_id` setado como `NULL` (preserva histórico).

**Response:** Redirect para `GET /admin/` com flash.

**Proteção:** Não é possível deletar os itens especiais default (`retry_default`, `no_win_default`) via esta rota — retorna erro 400.

---

### `POST /admin/prizes/<id>/toggle`
**Descrição:** Ativa ou desativa um brinde (alterna `is_active`).

**Response:** `application/json` `{ "is_active": true }` — usado via fetch do admin.js.

---

### `GET /admin/settings`
**Descrição:** Formulário de configurações gerais.

**Response:** HTML

---

### `POST /admin/settings`
**Descrição:** Salva configurações.

**Campos:**

| Campo | Tipo | Validação |
|---|---|---|
| `retry_weight` | float | 0.0–0.99 |
| `no_win_weight` | float | 0.0–0.99 |
| `spin_duration_ms` | int | 2000–10000 |
| `event_name` | string | 1–100 caracteres |

**Nota:** `retry_weight + no_win_weight` deve ser < 1.0. O backend valida e retorna erro se a soma for ≥ 1.0.

---

### `GET /admin/history`
**Descrição:** Histórico de sorteios com paginação.

**Query params:**
- `?page=1` (padrão: 1)
- `?per_page=50` (padrão: 50, máx: 200)

**Response:** HTML — tabela com `drawn_at`, `prize_name`, `prize_type`, paginação.

---

## Rotas de Relatórios

### `GET /admin/reports/csv`
**Descrição:** Download do histórico completo em CSV.

**Response:** `text/csv; charset=utf-8`

**Filename:** `historico_sorteios_YYYY-MM-DD.csv`

**Campos do CSV:**

```
ID,Data/Hora,Nome do Brinde,Tipo,Premio Real
1,2026-04-10 14:35:22,Fone de Ouvido,prize,Sim
2,2026-04-10 14:37:05,Tente Novamente,retry,Não
```

---

### `GET /admin/reports/pdf`
**Descrição:** Download do histórico em PDF formatado.

**Response:** `application/pdf`

**Filename:** `relatorio_sorteios_YYYY-MM-DD.pdf`

**Conteúdo do PDF:**
- Cabeçalho com nome do evento (`settings.event_name`) e data de geração
- Tabela com todos os sorteios (ID, Data/Hora, Brinde, Tipo)
- Rodapé com totais: total de sorteios, total de prêmios entregues, total de "tente novamente"

---

## Upload de Imagens

**Rota:** Processado internamente nas rotas `new` e `edit` do admin.

**Fluxo:**
1. Validar extensão: apenas `jpg`, `jpeg`, `png`, `webp`, `gif`
2. Validar tamanho: máximo 5MB (configurado em `Config.MAX_CONTENT_LENGTH`)
3. Gerar nome único: `uuid4().hex + extensão_original`
4. Redimensionar com Pillow: máximo 400×400px, mantendo proporção
5. Salvar em `app/static/uploads/<uuid>.ext`
6. Gravar apenas o filename (ex: `abc123.jpg`) no banco

**Segurança:** O nome original do arquivo **nunca é usado** — o UUID previne path traversal e colisões.

---

## Tratamento de Erros

| Código | Situação | Resposta |
|---|---|---|
| 400 | Dados de formulário inválidos | Formulário com mensagens de erro |
| 404 | Brinde não encontrado | Página de erro HTML ou JSON |
| 409 | Nenhum item ativo para sortear | JSON com campo `error` |
| 413 | Imagem maior que 5MB | Flash e re-renderiza formulário |
| 500 | Erro interno | Página de erro HTML ou JSON |

Para requests que enviam `Accept: application/json`, erros retornam JSON. Para requests normais de browser, retornam HTML.
