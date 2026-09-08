from backend.app.adapters.base import AccountCapabilities


def live_trading_allowed(
    capabilities: AccountCapabilities,
    trusted_outbound_ips: tuple[str, ...],
    mode: str,
) -> tuple[bool, str]:
    if mode != "LIVE":
        return True, "الوضع ليس تداولًا حقيقيًا"
    if not trusted_outbound_ips:
        return False, "لا يمكن تفعيل التداول الحقيقي حتى يتم تقييد مفتاح Binance على عنوان IP الموثوق الخاص بالخادم."
    if capabilities.withdrawal_enabled:
        return False, "مفتاح API يملك صلاحية سحب؛ تم حظر التداول الحقيقي."
    if not capabilities.trusted_ip_restriction:
        return False, "تقييد IP لمفتاح Binance غير مفعّل."
    if not capabilities.trading_enabled:
        return False, "صلاحية التداول غير مفعلة للمفتاح."
    return True, "اجتاز فحص أمان التداول الحقيقي"
