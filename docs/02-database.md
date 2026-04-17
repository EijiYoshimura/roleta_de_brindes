# 02 — Banco de Dados

## Visão Geral

O projeto usa **SQLite 3** como banco de dados, gerenciado via **SQLAlchemy 2.0** (ORM). O arquivo do banco é criado automaticamente em `instance/roleta.db` na primeira execução.

Três tabelas compõem o schema:

| Tabela | Propósito |
|---|---|
| `prizes` | Brindes, itens especiais (tente novamente / não ganhou) |
| `draws` | Histórico de todos os sorteios realizados |
| `settings` | Configurações chave-valor da aplicação |

---

## Schema Completo

### Tabela `prizes`

```sql
CREATE TABLE prizes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                VARCHAR(100)    NOT NULL,
    image_filename      VARCHAR(255)    NULL,           -- arquivo em static/uploads/
    quantity            INTEGER         NOT NULL DEFAULT 0,
    item_type           VARCHAR(10)     NOT NULL DEFAULT 'prize',
                        -- valores: 'prize' | 'retry' | 'no_win'
    weight              FLOAT           NOT NULL DEFAULT 0.0,
                        -- para 'retry'/'no_win': percentual (0.0 a 1.0)
                        -- para 'prize': ignorado (usa quantity)
    color               VARCHAR(7)      NOT NULL DEFAULT '#3498db',
                        -- cor hex do segmento na roda
    exhausted_behavior  VARCHAR(15)     NOT NULL DEFAULT 'hide_weight',
                        -- 'hide_weight': esgotado nunca é sorteado
                        -- 'act_as_retry': esgotado vira "Tente Novamente"
    is_active           BOOLEAN         NOT NULL DEFAULT 1,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### Restrições de `item_type`

| Valor | Significado | Usa `quantity`? | Usa `weight`? | Usa `exhausted_behavior`? |
|---|---|---|---|---|
| `prize` | Brinde real (pode ganhar) | Sim | Não | Sim |
| `retry` | "Tente Novamente" | Não | Sim | Não |
| `no_win` | "Não foi dessa vez" | Não | Sim | Não |

#### Campo `exhausted_behavior` (apenas para `item_type = 'prize'`)

| Valor | Comportamento quando `quantity = 0` |
|---|---|
| `hide_weight` | Segmento visível na roda, **peso = 0**, nunca é sorteado |
| `act_as_retry` | Segmento visível na roda, pode ser sorteado, **retorna "Tente Novamente"** sem decrementar |

---

### Tabela `draws`

```sql
CREATE TABLE draws (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    prize_id    INTEGER     NULL REFERENCES prizes(id) ON DELETE SET NULL,
    prize_name  VARCHAR(100) NOT NULL,  -- snapshot do nome no momento do sorteio
    prize_type  VARCHAR(10)  NOT NULL,  -- snapshot do tipo ('prize'/'retry'/'no_win')
    drawn_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

> **Por que `prize_name` como snapshot?**
> Se um brinde for deletado do admin, o histórico de sorteios ainda deve mostrar o nome correto. O campo `prize_name` preserva o nome no momento do sorteio.

---

### Tabela `settings`

```sql
CREATE TABLE settings (
    key     VARCHAR(50) PRIMARY KEY,
    value   TEXT        NOT NULL
);
```

#### Chaves padrão inseridas no seed

| Chave | Valor padrão | Descrição |
|---|---|---|
| `retry_weight` | `0.15` | Peso percentual do item "Tente Novamente" (15%) |
| `no_win_weight` | `0.10` | Peso percentual do item "Não foi dessa vez" (10%) |
| `spin_duration_ms` | `5000` | Duração da animação de giro em milissegundos |
| `event_name` | `Roleta de Brindes` | Nome do evento (usado no PDF) |

---

## Dados Iniciais (Seed)

O script `migrations/init_db.py` insere automaticamente:

```sql
-- Item: Tente Novamente
INSERT INTO prizes (name, item_type, weight, color, is_active, exhausted_behavior)
VALUES ('Tente Novamente', 'retry', 0.15, '#e74c3c', 1, 'hide_weight');

-- Item: Não foi dessa vez
INSERT INTO prizes (name, item_type, weight, color, is_active, exhausted_behavior)
VALUES ('Não foi dessa vez', 'no_win', 0.10, '#95a5a6', 1, 'hide_weight');

-- Configurações padrão
INSERT INTO settings (key, value) VALUES ('retry_weight', '0.15');
INSERT INTO settings (key, value) VALUES ('no_win_weight', '0.10');
INSERT INTO settings (key, value) VALUES ('spin_duration_ms', '5000');
INSERT INTO settings (key, value) VALUES ('event_name', 'Roleta de Brindes');
```

---

## Exemplos de Consultas SQL

### Listar todos os brindes ativos com estoque disponível
```sql
SELECT id, name, quantity, color
FROM prizes
WHERE is_active = 1
  AND item_type = 'prize'
  AND quantity > 0
ORDER BY name;
```

### Histórico dos últimos 50 sorteios
```sql
SELECT d.drawn_at, d.prize_name, d.prize_type
FROM draws d
ORDER BY d.drawn_at DESC
LIMIT 50;
```

### Total de brindes entregues por tipo
```sql
SELECT prize_name, COUNT(*) as total
FROM draws
WHERE prize_type = 'prize'
GROUP BY prize_name
ORDER BY total DESC;
```

### Verificar qual brinde foi mais sorteado
```sql
SELECT p.name, COUNT(d.id) as vezes_sorteado, p.quantity as estoque_atual
FROM prizes p
LEFT JOIN draws d ON d.prize_id = p.id
WHERE p.item_type = 'prize'
GROUP BY p.id
ORDER BY vezes_sorteado DESC;
```

---

## Operações de Manutenção

### Backup do banco
```bash
cp instance/roleta.db instance/roleta_backup_$(date +%Y%m%d_%H%M%S).db
```

### Zerar histórico de sorteios (mantém brindes)
```sql
DELETE FROM draws;
```

### Restaurar estoque de todos os brindes para um valor
```sql
UPDATE prizes SET quantity = 10 WHERE item_type = 'prize';
```

### Ver tamanho do banco
```bash
ls -lh instance/roleta.db
```

---

## Notas sobre SQLAlchemy

O projeto usa o estilo **declarativo** do SQLAlchemy 2.0:

```python
from sqlalchemy.orm import DeclarativeBase, mapped_column

class Base(DeclarativeBase):
    pass

class Prize(Base):
    __tablename__ = "prizes"
    id: Mapped[int] = mapped_column(primary_key=True)
    # ...
```

O banco é criado com `db.create_all()` dentro do `create_app()`, garantindo que as tabelas existam antes de qualquer request.
