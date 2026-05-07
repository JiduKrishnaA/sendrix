/* ============================================================
   SENDRIX EASTER EGGS
   CoBrA  → 3D Snake Game
   HappyFace → Emoji Alchemy
   ============================================================ */

(function () {
  'use strict';

  // ─── TRIGGER DETECTION ───────────────────────────────────────
  function initTrigger() {
    const input = document.getElementById('easter-code-input');
    if (!input) return;
    input.addEventListener('input', function () {
      const v = input.value;
      if (v === 'CoBrA') { input.value = ''; openSnake(); }
      else if (v === 'HappyFace') { input.value = ''; openAlchemy(); }
    });
  }

  // ─── UTILITY ─────────────────────────────────────────────────
  function $(id) { return document.getElementById(id); }

  function closeOverlay(id) {
    const el = $(id);
    if (el) { el.style.opacity = '0'; setTimeout(() => el.style.display = 'none', 300); }
  }

  function openOverlay(id) {
    const el = $(id);
    if (!el) return;
    el.style.display = 'flex';
    requestAnimationFrame(() => el.style.opacity = '1');
  }

  // ─────────────────────────────────────────────────────────────
  // EASTER EGG 1 : 3D SNAKE
  // ─────────────────────────────────────────────────────────────
  let snakeRAF = null, snakeRunning = false;

  function openSnake() {
    openOverlay('snake-overlay');
    startSnake();
  }

  function closeSnake() {
    snakeRunning = false;
    cancelAnimationFrame(snakeRAF);
    closeOverlay('snake-overlay');
  }

  function startSnake() {
    const canvas = $('snake-canvas');
    const ctx = canvas.getContext('2d');

    // Responsive size
    const size = Math.min(window.innerWidth * 0.85, window.innerHeight * 0.7, 540);
    canvas.width = canvas.height = size;

    const GRID = 20;        // grid cells
    const CELL = size / GRID;

    // Game state
    let snake, dir, nextDir, food, score, speed, lastTime, tickAcc;

    function resetGame() {
      snake = [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }];
      dir = { x: 1, y: 0 };
      nextDir = { x: 1, y: 0 };
      food = spawnFood();
      score = 0;
      speed = 180;
      lastTime = null;
      tickAcc = 0;
      $('snake-score').textContent = '0';
    }

    function spawnFood() {
      let f;
      do { f = { x: Math.floor(Math.random() * GRID), y: Math.floor(Math.random() * GRID) }; }
      while (snake.some(s => s.x === f.x && s.y === f.y));
      return f;
    }

    // Standard 2D draw helpers
    function drawGrid() {
      ctx.fillStyle = '#050c05';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = 'rgba(0, 255, 100, 0.05)';
      ctx.lineWidth = 1;
      for (let i = 0; i <= GRID; i++) {
        // vertical
        ctx.beginPath();
        ctx.moveTo(i * CELL, 0);
        ctx.lineTo(i * CELL, canvas.height);
        ctx.stroke();
        // horizontal
        ctx.beginPath();
        ctx.moveTo(0, i * CELL);
        ctx.lineTo(canvas.width, i * CELL);
        ctx.stroke();
      }
    }

    function drawSnake() {
      snake.forEach((seg, i) => {
        ctx.fillStyle = i === 0 ? '#00ff88' : `hsl(${145 - i * 4}, 90%, 50%)`;
        if (i === 0) {
          ctx.shadowColor = '#00ff88';
          ctx.shadowBlur = 12;
        } else {
          ctx.shadowBlur = 0;
        }

        const x = seg.x * CELL + 2;
        const y = seg.y * CELL + 2;
        const w = CELL - 4;
        const h = CELL - 4;
        const r = CELL * 0.25;

        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(x, y, w, h, r);
        } else {
          ctx.rect(x, y, w, h);
        }
        ctx.fill();
      });
      ctx.shadowBlur = 0; // reset
    }

    function drawFood() {
      const pulse = 1 + 0.15 * Math.sin(Date.now() / 150);
      const cx = food.x * CELL + CELL / 2;
      const cy = food.y * CELL + CELL / 2;
      const r = (CELL / 2.6) * pulse;

      ctx.shadowColor = '#ff3366';
      ctx.shadowBlur = 15;
      ctx.fillStyle = '#ff3366';
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0; // reset
    }

    function gameOver() {
      snakeRunning = false;
      ctx.fillStyle = 'rgba(0,0,0,0.6)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#ff4444';
      ctx.font = `bold ${Math.round(size / 12)}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 20);
      ctx.fillStyle = '#aaffaa';
      ctx.font = `${Math.round(size / 20)}px Inter, sans-serif`;
      ctx.fillText(`Score: ${score}  •  Press R to restart`, canvas.width / 2, canvas.height / 2 + 20);
    }

    function tick() {
      dir = { ...nextDir };
      const head = { x: (snake[0].x + dir.x + GRID) % GRID, y: (snake[0].y + dir.y + GRID) % GRID };
      if (snake.some(s => s.x === head.x && s.y === head.y)) { gameOver(); return; }
      snake.unshift(head);
      if (head.x === food.x && head.y === food.y) {
        score++;
        $('snake-score').textContent = score;
        food = spawnFood();
        if (speed > 60) speed -= 4;
      } else { snake.pop(); }
    }

    function loop(ts) {
      if (!snakeRunning) return;
      if (lastTime === null) lastTime = ts;
      tickAcc += ts - lastTime;
      lastTime = ts;
      if (tickAcc >= speed) { tick(); tickAcc -= speed; }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      drawGrid();
      drawFood();
      drawSnake();
      snakeRAF = requestAnimationFrame(loop);
    }

    // Keys
    function onKey(e) {
      const map = {
        ArrowUp: { x: 0, y: -1 }, ArrowDown: { x: 0, y: 1 },
        ArrowLeft: { x: -1, y: 0 }, ArrowRight: { x: 1, y: 0 },
        w: { x: 0, y: -1 }, s: { x: 0, y: 1 },
        a: { x: -1, y: 0 }, d: { x: 1, y: 0 },
        W: { x: 0, y: -1 }, S: { x: 0, y: 1 },
        A: { x: -1, y: 0 }, D: { x: 1, y: 0 },
      };
      if (e.key === 'Escape') { closeSnake(); return; }
      if (e.key === 'r' || e.key === 'R') { snakeRunning = false; cancelAnimationFrame(snakeRAF); resetGame(); snakeRunning = true; snakeRAF = requestAnimationFrame(loop); return; }
      const nd = map[e.key];
      if (nd && !(nd.x === -dir.x && nd.y === -dir.y)) nextDir = nd;
      if (map[e.key]) e.preventDefault();
    }

    document.addEventListener('keydown', onKey);
    // Clean up listener on close
    $('snake-close-btn').onclick = function () {
      document.removeEventListener('keydown', onKey);
      closeSnake();
    };
    $('snake-restart-btn').onclick = function () {
      snakeRunning = false;
      cancelAnimationFrame(snakeRAF);
      resetGame();
      snakeRunning = true;
      snakeRAF = requestAnimationFrame(loop);
    };

    // On-screen D-Pad Controls for Mobile
    const upBtn = $('dpad-up');
    const downBtn = $('dpad-down');
    const leftBtn = $('dpad-left');
    const rightBtn = $('dpad-right');

    function setDirection(nd) {
      if (nd && !(nd.x === -dir.x && nd.y === -dir.y)) nextDir = nd;
    }

    if (upBtn) {
      upBtn.onclick = () => setDirection({ x: 0, y: -1 });
      upBtn.addEventListener('touchstart', (e) => { e.preventDefault(); setDirection({ x: 0, y: -1 }); });
    }
    if (downBtn) {
      downBtn.onclick = () => setDirection({ x: 0, y: 1 });
      downBtn.addEventListener('touchstart', (e) => { e.preventDefault(); setDirection({ x: 0, y: 1 }); });
    }
    if (leftBtn) {
      leftBtn.onclick = () => setDirection({ x: -1, y: 0 });
      leftBtn.addEventListener('touchstart', (e) => { e.preventDefault(); setDirection({ x: -1, y: 0 }); });
    }
    if (rightBtn) {
      rightBtn.onclick = () => setDirection({ x: 1, y: 0 });
      rightBtn.addEventListener('touchstart', (e) => { e.preventDefault(); setDirection({ x: 1, y: 0 }); });
    }

    resetGame();
    snakeRunning = true;
    snakeRAF = requestAnimationFrame(loop);
  }

  // ─────────────────────────────────────────────────────────────
  // EASTER EGG 2 : EMOJI ALCHEMY
  // ─────────────────────────────────────────────────────────────
  const EMOJI_CATEGORIES = {
    '🔥 Elements': ['🔥', '💧', '🌊', '❄️', '⚡', '💨', '🌪️', '🌋', '☀️', '🌧️', '🌙', '⭐'],
    '🌿 Nature':   ['🌱', '🌿', '🍃', '🌸', '🌺', '🍎', '🍋', '🍇', '🌾', '🌴', '🌹', '🌍'],
    '🐾 Animals':  ['🦁', '🐯', '🐺', '🐟', '🐬', '🦅', '🐝', '🐛', '🦋', '🐊', '🦇', '🐸'],
    '👤 People':   ['👶', '👦', '👸', '🤴', '🧙', '👨', '🧑', '💀', '🦸', '👑', '🦶', '🧒'],
    '🍽️ Food':     ['🥚', '🍳', '🧁', '🎂', '🍺', '🍷', '🧋', '🥤', '☕', '🥛', '🧁', '🥧'],
    '🔧 Objects':  ['🔑', '🏠', '📱', '💻', '💡', '📚', '⚙️', '💎', '🔮', '🏏', '⚽', '⏳'],
    '🎵 Arts':     ['🎵', '🎶', '🎨', '🎭', '🎬', '🎤', '🎸', '🥁', '🎹', '🎺', '🎻', '🎼'],
    '🏔️ Places':   ['🏠', '🏡', '🏛️', '🏝️', '🏔️', '🌆', '🌃', '🚀', '🔬', '🪵', '🌿', '🗿'],
  };

  let slot1 = null, slot2 = null;
  let alchemyHistory = [];

  function openAlchemy() {
    slot1 = null; slot2 = null;
    renderAlchemy();
    openOverlay('alchemy-overlay');
  }

  function closeAlchemy() { closeOverlay('alchemy-overlay'); }

  function renderAlchemy() {
    // Category tabs + grid
    const tabBar = $('alchemy-tabs');
    const grid = $('alchemy-grid');
    if (!tabBar || !grid) return;

    const cats = Object.keys(EMOJI_CATEGORIES);
    let activeTab = cats[0];

    function renderGrid(cat) {
      grid.innerHTML = '';
      EMOJI_CATEGORIES[cat].forEach(em => {
        const btn = document.createElement('button');
        btn.className = 'alchemy-emoji-btn';
        btn.textContent = em;
        btn.title = em;
        btn.onclick = () => pickEmoji(em);
        grid.appendChild(btn);
      });
    }

    tabBar.innerHTML = '';
    cats.forEach(cat => {
      const tb = document.createElement('button');
      tb.className = 'alchemy-tab' + (cat === activeTab ? ' active' : '');
      tb.textContent = cat.split(' ')[0]; // just the emoji icon
      tb.title = cat;
      tb.onclick = () => {
        activeTab = cat;
        tabBar.querySelectorAll('.alchemy-tab').forEach(t => t.classList.remove('active'));
        tb.classList.add('active');
        renderGrid(cat);
      };
      tabBar.appendChild(tb);
    });
    renderGrid(activeTab);
    updateSlots();
  }

  function updateSlots() {
    const s1 = $('alchemy-slot1');
    const s2 = $('alchemy-slot2');
    if (s1) s1.textContent = slot1 || '+';
    if (s2) s2.textContent = slot2 || '+';

    const clearBtn = $('alchemy-clear-btn');
    if (clearBtn) clearBtn.disabled = !slot1 && !slot2;

    const combineBtn = $('alchemy-combine-btn');
    if (combineBtn) combineBtn.disabled = !slot1 || !slot2;
  }

  function pickEmoji(em) {
    if (!slot1) { slot1 = em; }
    else if (!slot2) { slot2 = em; }
    else { slot1 = slot2; slot2 = em; }
    updateSlots();
  }

  async function combineEmojis() {
    if (!slot1 || !slot2) return;
    const btn = $('alchemy-combine-btn');
    const resultBox = $('alchemy-result');
    btn.disabled = true;
    btn.textContent = '⏳ Mixing...';
    resultBox.innerHTML = '<span class="alchemy-spinner">🔮</span>';

    try {
      const resp = await fetch('/api/emoji-alchemy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emoji1: slot1, emoji2: slot2 })
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);

      // Record history
      const combo = { e1: slot1, e2: slot2, result: data.result, name: data.name, desc: data.description };
      alchemyHistory.unshift(combo);
      if (alchemyHistory.length > 10) alchemyHistory.pop();

      resultBox.innerHTML = `
        <div class="alchemy-result-emoji" id="alchemy-result-em">${data.result}</div>
        <div class="alchemy-result-name">${data.name}</div>
        <div class="alchemy-result-desc">${data.description}</div>
        <button class="alchemy-use-btn" onclick="window._alchemyUse('${data.result}')">Use as ingredient ➕</button>
      `;
      renderHistory();

    } catch (e) {
      resultBox.innerHTML = `<div style="color:#ff6b6b">⚠️ ${e.message || 'Combination failed'}</div>`;
    }
    btn.disabled = false;
    btn.textContent = '✨ Combine!';
  }

  window._alchemyUse = function (em) {
    if (!slot1) { slot1 = em; }
    else if (!slot2) { slot2 = em; }
    else { slot1 = em; slot2 = null; }
    updateSlots();
  };

  function renderHistory() {
    const hist = $('alchemy-history');
    if (!hist || alchemyHistory.length === 0) return;
    hist.innerHTML = alchemyHistory.map(c =>
      `<div class="alchemy-hist-row">${c.e1} + ${c.e2} = <strong>${c.result}</strong> <em>${c.name}</em></div>`
    ).join('');
  }

  // Wire combine / clear buttons (called after DOM ready)
  function wireAlchemyButtons() {
    const cb = $('alchemy-combine-btn');
    if (cb) cb.onclick = combineEmojis;
    const clr = $('alchemy-clear-btn');
    if (clr) clr.onclick = () => { slot1 = null; slot2 = null; updateSlots(); $('alchemy-result').innerHTML = ''; };
    const cl = $('alchemy-close-btn');
    if (cl) cl.onclick = closeAlchemy;
    const s1btn = $('alchemy-slot1');
    if (s1btn) s1btn.onclick = () => { slot1 = null; updateSlots(); };
    const s2btn = $('alchemy-slot2');
    if (s2btn) s2btn.onclick = () => { slot2 = null; updateSlots(); };
  }

  // ─── BOOT ─────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    initTrigger();
    wireAlchemyButtons();
  });

})();
