from collections import Counter


def _avg(values):
    return round(sum(values) / len(values), 2) if values else None


def build_summary(processed, total_input, rejected_count):
    by_month = Counter(r["date"][:7] for r in processed)
    by_channel = Counter(r["channel"] for r in processed)
    by_month_channel = {}
    for r in processed:
        by_month_channel.setdefault(r["date"][:7], Counter())[r["channel"]] += 1

    gel_amounts = [r["amount_gel"] for r in processed if r.get("amount_gel") is not None]
    nonzero = [a for a in gel_amounts if a > 0]
    categories = Counter(r.get("category") or "კატეგორიის გარეშე" for r in processed)

    return {
        "total_input_records": total_input,
        "processed_records": len(processed),
        "rejected_records": rejected_count,
        "requests_by_month": dict(sorted(by_month.items())),
        "requests_by_channel": dict(by_channel),
        "requests_by_month_and_channel": {m: dict(c) for m, c in sorted(by_month_channel.items())},
        "average_amount_gel": _avg(gel_amounts),
        "average_amount_gel_excluding_zero": _avg(nonzero),
        "amounts_used_in_average": len(gel_amounts),
        "records_without_gel_amount": len(processed) - len(gel_amounts),
        "requests_by_category": dict(categories),
    }
