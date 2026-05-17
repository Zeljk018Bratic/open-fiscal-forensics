(function(){
  'use strict';
  const defaultLang = localStorage.getItem('splash_lang') || 'bs';
  const modeLabels = {
    bs: ['📄 DOKUMENT REŽIM','🎨 POSTER REŽIM'],
    en: ['📄 DOCUMENT MODE','🎨 POSTER MODE'],
    de: ['📄 DOKUMENT MODUS','🎨 POSTER MODUS'],
    es: ['📄 MODO DOCUMENTO','🎨 MODO PÓSTER'],
    it: ['📄 MODALITÀ DOCUMENTO','🎨 MODALITÀ POSTER'],
    fr: ['📄 MODE DOCUMENT','🎨 MODE POSTER']
  };

  function applyLangToDom(lang){
    // toggle .active for data-lang elements
    document.querySelectorAll('[data-lang]').forEach(el=>{
      el.classList.toggle('active', el.getAttribute('data-lang') === lang);
    });
    // toggle active on buttons
    document.querySelectorAll('.lang-btn').forEach(b=>{
      const l = b.getAttribute('data-lang');
      if(l) b.classList.toggle('active', l === lang);
    });
    document.documentElement.lang = lang;
    localStorage.setItem('splash_lang', lang);
    // update mode button label
    const modeBtn = document.getElementById('mode-toggle');
    const isDoc = document.body.classList.contains('doc-mode');
    if(modeBtn){
      modeBtn.textContent = isDoc ? (modeLabels[lang]?.[1] || modeBtn.textContent) : (modeLabels[lang]?.[0] || modeBtn.textContent);
    }
  }

  function setLang(lang){
    try{ applyLangToDom(lang); }catch(e){ console.warn('setLang error', e); }
  }

  function toggleMode(){
    document.body.classList.toggle('doc-mode');
    const current = document.documentElement.lang || localStorage.getItem('splash_lang') || defaultLang;
    const modeBtn = document.getElementById('mode-toggle');
    if(modeBtn){
      modeBtn.textContent = document.body.classList.contains('doc-mode') ? (modeLabels[current]?.[1] || modeBtn.textContent) : (modeLabels[current]?.[0] || modeBtn.textContent);
    }
  }

  // Expose globally
  window.setLang = setLang;
  window.toggleMode = toggleMode;

  // QR fallback: if QRCode library is missing or blocked, use external QR image generator
  function generateQrFallback(targetId, url, size){
    try{
      const el = document.getElementById(targetId);
      if(!el) return;
      size = size || 160;
      // prefer an <img> so CSP won't block
      const img = document.createElement('img');
      const safeUrl = encodeURIComponent(url);
      img.src = 'https://api.qrserver.com/v1/create-qr-code/?size='+size+'x'+size+'&data='+safeUrl;
      img.alt = 'QR code';
      img.width = size; img.height = size;
      // clear and append
      el.innerHTML = '';
      el.appendChild(img);
    }catch(e){
      console.warn('QR fallback error', e);
    }
  }

  // Try to generate QR using page scripts if needed; pages may call new QRCode(...) themselves.
  // Here we provide a safe helper for pages to call if QRCode is not available.
  window.generateQrFallback = generateQrFallback;

  document.addEventListener('DOMContentLoaded', function(){
    // attach click handlers to .lang-btn elements (data-lang attribute)
    document.querySelectorAll('.lang-btn').forEach(btn=>{
      const l = btn.getAttribute('data-lang');
      if(l) btn.addEventListener('click', function(){ setLang(l); });
    });
    // attach mode toggle
    const mode = document.getElementById('mode-toggle');
    if(mode) mode.addEventListener('click', toggleMode);

    // apply saved/default language
    applyLangToDom(defaultLang);

    // automatic QR fallback: if element with id 'qr-canvas' exists and QRCode isn't present, create image
    try{
      const qrCanvas = document.getElementById('qr-canvas');
      if(qrCanvas && typeof window.QRCode === 'undefined'){
        const pageUrl = window.location.href;
        generateQrFallback('qr-canvas', pageUrl, 160);
      }
    }catch(e){ console.warn(e); }
  });
})();
