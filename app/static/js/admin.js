/* ═══════════════════════════════════════════════════════════════
   Admin JS — Roleta Virtual
   Pure Vanilla JS, no external dependencies
   ═══════════════════════════════════════════════════════════════ */

/* ── Tipo de item: mostrar/esconder campos condicionais ───────── */
function updateFormFields() {
  const type = document.getElementById('item_type')?.value;
  if (!type) return;

  const groupQty        = document.getElementById('group-quantity');
  const groupExhausted  = document.getElementById('group-exhausted');
  const groupWeight     = document.getElementById('group-weight');

  if (!groupQty || !groupExhausted || !groupWeight) return;

  if (type === 'prize') {
    groupQty.style.display       = '';
    groupExhausted.style.display = '';
    groupWeight.style.display    = 'none';
    // Quantidade obrigatória para brindes
    document.getElementById('quantity').required = true;
  } else {
    groupQty.style.display       = 'none';
    groupExhausted.style.display = 'none';
    groupWeight.style.display    = '';
    document.getElementById('quantity').required = false;
  }
}

/* ── Preview de imagem no formulário ─────────────────────────── */
function previewImage(input) {
  const preview = document.getElementById('img-preview');
  if (!preview) return;

  if (input.files && input.files[0]) {
    const file = input.files[0];

    // Validação de tamanho (5 MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Arquivo muito grande! Máximo permitido: 5 MB.');
      input.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      preview.src = e.target.result;
      preview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  }
}

/* ── Sincronização slider ↔ input numérico (peso) ────────────── */
function syncWeight(value) {
  const num   = document.getElementById('weight');
  const pct   = document.getElementById('weight-pct');
  const float = (parseFloat(value) / 100).toFixed(2);
  if (num)  num.value  = float;
  if (pct)  pct.textContent = value + '%';
}

function syncWeightFromNumber(value) {
  const range = document.getElementById('weight-range');
  const pct   = document.getElementById('weight-pct');
  const intVal = Math.round(parseFloat(value) * 100);
  if (range) range.value     = intVal;
  if (pct)   pct.textContent = intVal + '%';
}

/* ── Confirmação de exclusão ─────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Todos os forms de exclusão recebem confirmação
  document.querySelectorAll('.form-delete').forEach((form) => {
    form.addEventListener('submit', (e) => {
      const name = form.dataset.name || 'este item';
      if (!confirm(`Excluir "${name}"? Esta ação não pode ser desfeita.`)) {
        e.preventDefault();
      }
    });
  });

  // Inicializar campos condicionais
  updateFormFields();

  // Atualizar label da cor em tempo real
  const colorInput = document.getElementById('color');
  const colorLabel = document.getElementById('color-label');
  if (colorInput && colorLabel) {
    colorInput.addEventListener('input', () => {
      colorLabel.textContent = colorInput.value;
    });
  }
});

/* ── Settings: sliders de peso ───────────────────────────────── */
function updateWeightDisplay(key, value) {
  const display  = document.getElementById(`${key}-display`);
  const hidden   = document.getElementById(`${key}_weight`);
  const float    = (parseFloat(value) / 100).toFixed(2);

  if (display) display.textContent = value + '%';
  if (hidden)  hidden.value = float;

  _recalcWeightSummary();
}

function _recalcWeightSummary() {
  const retryRange  = document.getElementById('retry_weight_range');
  const noWinRange  = document.getElementById('no_win_weight_range');
  const sumEl       = document.getElementById('weight-sum');
  const remainEl    = document.getElementById('weight-remaining');

  if (!retryRange || !noWinRange || !sumEl || !remainEl) return;

  const sum = parseInt(retryRange.value, 10) + parseInt(noWinRange.value, 10);
  sumEl.textContent    = sum + '%';
  remainEl.textContent = (100 - sum) + '%';

  // Alerta visual se soma > 99
  const summary = document.getElementById('weight-summary');
  if (summary) {
    summary.classList.toggle('weight-warning', sum >= 100);
  }
}

/* ── Settings: slider de duração do giro ─────────────────────── */
function updateSpinDisplay(value) {
  const display = document.getElementById('spin-display');
  if (display) display.textContent = value + 'ms';
}
