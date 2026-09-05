# المعمارية وخطة الإكمال

## حدود الثقة
واجهة الهاتف لا تحمل مفاتيح البورصة. API يتحقق من الهوية والصلاحية ويكتب audit log. الإشارة والذكاء الاصطناعي والاستراتيجية مصادر غير موثوقة؛ تنتج **طلبًا** فقط. Risk Engine هو بوابة غير قابلة للتجاوز قبل Execution Engine. لا يسمح execution بوضع LIVE دون فحص IP وصلاحيات المفتاح.

## العمال المعزولون
- `workers`: jobs للبيانات، التقارير، Telegram، وbacktesting عبر queue.
- `strategies`: استخراج ZIP وتشغيل lint/test داخل container rootless بلا شبكة وبنظام ملفات للقراءة فقط وحدود موارد.
- `trading`: Freqtrade deployment منفصل، مقفل version، ويتصل بالمنصة عبر REST/webhook محمي؛ لا نسخ أو تعديل لكوده في هذا المستودع.

## مراحل الإنتاج المتبقية
1. migrations وPostgreSQL repository، ثم session/RBAC/2FA/CSRF/rate limiting.
2. envelope encryption عبر KMS وAPI-account verification من Binance.
3. تنفيذ adapters لكل سوق مع symbol/filter precision وحالات order idempotent.
4. workers وRedis وWebSocket وTelegram مع allow-list chat IDs.
5. sandbox حقيقي وقياسات backtest/reports/backup restore drill.
6. security review خارجي، DRY_RUN، ثم موافقة بشرية موثقة قبل LIVE.

## Alpha Engine
`modules/alpha` يكتشف حالة السوق، يرتب الاستراتيجيات وفق نتائج خارج العينة، ويحسب الحجم. لا يوجد مسار تنفيذ في الوحدة: قرارها يمر دائمًا إلى `risk.engine.evaluate`، ويتطلب نجاح فحص IP/Security قبل أن ينتج حجمًا أكبر من صفر. نتائج Walk-Forward وTrade Journal أدلة تاريخية/تشغيلية وليست توقعًا أو ضمانًا للربح.
