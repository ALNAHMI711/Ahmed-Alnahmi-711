import './style.css';

type User = { id: string; username: string; role: string };
type Availability<T> = { status: 'unavailable' | string; reason: string; data: T };
type ApiAccount = { id: string; name: string; market: string; enabled: boolean; status: string; ip_restriction: string; capabilities: string; last_check: string | null };
type Readiness = { allowed: boolean; reason: string };
type Health = { status: string; live_trading: string };
type Notice = { message?: string };
type StrategyScan = { status: string; checksum?: string; findings?: string[]; reason: string };
type RiskEvaluation = { allowed: boolean; reason?: string; violations?: string[] };
type ParsedSignal = { [key: string]: unknown };

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const app = document.querySelector<HTMLDivElement>('#app')!;
let activeUser: User | null = null;
let reconnectTimer: number | undefined;

const escapeHtml = (value: string) => value.replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char] ?? char));
const unavailable = (message = 'غير متاح حاليًا') => `<div class="state unavailable">${escapeHtml(message)}</div>`;
const loading = () => '<div class="state loading">جار التحميل…</div>';
const empty = (message: string) => `<div class="state empty">${escapeHtml(message)}</div>`;
const table = (headers: string[], content: string) => `<div class="table-wrap"><table><thead><tr>${headers.map(header => `<th>${header}</th>`).join('')}</tr></thead><tbody>${content}</tbody></table></div>`;
const unavailableRow = (headers: string[], message: string) => `<tr><td colspan="${headers.length}">${escapeHtml(message)}</td></tr>`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}/api/v1${path}`, {
    credentials: 'include',
    headers: { ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(init?.headers ?? {}) },
    ...init,
  });
  if (response.status === 401) {
    activeUser = null;
    renderLogin('انتهت الجلسة، يرجى تسجيل الدخول مجددًا.');
    throw new Error('انتهت الجلسة');
  }
  if (response.status === 403) throw new Error('ليس لديك صلاحية الوصول إلى هذا القسم.');
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'تعذر الاتصال بالخادم' })) as { detail?: string };
    throw new Error(body.detail ?? 'تعذر تنفيذ الطلب');
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function renderLogin(message = 'أدخل بيانات حسابك للمتابعة. تحفظ الجلسة في Cookie آمن من الخادم.') {
  app.innerHTML = `<main class="login-page"><section class="login-card"><div class="logo">α</div><p class="eyebrow">ALNAHMI711</p><h1>منصة التداول</h1><p id="login-message" class="muted">${escapeHtml(message)}</p><form id="login-form"><label>اسم المستخدم<input name="username" autocomplete="username" required></label><label>كلمة المرور<input name="password" type="password" autocomplete="current-password" required></label><button type="submit">تسجيل الدخول</button><p id="login-error" class="form-error" role="alert"></p></form></section></main>`;
  document.querySelector<HTMLFormElement>('#login-form')!.addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const button = form.querySelector<HTMLButtonElement>('button')!;
    const error = document.querySelector<HTMLElement>('#login-error')!;
    button.disabled = true; error.textContent = '';
    try {
      activeUser = await request<User>('/auth/login', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(form))) });
      renderTerminal();
    } catch (reason) { error.textContent = reason instanceof Error ? reason.message : 'تعذر تسجيل الدخول'; }
    finally { button.disabled = false; }
  });
}

const nav = [['dashboard', 'الرئيسية'], ['markets', 'الأسواق'], ['portfolio', 'المحفظة'], ['positions', 'المراكز'], ['orders', 'الأوامر'], ['alpha', 'Alpha'], ['risk', 'المخاطر'], ['strategies', 'الاستراتيجيات'], ['signals', 'الإشارات'], ['accounts', 'حسابات التداول'], ['providers', 'AI Providers'], ['sources', 'مصادر الإشارات'], ['workflow', 'سير العمل'], ['backtesting', 'Backtesting'], ['reports', 'التقارير'], ['notifications', 'التنبيهات'], ['settings', 'الإعدادات']];

function section(id: string, title: string, body: string, subtitle = '') { return `<section id="${id}" class="panel"><div class="section-heading"><div><p class="eyebrow">${subtitle}</p><h2>${title}</h2></div></div>${body}</section>`; }
function renderTerminal() {
  app.innerHTML = `<div class="terminal"><aside class="sidebar"><a class="brand" href="#dashboard"><i>α</i><span>ALNAHMI711<small>TRADING TERMINAL</small></span></a><nav>${nav.map(([id, label]) => `<a href="#${id}">${label}</a>`).join('')}</nav></aside><div class="shell"><header><div><p class="eyebrow">TRADING OPERATIONS CENTER</p><h1>منصة التداول</h1></div><div class="header-actions"><span id="system-status" class="badge neutral">جار التحقق</span><span id="ws-status" class="badge neutral">غير متصل</span><a class="icon" href="#notifications" aria-label="التنبيهات">🔔</a><span id="user-name" class="user">${escapeHtml(activeUser?.username ?? '')}</span><button id="logout" class="text-button">خروج</button></div></header><main>
${section('dashboard', 'لوحة المتابعة', `<div class="hero"><div><p class="eyebrow">SYSTEM OVERVIEW</p><h2>مركز عمليات التداول</h2><p class="muted">تعرض المنصة بيانات الخادم فقط؛ لا توجد بيانات أو نتائج افتراضية.</p></div><button id="kill-switch" class="danger">إيقاف التداول</button></div><div id="dashboard-status" class="summary-grid">${loading()}</div>`)}
${section('markets', 'الأسواق', `<div id="market-data">${loading()}</div>`, 'MARKETS')}
${section('portfolio', 'المحفظة', `<div id="portfolio-data">${loading()}</div>`, 'PORTFOLIO')}
${section('positions', 'المراكز', `<div id="positions-data">${loading()}</div>`, 'POSITIONS')}
${section('orders', 'الأوامر', `<div id="orders-data">${loading()}</div>`, 'ORDERS')}
${section('alpha', 'Alpha Engine', `<div id="alpha-data">${loading()}</div><p class="muted">تعرض هذه الشاشة ناتج محرك Alpha من الخادم فقط؛ لا يُنفّذ أي منطق Alpha في المتصفح.</p>`, 'ALPHA')}
${section('risk', 'مركز المخاطر', `<div id="risk-data">${loading()}</div><details><summary>تقييم طلب تداول عبر محرك المخاطر</summary><p class="muted">لا يُنشئ هذا التقييم أمرًا ولا يتجاوز بوابات التنفيذ.</p><form id="risk-form" class="compact-form"><label>حجم المركز<input name="position_size" type="number" min="0" step="any" required></label><label>الرافعة المالية<input name="leverage" type="number" min="0" step="any" required></label><label>الخسارة اليومية<input name="daily_loss" type="number" min="0" step="any" required></label><label>عدد المراكز المفتوحة<input name="open_positions" type="number" min="0" step="1" required></label><label>التعرض<input name="exposure" type="number" min="0" step="any" required></label><label>الـ Spread<input name="spread" type="number" min="0" step="any" required></label><label>الانزلاق السعري<input name="slippage" type="number" min="0" step="any" required></label><label class="check-label"><input name="kill_switch" type="checkbox"> Kill Switch مفعّل</label><button>تقييم المخاطر</button></form><p id="risk-result" class="muted" aria-live="polite"></p></details>`, 'RISK')}
${section('strategies', 'الاستراتيجيات', `${unavailable('لا توجد واجهة API لعرض الاستراتيجيات حاليًا.')}<details><summary>رفع استراتيجية للفحص الأمني</summary><p class="muted">يُرسل الملف إلى مسار الفحص المتاح فقط ولا يُشغّل من الواجهة.</p><form id="strategy-form"><label>ملف الاستراتيجية<input name="file" type="file" accept=".py,.json,.yaml,.yml,.toml,.txt,.zip" required></label><button>رفع وفحص</button></form><p id="scan-status" class="muted"></p><pre id="scan-result"></pre></details>`, 'STRATEGIES')}
${section('signals', 'الإشارات', `${unavailable('لا توجد قائمة إشارات محفوظة حاليًا.')}<details><summary>تحليل رسالة إشارة</summary><p class="muted">تحليل مباشر للرسالة عبر الخادم؛ لا تحفظ الواجهة الإشارات ولا تعرض نتائج افتراضية.</p><form id="signal-form"><label>نص الإشارة<textarea name="message" rows="5" maxlength="10000" required></textarea></label><button>تحليل الإشارة</button></form><pre id="signal-result" aria-live="polite"></pre></details>`, 'SIGNALS')}
${section('accounts', 'حسابات التداول', `<p class="muted">لا تظهر مفاتيح API أو الأسرار في الواجهة ولا تُخزن في المتصفح.</p><div id="accounts-data">${loading()}</div><details><summary>إضافة حساب تداول</summary><form id="account-form"><label>اسم الحساب<input name="name" required></label><label>نوع السوق<select name="market"><option value="spot">Spot</option><option value="cross_margin">Cross Margin</option><option value="isolated_margin">Isolated Margin</option><option value="usds_m">USDⓈ-M Futures</option><option value="coin_m">COIN-M Futures</option><option value="alpha">Alpha</option><option value="stocks">Stocks</option></select></label><label>API Key<input name="api_key" autocomplete="off" minlength="8" required></label><label>API Secret<input name="api_secret" type="password" autocomplete="new-password" minlength="8" required></label><button>حفظ مشفر</button></form><p id="account-status" class="muted"></p></details>`, 'TRADING ACCOUNTS')}
${['providers', 'sources', 'workflow', 'backtesting', 'reports', 'settings'].map(id => section(id, ({ providers: 'AI Providers', sources: 'مصادر الإشارات', workflow: 'سير العمل', backtesting: 'Backtesting', reports: 'التقارير', settings: 'الإعدادات' } as Record<string, string>)[id], unavailable('غير متاح حاليًا — لا توجد API داعمة لهذا القسم.'))).join('')}
${section('notifications', 'التنبيهات', '<ul id="notification-list" class="notification-list">' + empty('لا توجد تنبيهات حاليًا') + '</ul>', 'NOTIFICATIONS')}
</main><nav class="bottom-nav">${nav.slice(0, 5).map(([id, label]) => `<a href="#${id}">${label}</a>`).join('')}</nav></div></div><dialog id="kill-modal"><h2>تأكيد إيقاف التداول</h2><p>هل تريد إرسال طلب Kill Switch إلى الخادم؟ لن تعرض المنصة نجاحًا ما لم يؤكده الخادم.</p><div class="dialog-actions"><button id="kill-cancel" class="text-button">إلغاء</button><button id="kill-confirm" class="danger">تأكيد الإيقاف</button></div><p id="kill-result" class="muted"></p></dialog>`;
  bindTerminal(); void loadTerminal(); connectWebSocket();
}

function availability<T>(target: string, result: Availability<T>, renderer: (data: T) => string, fallback: string) {
  const node = document.querySelector<HTMLElement>(target)!;
  node.innerHTML = result.status === 'unavailable' ? unavailable(result.reason || fallback) : renderer(result.data);
}
async function loadTerminal() {
  const safe = async <T>(task: () => Promise<T>, target: string, fallback: string, render: (value: T) => void) => { try { render(await task()); } catch (error) { document.querySelector<HTMLElement>(target)!.innerHTML = unavailable(error instanceof Error ? error.message : fallback); } };
  void safe(() => fetch(`${apiBase}/health`).then(response => response.json() as Promise<Health>), '#dashboard-status', 'تعذر الوصول إلى حالة النظام', health => { document.querySelector('#system-status')!.textContent = health.status === 'ok' ? 'النظام متصل' : 'النظام غير متصل'; document.querySelector('#dashboard-status')!.innerHTML = `<article class="metric"><span>حالة النظام</span><b>${escapeHtml(health.status)}</b></article><article class="metric"><span>التداول المباشر</span><b>${escapeHtml(health.live_trading)}</b></article>`; });
  void safe(() => request<Availability<unknown[]>>('/market-data'), '#market-data', 'الاتصال بالسوق غير متاح', result => availability('#market-data', result, data => data.length ? table(['الرمز', 'السعر', 'تغير 24h', 'الحجم', 'Spread', 'الإشارة', 'المركز', 'المخاطر'], '') : empty('لا توجد بيانات سوق متاحة حاليًا'), 'الاتصال بالسوق غير متاح'));
  void safe(() => request<Availability<unknown>>('/portfolio'), '#portfolio-data', 'لا توجد بيانات متاحة حاليًا', result => availability('#portfolio-data', result, () => unavailable('لا توجد بيانات متاحة حاليًا'), 'لا توجد بيانات متاحة حاليًا'));
  void safe(() => request<Availability<unknown[]>>('/positions'), '#positions-data', 'لا توجد مراكز مفتوحة', result => availability('#positions-data', result, data => data.length ? table(['الرمز', 'الجانب', 'الحجم', 'سعر الدخول', 'سعر السوق', 'PNL غير المحقق', 'الرافعة', 'الهامش', 'SL', 'TP', 'المخاطر'], '') : empty('لا توجد مراكز مفتوحة'), 'لا توجد مراكز مفتوحة'));
  void safe(() => request<Availability<unknown[]>>('/orders'), '#orders-data', 'لا توجد أوامر حديثة', result => availability('#orders-data', result, data => data.length ? table(['الرمز', 'الجانب', 'النوع', 'السعر', 'الكمية', 'الحالة', 'الوقت'], '') : empty('لا توجد أوامر حديثة'), 'لا توجد أوامر حديثة'));
  void safe(() => request<Availability<unknown>>('/alpha/snapshot'), '#alpha-data', 'بيانات Alpha غير متاحة حاليًا', result => availability('#alpha-data', result, () => unavailable('بيانات Alpha غير متاحة حاليًا'), 'بيانات Alpha غير متاحة حاليًا'));
  void safe(() => request<Readiness>('/live-readiness'), '#risk-data', 'تعذر قراءة قرار المخاطر', result => { document.querySelector('#risk-data')!.innerHTML = `<div class="risk-card"><span>LIVE Readiness</span><b class="${result.allowed ? 'good' : 'bad'}">${result.allowed ? 'مسموح' : 'غير مسموح'}</b><p>${escapeHtml(result.reason)}</p></div>`; });
  void loadAccounts();
}
async function loadAccounts() { const node = document.querySelector<HTMLElement>('#accounts-data')!; try { const accounts = await request<ApiAccount[]>('/api-accounts'); node.innerHTML = accounts.length ? table(['اسم الحساب', 'نوع السوق', 'الحالة', 'IP Restriction', 'Capabilities', 'آخر تحقق'], accounts.map(account => `<tr><td>${escapeHtml(account.name)}</td><td>${escapeHtml(account.market)}</td><td>${escapeHtml(account.status)}</td><td>${escapeHtml(account.ip_restriction)}</td><td>${escapeHtml(account.capabilities)}</td><td>${escapeHtml(account.last_check ?? 'غير متاح')}</td></tr>`).join('')) : empty('لم يتم ربط أي حساب تداول'); } catch (error) { node.innerHTML = unavailable(error instanceof Error ? error.message : 'تعذر تحميل الحسابات'); } }
function bindTerminal() {
  document.querySelector('#logout')!.addEventListener('click', async () => { try { await request('/auth/logout', { method: 'POST' }); } finally { activeUser = null; window.clearTimeout(reconnectTimer); renderLogin('تم تسجيل الخروج.'); } });
  document.querySelector('#kill-switch')!.addEventListener('click', () => document.querySelector<HTMLDialogElement>('#kill-modal')!.showModal());
  document.querySelector('#kill-cancel')!.addEventListener('click', () => document.querySelector<HTMLDialogElement>('#kill-modal')!.close());
  document.querySelector('#kill-confirm')!.addEventListener('click', async () => { const output = document.querySelector('#kill-result')!; try { await request('/kill-switch', { method: 'POST' }); output.textContent = 'تم تأكيد إيقاف التداول من الخادم.'; } catch (error) { output.textContent = error instanceof Error && error.message.includes('محرك التنفيذ') ? 'Kill Switch غير متاح حاليًا لأن محرك التنفيذ غير متصل.' : (error instanceof Error ? error.message : 'تعذر تنفيذ Kill Switch'); } });
  document.querySelector<HTMLFormElement>('#account-form')!.addEventListener('submit', async event => { event.preventDefault(); const form = event.currentTarget as HTMLFormElement; const output = document.querySelector('#account-status')!; try { const result = await request<Notice>('/api-accounts', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(form))) }); form.reset(); output.textContent = result.message ?? 'تم الحفظ.'; void loadAccounts(); } catch (error) { output.textContent = error instanceof Error ? error.message : 'تعذر حفظ الحساب'; } });
  document.querySelector<HTMLFormElement>('#strategy-form')!.addEventListener('submit', async event => { event.preventDefault(); const body = new FormData(event.currentTarget as HTMLFormElement); const output = document.querySelector('#scan-result')!; try { const result = await request<StrategyScan>('/strategies/scan', { method: 'POST', body }); output.textContent = JSON.stringify(result, null, 2); } catch (error) { output.textContent = error instanceof Error ? error.message : 'تعذر فحص الملف'; } });
  document.querySelector<HTMLFormElement>('#signal-form')!.addEventListener('submit', async event => { event.preventDefault(); const form = event.currentTarget as HTMLFormElement; const output = document.querySelector('#signal-result')!; try { const result = await request<ParsedSignal>('/signals/parse', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(form))) }); output.textContent = JSON.stringify(result, null, 2); } catch (error) { output.textContent = error instanceof Error ? error.message : 'تعذر تحليل الإشارة'; } });
  document.querySelector<HTMLFormElement>('#risk-form')!.addEventListener('submit', async event => { event.preventDefault(); const form = event.currentTarget as HTMLFormElement; const output = document.querySelector('#risk-result')!; const values = Object.fromEntries(new FormData(form)); const body = { ...Object.fromEntries(Object.entries(values).filter(([key]) => key !== 'kill_switch').map(([key, value]) => [key, Number(value)])), kill_switch: values.kill_switch === 'on' }; try { const result = await request<RiskEvaluation>('/risk/evaluate', { method: 'POST', body: JSON.stringify(body) }); output.textContent = result.allowed ? 'القرار: مسموح — تم تأكيده من محرك المخاطر.' : `القرار: غير مسموح${result.reason ? ` — ${result.reason}` : ''}${result.violations?.length ? ` (${result.violations.join('، ')})` : ''}`; } catch (error) { output.textContent = error instanceof Error ? error.message : 'تعذر تقييم المخاطر'; } });
}
function connectWebSocket() { const status = document.querySelector<HTMLElement>('#ws-status')!; const protocol = location.protocol === 'https:' ? 'wss' : 'ws'; const base = import.meta.env.VITE_WS_BASE_URL ?? `${protocol}://${location.host}`; status.textContent = 'جاري إعادة الاتصال'; let socket: WebSocket; try { socket = new WebSocket(`${base}/api/v1/ws/notifications`); } catch { retry(); return; } socket.onopen = () => { status.textContent = 'متصل'; status.className = 'badge good'; }; socket.onmessage = event => { const notice = JSON.parse(event.data) as Notice; const list = document.querySelector('#notification-list')!; if (notice.message) list.innerHTML = `<li>${escapeHtml(notice.message)}</li>` + list.innerHTML; }; socket.onerror = () => { status.textContent = 'غير متصل'; status.className = 'badge bad'; }; socket.onclose = retry; function retry() { status.textContent = 'جاري إعادة الاتصال'; status.className = 'badge neutral'; reconnectTimer = window.setTimeout(connectWebSocket, 3000); } }
async function start() { try { activeUser = await request<User>('/auth/me'); renderTerminal(); } catch { renderLogin(); } }
void start();
