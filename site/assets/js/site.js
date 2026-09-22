/* EDIFY public site — motion and small behaviours.
   A plain-JS port of the Component in EDIFY Site.dc.html: boot, reveal system,
   canvas field, plate gallery, velocity marquee, stacked cards, meter, typed
   terminals, tabbed matrix, bars and counters, all driven by one rAF loop.
   The page reads fully without this file: nothing is hidden until JS hides it. */
(function () {
  'use strict';

  var doc = document;
  var root = doc.documentElement;
  var reduced = window.matchMedia('(prefers-reduced-motion:reduce)').matches;
  var small = window.innerWidth < 560;
  var $ = function (s, r) { return (r || doc).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || doc).querySelectorAll(s)); };

  var S = {
    counters: [], pending: [], skew: 0, vel: 0, lastY: window.scrollY,
    marqueeOffset: 0, dir: 1, frameTimes: [], meterT: 0, hidden: false, rafDead: false, n: 0
  };

  /* ---------- menu, copy buttons, year ---------- */

  function setupChrome() {
    var menu = $('#ed-menu');
    $$('[data-menu-toggle]').forEach(function (b) {
      b.addEventListener('click', function () {
        if (!menu) return;
        var open = !menu.classList.contains('open');
        menu.classList.toggle('open', open);
        doc.body.style.overflow = open ? 'hidden' : '';
        $$('[data-menu-toggle]').forEach(function (x) { x.setAttribute('aria-expanded', String(open)); });
      });
    });
    window.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu && menu.classList.contains('open')) $('[data-menu-toggle]').click();
    });

    $$('[data-copy]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var text = btn.getAttribute('data-copy');
        var done = function () {
          var was = btn.textContent;
          btn.textContent = 'copied';
          btn.classList.add('done');
          setTimeout(function () { btn.textContent = was; btn.classList.remove('done'); }, 1400);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () {});
        else {
          var t = doc.createElement('textarea'); t.value = text; doc.body.appendChild(t); t.select();
          try { doc.execCommand('copy'); done(); } catch (e) {}
          t.remove();
        }
      });
    });

    $$('[data-year]').forEach(function (el) { el.textContent = String(new Date().getFullYear()); });
  }

  /* ---------- logo spine redraw on hover ---------- */

  function setupLogo() {
    var lock = $('.lockup');
    if (!lock || reduced) return;
    var spine = lock.querySelector('[data-nav-spine]');
    lock.addEventListener('pointerenter', function () {
      if (!spine) return;
      var L = spine.getTotalLength();
      spine.style.transition = 'none';
      spine.style.strokeDasharray = L;
      spine.style.strokeDashoffset = L;
      void spine.getBoundingClientRect();
      spine.style.transition = 'stroke-dashoffset var(--d-el) var(--e-emph)';
      spine.style.strokeDashoffset = '0';
    });
  }

  /* ---------- reveal system ---------- */

  function prep(el) {
    var kind = el.dataset.rv;
    if (kind === 'card') el.style.opacity = '0';
    else if (kind === 'media') el.style.clipPath = 'inset(0 0 100% 0)';
    else if (kind === 'rule') { el.style.transform = 'scaleX(0)'; el.style.transformOrigin = 'center'; }
    else if (kind === 'claim') $$('.ln > span', el).forEach(function (s) { s.style.transform = 'translate3d(0,110%,0)'; });
    else if (kind === 'num') {
      el.dataset.text = el.textContent;
      el.textContent = (el.dataset.prefix || '') + '0' + (el.dataset.suffix || '');
      var src = el.parentNode.querySelector('.num-s');
      if (src) src.style.opacity = '0';
    }
  }

  function reveal(el) {
    if (el.dataset.in === '1') return;
    el.dataset.in = '1';
    var kind = el.dataset.rv;
    var step = el.dataset.step === 'tight' ? 40 : 60;
    var d = Math.min(parseInt(el.dataset.i || '0', 10), 12) * step;
    var clear = function () { el.style.willChange = ''; };
    if (kind === 'card') {
      el.style.willChange = 'opacity, filter, transform';
      el.style.animation = (small ? 'blurFadeUpSm' : 'blurFadeUp') + ' var(--d-section) var(--e-out) ' + d + 'ms both';
      el.addEventListener('animationend', function () { clear(); el.style.opacity = '1'; }, { once: true });
    } else if (kind === 'media') {
      el.style.willChange = 'clip-path';
      el.style.transition = 'clip-path var(--d-section) var(--e-emph) ' + d + 'ms';
      void el.offsetWidth;
      el.style.clipPath = 'inset(0 0 0% 0)';
      el.addEventListener('transitionend', clear, { once: true });
    } else if (kind === 'rule') {
      el.style.willChange = 'transform';
      el.style.transition = 'transform var(--d-section) var(--e-out)';
      void el.offsetWidth;
      el.style.transform = 'scaleX(1)';
      el.addEventListener('transitionend', clear, { once: true });
    } else if (kind === 'claim') {
      var lines = $$('.ln > span', el);
      void el.offsetWidth;
      lines.forEach(function (s, n) {
        s.style.willChange = 'transform';
        s.style.transition = 'transform var(--d-section) var(--e-out) ' + (n * 110) + 'ms';
        s.style.transform = 'translate3d(0,0,0)';
        s.addEventListener('transitionend', function () { s.style.willChange = ''; }, { once: true });
      });
    } else if (kind === 'num') {
      var src = el.parentNode.querySelector('.num-s');
      if (S.rafDead) {
        el.textContent = el.dataset.text;
        if (src) { src.style.transition = 'opacity var(--d-el) var(--e-edify)'; src.style.opacity = '1'; }
      } else {
        S.counters.push({ el: el, target: parseFloat(el.dataset.value || '0'), dec: parseInt(el.dataset.dec || '0', 10), t0: 0, dur: 900, delay: d, src: src });
      }
    }
  }

  function setupReveal() {
    var els = $$('[data-rv]');
    if (reduced) { S.pending = []; return; }
    els.forEach(prep);
    S.pending = els;
    sweep();
  }

  function sweep() {
    var vh = window.innerHeight;
    if (S.pending.length) {
      var rest = [];
      for (var i = 0; i < S.pending.length; i++) {
        var el = S.pending[i];
        if (el.getBoundingClientRect().top < vh * 0.92) reveal(el); else rest.push(el);
      }
      S.pending = rest;
    }
    if (!S.barsDone) {
      var bars = $$('[data-bar]');
      if (bars.length && bars[0].getBoundingClientRect().top < vh * 0.88 && bars[0].offsetParent) {
        S.barsDone = true;
        if (!reduced) bars.forEach(function (b, i) {
          b.style.transform = 'scaleX(0)';
          b.style.willChange = 'transform';
          void b.offsetWidth;
          b.style.transition = 'transform var(--d-section) var(--e-edify) ' + (i * 60) + 'ms';
          b.style.transform = 'scaleX(1)';
          b.addEventListener('transitionend', function () { b.style.willChange = ''; }, { once: true });
        });
      }
    }
    S.terms.forEach(function (t) {
      if (!t.done && t.host.getBoundingClientRect().top < vh * 0.85 && t.host.offsetParent) { t.done = true; runTerminal(t); }
    });
  }

  /* ---------- terminals: the lines are real output, already in the HTML ---------- */

  function setupTerminals() {
    S.terms = $$('[data-term]').map(function (host) {
      var lines = $$('.l', host);
      if (!reduced) lines.forEach(function (l) { l.style.opacity = '0'; });
      return { host: host, lines: lines, done: reduced };
    });
  }

  function runTerminal(t) {
    var caret = doc.createElement('span');
    caret.className = 'caret';
    var step = function (i) {
      if (i >= t.lines.length) { var last = t.lines[t.lines.length - 1]; if (last) last.appendChild(caret); return; }
      var ln = t.lines[i];
      ln.style.transition = 'opacity 160ms linear';
      ln.style.opacity = '1';
      var c = ln.classList;
      var wait = ln.textContent.trim() === '' ? 60 : (c.contains('cmd') ? 380 : (c.contains('dim') ? 220 : 150));
      setTimeout(function () { step(i + 1); }, wait);
    };
    step(0);
  }

  /* ---------- tabs (matrix) ---------- */

  function setupTabs() {
    $$('[data-tabs]').forEach(function (group) {
      var btns = $$('[role="tab"]', group);
      var body = $('#' + group.getAttribute('data-tabs'));
      btns.forEach(function (b, i) {
        b.addEventListener('click', function () { select(i); });
        b.addEventListener('keydown', function (e) {
          if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
            e.preventDefault();
            var n = (i + (e.key === 'ArrowRight' ? 1 : btns.length - 1)) % btns.length;
            select(n); btns[n].focus();
          }
        });
      });
      function select(i) {
        if (btns[i].getAttribute('aria-selected') === 'true') return;
        btns.forEach(function (b, n) {
          b.setAttribute('aria-selected', String(n === i));
          b.tabIndex = n === i ? 0 : -1;
          var p = doc.getElementById(b.getAttribute('aria-controls'));
          if (p) p.hidden = n !== i;
        });
        if (!body || reduced) return;
        body.style.animation = 'none';
        void body.offsetWidth;
        body.style.willChange = 'clip-path';
        body.style.animation = 'edWipe var(--d-el) var(--e-edify) both';
        body.addEventListener('animationend', function () { body.style.willChange = ''; }, { once: true });
        var panel = doc.getElementById(btns[i].getAttribute('aria-controls'));
        $$('.row', panel).forEach(function (r, n) {
          r.style.opacity = '0';
          r.style.transition = 'opacity var(--d-el) var(--e-edify) ' + (n * 40) + 'ms';
          void r.offsetWidth;
          r.style.opacity = '1';
        });
      }
    });
  }

  /* ---------- FAQ: one open at a time is not enforced; smooth reveal only ---------- */

  function setupFaq() {
    if (reduced) return;
    $$('.faq details').forEach(function (d) {
      d.addEventListener('toggle', function () {
        if (!d.open) return;
        var a = d.querySelector('.ans');
        if (a) { a.style.animation = 'none'; void a.offsetWidth; a.style.animation = 'blurFadeUpSm var(--d-el) var(--e-out) both'; }
      });
    });
  }

  /* ---------- boot ---------- */

  function setupBoot() {
    if (!root.hasAttribute('data-boot')) return;
    clearTimeout(window.__edBootFallback);
    S.bootStart = performance.now();
    var grid = $('.boot-grid');
    if (grid) { grid.style.transition = 'opacity 700ms var(--e-out)'; void grid.offsetWidth; grid.style.opacity = '1'; }
    $$('[data-boot-draw]').forEach(function (draw, i) {
      var L = draw.getTotalLength();
      draw.style.strokeDasharray = L;
      draw.style.strokeDashoffset = L;
      draw.style.transition = 'stroke-dashoffset 1500ms var(--e-emph) ' + (i * 260) + 'ms';
      void draw.getBoundingClientRect();
      draw.style.strokeDashoffset = '0';
    });
    var word = $('.boot-word');
    if (word) {
      word.style.transition = 'opacity 800ms var(--e-out) 900ms, letter-spacing 1200ms var(--e-emph) 900ms';
      word.style.letterSpacing = '0.24em';
      void word.offsetWidth;
      word.style.opacity = '1';
      word.style.letterSpacing = '0.02em';
    }
    var log = $('#ed-boot-log');
    var steps = ['reading every file', 'building the map', 'mirroring skills into each runtime', 'next: /spec'];
    if (log) steps.forEach(function (s, i) {
      setTimeout(function () {
        if (S.booted) return;
        var d = doc.createElement('div');
        d.textContent = s;
        d.style.cssText = 'opacity:0;transition:opacity 240ms linear;color:' + (i === steps.length - 1 ? 'var(--ed-blue-bright)' : 'var(--ed-text-3)');
        log.appendChild(d);
        void d.offsetWidth;
        d.style.opacity = '1';
        while (log.children.length > 3) log.removeChild(log.firstChild);
      }, 420 + i * 460);
    });
    S.bootCap = setTimeout(function () { endBoot(); }, 2600);
    var skip = function () { endBoot(); };
    window.addEventListener('keydown', skip, { once: true });
    window.addEventListener('pointerdown', skip, { once: true });
    Promise.all([
      doc.fonts ? doc.fonts.ready : Promise.resolve(),
      new Promise(function (res) { S.firstFrameResolve = res; setTimeout(res, 1200); })
    ]).then(function () {
      var wait = Math.max(0, 2000 - (performance.now() - S.bootStart));
      S.bootReady = setTimeout(endBoot, wait);
    });
  }

  function endBoot() {
    if (S.booted) return;
    S.booted = true;
    clearTimeout(S.bootCap);
    clearTimeout(S.bootReady);
    try { sessionStorage.setItem('ed:boot', '1'); } catch (e) {}
    var ov = $('#ed-boot'), bm = $('#ed-boot-mark'), nm = $('.lockup svg');
    var done = function () { root.removeAttribute('data-boot'); if (nm) nm.style.opacity = ''; };
    if (!ov || !bm || !nm) { done(); return; }
    $$('.boot-hide,.boot-word,.boot-grid', ov).forEach(function (e) { e.style.transition = 'opacity 260ms linear'; e.style.opacity = '0'; });
    var bg = $('.boot-bg', ov);
    if (bg) { bg.style.transition = 'opacity var(--d-flip) var(--e-in-out)'; bg.style.opacity = '0'; }
    var a = bm.getBoundingClientRect(), b = nm.getBoundingClientRect();
    nm.style.opacity = '0';
    var anim = bm.animate ? bm.animate(
      [{ transform: 'none' }, { transform: 'translate(' + (b.left - a.left) + 'px, ' + (b.top - a.top) + 'px) scale(' + (b.width / a.width) + ')' }],
      { duration: 700, easing: 'cubic-bezier(0.22,1,0.36,1)', fill: 'forwards' }) : null;
    if (anim && anim.finished) anim.finished.then(done).catch(done); else setTimeout(done, 700);
  }

  /* ---------- gallery ---------- */

  function setupGallery() {
    var track = $('#ed-track');
    S.frames = [];
    if (!track) return;
    var frames = S.frames = $$('[data-frame]', track);
    var count = $('#ed-gallery-count'), bar = $('#ed-gallery-bar');
    var fine = window.matchMedia('(hover:hover) and (pointer:fine)').matches;
    var pad = function (n) { return ('0' + n).slice(-2); };
    var sync = function () {
      var max = track.scrollWidth - track.clientWidth;
      var p = max > 0 ? track.scrollLeft / max : 0;
      var idx = Math.min(frames.length, Math.max(1, Math.round(p * (frames.length - 1)) + 1));
      if (count) count.textContent = pad(idx) + ' / ' + pad(frames.length);
      if (bar) bar.style.width = (100 / frames.length + p * (100 - 100 / frames.length)) + '%';
    };
    track.addEventListener('scroll', sync, { passive: true });
    sync();
    frames.forEach(function (f) {
      var img = f.querySelector('img');
      var on = function () { if (img) img.style.filter = 'grayscale(0)'; };
      var off = function () { if (img) img.style.filter = 'grayscale(1)'; };
      f.addEventListener('focus', function () {
        on();
        f.style.borderColor = 'var(--ed-blue)';
        f.style.background = 'var(--ed-plate)';
        var r = f.getBoundingClientRect(), t = track.getBoundingClientRect();
        track.scrollLeft += (r.left - t.left) - (t.width - r.width) / 2;
      });
      f.addEventListener('blur', function () { off(); f.style.borderColor = ''; f.style.background = ''; f.dataset.mag = ''; });
      f.addEventListener('pointerenter', on);
      f.addEventListener('pointerleave', function () { off(); f.dataset.mag = ''; });
      f.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); expand(f); } });
      f.addEventListener('click', function () { expand(f); });
      if (fine && !reduced) f.addEventListener('pointermove', function (e) {
        var r = f.getBoundingClientRect();
        var dx = (e.clientX - r.left) / r.width - 0.5, dy = (e.clientY - r.top) / r.height - 0.5;
        f.dataset.mag = 'translate3d(' + (dx * 14) + 'px,' + (dy * 14) + 'px,0) rotateX(' + (-dy * 6) + 'deg) rotateY(' + (dx * 6) + 'deg)';
      });
    });
    track.style.perspective = '1200px';
  }

  function expand(frame) {
    var body = frame.lastElementChild;
    if (!body) return;
    frame.setAttribute('aria-expanded', frame.dataset.open === '1' ? 'false' : 'true');
    if (frame.dataset.open === '1') {
      frame.dataset.open = '';
      frame.style.flexBasis = '';
      var extra = frame.querySelector('[data-detail]');
      if (extra) extra.remove();
      return;
    }
    frame.dataset.open = '1';
    var first = frame.getBoundingClientRect();
    frame.style.flexBasis = 'clamp(320px,52vw,660px)';
    var last = frame.getBoundingClientRect();
    if (!reduced && frame.animate) {
      frame.style.willChange = 'transform';
      var anim = frame.animate(
        [{ transform: 'scaleX(' + (first.width / last.width) + ')', transformOrigin: 'left center' }, { transform: 'scaleX(1)', transformOrigin: 'left center' }],
        { duration: 420, easing: 'cubic-bezier(0.22,1,0.36,1)' });
      if (anim && anim.finished) anim.finished.then(function () { frame.style.willChange = ''; }).catch(function () {});
    }
    var d = doc.createElement('div');
    d.setAttribute('data-detail', '');
    d.textContent = frame.getAttribute('data-detail-text') || 'Click again to collapse.';
    body.appendChild(d);
  }

  /* ---------- canvas field: grille on the home hero, particle field elsewhere ---------- */

  function setupField() {
    var c = $('#ed-field');
    S.canvas = c || null;
    if (!c) return;
    S.ctx = c.getContext('2d');
    S.mode = c.dataset.mode || 'grille';
    S.spin = 0;
    sizeField();
    var base = S.mode === 'field' ? 1500 : 620;
    var n = S.pcount = Math.round(window.innerWidth < 560 ? base * 0.45 : base);
    S.pts = new Float32Array(n * 4);
    for (var i = 0; i < n; i++) spawnPt(i);
    S.fieldVisible = true;
    if (reduced) drawField(0, 0);
  }

  function sizeField() {
    var c = S.canvas;
    if (!c) return;
    var r = c.getBoundingClientRect();
    S.W = Math.max(1, Math.round(r.width));
    S.H = Math.max(1, Math.round(r.height));
    var d = Math.min(2, window.devicePixelRatio || 1);
    d = Math.max(1, Math.min(d, 4096 / Math.max(S.W, S.H), Math.sqrt(4200000 / (S.W * S.H))));
    c.width = Math.round(S.W * d);
    c.height = Math.round(S.H * d);
    S.ctx.setTransform(c.width / S.W, 0, 0, c.height / S.H, 0, 0);
    var vh = window.innerHeight;
    S.cx = S.W > 980 ? S.W * 0.7 : S.W * 0.5;
    S.cy = Math.min(S.H * 0.5, vh * 0.5);
    S.R = Math.round(Math.min(S.W * 0.4, vh * 0.46) * 0.46);
    var lab = $('#ed-ceiling-label');
    if (lab) { lab.style.top = (S.cy - S.R - 14) + 'px'; lab.style.left = S.cx + 'px'; }
  }

  function spawnPt(i) {
    var a = Math.random() * Math.PI * 2;
    var R = S.R || 100;
    var r = R * (2.4 + Math.random() * 3.2);
    var s = Math.sqrt(0.55 * R / r) * (0.7 + Math.random() * 0.6);
    S.pts[i * 4] = Math.cos(a) * r;
    S.pts[i * 4 + 1] = Math.sin(a) * r;
    S.pts[i * 4 + 2] = -Math.sin(a) * s;
    S.pts[i * 4 + 3] = Math.cos(a) * s;
  }

  function warp(x, y) {
    var dx = x - S.cx, dy = y - S.cy;
    var r = Math.sqrt(dx * dx + dy * dy);
    if (r < 0.001) return [x, y];
    var R = S.R, rr;
    if (r <= R) rr = r; else { var o = r - R; rr = R + o / (1 + o / (R * 2.0)); }
    var k = rr / r;
    return [S.cx + dx * k, S.cy + dy * k];
  }

  function drawField(t, v) {
    var ctx = S.ctx;
    if (!ctx) return;
    var W = S.W, H = S.H, R = S.R, i, x, y;
    S.spin = (S.spin || 0) + 0.0006 + (v || 0) * 0.00035;
    if (S.mode === 'field') {
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = 'rgba(7,9,12,0.20)';
      ctx.fillRect(0, 0, W, H);
    } else {
      ctx.clearRect(0, 0, W, H);
      var pitch = 56, grid = new Path2D(), off = (S.spin * 40) % pitch, span = 4.4 * R;
      var yTop = Math.max(-H * 0.2, S.cy - span), yBot = Math.min(H * 1.2, S.cy + span), started, p;
      for (x = -pitch * 2 - off; x < W + pitch * 2; x += pitch) {
        started = false;
        for (y = yTop; y <= yBot; y += 14) { p = warp(x, y); if (!started) { grid.moveTo(p[0], p[1]); started = true; } else grid.lineTo(p[0], p[1]); }
      }
      for (y = S.cy - Math.ceil(span / pitch) * pitch + off; y < S.cy + span; y += pitch) {
        started = false;
        for (x = -W * 0.15; x <= W * 1.15; x += 14) { p = warp(x, y); if (!started) { grid.moveTo(p[0], p[1]); started = true; } else grid.lineTo(p[0], p[1]); }
      }
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(232,236,242,0.05)';
      ctx.stroke(grid);
      ctx.save();
      ctx.beginPath();
      ctx.arc(S.cx, S.cy, R * 2.7, 0, Math.PI * 2);
      ctx.clip();
      ctx.strokeStyle = 'rgba(90,147,245,0.055)';
      ctx.stroke(grid);
      ctx.restore();
    }
    if (S.mode === 'field') ctx.globalCompositeOperation = 'lighter';
    var n = S.pcount, soft = R * R * 0.25;
    for (i = 0; i < n; i++) {
      var o = i * 4;
      x = S.pts[o]; y = S.pts[o + 1];
      var vx = S.pts[o + 2], vy = S.pts[o + 3];
      var r2 = x * x + y * y, r = Math.sqrt(r2) || 1;
      var a = -(R * 0.9) / (r2 + soft);
      vx += a * (x / r) * 6; vy += a * (y / r) * 6;
      x += vx; y += vy;
      if (r < R * 0.98) { spawnPt(i); continue; }
      S.pts[o] = x; S.pts[o + 1] = y; S.pts[o + 2] = vx; S.pts[o + 3] = vy;
      var px = S.cx + x, py = S.cy + y;
      if (px < -20 || px > W + 20 || py < -20 || py > H + 20) continue;
      var near = Math.max(0, 1 - (r - R) / (R * 2.6));
      if (S.mode === 'field') {
        ctx.fillStyle = 'rgba(90,147,245,' + (0.07 + near * 0.26) + ')';
        ctx.fillRect(px, py, 1.5, 1.5);
      } else {
        var sp = Math.sqrt(vx * vx + vy * vy) || 1;
        ctx.strokeStyle = 'rgba(232,236,242,' + (0.06 + near * 0.26) + ')';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(px + (vx / sp) * 3.4, py + (vy / sp) * 3.4);
        ctx.stroke();
      }
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(S.cx, S.cy, R, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(90,147,245,' + (0.5 + 0.18 * Math.sin(t / 900)) + ')';
    ctx.stroke();
    ctx.setLineDash([2, 6]);
    ctx.beginPath();
    ctx.arc(S.cx, S.cy, Math.round(R * 1.34), 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(232,236,242,0.10)';
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(S.cx - R - 13, S.cy); ctx.lineTo(S.cx - R + 13, S.cy);
    ctx.moveTo(S.cx + R - 13, S.cy); ctx.lineTo(S.cx + R + 13, S.cy);
    ctx.strokeStyle = 'rgba(90,147,245,0.55)';
    ctx.stroke();
    if (S.firstFrameResolve) { var f = S.firstFrameResolve; S.firstFrameResolve = null; f(); }
  }

  /* ---------- measure ---------- */

  function measure() {
    var inner = $('#ed-marquee-inner');
    if (inner) { var s = inner.querySelector('.strip'); S.stripW = s ? s.getBoundingClientRect().width : 0; }
    S.stackCards = $$('.stack-card');
    S.stackCards.forEach(function (c, i) { c.style.top = (66 + 20 + i * 12) + 'px'; c.style.zIndex = String(i + 1); });
    S.meterCard = $('#ed-meter-card');
    S.meterFill = $('#ed-meter-fill');
    S.meterValue = $('#ed-meter-value');
    S.meterPhase = $('#ed-meter-phase');
    S.meterFile = $('#ed-meter-file');
    S.phaseCells = $$('[data-phase]');
  }

  /* meter: the six phases, and the file each one leaves behind */
  var PHASES = [
    { name: 'brief', file: 'your words', note: 'a paragraph, not a prompt' },
    { name: 'spec', file: 'specs/&lt;f&gt;/spec.md', note: 'ends at a human' },
    { name: 'plan', file: 'specs/&lt;f&gt;/plan.md', note: 'ends at a human' },
    { name: 'tasks', file: 'specs/&lt;f&gt;/tasks.md', note: 'ends at a human' },
    { name: 'build', file: 'a diff + green suite', note: 'cheapest model that follows' },
    { name: 'verify', file: 'verification.md', note: 'a session that wrote no code' }
  ];

  function tickMeter() {
    if (!S.meterFill || !S.meterCard) return;
    var cr = S.meterCard.getBoundingClientRect();
    if (!(cr.bottom > 0 && cr.top < window.innerHeight)) return;
    S.meterT += 0.0032;
    var cycle = S.meterT % 6, phase = Math.floor(cycle), local = cycle - phase;
    var rise = 1 - Math.pow(1 - Math.min(1, local / 0.7), 3);
    var val = ((phase + rise) / 6) * 100;
    S.meterFill.style.width = val.toFixed(1) + '%';
    if (S._phase !== phase) {
      S._phase = phase;
      var ph = PHASES[phase];
      S.meterValue.innerHTML = (phase + 1) + '<small>/6</small>';
      S.meterPhase.textContent = ph.name;
      S.meterFile.innerHTML = ph.file + '<br><span>' + ph.note + '</span>';
      S.phaseCells.forEach(function (c, i) {
        c.style.color = i === phase ? 'var(--ed-text-1)' : (i < phase ? 'var(--ed-text-3)' : 'var(--ed-text-4)');
        c.style.background = i === phase ? 'var(--ed-plate)' : 'var(--ed-panel)';
      });
    }
  }

  function staticScroll() {
    if (S.stackCards && S.stackCards.length > 1 && window.innerWidth > 720) {
      for (var i = 0; i < S.stackCards.length - 1; i++) {
        var cur = S.stackCards[i], nxt = S.stackCards[i + 1];
        var cr = cur.getBoundingClientRect(), nr = nxt.getBoundingClientRect();
        var overlap = Math.max(0, Math.min(1, (cr.bottom - nr.top) / Math.max(1, cr.height)));
        cur.style.transform = 'scale(' + (1 - overlap * 0.04).toFixed(4) + ')';
        cur.style.opacity = String(1 - overlap * 0.45);
      }
    }
  }

  function noRaf() {
    S.rafDead = true;
    if (S.canvas) drawField(0, 0);
    S.counters.forEach(function (c) {
      c.el.textContent = c.el.dataset.text;
      if (c.src) { c.src.style.transition = 'opacity var(--d-el) var(--e-edify)'; c.src.style.opacity = '1'; }
    });
    S.counters = [];
  }

  /* ---------- the one rAF loop ---------- */

  function tick(t) {
    if (S.hidden) return;
    S.n++;
    if (S.n % 3 === 0) {
      sweep();
      if (S.canvas) {
        var cr = S.canvas.getBoundingClientRect();
        S.fieldVisible = cr.bottom > 0 && cr.top < window.innerHeight;
        if (Math.abs(Math.round(cr.width) - S.W) > 1 || Math.abs(Math.round(cr.height) - S.H) > 1) sizeField();
      }
    }
    var y = window.scrollY, raw = y - S.lastY;
    S.lastY = y;
    S.vel += (Math.max(-60, Math.min(60, raw)) - S.vel) * 0.12;
    var v = S.vel;

    if (S.canvas && S.fieldVisible) {
      var t0 = performance.now();
      drawField(t, v);
      if (S.frameTimes.length < 30) {
        S.frameTimes.push(performance.now() - t0);
        if (S.frameTimes.length === 30) {
          var avg = S.frameTimes.reduce(function (a, b) { return a + b; }, 0) / 30;
          if (avg > 9 && S.pcount > 300) S.pcount = Math.round(S.pcount * 0.4);
        }
      }
    }

    if (S.frames && S.frames.length) {
      var target = Math.max(-12, Math.min(12, v * 0.35));
      S.skew += (target - S.skew) * 0.1;
      if (Math.abs(S.skew) < 0.02) S.skew = 0;
      var sy = 1 - Math.abs(S.skew) * 0.004;
      for (var i = 0; i < S.frames.length; i++) {
        var f = S.frames[i];
        f.style.transform = (f.dataset.mag || '') + ' skewX(' + S.skew.toFixed(3) + 'deg) scaleY(' + sy.toFixed(4) + ')';
      }
    }

    var inner = $('#ed-marquee-inner');
    if (inner && S.stripW) {
      if (Math.abs(v) > 0.4) S.dir = v > 0 ? 1 : -1;
      S.marqueeOffset = (S.marqueeOffset + 0.35 * S.dir + v * 0.8) % S.stripW;
      if (S.marqueeOffset < 0) S.marqueeOffset += S.stripW;
      inner.style.transform = 'translate3d(' + (-S.marqueeOffset) + 'px,0,0)';
    }

    tickMeter();
    staticScroll();

    for (var k = S.counters.length - 1; k >= 0; k--) {
      var c = S.counters[k];
      if (!c.t0) { c.t0 = t + c.delay; continue; }
      var e = t - c.t0;
      if (e < 0) continue;
      var q = Math.min(1, e / c.dur);
      var val = c.target * (1 - Math.pow(1 - q, 3));
      c.el.textContent = (c.el.dataset.prefix || '') + (c.dec ? val.toFixed(c.dec) : Math.round(val).toLocaleString('en-US')) + (c.el.dataset.suffix || '');
      if (q >= 1) {
        c.el.textContent = c.el.dataset.text;
        if (c.src) (function (src) { setTimeout(function () { src.style.transition = 'opacity var(--d-el) var(--e-edify)'; src.style.opacity = '1'; }, 200); })(c.src);
        S.counters.splice(k, 1);
      }
    }
  }

  /* ---------- start ---------- */

  function start() {
    setupChrome();
    setupLogo();
    setupTerminals();
    setupTabs();
    setupFaq();
    setupField();
    setupGallery();
    measure();
    setupReveal();
    doc.addEventListener('visibilitychange', function () { S.hidden = doc.hidden; });
    window.addEventListener('resize', function () {
      clearTimeout(S.rt);
      S.rt = setTimeout(function () { small = window.innerWidth < 560; sizeField(); measure(); }, 150);
    });
    window.addEventListener('scroll', function () { sweep(); if (S.rafDead) staticScroll(); }, { passive: true });
    if (!reduced) {
      var loop = function (t) { tick(t); requestAnimationFrame(loop); };
      requestAnimationFrame(loop);
      setTimeout(function () { if (!S.n) noRaf(); }, 1400);
    } else {
      noRaf();
      if (S.meterValue) { S.meterFill.style.width = '100%'; }
    }
    setupBoot();
  }

  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start);
  else start();
})();
