# Ahmed Alnahmi 711 — منصة تداول سحابية آمنة

> **تحذير:** ليست المنصة وعدًا بالربح. التداول عالي المخاطر، وLIVE مغلق افتراضيًا. الهاتف واجهة HTTPS فقط؛ تشغيل المحرك يكون على VPS/Cloud.

## البنية
`Dashboard → API → Signal/Strategy → Risk (إلزامي) → Execution → Exchange adapters`.
توجد واجهات منفصلة لـ Spot وCross Margin وIsolated Margin وUSDⓈ-M وCOIN-M وAlpha وStocks. لا يُسمح لـ AI أو Telegram أو استراتيجية بتجاوز risk engine أو فحوص الأمن.

## التشغيل المحلي
1. انسخ `cp .env.example .env` واضبط `APP_SECRET_KEY` و`POSTGRES_PASSWORD` خارج Git.
2. للتطوير: `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt` ثم `uvicorn backend.app.main:app --reload`.
3. افتح `http://127.0.0.1:8000`، والتوثيق التفاعلي في `/api/docs`.
4. للإنتاج: عيّن `DOMAIN`، أسرار قوية، و`APP_ENV=production`، ثم `docker compose up -d --build`. ينهي Caddy TLS تلقائيًا.

## First Run وتسجيل الدخول
يجب إنشاء مستخدم admin من متغيرات البيئة في worker first-run، وتخزين كلمة المرور بـ Argon2id. الجلسات Cookies `HttpOnly`, `Secure`, `SameSite=Strict` بمهلة، مع rate limit وCSRF وتسجيل audit. هذه الواجهات ما زالت ضمن قائمة الإكمال في `KNOWN_ISSUES.md`؛ لا تنشر LIVE قبل اكتمالها.

## Binance وIP
- أنشئ مفتاح تداول فقط؛ **لا Withdrawal**.
- قيّد المفتاح بعنوان/عناوين IP outbound الثابتة لخادم VPS، لا IP الهاتف.
- إذا غاب تقييد IP أو فُعّلت Withdrawal، تمنع المنصة LIVE.
- لا يظهر secret بعد الحفظ، ويشفّر at rest باستخدام KMS/secret manager في بيئة الإنتاج.

## الإشارات والاستراتيجيات
يدعم parser صيغة symbol/market/Buy أو Sell/TP حتى 7/SL، لكنه لا يرسل أمرًا. تمر الإشارة بالرمز والسوق والسعر والسيولة وspread وslippage والتكرار والتعرّض وrisk ثم اعتماد بشري أو auto policy. الرفع يقبل Python/JSON/YAML/TOML/TXT/ZIP، ولا يشغل أي ملف مباشر.

## Backtest وDry Run وLIVE
الأوضاع: DEVELOPMENT، BACKTEST، DRY_RUN، PAPER، LIVE. استخدم بيانات تاريخية حقيقية ورسوم/انزلاق/funding، وافصل train وvalidation وout-of-sample وwalk-forward. لا تنقل نتيجة backtest إلى ادعاء أداء مستقبلي. يلزم dry run واختبارات وفحص الاستراتيجية وrisk وIP قبل LIVE.

## Telegram، النسخ الاحتياطي، والتحديث
Telegram worker منفصل وتُخزن token مشفرة؛ يدعم الأوامر العربية المطلوبة عند اكتماله. النسخ الاحتياطي يشمل PostgreSQL والإعدادات والاستراتيجيات وسجل الصفقات، ويستثني الأسرار أو يشفرها. حدّث الحاويات بعد CI ناجح وفحص CVE، ثم اختبر DRY_RUN قبل LIVE.

## الاختبارات
`pytest -q` لاختبارات parser وrisk وحماية LIVE. CI يشغّل lint وtests وdependency audit وDocker build، ولا يحتوي نشر إنتاج.

## تطوير الواجهة وE2E
من `frontend`: شغّل `npm install` ثم `npm run build`. تعتمد الواجهة على Vite/TypeScript وتتكامل مع `GET/POST /api/v1/api-accounts`، و`POST /api/v1/strategies/scan`، وWebSocket عند `/api/v1/ws/notifications`. شغّل `npm run test:e2e` بعد البناء؛ CI يثبت Chromium ويشغّل Playwright.

## دمج الفرع
بعد ربط remote وتسجيل GitHub CLI، راجع حالة CI ثم نفّذ: `gh pr create --base main --head feature/phase-4-frontend --fill`، وبعد نجاح جميع checks: `gh pr merge feature/phase-4-frontend --squash --delete-branch`.

## GitHub Pages والاستضافة السحابية
ينشر workflow `deploy-pages.yml` مجلد `frontend/dist` عند الدمج إلى `main`. فعّل **Settings → Pages → Build and deployment → GitHub Actions**، ثم أضف Repository Variables العامة فقط: `VITE_API_BASE_URL` و`VITE_WS_BASE_URL`. GitHub Pages يستضيف الواجهة الثابتة فقط؛ يجب نشر FastAPI وPostgreSQL على VPS/Vercel/Render/خدمة حاويات منفصلة مع HTTPS وCORS مضبوطين. لا تضع مفاتيح أو كلمات مرور في GitHub Variables العامة أو ملفات Vite.

## Alpha / Profitability Engine
وحدة `modules/alpha` تضيف كشف النظام السوقي، تقييم الاستراتيجية من بيانات Out-of-Sample، حجم مركز ديناميكي، Walk-Forward، مراقبة تراجع الأداء، وJournal. لا تنفذ صفقة ولا تتجاوز Risk Engine: فشل Daily Loss أو leverage أو spread أو kill switch أو فحص IP يرد حجمًا صفرًا وقرارًا مرفوضًا.
