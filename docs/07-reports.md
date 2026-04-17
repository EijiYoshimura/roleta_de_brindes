# 07 — Relatórios (CSV e PDF)

## Visão Geral

O painel admin oferece exportação do histórico completo de sorteios em dois formatos:

| Formato | URL | Uso recomendado |
|---|---|---|
| CSV | `/admin/reports/csv` | Excel, LibreOffice Calc, análise de dados |
| PDF | `/admin/reports/pdf` | Impressão, arquivo formal, apresentação |

Ambos exportam **todos os sorteios** registrados (sem paginação). Se necessário filtrar por data, isso deverá ser feito nas ferramentas receptoras.

---

## Formato CSV

### Especificações técnicas

| Atributo | Valor |
|---|---|
| Encoding | UTF-8 com BOM (`utf-8-sig`) — garante acentos no Excel/Windows |
| Delimitador | Vírgula (`,`) |
| Quebra de linha | `\r\n` (Windows-compatible) |
| Header | Sim (primeira linha) |
| Filename | `historico_sorteios_YYYY-MM-DD.csv` |

### Colunas do CSV

```
ID,Data/Hora,Nome do Brinde,Tipo,Prêmio Real
```

| Coluna | Fonte | Exemplo |
|---|---|---|
| `ID` | `draws.id` | `42` |
| `Data/Hora` | `draws.drawn_at` | `10/04/2026 14:35:22` |
| `Nome do Brinde` | `draws.prize_name` | `Fone de Ouvido Bluetooth` |
| `Tipo` | `draws.prize_type` | `prize` |
| `Prêmio Real` | Calculado | `Sim` se `prize_type == 'prize'`, senão `Não` |

### Exemplo de arquivo CSV

```csv
ID,Data/Hora,Nome do Brinde,Tipo,Prêmio Real
1,10/04/2026 14:35:22,Fone de Ouvido Bluetooth,prize,Sim
2,10/04/2026 14:37:05,Tente Novamente,retry,Não
3,10/04/2026 14:38:41,Camiseta Evento,prize,Sim
4,10/04/2026 14:40:18,Não foi dessa vez,no_win,Não
```

### Código de geração (Python)

```python
import csv
import io
from flask import Response

def generate_csv():
    draws = Draw.query.order_by(Draw.drawn_at).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Data/Hora', 'Nome do Brinde', 'Tipo', 'Prêmio Real'])

    for draw in draws:
        writer.writerow([
            draw.id,
            draw.drawn_at.strftime('%d/%m/%Y %H:%M:%S'),
            draw.prize_name,
            draw.prize_type,
            'Sim' if draw.prize_type == 'prize' else 'Não'
        ])

    output.seek(0)
    # UTF-8 BOM para compatibilidade com Excel
    bom = '\ufeff'
    return Response(
        bom + output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename=historico_sorteios_{date.today()}.csv'
        }
    )
```

---

## Formato PDF

### Especificações técnicas

| Atributo | Valor |
|---|---|
| Biblioteca | ReportLab 4.x |
| Tamanho de página | A4 (210 × 297 mm) |
| Orientação | Retrato |
| Encoding | UTF-8 (ReportLab nativo) |
| Filename | `relatorio_sorteios_YYYY-MM-DD.pdf` |

### Estrutura do PDF

#### Cabeçalho (primeira página)
- **Título:** "[Nome do Evento]" (de `settings.event_name`)
- **Subtítulo:** "Relatório de Sorteios"
- **Data de emissão:** "Emitido em: DD/MM/YYYY HH:MM"
- **Linha separadora**

#### Bloco de Resumo
| Campo | Valor |
|---|---|
| Total de sorteios | N |
| Prêmios entregues | N |
| "Tente Novamente" | N |
| "Não Ganhou" | N |

#### Tabela de Sorteios

| # | Data/Hora | Brinde | Tipo |
|---|---|---|---|
| 1 | 10/04/2026 14:35:22 | Fone de Ouvido | Prêmio |
| 2 | 10/04/2026 14:37:05 | Tente Novamente | Especial |

- Cabeçalho da tabela em fundo cinza escuro, texto branco, negrito
- Linhas alternadas (branco / cinza claro) para legibilidade
- Coluna "Tipo" com cor: verde para "Prêmio", laranja para "Especial"/"Esgotado", cinza para "Não Ganhou"
- Paginação automática com cabeçalho repetido em cada página

#### Rodapé (todas as páginas)
- "Página X de Y"
- Nome da aplicação: "Roleta Virtual — gerado em [data]"

### Mapeamento de tipos para texto legível

| `prize_type` no banco | Texto no PDF |
|---|---|
| `prize` | `Prêmio` |
| `retry` | `Tente Novamente` |
| `no_win` | `Não Ganhou` |

---

## Dependências

Adicionar ao `requirements.txt`:

```
reportlab==4.2.5
```

O ReportLab não tem dependências externas além das inclusas e funciona 100% offline.

---

## Notas de Produção

- **Fontes com acentos:** ReportLab suporta UTF-8 nativo. Usar `pdfmetrics.registerFont()` apenas se fontes customizadas forem necessárias; as fontes built-in (Helvetica) suportam caracteres PT-BR.
- **Tabelas grandes:** Para eventos com mais de 1000 sorteios, o PDF pode ser gerado como stream (`StreamingResponse`) para não bloquear o servidor.
- **Erro de geração:** Se o PDF falhar (ex: memória insuficiente no RPi), o backend retorna HTTP 500 com mensagem e o admin exibe flash de erro amigável.
