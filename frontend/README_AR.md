# واجهة لوحة التحكم — Frontend (عربي RTL)

تشغيل محلي:
1. cd frontend
2. npm ci
3. npm run dev
4. افتح: http://localhost:5173

بناء للإنتاج:
1. npm run build
2. Dockerfile مرفق لبناء الصورة وتقديمها عبر nginx.

ملحوظات:
- الاتجاه RTL مُفعّل عبر html dir="rtl".
- الواجهة تستخدم الـcookie (HttpOnly) للتوثيق؛ تأكد من إعداد reverse proxy لتمرير المسار /api إلى backend.
