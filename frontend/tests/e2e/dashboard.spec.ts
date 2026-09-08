import { expect, test } from '@playwright/test';

test('Arabic dashboard renders server-backed operational sections without demo balances', async ({ page }) => {
  await page.route('**/api/v1/auth/me', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'test-user', username: 'admin', role: 'admin' }) }));
  await page.route('**/health', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok', live_trading: 'disabled_by_default' }) }));
  await page.route('**/api/v1/market-data', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'unavailable', reason: 'اتصال السوق غير متاح', data: [] }) }));
  await page.route('**/api/v1/portfolio', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'unavailable', reason: 'لا يوجد حساب تداول متصل يوفّر بيانات محفظة حالياً', data: null }) }));
  await page.route('**/api/v1/positions', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'unavailable', reason: 'لا توجد بيانات مراكز من موصل تداول متصل', data: [] }) }));
  await page.route('**/api/v1/orders', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'unavailable', reason: 'لا توجد بيانات أوامر من موصل تداول متصل', data: [] }) }));
  await page.route('**/api/v1/alpha/snapshot', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'unavailable', reason: 'لا توجد نتيجة Alpha تشغيلية مسجلة', data: null }) }));
  await page.route('**/api/v1/live-readiness', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ allowed: false, reason: 'LIVE معطل افتراضيًا' }) }));
  await page.route('**/api/v1/api-accounts', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) }));

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'مركز عمليات التداول' })).toBeVisible();
  await expect(page.getByText('تعرض المنصة بيانات الخادم فقط؛ لا توجد بيانات أو نتائج افتراضية.')).toBeVisible();
  await expect(page.getByText('LIVE Readiness')).toBeVisible();
  await expect(page.getByText('لم يتم ربط أي حساب تداول')).toBeVisible();
  await expect(page.locator('body')).not.toContainText('1,250.00 USDT');
});
