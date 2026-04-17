# 04 — Painel de Administração

## Visão Geral

O painel de administração é acessado via `http://localhost:5000/admin/` no mesmo Raspberry Pi. Ele permite:

- Cadastrar, editar e excluir brindes
- Ativar/desativar brindes sem excluí-los
- Configurar pesos dos itens especiais
- Visualizar e exportar o histórico de sorteios

---

## Telas do Admin

### 1. Lista de Brindes (`/admin/`)

Layout de tabela com as colunas:

| Coluna | Descrição |
|---|---|
| Cor | Quadrado colorido mostrando a cor do segmento na roda |
| Nome | Nome do brinde |
| Tipo | "Brinde", "Tente Novamente" ou "Não foi dessa vez" |
| Quantidade | Estoque atual (— para itens sem quantidade) |
| Status | Toggle ativo/inativo (botão visual) |
| Ações | Botões: Editar, Excluir |

**Indicadores visuais:**
- Brindes com `quantity = 0` exibem badge "ESGOTADO" em vermelho ao lado do nome
- Itens inativos aparecem com texto acinzentado
- Linha de totais no rodapé: "X brindes ativos | Y unidades disponíveis"

**Ações rápidas no topo:**
- Botão "+ Novo Brinde"
- Botão "⚙ Configurações"
- Botão "Abrir Roleta" (abre `/` em nova aba)
- Botão "Ver Histórico"

---

### 2. Formulário de Cadastro/Edição (`/admin/prizes/new` e `/admin/prizes/<id>/edit`)

O formulário adapta seus campos conforme o **Tipo** selecionado (campo obrigatório):

#### Campos sempre visíveis:

| Campo | Tipo HTML | Validação |
|---|---|---|
| Nome | `input[type=text]` | Obrigatório, 1–100 chars |
| Tipo | `select` | prize / retry / no_win |
| Cor do Segmento | `input[type=color]` | Picker visual |
| Imagem (opcional) | `input[type=file]` | jpg, png, webp, gif ≤ 5MB |

#### Campos visíveis apenas para `Tipo = Brinde (prize)`:

| Campo | Tipo HTML | Validação |
|---|---|---|
| Quantidade | `input[type=number]` | Inteiro ≥ 0 |
| Comportamento ao esgotar | `radio` | Ver abaixo |

**Opções de "Comportamento ao esgotar":**
```
( ) Nunca cair neste segmento
    → Segmento fica visível na roda mas peso vai a zero.
    → Participante nunca cairá aqui após o estoque acabar.

( ) Exibir como Esgotado e tratar como "Tente Novamente"
    → Segmento fica visível E pode ser sorteado.
    → Se o participante cair aqui, vê mensagem "Esgotado — Tente Novamente".
```

#### Campos visíveis apenas para `Tipo = Tente Novamente` ou `Tipo = Não foi dessa vez`:

| Campo | Tipo HTML | Validação |
|---|---|---|
| Peso (%) | `input[type=range]` + display numérico | 1%–99% |

**Preview de imagem ao selecionar arquivo:** O JavaScript exibe imediatamente a prévia da imagem selecionada antes de salvar.

**Preview da cor na roda:** O quadrado de preview da cor é atualizado em tempo real conforme o usuário usa o color picker.

---

### 3. Configurações (`/admin/settings`)

| Campo | Descrição | Padrão |
|---|---|---|
| Peso "Tente Novamente" | % de chance deste item ser sorteado (relativo ao total de brindes) | 15% |
| Peso "Não foi dessa vez" | % de chance deste item ser sorteado | 10% |
| Duração do giro (ms) | Tempo de animação da roda em milissegundos | 5000 |
| Nome do Evento | Usado no cabeçalho do relatório PDF | Roleta de Brindes |

**Validação:** A soma dos pesos especiais (retry + no_win) não pode ser ≥ 100%. Se o administrador configurar valores que somem ≥ 100%, o formulário exibe erro: "A soma dos pesos especiais não pode atingir 100% — não restariam brindes reais para sortear."

Link direto para abrir a roleta em tela cheia está disponível nesta tela.

---

### 4. Histórico de Sorteios (`/admin/history`)

Tabela paginada (50 por página) com:

| Coluna | Descrição |
|---|---|
| # | Número sequencial do sorteio |
| Data/Hora | Timestamp completo (`dd/mm/yyyy HH:MM:SS`) |
| Nome do Brinde | Nome no momento do sorteio (snapshot) |
| Tipo | Badge colorido: "Prêmio" (verde), "Tente Novamente" (laranja), "Não Ganhou" (cinza) |

**Resumo no topo da página:**
- Total de sorteios realizados
- Total de prêmios entregues
- Total de "Tente Novamente" + "Não Ganhou"

**Botões de exportação:**
- "⬇ Exportar CSV" → `/admin/reports/csv`
- "⬇ Exportar PDF" → `/admin/reports/pdf`

---

## Fluxo de Cadastro de um Brinde (passo a passo)

1. Acessar `/admin/` → clicar em "+ Novo Brinde"
2. Preencher **Nome** (ex: "Fone de Ouvido Bluetooth")
3. Selecionar **Tipo**: "Brinde"
4. Preencher **Quantidade**: 10
5. Escolher **Cor**: clicar no color picker e selecionar uma cor vibrante
6. (Opcional) Selecionar **Imagem**: clicar em "Escolher arquivo", selecionar JPG/PNG
7. Escolher **Comportamento ao esgotar**:
   - Se os brindes são limitados e você não quer que o segmento seja sorteado após se esgotar: "Nunca cair neste segmento"
   - Se você quer que o segmento permaneça sorteável mas exiba "Tente Novamente": segunda opção
8. Clicar em **Salvar**
9. Verificar que aparece na lista com quantidade e cor corretas

---

## Fluxo de Configuração dos Pesos (passo a passo)

1. Acessar `/admin/settings`
2. Ajustar sliders de peso conforme desejado
   - Ex: retry = 20%, no_win = 15% → brindes reais terão 65% das chances proporcionais
3. Clicar em **Salvar Configurações**
4. Abrir a roleta para confirmar visualmente

---

## Comportamento de Exclusão

Ao clicar em "Excluir" em um brinde:
- Aparece diálogo de confirmação JavaScript (`confirm()`)
- Se confirmado, o brinde é removido do banco
- Registros de histórico (`draws`) que referenciam este brinde têm `prize_id = NULL` mas mantêm `prize_name` (histórico preservado)
- A roda é atualizada automaticamente na próxima vez que for carregada

**Nota:** Os itens padrão "Tente Novamente" e "Não foi dessa vez" podem ser editados (mudar nome, cor, peso) mas não podem ser excluídos via interface — o botão "Excluir" não aparece para eles.
