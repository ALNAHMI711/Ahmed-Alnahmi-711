import './style.css';

type User = { id: string; username: string; role: string };
type Availability<T> = { status: string; reason?: string; data: T };
type Health = { status: string; live_trading: string };
type Readiness = { allowed: boolean; reason: string };
type PublicIp = { status: string; ip: string | null; reason?: string };
type ApiAccount = { id: string; name: string; market: string; enabled: boolean; status: string; ip_restriction: string; capabilities: string; last_check: string | null };
type Notice = { message?: string; reason?: string };
type StrategyScan = { status: string; checksum?: string; findings?: string[]; reason?: string };
type ApiRecord = Record<string, unknown>;

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const backendConfigured = apiBase.length > 0;
const mount = document.querySelector<HTMLDivElement>('#app');
if (!mount) throw new Error('Application mount point is missing.');
const app: HTMLDivElement = mount;

let activeUser: User | null = null;
let reconnectTimer: number | undefined;
let socket: WebSocket | undefined;

const navigation = [
  ['dashboard', 'الرئيسية'], ['markets', 'الأسواق'], ['portfolio', 'المحفظة'], ['positions', 'المراكز'], ['orders', 'الأوامر'],
  ['alpha', 'Alpha'], ['risk', 'المخاطر'], ['strategies', 'الاستراتيجيات'], ['signals', 'الإشارات'], ['accounts', 'حسابات التداول'],
  ['providers', 'AI Providers'], ['sources', 'مصادر الإشارات'], ['workflow', 'سير العمل'], ['backtesting', 'Backtesting'], ['reports', 'التقارير'], ['notifications', 'التنبيهات'], ['settings', 'الإعدادات'],
] as const;

function escapeHtml(value: unknown): string {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char] ?? char));
}
function state(kind: 'loading' | 'empty' | 'unavailable', message: string): string {
  return `<div class="state ${kind}" role="status">${escapeHtml(message)}</div>`;
}
const loading = () => state('loading', 'جار التحميل…');
const empty = (message: string) => state('empty', message);
const unavailable = (message = 'غير متاح حاليًا') => state('unavailable', message);
function value(record: ApiRecord, ...keys: string[]): string {
  for (const key of keys) if (record[key] !== null && record[key] !== undefined) return escapeHtml(record[key]);
  return 'غير متاح';
}
function table(headers: string[], rows: string): string {
  return `<div class="table-wrap"><table><thead><tr>${headers.map(header => `<th>${escapeHtml(header)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
}
function rows(data: ApiRecord[], columns: string[][]): string {
  return data.map(record => `<tr>${columns.map(keys => `<td>${value(record, ...keys)}</td>`).join('')}</tr>`).join('');
}
function section(id: string, title: string, body: string, subtitle = ''): string {
  return `<section id="${id}" class="panel"><div class="section-heading"><div><p class="eyebrow">${escapeHtml(subtitle)}</p><h2>${escapeHtml(title)}</h2></div></div>${body}</section>`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!backendConfigured) throw new Error('Backend not configured — اضبط VITE_API_BASE_URL بعنوان HTTPS لخادم المنصة.');
  const response = await fetch(`${apiBase}/api/v1${path}`, {
    credentials: 'include',
    headers: { ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(init.headers ?? {}) },
    ...init,
  });
  if (response.status === 401) {
    activeUser = null;
    closeSocket();
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

function renderLogin(message = 'أدخل بيانات حسابك للمتابعة. تحفظ الجلسة في Cookie من الخادم.') {
  app.innerHTML = `<main class="login-page"><section class="login-card"><div class="logo">α</div><p class="eyebrow">ALNAHMI711</p><h1>منصة التداول</h1><p class="muted">${escapeHtml(message)}</p><form id="login-form"><label>اسم المستخدم<input name="username" autocomplete="username" required></label><label>كلمة المرور<input name="password" type="password" autocomplete="current-password" required></label><button type="submit">تسجيل الدخول</button><p id="login-error" class="form-error" role="alert"></p></form></section></main>`;
  document.querySelector<HTMLFormElement>('#login-form')?.addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const button = form.querySelector<HTMLButtonElement>('button');
    const output = document.querySelector<HTMLElement>('#login-error');
    if (!button || !output) return;
    button.disabled = true;
    output.textContent = '';
    try {
      activeUser = await request<User>('/auth/login', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(form))) });
      renderTerminal();
    } catch (error) {
      output.textContent = error instanceof Error ? error.message : 'تعذر تسجيل الدخول';
    } finally {
      button.disabled = false;
    }
  });
}

function renderTerminal() {
  app.innerHTML = `<div class="terminal"><aside class="sidebar"><a class="brand" href="#dashboard"><i>α</i><span>ALNAHMI711<small>TRADING TERMINAL</small></span></a><nav>${navigation.map(([id, label]) => `<a href="#${id}">${label}</a>`).join('')}</nav></aside><div class="shell"><header><div><p class="eyebrow">TRADING OPERATIONS CENTER</p><h1>منصة التداول</h1></div><div class="header-actions"><span id="system-status" class="badge neutral">جار التحقق</span><span id="ws-status" class="badge neutral">غير متصل</span><a class="icon" href="#notifications" aria-label="التنبيهات">🔔</a><span class="user">${escapeHtml(activeUser?.username)}</span><button id="logout" class="text-button">خروج</button></div></header><main>
${section('dashboard', 'لوحة المتابعة', `<div class="hero"><div><p class="eyebrow">SYSTEM OVERVIEW</p><h2>مركز عمليات التداول</h2><p class="muted">تعرض المنصة بيانات الخادم فقط؛ لا توجد بيانات أو نتائج افتراضية.</p></div><button id="kill-switch" class="danger">إيقاف التداول</button></div><div id="dashboard-status" class="summary-grid">${loading()}</div><div id="public-ip">${loading()}</div>`)}
${section('markets', 'الأسواق', `<div id="market-data">${loading()}</div>`, 'MARKETS')}
${section('portfolio', 'المحفظة', `<div id="portfolio-data">${loading()}</div>`, 'PORTFOLIO')}
${section('positions', 'المراكز', `<div id="positions-data">${loading()}</div>`, 'POSITIONS')}
${section('orders', 'الأوامر', `<div id="orders-data">${loading()}</div>`, 'ORDERS')}
${section('alpha', 'Alpha Engine', `<div id="alpha-data">${loading()}</div><p class="muted">تعرض هذه الشاشة ناتج محرك Alpha من الخادم فقط؛ لا يُنفّذ منطق Alpha في المتصفح.</p>`, 'ALPHA')}
${section('risk', 'مركز المخاطر', `<div id="risk-data">${loading()}</div>`, 'RISK')}
${section('strategies', 'الاستراتيجيات', `${unavailable('قائمة الاستراتيجيات غير متاحة حاليًا — Backend endpoint غير منفذ.')}<details><summary>رفع استراتيجية للفحص الأمني</summary><p class="muted">يُرسل الملف لمسار الفحص المتاح فقط ولا يُشغّل من الواجهة.</p><form id="strategy-form"><label>ملف الاستراتيجية<input name="file" type="file" accept=".py,.json,.yaml,.yml,.toml,.txt,.zip" required></label><button>رفع وفحص</button></form><pre id="scan-result"></pre></details>`, 'STRATEGIES')}
${section('signals', 'الإشارات', unavailable('Signal storage/API unavailable — لا توجد قائمة إشارات محفوظة من الخادم.'), 'SIGNALS')}
${section('accounts', 'حسابات التداول', `<p class="muted">لا تظهر مفاتيح API أو الأسرار في الواجهة ولا تُخزن في المتصفح.</p><div id="accounts-data">${loading()}</div><p id="account-test-status" class="muted" role="status"></p><details><summary>إضافة حساب تداول</summary><form id="account-form"><label>اسم الحساب<input name="name" required></label><label>نوع السوق<select name="market"><option value="spot">Spot</option><option value="cross_margin">Cross Margin</option><option value="isolated_margin">Isolated Margin</option><option value="usds_m">USDⓈ-M Futures</option><option value="coin_m">COIN-M Futures</option><option value="alpha">Alpha</option><option value="stocks">Stocks</option></select></label><label>API Key<input name="api_key" autocomplete="off" minlength="8" required></label><label>API Secret<input name="api_secret" type="password" autocomplete="new-password" minlength="8" required></label><button>حفظ مشفر</button></form><p id="account-status" class="muted" role="status"></p></details>`, 'TRADING ACCOUNTS')}
${['providers', 'sources', 'workflow', 'backtesting', 'reports', 'settings'].map(id => section(id, ({ providers: 'AI Providers', sources: 'مصادر الإشارات', workflow: 'سير العمل', backtesting: 'Backtesting', reports: 'التقارير', settings: 'الإعدادات' } as Record<string, string>)[id], unavailable('غير متاح حاليًا — Backend endpoint غير منفذ.'))).join('')}
${section('notifications', 'التنبيهات', `<ul id="notification-list" class="notification-list"><li class="state empty">لا توجد تنبيهات حاليًا</li></ul>`, 'NOTIFICATIONS')}
</main><nav class="bottom-nav">${navigation.slice(0, 5).map(([id, label]) => `<a href="#${id}">${label}</a>`).join('')}</nav></div></div><dialog id="kill-modal"><h2>تأكيد إيقاف التداول</h2><p>هل تريد إرسال طلب Kill Switch إلى الخادم؟ لن تظهر المنصة نجاحًا ما لم يؤكده الخادم.</p><div class="dialog-actions"><button id="kill-cancel" class="text-button">إلغاء</button><button id="kill-confirm" class="danger">تأكيد الإيقاف</button></div><p id="kill-result" class="muted" role="status"></p></dialog>`;
  bindTerminal();
  void loadTerminal();
  connectWebSocket();
}

function put(target: string, html: string) {
  const node = document.querySelector<HTMLElement>(target);
  if (node) node.innerHTML = html;
}
async function safe<T>(task: () => Promise<T>, target: string, fallback: string, render: (result: T) => string) {
  try { put(target, render(await task())); }
  catch (error) { put(target, unavailable(error instanceof Error ? error.message : fallback)); }
}
function availability<T>(result: Availability<T>, fallback: string, renderer: (data: T) => string): string {
  return result.status === 'unavailable' ? unavailable(result.reason || fallback) : renderer(result.data);
}
function renderPortfolio(data: unknown): string {
  if (!data || typeof data !== 'object') return unavailable('لا توجد بيانات متاحة حاليًا');
  const record = data as ApiRecord;
  const metrics: [string, string[]][] = [['Equity', ['equity']], ['الرصيد المتاح', ['available_balance', 'availableBalance']], ['الهامش المستخدم', ['used_margin', 'usedMargin']], ['PNL المحقق', ['realized_pnl', 'realizedPnl']], ['PNL غير المحقق', ['unrealized_pnl', 'unrealizedPnl']], ['PNL اليومي', ['daily_pnl', 'dailyPnl']], ['Drawdown', ['drawdown']]];
  return `<div class="summary-grid">${metrics.map(([label, keys]) => `<article class="metric"><span>${label}</span><b>${value(record, ...keys)}</b></article>`).join('')}</div>`;
}
function renderAlpha(data: unknown): string {
  if (!data || typeof data !== 'object') return unavailable('بيانات Alpha غير متاحة حاليًا');
  const record = data as ApiRecord;
  const fields: [string, string[]][] = [['Market Regime', ['market_regime', 'regime']], ['Strategy Ranking', ['strategy_ranking', 'ranking']], ['Signal', ['signal']], ['Confidence', ['confidence']], ['Position Size', ['position_size']], ['Risk', ['risk']], ['Performance', ['performance']]];
  return `<div class="summary-grid">${fields.map(([label, keys]) => `<article class="metric"><span>${label}</span><b>${value(record, ...keys)}</b></article>`).join('')}</div>`;
}
async function loadTerminal() {
  void safe(() => request<Health>('/health'), '#dashboard-status', 'تعذر الوصول إلى حالة النظام', health => {
    const status = document.querySelector<HTMLElement>('#system-status');
    if (status) { status.textContent = health.status === 'ok' ? 'النظام متصل' : 'النظام غير متصل'; status.className = `badge ${health.status === 'ok' ? 'good' : 'bad'}`; }
    return `<article class="metric"><span>حالة النظام</span><b>${escapeHtml(health.status)}</b></article><article class="metric"><span>التداول المباشر</span><b>${escapeHtml(health.live_trading)}</b></article>`;
  });
  void safe(() => request<PublicIp>('/system/public-ip'), '#public-ip', 'عنوان الخروج غير متاح', result => result.status === 'available' && result.ip ? `<div class="state empty"><strong>عنوان IP للخادم:</strong> <code>${escapeHtml(result.ip)}</code><p class="muted">أضف هذا العنوان إلى Trusted IP في Binance، وليس عنوان الهاتف.</p></div>` : unavailable(result.reason ?? 'عنوان الخروج غير متاح'));
  void safe(() => request<Availability<ApiRecord[]>>('/market-data'), '#market-data', 'الاتصال بالسوق غير متاح', result => availability(result, 'الاتصال بالسوق غير متاح', data => data.length ? table(['الرمز', 'السعر', 'تغير 24h', 'الحجم', 'Spread', 'الإشارة', 'المركز', 'المخاطر'], rows(data, [['symbol'], ['price', 'last_price'], ['change_24h', 'price_change_percent'], ['volume'], ['spread'], ['signal'], ['position'], ['risk']])) : empty('لا توجد بيانات سوق متاحة حاليًا')));
  void safe(() => request<Availability<unknown>>('/portfolio'), '#portfolio-data', 'لا توجد بيانات متاحة حاليًا', result => availability(result, 'لا توجد بيانات متاحة حاليًا', renderPortfolio));
  void safe(() => request<Availability<ApiRecord[]>>('/positions'), '#positions-data', 'لا توجد مراكز مفتوحة', result => availability(result, 'لا توجد مراكز مفتوحة', data => data.length ? table(['الرمز', 'الجانب', 'الحجم', 'سعر الدخول', 'سعر السوق', 'PNL غير المحقق', 'الرافعة', 'الهامش', 'SL', 'TP', 'المخاطر'], rows(data, [['symbol'], ['side'], ['size', 'quantity'], ['entry_price'], ['mark_price'], ['unrealized_pnl'], ['leverage'], ['margin'], ['sl'], ['tp'], ['risk']])) : empty('لا توجد مراكز مفتوحة')));
  void safe(() => request<Availability<ApiRecord[]>>('/orders'), '#orders-data', 'لا توجد أوامر حديثة', result => availability(result, 'لا توجد أوامر حديثة', data => data.length ? table(['الرمز', 'الجانب', 'النوع', 'السعر', 'الكمية', 'الحالة', 'الوقت'], rows(data, [['symbol'], ['side'], ['type', 'order_type'], ['price'], ['quantity', 'size'], ['status'], ['time', 'created_at']])) : empty('لا توجد أوامر حديثة')));
  void safe(() => request<Availability<unknown>>('/alpha/snapshot'), '#alpha-data', 'بيانات Alpha غير متاحة حاليًا', result => availability(result, 'بيانات Alpha غير متاحة حاليًا', renderAlpha));
  void safe(() => request<Readiness>('/live-readiness'), '#risk-data', 'تعذر قراءة قرار المخاطر', result => `<div class="risk-card"><span>LIVE Readiness</span><b class="${result.allowed ? 'good' : 'bad'}">${result.allowed ? 'مسموح' : 'غير مسموح'}</b><p>${escapeHtml(result.reason)}</p></div>`);
  void loadAccounts();
}
async function loadAccounts() {
  await safe(() => request<ApiAccount[]>('/api-accounts'), '#accounts-data', 'تعذر تحميل الحسابات', accounts => accounts.length ? table(['اسم الحساب', 'نوع السوق', 'الحالة', 'IP Restriction', 'Capabilities', 'فحص'], accounts.map(account => `<tr><td>${escapeHtml(account.name)}</td><td>${escapeHtml(account.market)}</td><td>${escapeHtml(account.status)}</td><td>${escapeHtml(account.ip_restriction)}</td><td>${escapeHtml(account.capabilities)}</td><td><button class="account-test" data-account-id="${escapeHtml(account.id)}">فحص الاتصال</button></td></tr>`).join('')) : empty('لم يتم ربط أي حساب تداول'));
}
function bindTerminal() {
  document.querySelector('#logout')?.addEventListener('click', async () => { try { await request('/auth/logout', { method: 'POST' }); } finally { activeUser = null; closeSocket(); renderLogin('تم تسجيل الخروج.'); } });
  const dialog = document.querySelector<HTMLDialogElement>('#kill-modal');
  document.querySelector('#kill-switch')?.addEventListener('click', () => dialog?.showModal());
  document.querySelector('#kill-cancel')?.addEventListener('click', () => dialog?.close());
  document.querySelector('#kill-confirm')?.addEventListener('click', async () => { const output = document.querySelector<HTMLElement>('#kill-result'); if (!output) return; try { await request('/kill-switch', { method: 'POST' }); output.textContent = 'تم تأكيد إيقاف التداول من الخادم.'; } catch (error) { output.textContent = error instanceof Error && error.message.includes('محرك التنفيذ') ? 'Kill Switch غير متاح حاليًا لأن محرك التنفيذ غير متصل.' : (error instanceof Error ? error.message : 'تعذر تنفيذ Kill Switch'); } });
  document.querySelector<HTMLFormElement>('#account-form')?.addEventListener('submit', async event => { event.preventDefault(); const form = event.currentTarget as HTMLFormElement; const output = document.querySelector<HTMLElement>('#account-status'); if (!output) return; try { const result = await request<Notice>('/api-accounts', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(form))) }); form.reset(); output.textContent = result.message ?? 'تم الحفظ.'; void loadAccounts(); } catch (error) { output.textContent = error instanceof Error ? error.message : 'تعذر حفظ الحساب'; } });
  document.querySelector<HTMLFormElement>('#strategy-form')?.addEventListener('submit', async event => { event.preventDefault(); const output = document.querySelector<HTMLElement>('#scan-result'); if (!output) return; try { const result = await request<StrategyScan>('/strategies/scan', { method: 'POST', body: new FormData(event.currentTarget as HTMLFormElement) }); output.textContent = JSON.stringify(result, null, 2); } catch (error) { output.textContent = error instanceof Error ? error.message : 'تعذر فحص الملف'; } });
  document.querySelector('#accounts-data')?.addEventListener('click', async event => { const button = (event.target as HTMLElement).closest<HTMLButtonElement>('.account-test'); const output = document.querySelector<HTMLElement>('#account-test-status'); if (!button || !output) return; button.disabled = true; output.textContent = 'جار فحص اتصال Binance من الخادم…'; try { const result = await request<Notice>(`/api-accounts/${button.dataset.accountId}/test`, { method: 'POST' }); output.textContent = result.reason ?? 'اكتمل فحص الاتصال؛ راجع الصلاحيات قبل أي تفعيل.'; void loadAccounts(); } catch (error) { output.textContent = error instanceof Error ? error.message : 'تعذر فحص الاتصال'; } finally { button.disabled = false; } });
}
function closeSocket() { window.clearTimeout(reconnectTimer); socket?.close(); socket = undefined; }
function connectWebSocket() {
  const status = document.querySelector<HTMLElement>('#ws-status');
  if (!status || !backendConfigured) { if (status) { status.textContent = 'Backend غير مهيأ'; status.className = 'badge bad'; } return; }
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const base = (import.meta.env.VITE_WS_BASE_URL ?? apiBase).replace(/\/$/, '') || `${protocol}://${location.host}`;
  status.textContent = 'جاري إعادة الاتصال'; status.className = 'badge neutral';
  try { socket = new WebSocket(`${base}/api/v1/ws/notifications`); } catch { scheduleReconnect(); return; }
  socket.onopen = () => { status.textContent = 'متصل'; status.className = 'badge good'; };
  socket.onmessage = event => { try { const notice = JSON.parse(event.data) as Notice; if (!notice.message) return; const list = document.querySelector<HTMLElement>('#notification-list'); if (list) list.innerHTML = `<li>${escapeHtml(notice.message)}</li>${list.innerHTML}`; } catch { /* Ignore malformed server events. */ } };
  socket.onerror = () => { status.textContent = 'غير متصل'; status.className = 'badge bad'; };
  socket.onclose = scheduleReconnect;
}
function scheduleReconnect() { if (!activeUser) return; reconnectTimer = window.setTimeout(connectWebSocket, 3000); }
async function start() { if (!backendConfigured) { renderLogin('Backend not configured — اضبط VITE_API_BASE_URL بعنوان HTTPS لخادم المنصة.'); return; } try { activeUser = await request<User>('/auth/me'); renderTerminal(); } catch { renderLogin(); } }
void start();
