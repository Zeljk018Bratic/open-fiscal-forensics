(function () {
  'use strict';

  const cfg = window.LANG_CONFIG || {};
  const supported = cfg.supported || ['bs', 'de', 'en', 'it', 'fr'];
  const fallbackLang = cfg.defaultLang || 'bs';
  const pageKey = document.body?.dataset?.page || 'index';
  const pageConfig = (cfg.pages && cfg.pages[pageKey]) || {};

  function getLangFromQuery() {
    try {
      const queryLang = (new URLSearchParams(window.location.search).get('lang') || '').toLowerCase();
      return supported.includes(queryLang) ? queryLang : '';
    } catch (_err) {
      return '';
    }
  }

  function getLang() {
    const fromQuery = getLangFromQuery();
    if (fromQuery) return fromQuery;
    const stored = localStorage.getItem('bb_lang');
    return supported.includes(stored) ? stored : fallbackLang;
  }

  function pick(translated, lang) {
    if (!translated || typeof translated !== 'object') return '';
    return translated[lang] || translated[fallbackLang] || Object.values(translated)[0] || '';
  }

  function textForKey(key, lang) {
    const pageText = pageConfig.text || {};
    const ui = cfg.ui || {};
    if (pageText[key]) return pick(pageText[key], lang);
    if (ui[key]) return pick(ui[key], lang);
    return '';
  }

  function setMeta(lang) {
    const meta = pageConfig.meta || {};
    const title = pick(meta.title, lang);
    const desc = pick(meta.desc, lang);

    if (title) {
      document.title = title;
      const pageTitle = document.getElementById('page-title');
      if (pageTitle) pageTitle.textContent = title;
      const ogTitle = document.getElementById('og-title');
      if (ogTitle) ogTitle.setAttribute('content', title);
    }

    if (desc) {
      const metaDesc = document.getElementById('meta-desc');
      if (metaDesc) metaDesc.setAttribute('content', desc);
      const ogDesc = document.getElementById('og-desc');
      if (ogDesc) ogDesc.setAttribute('content', desc);
    }
  }

  function setLangQuery(lang) {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('lang', lang);
      const next = `${url.pathname}${url.search}${url.hash}`;
      window.history.replaceState({}, '', next);
    } catch (_err) {
      // no-op
    }
  }

  function setLangOnInternalLinks(lang) {
    document.querySelectorAll('a.nav-link[href], a.logo-link[href]').forEach((link) => {
      const href = link.getAttribute('href');
      if (!href) return;
      try {
        const url = new URL(href, window.location.href);
        if (url.origin !== window.location.origin) return;
        url.searchParams.set('lang', lang);
        link.setAttribute('href', `${url.pathname}${url.search}${url.hash}`);
      } catch (_err) {
        // no-op
      }
    });
  }

  function applyLanguage(lang) {
    const current = supported.includes(lang) ? lang : fallbackLang;

    document.querySelectorAll('.lang-btn[data-set-lang]').forEach((btn) => {
      const btnLang = btn.getAttribute('data-set-lang');
      btn.classList.toggle('active', btnLang === current);
      const label = cfg.ui?.languages?.[btnLang] || btnLang.toUpperCase();
      btn.textContent = label;
    });

    // Update inline multilanguage spans (class .t + data-lang)
    document.querySelectorAll('.t[data-lang]').forEach((el) => {
      el.classList.toggle('active', el.getAttribute('data-lang') === current);
    });

    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const value = textForKey(el.getAttribute('data-i18n'), current);
      if (value) el.textContent = value;
    });

    document.querySelectorAll('[data-i18n-lines]').forEach((el) => {
      const value = textForKey(el.getAttribute('data-i18n-lines'), current);
      if (!value) return;
      const lines = value.split('\n').filter(Boolean);
      el.innerHTML = '';
      lines.forEach((line) => {
        const li = document.createElement('li');
        li.textContent = line.replace(/^•\s*/, '');
        el.appendChild(li);
      });
    });

    document.querySelectorAll('[data-nav-page]').forEach((link) => {
      const navKey = link.getAttribute('data-nav-page');
      const navValue = cfg.ui?.nav?.[navKey];
      if (navValue) link.textContent = pick(navValue, current);
    });

    document.documentElement.lang = current;
    localStorage.setItem('bb_lang', current);
    setMeta(current);
    setLangQuery(current);
    setLangOnInternalLinks(current);
  }

  function getCanonicalUrl() {
    const base = cfg.siteBaseUrl || 'https://zeljk018bratic.github.io/sound-of-freedom/';
    try {
      const { href, hostname, pathname } = window.location;
      const fileName = (pathname.split('/').filter(Boolean).pop() || pageConfig.file || 'index.html').replace(/\s/g, '');

      if (href.startsWith('file://') || href === 'about:blank' || hostname === 'github.com') {
        return new URL(fileName, base).href;
      }

      if (hostname === 'zeljk018bratic.github.io') {
        if (pathname === '/sound-of-freedom/' || pathname === '/sound-of-freedom') {
          return new URL('index.html', base).href;
        }
        return href;
      }

      return new URL(fileName, base).href;
    } catch (_err) {
      return new URL(pageConfig.file || 'index.html', base).href;
    }
  }

  function renderQrFallback(container, url, size) {
    const img = document.createElement('img');
    img.width = size;
    img.height = size;
    img.alt = `QR code: ${url}`;
    img.src = `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(url)}`;
    container.innerHTML = '';
    container.appendChild(img);
  }

  function renderQRCodes() {
    const url = getCanonicalUrl();
    document.querySelectorAll('.qr-canvas').forEach((container) => {
      const size = Number(container.getAttribute('data-qr-size')) || 220;
      container.innerHTML = '';
      try {
        if (typeof window.QRCode === 'function') {
          new window.QRCode(container, {
            text: url,
            width: size,
            height: size,
            colorDark: '#000000',
            colorLight: '#ffffff',
            correctLevel: window.QRCode.CorrectLevel?.H || 3
          });
        } else {
          renderQrFallback(container, url, size);
        }
      } catch (_err) {
        renderQrFallback(container, url, size);
      }
    });

    document.querySelectorAll('.qr-link').forEach((link) => {
      link.href = url;
      link.textContent = url;
    });
  }

  function setActiveNav() {
    document.querySelectorAll('.nav-link[data-nav-page]').forEach((link) => {
      link.classList.toggle('active', link.getAttribute('data-nav-page') === pageKey);
    });
  }

  function bindEvents() {
    document.querySelectorAll('.lang-btn[data-set-lang]').forEach((btn) => {
      btn.addEventListener('click', () => applyLanguage(btn.getAttribute('data-set-lang')));
    });

    // mode toggle (buttons with id mode-toggle present on pages)
    const modeBtn = document.getElementById('mode-toggle');
    if (modeBtn) {
      modeBtn.addEventListener('click', () => {
        document.body.classList.toggle('doc-mode');
        // refresh language labels for correct mode text if necessary
        const current = localStorage.getItem('bb_lang') || fallbackLang;
        applyLanguage(current);
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    setActiveNav();
    applyLanguage(getLang());
    renderQRCodes();
  });
})();
