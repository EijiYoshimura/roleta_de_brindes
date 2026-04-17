# 06 — Algoritmo de Peso (Weighted Random)

## Conceito

O sorteio **não é totalmente aleatório**. Cada item na roda tem um "peso" que determina sua probabilidade de ser sorteado. Brindes com mais unidades disponíveis têm mais chances; brindes esgotados podem ter peso zero ou simbólico; itens especiais ("Tente Novamente", "Não Ganhou") têm peso percentual fixo configurável.

---

## Regras de Peso por Tipo de Item

### Brindes Reais (`item_type = 'prize'`)

| Condição | Peso atribuído |
|---|---|
| `quantity > 0` | `quantity` (o número de unidades) |
| `quantity == 0` e `exhausted_behavior = 'hide_weight'` | `0` (nunca sorteado) |
| `quantity == 0` e `exhausted_behavior = 'act_as_retry'` | `1` (peso simbólico mínimo) |

**Exemplo:** Brinde A com 10 unidades tem o dobro de chance de Brinde B com 5 unidades.

### Itens Especiais (`item_type = 'retry'` ou `'no_win'`)

O peso é calculado como um **percentual relativo ao total de brindes disponíveis**:

```
peso_retry = retry_weight_setting × total_de_brindes_disponiveis
peso_no_win = no_win_weight_setting × total_de_brindes_disponiveis
```

Onde `total_de_brindes_disponiveis` = soma das `quantity` de todos os brindes com `quantity > 0`.

**Por que relativo ao total?** Isso garante que mesmo quando os brindes diminuem (estoque sendo consumido), a *proporção* de chance dos itens especiais permanece constante. Se configurado em 15%, o "Tente Novamente" sempre terá ~15% de chance, independente de quantos brindes restam.

---

## Algoritmo Passo a Passo

```python
import random

def perform_spin(db):
    # 1. Buscar todos os itens ativos
    prizes = Prize.query.filter_by(is_active=True).all()

    # 2. Calcular total de unidades de brindes reais disponíveis
    total_prize_qty = sum(
        p.quantity for p in prizes
        if p.item_type == 'prize' and p.quantity > 0
    )

    # 3. Calcular o peso de cada item
    weighted_items = []
    for prize in prizes:
        if prize.item_type == 'prize':
            if prize.quantity > 0:
                weight = prize.quantity
            elif prize.exhausted_behavior == 'act_as_retry':
                weight = 1  # peso simbólico
            else:  # hide_weight
                weight = 0  # nunca sorteado
        else:  # retry ou no_win
            # peso % × total de brindes
            weight = prize.weight * total_prize_qty

        if weight > 0:
            weighted_items.append((prize, weight))

    # 4. Se nenhum item tem peso, retornar erro
    if not weighted_items:
        raise NoActivePrizesError()

    # 5. Construir lista acumulada (prefix sum)
    total_weight = sum(w for _, w in weighted_items)
    pick = random.uniform(0, total_weight)

    accumulated = 0
    winner = None
    for prize, weight in weighted_items:
        accumulated += weight
        if pick <= accumulated:
            winner = prize
            break

    # 6. Determinar se é resultado "esgotado"
    is_exhausted_result = (
        winner.item_type == 'prize'
        and winner.quantity == 0
        and winner.exhausted_behavior == 'act_as_retry'
    )

    # 7. Decrementar estoque APENAS se ganhou brinde real com estoque
    if winner.item_type == 'prize' and winner.quantity > 0:
        winner.quantity -= 1

    # 8. Gravar no histórico
    effective_type = 'retry' if is_exhausted_result else winner.item_type
    draw = Draw(
        prize_id=winner.id,
        prize_name=winner.name,
        prize_type=effective_type
    )
    db.session.add(draw)
    db.session.commit()

    return winner, is_exhausted_result
```

---

## Exemplo Numérico

**Configuração:**
- Brinde A: 10 unidades → peso 10
- Brinde B: 5 unidades → peso 5
- Brinde C: 0 unidades, `hide_weight` → peso 0
- Brinde D: 0 unidades, `act_as_retry` → peso 1
- Tente Novamente: 15% de 16 (10+5+1) = peso 2.4
- Não Ganhou: 10% de 16 = peso 1.6

**Total de peso:** `10 + 5 + 0 + 1 + 2.4 + 1.6 = 20`

**Probabilidades resultantes:**

| Item | Peso | Probabilidade |
|---|---|---|
| Brinde A | 10 | 50.0% |
| Brinde B | 5 | 25.0% |
| Brinde C | 0 | 0.0% (nunca) |
| Brinde D (esgotado) | 1 | 5.0% → exibe "Tente Novamente" |
| Tente Novamente | 2.4 | 12.0% |
| Não Ganhou | 1.6 | 8.0% |
| **Total** | **20** | **100%** |

---

## Validação do Algoritmo (Teste)

Para verificar a distribuição, execute no terminal da máquina de desenvolvimento:

```python
# script de teste: migrations/test_algorithm.py
from app import create_app
from app.routes.roulette import perform_spin

app = create_app()
results = {}

with app.app_context():
    for _ in range(1000):
        winner, is_exhausted = perform_spin(db)
        key = f"{winner.name} ({'esgotado' if is_exhausted else winner.item_type})"
        results[key] = results.get(key, 0) + 1

for name, count in sorted(results.items(), key=lambda x: -x[1]):
    print(f"{name:30s}: {count:4d}x  ({count/10:.1f}%)")
```

Resultado esperado com a configuração do exemplo acima (1000 sorteios):
```
Brinde A                      :  500x  (50.0%)
Brinde B                      :  250x  (25.0%)
Brinde D (esgotado)           :   50x   (5.0%)
Tente Novamente               :  120x  (12.0%)
Não Ganhou                    :   80x   (8.0%)
```

Variação de ±3% é esperada pelo resultado aleatório.

---

## Edge Cases Tratados

### Todos os brindes zerados (hide_weight)
Se todos os brindes reais estão com `quantity = 0` e `exhausted_behavior = 'hide_weight'`:

- `total_prize_qty = 0`
- `weighted_items` conterá apenas retry/no_win com peso = 0 (0% × 0 = 0)
- `weighted_items` ficará vazio após filtrar peso > 0
- A API retorna HTTP 409 com `{ "error": "no_active_prizes" }`
- O frontend desabilita o botão GIRAR e exibe mensagem: "Todos os brindes foram entregues!"

### Apenas um brinde restante
Funciona normalmente — esse brinde tem 100% das chances (excluindo itens especiais cujo peso é relativo ao total).

### Peso de itens especiais muito alto (soma ≥ 100%)
Prevenido pelo admin: se `retry_weight + no_win_weight >= 1.0`, o formulário de settings rejeita o save com mensagem de erro. O backend também valida e lança exceção se ocorrer.

### Itens especiais sem peso (retry_weight = 0)
Permitido. O item terá peso 0 e nunca será sorteado — mas permanece visível na roda se `is_active = True`.
