# مسائل معروفة
- هذه النواة لا تنفذ أوامر حقيقية بعد؛ موصلات البورصة واجهات متعمدة تحتاج تنفيذًا مدققًا ومفاتيح مقيدة IP.
- صفحة الدخول الكاملة (RBAC/2FA/CSRF)، worker Telegram، وموزع WebSocket متعدد العمليات هي مراحل لازمة قبل أي نشر LIVE. تشفير Fernet وWebSocket الأولي موجودان لكن يحتاجان مراجعة تشغيلية.
- فحص ZIP يحتاج عامل sandbox معزولًا (بدون شبكة، ملفات read-only، وحدود CPU/RAM)؛ لذلك لا يعتمد هذا الإصدار أي ZIP تلقائيًا.
- لا توجد بيانات اعتماد GitHub (`GH_TOKEN`) ولا remote في بيئة التنفيذ، لذلك لم يمكن فتح PR أو مراقبة CI من هنا. لا تضع token في ملف `.env` أو المستودع.
- `IMPLEMENTATION_GAP.md` is the authoritative list of gates remaining before LIVE. Compose workers only initialise the schema today; they do not run simulated execution.
- WebSocket events are committed-data only. Non-admin account-scoped events require ownership mapping before they can be delivered.
