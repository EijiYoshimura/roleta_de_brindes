/* ═══════════════════════════════════════════════════════════════
   Roulette JS — Roleta Virtual
   Canvas wheel + weighted spin animation (Vanilla JS)
   ═══════════════════════════════════════════════════════════════ */

'use strict';

// ── State ──────────────────────────────────────────────────────────────────
let segments   = [];        // Array of segment objects from /api/wheel
let rotation   = 0;         // Current rotation in radians
let isSpinning = false;

const canvas  = document.getElementById('wheel-canvas');
const ctx     = canvas ? canvas.getContext('2d') : null;
const btnSpin = document.getElementById('btn-spin');

// ── Bootstrap ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadWheel();

  // Keyboard support: Enter or Space triggers spin
  document.addEventListener('keydown', (e) => {
    if ((e.code === 'Enter' || e.code === 'Space') && !isSpinning) {
      e.preventDefault();
      spinWheel();
    }
    if (e.code === 'Escape') {
      closeResult();
    }
  });
});

// ── Load wheel data ────────────────────────────────────────────────────────
async function loadWheel() {
  try {
    const res  = await fetch('/api/wheel');
    const data = await res.json();
    segments = data.segments || [];

    if (segments.length === 0) {
      showEmptyState();
      return;
    }

    hideEmptyState();
    resizeCanvas();
    drawWheel(rotation);
  } catch (err) {
    console.error('Erro ao carregar a roda:', err);
    showEmptyState();
  }
}

// ── Canvas resize (responsive) ─────────────────────────────────────────────
function resizeCanvas() {
  if (!canvas) return;

  // Fit the wheel inside the available viewport space, leaving room for title + button
  const maxSize = Math.min(
    window.innerWidth  * 0.85,
    window.innerHeight * 0.60,
    560
  );
  const size = Math.max(maxSize, 200);

  canvas.width  = size;
  canvas.height = size;
}

window.addEventListener('resize', () => {
  if (segments.length > 0) {
    resizeCanvas();
    drawWheel(rotation);
  }
});

// ── Draw Wheel ─────────────────────────────────────────────────────────────
function drawWheel(rot) {
  if (!ctx || segments.length === 0) return;

  const size    = canvas.width;
  const cx      = size / 2;
  const cy      = size / 2;
  const radius  = size / 2 - 4;          // 4px padding for border shadow
  const n       = segments.length;
  const arc     = (2 * Math.PI) / n;     // equal arc per segment

  ctx.clearRect(0, 0, size, size);

  segments.forEach((seg, i) => {
    const startAngle = rot + i * arc - Math.PI / 2;
    const endAngle   = startAngle + arc;
    const midAngle   = startAngle + arc / 2;

    // ── Segment fill ─────────────────────────────────────────────────
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.closePath();

    if (seg.is_exhausted) {
      // Dessaturate: draw grey overlay
      ctx.fillStyle = _desaturate(seg.color, 0.15);
    } else {
      ctx.fillStyle = seg.color;
    }
    ctx.fill();

    // ── Segment border ────────────────────────────────────────────────
    ctx.strokeStyle = 'rgba(255,255,255,0.45)';
    ctx.lineWidth   = 2;
    ctx.stroke();

    // ── Image (if available and not exhausted) ────────────────────────
    const imgOffset = radius * 0.68;
    const imgX = cx + Math.cos(midAngle) * imgOffset;
    const imgY = cy + Math.sin(midAngle) * imgOffset;

    if (seg._img && seg._img.complete && !seg.is_exhausted) {
      const imgSize = Math.min(size * 0.09, 40);
      ctx.save();
      ctx.translate(imgX, imgY);
      ctx.rotate(midAngle + Math.PI / 2);
      // Circular clip
      ctx.beginPath();
      ctx.arc(0, 0, imgSize / 2, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(seg._img, -imgSize / 2, -imgSize / 2, imgSize, imgSize);
      ctx.restore();
    }

    // ── Text ──────────────────────────────────────────────────────────
    const textLabel = seg.is_exhausted ? 'ESGOTADO' : seg.name;
    const textColor = seg.is_exhausted ? 'rgba(0,0,0,0.4)' : _contrastColor(seg.color);

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(midAngle);

    const textDist = radius * (seg._img && !seg.is_exhausted ? 0.42 : 0.52);
    const fontSize = _calcFontSize(textLabel, arc, radius, size);

    ctx.font        = `bold ${fontSize}px system-ui, sans-serif`;
    ctx.fillStyle   = textColor;
    ctx.textAlign   = 'right';
    ctx.textBaseline = 'middle';

    // Handle text wrap if label is long
    const maxWidth = radius * 0.5;
    const words    = textLabel.split(' ');

    if (words.length > 1 && ctx.measureText(textLabel).width > maxWidth) {
      const half = Math.ceil(words.length / 2);
      const line1 = words.slice(0, half).join(' ');
      const line2 = words.slice(half).join(' ');
      const lineH = fontSize * 1.2;
      ctx.fillText(line1, textDist, -lineH / 2);
      ctx.fillText(line2, textDist,  lineH / 2);
    } else {
      ctx.fillText(textLabel, textDist, 0);
    }

    // "ESGOTADO" icon overlay (lock symbol)
    if (seg.is_exhausted) {
      ctx.font      = `${Math.max(fontSize * .9, 10)}px system-ui`;
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillText('🔒', textDist - ctx.measureText(textLabel).width - 4, 0);
    }

    ctx.restore();
  });

  // ── Center hub ────────────────────────────────────────────────────────
  const hubRadius = Math.min(size * 0.07, 24);
  const gradient  = ctx.createRadialGradient(cx, cy, hubRadius * 0.1, cx, cy, hubRadius);
  gradient.addColorStop(0, '#ffffff');
  gradient.addColorStop(1, '#cccccc');

  ctx.beginPath();
  ctx.arc(cx, cy, hubRadius, 0, 2 * Math.PI);
  ctx.fillStyle   = gradient;
  ctx.fill();
  ctx.strokeStyle = 'rgba(0,0,0,0.2)';
  ctx.lineWidth   = 2;
  ctx.stroke();
}

// ── Spin Wheel ─────────────────────────────────────────────────────────────
async function spinWheel() {
  if (isSpinning || segments.length === 0) return;

  isSpinning = true;
  btnSpin.disabled = true;
  canvas.classList.add('spinning');

  let winner = null;

  try {
    const res  = await fetch('/api/spin', { method: 'POST' });

    if (!res.ok) {
      const err = await res.json();
      _showError(err.message || 'Erro ao sortear.');
      _resetSpin();
      return;
    }

    winner = await res.json();
  } catch (err) {
    _showError('Sem conexão com o servidor.');
    _resetSpin();
    return;
  }

  // ── Calculate target angle ─────────────────────────────────────────
  const n          = segments.length;
  const arc        = (2 * Math.PI) / n;
  const winnerIdx  = segments.findIndex(s => s.id === winner.winner_id);
  const targetIdx  = winnerIdx >= 0 ? winnerIdx : 0;

  // Target rotation to place this segment's center under the top pointer.
  // drawWheel already subtracts PI/2 when drawing, so the pointer alignment
  // formula is simply: rot = -(idx * arc + arc/2)  (no extra -PI/2 here).
  const segCenter  = -(targetIdx * arc + arc / 2);

  // Add random jitter within ±35% of the segment arc (so pointer lands inside)
  const jitter     = (Math.random() - 0.5) * arc * 0.7;

  // Full spins (between 5 and 8) plus the target position
  const fullSpins  = (5 + Math.floor(Math.random() * 4)) * 2 * Math.PI;
  const targetRot  = (Math.ceil(rotation / (2 * Math.PI)) * 2 * Math.PI)
                   + fullSpins
                   + segCenter
                   + jitter;

  // ── Animate ────────────────────────────────────────────────────────
  const startRot      = rotation;
  const totalDelta    = targetRot - startRot;
  const duration      = SPIN_DURATION_MS;
  let   startTime     = null;

  function animate(ts) {
    if (!startTime) startTime = ts;
    const elapsed  = ts - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased    = _easeOutCubic(progress);

    rotation = startRot + totalDelta * eased;
    drawWheel(rotation);

    if (progress < 1) {
      requestAnimationFrame(animate);
    } else {
      rotation = targetRot % (2 * Math.PI);
      drawWheel(rotation);
      _onSpinComplete(winner);
    }
  }

  requestAnimationFrame(animate);
}

// ── Post-spin: show result overlay ────────────────────────────────────────
function _onSpinComplete(winner) {
  canvas.classList.remove('spinning');

  const overlay    = document.getElementById('result-overlay');
  const emojiEl    = document.getElementById('result-emoji');
  const labelEl    = document.getElementById('result-label');
  const titleEl    = document.getElementById('result-title');
  const imgEl      = document.getElementById('result-img');
  const msgEl      = document.getElementById('result-msg');

  // Reset classes
  titleEl.className = 'result-title';

  const exhaustedBadge = document.getElementById('exhausted-badge');
  if (exhaustedBadge) exhaustedBadge.remove();

  if (winner.is_exhausted_result) {
    // Brinde esgotado agindo como retry
    emojiEl.textContent    = '😅';
    labelEl.textContent    = 'Esgotado';
    titleEl.textContent    = 'Tente Novamente!';
    titleEl.classList.add('exhausted');
    msgEl.textContent      = `"${winner.winner_name}" acabou por hoje. Tente mais uma vez!`;

    // Badge
    const badge = document.createElement('div');
    badge.id = 'exhausted-badge';
    badge.className = 'exhausted-badge';
    badge.textContent = '🎁 ESGOTADO';
    titleEl.insertAdjacentElement('beforebegin', badge);

    imgEl.classList.add('hidden');

  } else if (winner.winner_type === 'prize') {
    emojiEl.textContent    = '🎉';
    labelEl.textContent    = 'Parabéns!';
    titleEl.textContent    = winner.winner_name;
    titleEl.classList.add('prize-win');
    const qty = winner.remaining_quantity;
    msgEl.textContent = qty !== null
      ? `Você ganhou! Restam ${qty} unidade${qty !== 1 ? 's' : ''}.`
      : 'Você ganhou um brinde!';

    imgEl.classList.add('hidden');
    if (winner.image_url) {
      imgEl.onload  = () => imgEl.classList.remove('hidden');
      imgEl.onerror = () => imgEl.classList.add('hidden');
      imgEl.src = winner.image_url;
      imgEl.alt = winner.winner_name;
    }

  } else if (winner.winner_type === 'retry') {
    emojiEl.textContent    = '🔄';
    labelEl.textContent    = 'Que pena!';
    titleEl.textContent    = 'Tente Novamente!';
    titleEl.classList.add('retry');
    msgEl.textContent      = 'Não foi dessa vez, mas tente outra rodada!';
    imgEl.classList.add('hidden');

  } else { // no_win
    emojiEl.textContent    = '😔';
    labelEl.textContent    = 'Não foi dessa vez';
    titleEl.textContent    = 'Não ganhou';
    titleEl.classList.add('no-win');
    msgEl.textContent      = 'Continue tentando! Quem sabe na próxima?';
    imgEl.classList.add('hidden');
  }

  overlay.classList.add('visible');
  document.getElementById('btn-ok').focus();
}

// ── Close result overlay ───────────────────────────────────────────────────
function closeResult() {
  const overlay = document.getElementById('result-overlay');
  overlay.classList.remove('visible');
  _resetSpin();

  // Reload wheel data to reflect updated quantities
  loadWheel();
}

// ── Helper: reset spin state ───────────────────────────────────────────────
function _resetSpin() {
  isSpinning = false;
  if (btnSpin) {
    btnSpin.disabled = false;
    btnSpin.focus();
  }
}

// ── Helper: show error (reuse result overlay) ─────────────────────────────
function _showError(msg) {
  const emojiEl = document.getElementById('result-emoji');
  const labelEl = document.getElementById('result-label');
  const titleEl = document.getElementById('result-title');
  const msgEl   = document.getElementById('result-msg');
  const imgEl   = document.getElementById('result-img');

  emojiEl.textContent  = '⚠️';
  labelEl.textContent  = 'Atenção';
  titleEl.textContent  = 'Não foi possível girar';
  titleEl.className    = 'result-title no-win';
  msgEl.textContent    = msg;
  imgEl.classList.add('hidden');

  document.getElementById('result-overlay').classList.add('visible');
}

// ── Empty / loaded state helpers ───────────────────────────────────────────
function showEmptyState() {
  const es = document.getElementById('empty-state');
  if (es) es.classList.remove('hidden');
  if (btnSpin) btnSpin.disabled = true;
  if (canvas)  canvas.style.display = 'none';
}

function hideEmptyState() {
  const es = document.getElementById('empty-state');
  if (es) es.classList.add('hidden');
  if (canvas) canvas.style.display = '';
}

// ── Preload images ─────────────────────────────────────────────────────────
// Called after loadWheel(); attaches Image objects to segment data so drawWheel can use them.
(function preloadImages() {
  // MutationObserver replacement: we hook into loadWheel via monkey-patch pattern.
  const _orig = loadWheel;
  window.loadWheel = async function() {
    await _orig.apply(this, arguments);
    segments.forEach(seg => {
      if (seg.image_url && !seg._img) {
        const img      = new Image();
        img.onload     = () => drawWheel(rotation);
        img.src        = seg.image_url;
        seg._img       = img;
      }
    });
  };
})();

// Ensure re-triggered loadWheel re-checks preloading
const _origLoad = loadWheel;
window.loadWheel = async function() {
  await _origLoad();
  segments.forEach(seg => {
    if (seg.image_url && !seg._img) {
      const img  = new Image();
      img.onload = () => drawWheel(rotation);
      img.src    = seg.image_url;
      seg._img   = img;
    }
  });
};

// ── Easing function ────────────────────────────────────────────────────────
function _easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3);
}

// ── Calc font size that fits arc ───────────────────────────────────────────
function _calcFontSize(text, arc, radius, canvasSize) {
  // Rough heuristic: chord length at 60% of radius
  const chord      = 2 * radius * 0.5 * Math.sin(arc / 2);
  const charWidth  = chord / Math.max(text.length, 1);
  return Math.min(Math.max(charWidth * 1.1, 9), canvasSize * 0.038);
}

// ── Desaturate a hex colour ────────────────────────────────────────────────
function _desaturate(hex, lightness) {
  let r = parseInt(hex.slice(1, 3), 16);
  let g = parseInt(hex.slice(3, 5), 16);
  let b = parseInt(hex.slice(5, 7), 16);
  const grey = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
  r = Math.round(r * lightness + grey * (1 - lightness));
  g = Math.round(g * lightness + grey * (1 - lightness));
  b = Math.round(b * lightness + grey * (1 - lightness));
  return `rgb(${r},${g},${b})`;
}

// ── Choose contrasting text colour (black or white) ───────────────────────
function _contrastColor(hex) {
  if (!hex || hex.length < 7) return '#ffffff';
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  // Perceived luminance formula
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.55 ? '#1e293b' : '#ffffff';
}
