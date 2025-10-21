// Mini App redirect logic for GitHub Pages
// Reads start_param from Telegram WebApp or tgWebAppStartParam from query
// Supports two payload formats: "id_p2_l" and base64url("id:p2:l")

(function () {
  const statusEl = document.getElementById('status');
  const errorEl = document.getElementById('error');
  const fallbackEl = document.getElementById('fallback');

  function showError(msg) {
    if (errorEl) {
      errorEl.style.display = 'block';
      errorEl.textContent = 'Ошибка: ' + msg;
    }
    if (statusEl) statusEl.textContent = '';
  }

  function parsePayload(raw) {
    if (!raw) throw new Error('Пустой payload');
    // Telegram ограничивает payload 64 байтами
    if (new Blob([raw]).size > 64) throw new Error('Payload превышает 64 байта');

    const reNum = /^\d+$/;
    if (raw.includes('_')) {
      const parts = raw.split('_');
      if (parts.length !== 3) throw new Error('Некорректный формат payload: ожидается id_p2_l');
      const [id, p2, l] = parts;
      if (!(reNum.test(id) && reNum.test(p2) && reNum.test(l))) {
        throw new Error('Параметры должны быть числами: id, p2 и l');
      }
      return [id, p2, l];
    } else if (/^[A-Za-z0-9_-]+$/.test(raw)) {
      // base64url decode to "id:p2:l"
      try {
        const pad = '='.repeat((-raw.length) % 4);
        const b64 = raw.replace(/-/g, '+').replace(/_/g, '/') + pad;
        const decoded = atob(b64);
        const parts = decoded.split(':');
        if (parts.length !== 3) throw new Error('Некорректный формат расшифровки: ожидается "id:p2:l"');
        const [id, p2, l] = parts;
        if (!(reNum.test(id) && reNum.test(p2) && reNum.test(l))) {
          throw new Error('Параметры должны быть числами: id, p2 и l');
        }
        return [id, p2, l];
      } catch (_) {
        throw new Error('Некорректная base64url строка');
      }
    } else {
      throw new Error('Некорректный payload');
    }
  }

  function redirect(id, p2, l) {
    // Домен жёстко разрешён по ТЗ
    const target = `https://go.favbet.ua/${id}/${p2}?l=${l}`;
    if (statusEl) statusEl.textContent = 'Редиректим...';
    location.replace(target);
  }

  function run(raw) {
    try {
      const [id, p2, l] = parsePayload(raw);
      redirect(id, p2, l);
    } catch (e) {
      showError(e.message || String(e));
    }
  }

  try {
    // Make Telegram Web App API safe
    const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
    if (tg && typeof tg.ready === 'function') tg.ready();

    const search = new URLSearchParams(location.search);
    // Priority: Telegram start_param → tgWebAppStartParam → direct id&p2&l
    const startParam = tg && tg.initDataUnsafe ? tg.initDataUnsafe.start_param : null;
    const qParam = search.get('tgWebAppStartParam');
    const id = search.get('id');
    const p2 = search.get('p2');
    const l = search.get('l');

    if (startParam || qParam) {
      run(startParam || qParam);
    } else if (id && p2 && l) {
      // Allow /?id=330&p2=126&l=640 for quick tests
      redirect(id, p2, l);
    } else {
      if (fallbackEl) {
        fallbackEl.style.display = 'block';
        const btn = document.getElementById('go');
        const input = document.getElementById('payload');
        if (btn && input) btn.onclick = () => run(input.value.trim());
        if (statusEl) statusEl.textContent = 'Ожидаю payload';
      }
    }
  } catch (e) {
    showError('Инициализация не удалась: ' + (e.message || String(e)));
  }
})();
