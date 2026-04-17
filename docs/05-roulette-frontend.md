# 05 — Frontend da Roleta (Canvas)

## Visão Geral

A tela da roleta é uma página HTML fullscreen que usa a **Canvas API** do HTML5 para renderizar e animar a roda. Não há frameworks JavaScript — tudo é Vanilla JS (~300 linhas).

**URL:** `http://localhost:5000/`

---

## Layout da Tela

```
┌─────────────────────────────────────────────┐
│                                             │
│           ▼  ← ponteiro fixo                │
│        ╭──────╮                             │
│       /  FREE  \                            │
│      / SPIN ████│                           │
│     │ ██████████│                           │
│     │  BRINDE██ │                           │
│      \ ESGOTADO/                            │
│       ╰──────╯                              │
│                                             │
│         [ GIRAR ]  ← botão                  │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Componentes do JavaScript (`roulette.js`)

### Estado Global

```javascript
let segments = [];      // array de segmentos carregados da API
let currentRotation = 0;  // rotação atual da roda (radianos)
let isSpinning = false;   // trava para evitar double-spin
```

---

### `loadWheel()`

**Propósito:** Busca os segmentos da roda via `GET /api/wheel` e reinicializa o Canvas.

**Fluxo:**
1. `fetch('/api/wheel')`
2. Armazena `data.segments` em `segments`
3. Se `segments.length === 0`: exibe mensagem "Nenhum item cadastrado — acesse o painel admin."
4. Chama `drawWheel(currentRotation)`

**Chamada:** Automaticamente ao carregar a página e após fechar o overlay de resultado.

---

### `drawWheel(rotation)`

**Propósito:** Renderiza todos os segmentos no Canvas a partir de um ângulo de rotação.

**Fluxo:**
1. Limpar canvas com `ctx.clearRect()`
2. Calcular `sliceAngle = (2 * Math.PI) / segments.length`
3. Para cada segmento `i`:
   - Calcular `startAngle = rotation + i * sliceAngle`
   - Calcular `endAngle = startAngle + sliceAngle`
   - Desenhar arco com `ctx.arc()` preenchido com `segment.color`
   - **Se `segment.is_exhausted = true`:** aplicar overlay cinza semi-transparente (rgba 0,0,0,0.45)
   - Rotacionar contexto para o ângulo central do segmento
   - Escrever texto com wrap (máximo 2 linhas de ~12 chars cada)
   - Se `segment.image_url` existe e a imagem estiver pré-carregada: desenhar imagem centralizada
   - **Se `segment.is_exhausted = true`:** escrever "ESGOTADO" em vermelho em fonte menor
4. Desenhar círculo central (hub) com gradiente radial
5. Desenhar ponteiro fixo (triângulo branco no topo, fora do canvas rotacionado)

---

### `drawPointer()`

**Propósito:** Desenha o ponteiro indicador fixo no topo da roda.

**Implementação:** Triângulo preenchido com sombra, desenhado **fora** da `save/restore` de rotação — portanto sempre aponta para cima independente da rotação da roda.

---

### `spinWheel()`

**Propósito:** Orchestration do spin completo: chama a API, calcula ângulo, anima e exibe resultado.

**Fluxo detalhado:**

```
1. Se isSpinning == true: retornar (evita double click)
2. isSpinning = true
3. Desabilitar botão GIRAR (visual + funcional)
4. POST /api/spin
5. Receber { winner_id, winner_name, winner_type, image_url, is_exhausted_result }
6. Calcular índice do vencedor em segments[]
7. Calcular ângulo alvo:
   a. Ângulo do centro do segmento vencedor
   b. Offset aleatório dentro do segmento (- sliceAngle/2 a + sliceAngle/2)
   c. Adicionar N voltas completas (mínimo 5, máximo 8 — varia por tensão dramática)
   d. targetRotation = currentRotation + totalAngle
8. Iniciar animação com requestAnimationFrame
9. Aplicar easing easeOutCubic
10. Ao atingir targetRotation:
    a. currentRotation = targetRotation % (2 * Math.PI)  (normalizar)
    b. isSpinning = false
    c. Habilitar botão GIRAR
    d. Exibir overlay de resultado
```

---

### `animateSpin(startTime, startRotation, targetRotation, duration, callback)`

**Propósito:** Loop de animação usando `requestAnimationFrame`.

**Parâmetros:**
- `startTime`: timestamp do início (de `performance.now()`)
- `startRotation`: ângulo inicial
- `targetRotation`: ângulo final
- `duration`: duração em ms (lida de `settings.spin_duration_ms`)
- `callback`: função chamada ao término

**Easing `easeOutCubic`:**
```javascript
function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
}
```

---

### `showResult(data)`

**Propósito:** Exibe o overlay com o resultado do sorteio.

**Lógica:**
- `winner_type === 'prize'` e `is_exhausted_result === false`:
  - Título: "🎉 Parabéns!"
  - Subtítulo: nome do brinde
  - Imagem: se `image_url` não for null
  - Estilo: border verde, confetti (CSS animation)
- `winner_type === 'retry'` ou `is_exhausted_result === true`:
  - Título: "🔄 Tente Novamente!"
  - Subtítulo: "Boa sorte na próxima!"
  - Estilo: border laranja
- `winner_type === 'no_win'`:
  - Título: "😔 Não foi dessa vez"
  - Subtítulo: "Continue participando!"
  - Estilo: border cinza

**Fechar overlay:** Botão "OK" ou clique fora do modal → chama `loadWheel()` para re-sincronizar estado.

---

### Pré-carregamento de Imagens

Para evitar flash de imagem durante a animação, as imagens são pré-carregadas ao chamar `loadWheel()`:

```javascript
const imageCache = {};

function preloadImages(segments) {
    segments.forEach(seg => {
        if (seg.image_url) {
            const img = new Image();
            img.src = seg.image_url;
            imageCache[seg.id] = img;
        }
    });
}
```

---

## Cálculo de Ângulo do Vencedor

Este é o ponto mais crítico: o JS recebe `winner_id` da API e precisa calcular para qual ângulo a roda deve parar, de forma que o ponteiro (no topo) aponte para o segmento correto.

```javascript
function calculateTargetAngle(winnerId) {
    const winnerIndex = segments.findIndex(s => s.id === winnerId);
    const sliceAngle = (2 * Math.PI) / segments.length;

    // Ângulo do início do canvas é 0 = direita (3h no relógio)
    // O ponteiro está no TOPO (12h = -PI/2 ou 3*PI/2)
    // Precisamos que o CENTRO do segmento do vencedor fique no topo

    const segmentCenterAngle = winnerIndex * sliceAngle + sliceAngle / 2;

    // Para que o segmento fique no topo (ponteiro aponta para cima):
    // A roda deve rotacionar até que segmentCenterAngle + currentRotation = -PI/2
    // targetRotation = -PI/2 - segmentCenterAngle  (+ offset aleatório dentro do segmento)

    const randomOffset = (Math.random() - 0.5) * sliceAngle * 0.8;
    const spinRevolutions = (5 + Math.floor(Math.random() * 4)) * 2 * Math.PI;

    const baseTarget = -Math.PI / 2 - segmentCenterAngle + randomOffset;
    return currentRotation + spinRevolutions + (baseTarget - currentRotation % (2 * Math.PI));
}
```

---

## Renderização de Texto no Canvas

Texto longo é quebrado em múltiplas linhas via função `wrapText()`:

```javascript
function wrapText(ctx, text, maxWidth) {
    const words = text.split(' ');
    const lines = [];
    let line = '';
    words.forEach(word => {
        const test = line + (line ? ' ' : '') + word;
        if (ctx.measureText(test).width > maxWidth && line) {
            lines.push(line);
            line = word;
        } else {
            line = test;
        }
    });
    if (line) lines.push(line);
    return lines.slice(0, 2); // máximo 2 linhas
}
```

---

## Acessibilidade e UX

- **Teclado:** `Enter` e `Espaço` acionam o botão GIRAR (para uso com controle físico externo conectado via USB como teclado)
- **Duplo clique:** Prevenido por `isSpinning`
- **Estado de carregamento:** Botão exibe "..." enquanto a API /api/spin é chamada
- **Responsividade:** O Canvas redimensiona com `window.addEventListener('resize', resizeCanvas)` — o tamanho é sempre o menor entre largura e altura disponíveis menos margens
