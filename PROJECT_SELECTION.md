# اختيار المشاريع

تمت المراجعة المعمارية في 2026-09-05. نجوم GitHub وforks وآخر تحديث متغيرات خارجية ولم تُسجّل كحقائق ثابتة هنا؛ تُجمع في مراجعة إصدار مقفلة قبل التثبيت.

|الاسم|المستودع|License|Stars/Forks/آخر تحديث|اختبارات/أمان/توثيق|Spot|Futures|Telegram|Backtesting|القرار|
|---|---|---|---|---|---|---|---|---|---|
|Freqtrade|freqtrade/freqtrade|GPL-3.0|تتحقق عند pin للإصدار|ناضج؛ راجع release وCVE قبل التثبيت|نعم|نعم|نعم|نعم|APPROVED لتكامل منفصل متوافق مع GPL|
|Freqtrade Strategies|freqtrade/freqtrade-strategies|راجع الملف لكل استراتيجية|تتحقق عند المراجعة|استراتيجيات مجتمع؛ لا اعتماد بلا backtest|نعم|حسب الاستراتيجية|لا|نعم|NEEDS_REVIEW — غير مستخدم في الإنتاج|
|shivpatel-dev/binance-futures-bot|shivpatel-dev/binance-futures-bot|غير متحقق|تتحقق عند المراجعة|لا يُعتمد دون audit|لا|مفاهيم فقط|مفاهيم|محدود|REJECTED للإنتاج|
|Erfaniaa/binance-futures-trading-bot|Erfaniaa/binance-futures-trading-bot|غير متحقق|تتحقق عند المراجعة|بنية قديمة محتملة؛ راجع secrets/pickle|لا|مفاهيم فقط|مفاهيم|محدود|REJECTED للإنتاج|

لا يُستخدم صف NEEDS_REVIEW أو REJECTED في Production. لا تعني APPROVED أن استراتيجية مربحة أو أن مفاتيح API آمنة تلقائيًا.

## بوابة الاعتماد
لا يُدمج أي مشروع خارجي لتنفيذ orders أو Telegram أو backtesting قبل pin لإصدار محدد، فحص CVE/license، واختبارات تكامل على Testnet منفصل. لا يغير هذا السجل بوابات LIVE الموثقة في `IMPLEMENTATION_GAP.md`.
