(function () {
  'use strict';
  /* Встроенная часть виджета: высота сцены и фирменный узор загрузки — сразу, до приезда
     большого скрипта сцены (он грузится отдельно, из «Файлов» сайта). */
  var nw = document.querySelector('[data-sp-nw]');
  if (!nw || nw.getAttribute('data-inited')) return;
  nw.setAttribute('data-inited', '1');
  var root = document.documentElement, grid = nw.querySelector('.sp-nw__grid');

  /* ── высота: ровно экран — от верха блока до нижней панели телефона ── */
  function fit() {
    var top = nw.getBoundingClientRect().top + (window.pageYOffset || 0);
    var bar = document.querySelector('.sp-mbar'), mb = 0;
    if (bar && getComputedStyle(bar).display !== 'none') mb = bar.getBoundingClientRect().height;
    mb += parseFloat(getComputedStyle(root).marginBottom) || 0;   // полоса предпросмотра InSales
    var h = Math.max(160, Math.floor(window.innerHeight - top - mb));
    if (Math.abs(nw.offsetHeight - h) > 0.5) nw.style.height = h + 'px';
    drawGrid();
  }

  /* ── фирменный узор: генератор с подвала сайта (тот же, что у колеса Мастерской) ── */
  var ST = 'h0s0,0,0,0c.5,4.1,3.7,7.3,7.8,7.8h0,0c-4.1.5-7.3,3.7-7.8,7.8h0s0,0,0,0c-.5-4.1-3.7-7.3-7.8-7.8h0,0c4.1-.5,7.3-3.7,7.8-7.8Z';
  var drawn = '';
  function drawGrid() {
    if (!grid || grid.closest('[hidden]')) return;
    var W = nw.clientWidth, Hp = nw.clientHeight;
    if (!W || !Hp) return;
    var BW = W < 768 ? 700.34 : 1400.68, cols = Math.round(BW / 100);
    var u = W / BW, H = Hp / u, key = BW + 'x' + H.toFixed(1);
    if (key === drawn) return; drawn = key;
    grid.setAttribute('viewBox', '0 0 ' + BW + ' ' + H.toFixed(2)); grid.setAttribute('preserveAspectRatio', 'none');
    var d = '', c, y, st = '';
    for (c = 0; c <= cols; c++) d += 'M' + (c * 100 + 0.34) + ' 0V' + H.toFixed(2);
    for (y = 99.66; y < H; y += 100) d += 'M.34 ' + y.toFixed(2) + 'H' + (BW - 0.34).toFixed(2);
    for (y = 99.66; y < H - 12; y += 100) for (c = 1; c <= cols - 1; c++) st += '<path d="M' + (c * 100 + 0.34) + ',' + (y - 7.82).toFixed(2) + ST + '"/>';
    grid.innerHTML = '<path class="gd" d="' + d + '"/><g class="st">' + st + '</g>';
  }

  fit();
  window.addEventListener('resize', fit);
  window.addEventListener('orientationchange', fit);
  window.addEventListener('load', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
  var hd = document.querySelector('.layout[class*="widget_v4_header"]');
  if (hd && window.ResizeObserver) new ResizeObserver(fit).observe(hd);   // шапка дорастает, когда приезжают шрифты

  /* скрипт сцены не приехал — сказать об этом на экране загрузки */
  window.spNwFail = function () {
    var e = nw.querySelector('.sp-nw__err');
    if (!e) return;
    e.textContent = nw.getAttribute('data-lang') === 'en'
      ? 'The scene script did not load. Please reload the page.'
      : 'Не загрузился скрипт сцены. Обновите страницу.';
    e.hidden = false; nw.classList.add('is-error');
  };
})();
