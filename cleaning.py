
import math
import re
from datetime import date, datetime

VALID_CHANNELS = {"web", "email", "call"}
VALID_CURRENCIES = {"GEL", "USD", "EUR"}
CHANNEL_ALIASES = {"e-mail": "email"}
CURRENCY_ALIASES = {"₾": "GEL", "$": "USD", "€": "EUR"}

_YMD = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
_DMY = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$")
_TEXT_FORMATS = ("%d %B %Y", "%B %d, %Y", "%b %d, %Y", "%d %b %Y")
_AMOUNT = re.compile(r"^-?\d+(\.\d+)?$")


def parse_date(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("თარიღი არ არის მითითებული")
    s = re.split(r"[T ]\d", value.strip(), maxsplit=1)[0].strip()
    parsed = None
    try:
        m = _YMD.match(s)
        if m:
            y, mo, d = map(int, m.groups())
            parsed = date(y, mo, d)
        else:
            m = _DMY.match(s)  # დღე პირველია (DD.MM.YYYY)
            if m:
                d, mo, y = map(int, m.groups())
                parsed = date(y, mo, d)
            else:
                for fmt in _TEXT_FORMATS:
                    try:
                        parsed = datetime.strptime(s, fmt).date()
                        break
                    except ValueError:
                        continue
    except ValueError:
        raise ValueError(f"არარსებული თარიღი: {value!r}")
    if parsed is None:
        raise ValueError(f"თარიღის უცნობი ფორმატი: {value!r}")
    if parsed > date.today():
        raise ValueError(f"თარიღი მომავალშია: {value!r}")
    return parsed.isoformat()


def parse_amount(value):
    if value is None:
        raise ValueError("თანხა არ არის მითითებული")
    if isinstance(value, bool):
        raise ValueError(f"თანხა არასწორი ტიპისაა: {value!r}")
    if isinstance(value, (int, float)):
        num = float(value)
    elif isinstance(value, str):
        s = re.sub(r"\s", "", value)
        if not s:
            raise ValueError("თანხა ცარიელია")
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):   # 1.250,50
                s = s.replace(".", "").replace(",", ".")
            else:                             # 1,250.50
                s = s.replace(",", "")
        elif "," in s:
            if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s):
                s = s.replace(",", "")
            else:
                s = s.replace(",", ".")
        if not _AMOUNT.match(s):
            raise ValueError(f"თანხის უცნობი ფორმატი: {value!r}")
        num = float(s)
    else:
        raise ValueError(f"თანხა არასწორი ტიპისაა: {value!r}")
    if not math.isfinite(num):
        raise ValueError(f"თანხა არასწორია: {value!r}")
    if num < 0:
        raise ValueError(f"თანხა უარყოფითია: {value!r}")
    return num


def clean_records(records):
    processed, rejected = [], []
    seen_ids = set()

    for raw in records:
        if not isinstance(raw, dict):
            rejected.append({"id": None, "reason": "ჩანაწერი არ არის ობიექტი", "record": raw})
            continue

        reasons, fixes = [], []

        rid = raw.get("id")
        if isinstance(rid, str):
            rid = rid.strip()
        if rid is None or rid == "" or isinstance(rid, bool):
            reasons.append("id არ არის მითითებული")
        elif str(rid) in seen_ids:
            reasons.append(f"id დუბლირებულია: {rid!r}")

        date_iso = None
        try:
            date_iso = parse_date(raw.get("date"))
            if date_iso != raw.get("date"):
                fixes.append(f"date: {raw.get('date')!r} -> {date_iso!r}")
        except ValueError as exc:
            reasons.append(str(exc))

        channel = raw.get("channel")
        if isinstance(channel, str):
            norm = channel.strip().lower()
            norm = CHANNEL_ALIASES.get(norm, norm)
            if norm in VALID_CHANNELS:
                if norm != channel:
                    fixes.append(f"channel: {channel!r} -> {norm!r}")
                channel = norm
            else:
                reasons.append(f"უცნობი არხი: {channel!r}")
        else:
            reasons.append("არხი არ არის მითითებული")

        text = raw.get("text")
        if isinstance(text, str) and text.strip():
            if text != text.strip():
                fixes.append("text: ზედმეტი ჰარები მოიჭრა")
            text = text.strip()
        else:
            reasons.append("ტექსტი არ არის მითითებული")

        #
        amount = None
        try:
            amount = parse_amount(raw.get("amount"))
            if isinstance(raw.get("amount"), str):
                fixes.append(f"amount: სტრიქონი {raw.get('amount')!r} -> რიცხვი {amount}")
        except ValueError as exc:
            reasons.append(str(exc))

        currency = raw.get("currency")
        if isinstance(currency, str):
            norm = currency.strip()
            norm = CURRENCY_ALIASES.get(norm, norm.upper())
            if norm in VALID_CURRENCIES:
                if norm != currency:
                    fixes.append(f"currency: {currency!r} -> {norm!r}")
                currency = norm
            else:
                reasons.append(f"უცნობი ვალუტა: {currency!r}")
        else:
            reasons.append("ვალუტა არ არის მითითებული")

        if reasons:
            rejected.append({"id": raw.get("id"), "reason": "; ".join(reasons), "record": raw})
            continue

        seen_ids.add(str(rid))
        processed.append({
            "id": rid,
            "date": date_iso,
            "channel": channel,
            "text": text,
            "amount": amount,
            "currency": currency,
            "fixes": fixes,
        })

    return processed, rejected
