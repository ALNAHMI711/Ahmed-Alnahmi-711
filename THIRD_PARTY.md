# مكونات الطرف الثالث ومراجعة الحقوق

لم يُنسخ أي كود من المشاريع الآتية إلى هذا المستودع. أُنشئت النواة هنا من الصفر؛ لذلك لا تنتقل تراخيصها إلى المشروع.

|المستودع|الرابط|الترخيص|الإصدار/Commit|المؤلف|ما استُخدم|التعديل|متطلبات الحقوق|
|---|---|---|---|---|---|---|---|
|Freqtrade|https://github.com/freqtrade/freqtrade|GPL-3.0|يُثبّت إصدار stable عند التكامل|freqtrade contributors|تكامل REST/عملية منفصلة مقترح فقط|لا يوجد نسخ|احترام GPL-3.0 وإشعارات copyright عند توزيع عمل مشتق|
|Freqtrade Strategies|https://github.com/freqtrade/freqtrade-strategies|راجع LICENSE قبل كل استراتيجية|غير محدد|freqtrade contributors|مرجع أفكار فقط|لا يوجد|حفظ license وcopyright لكل ملف معتمد|
|binance-futures-bot|https://github.com/shivpatel-dev/binance-futures-bot|غير متحقق أثناء التدقيق|غير مستخدم|shivpatel-dev|مرجع صيغة إشارات فقط|لا يوجد|مرفوض للإنتاج إلى أن تتحقق الرخصة|
|binance-futures-trading-bot|https://github.com/Erfaniaa/binance-futures-trading-bot|غير متحقق أثناء التدقيق|غير مستخدم|Erfaniaa|مرجع مفاهيم فقط|لا يوجد|مرفوض للإنتاج إلى أن تتحقق الرخصة|

> لا تضف تبعية أو كودًا خارجيًا قبل مراجعة LICENSE، المصدر، الأمان، والاختبارات وتحديث هذا السجل.

## سجل التنفيذ الحالي
يستخدم `httpx` وSQLAlchemy وFastAPI كتبعيات معلنة في `requirements.txt`. لا يوجد SDK Binance أو Telegram مدمج؛ REST requests مكتوبة داخل adapter لتقليل سطح الاعتماد، ويجب تدقيق أي SDK جديد وترخيصه قبل إضافته.
