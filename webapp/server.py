from __future__ import annotations

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from bot_v3.utils import decode_payload, build_target_url

app = FastAPI(title="Fav Mini App Redirector")

# Allow local dev by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"]
)

INDEX_HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Fav Mini App Redirect</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial,sans-serif;margin:0;padding:24px;background:#0f1221;color:#fff}
    .card{background:#151936;border-radius:12px;padding:16px}
    .err{color:#ff7272}
    a.btn{display:inline-block;margin-top:12px;padding:10px 14px;background:#4b7cff;color:#fff;border-radius:8px;text-decoration:none}
    .muted{color:#b9bdd1}
  </style>
</head>
<body>
  <div class="card">
    <h2>Fav Mini App Redirect</h2>
    <div id="status" class="muted">Проверяем параметры...</div>
    <div id="error" class="err" style="display:none;"></div>
    <div id="fallback" style="display:none;">
      <p class="muted">Похоже, вы открыли страницу вне Telegram. Введите payload вручную ("330_126_640" или base64url("330:126:640")):</p>
      <input id="payload" placeholder="330_126_640" style="padding:8px;border-radius:8px;border:1px solid #444;background:#0f1221;color:#fff;width:100%;max-width:360px" />
      <button id="go" style="margin-top:10px;padding:10px 14px;border-radius:8px;background:#4b7cff;color:#fff;border:none">Перейти</button>
    </div>
  </div>
  <script>
    const ALLOWED = ("{allowed}");
    function buildTarget(id, p2, l) {{
      return `https://${{ALLOWED}}/${{id}}/${{p2}}?l=${{l}}`;
    }}
    function parsePayload(raw) {{
      if (!raw) throw new Error('Пустой payload');
      if (raw.includes('_')) {{
        const parts = raw.split('_');
        if (parts.length !== 3) throw new Error('Некорректный формат payload: ожидается id_p2_l');
        const [id, p2, l] = parts;
        const re = /^\d+$/;
        if (!(re.test(id) && re.test(p2) && re.test(l))) throw new Error('Параметры должны быть числами: id, p2 и l');
        return [id, p2, l];
      }} else {{
        try {{
          const pad = '='.repeat((-raw.length)%4);
          const decoded = atob(raw.replace(/-/g,'+').replace(/_/g,'/') + pad);
          const parts = decoded.split(':');
          if (parts.length !== 3) throw new Error('Некорректный формат расшифровки: ожидается "id:p2:l"');
          const [id, p2, l] = parts;
          const re = /^\d+$/;
          if (!(re.test(id) && re.test(p2) && re.test(l))) throw new Error('Параметры должны быть числами: id, p2 и l');
          return [id, p2, l];
        }} catch (e) {{
          throw new Error('Некорректная base64url строка');
        }}
      }}
    }}

    function run(raw) {{
      try {{
        const [id, p2, l] = parsePayload(raw);
        const target = buildTarget(id, p2, l);
        document.getElementById('status').textContent = 'Редиректим...';
        location.replace(target);
      }} catch (e) {{
        document.getElementById('error').style.display='block';
        document.getElementById('error').textContent = 'Ошибка: ' + e.message;
        document.getElementById('status').textContent = '';
      }}
    }}

    const tg = window.Telegram ? window.Telegram.WebApp : null;
    const search = new URLSearchParams(location.search);
    const qParam = search.get('tgWebAppStartParam');
    const startParam = tg && tg.initDataUnsafe ? tg.initDataUnsafe.start_param : null;

    if (startParam || qParam) {{
      run(startParam || qParam);
    }} else {{
      document.getElementById('fallback').style.display='block';
      document.getElementById('status').textContent = 'Ожидаю payload';
      document.getElementById('go').onclick = () => run(document.getElementById('payload').value.trim());
    }}
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index(_: Request) -> HTMLResponse:
    allowed = os.getenv("ALLOWED_REDIRECT_DOMAIN", "go.favbet.ua")
    html = INDEX_HTML.format(allowed=allowed)
    return HTMLResponse(content=html)

