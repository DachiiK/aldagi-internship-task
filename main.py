import argparse
import json
import logging
import os
import time
from pathlib import Path

from cleaning import clean_records
from llm import classify
from nbg import RateProvider
from stats import build_summary

log = logging.getLogger("main")


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="მომხმარებელთა მიმართვების დამუშავება")
    parser.add_argument("--input", default="requests.json")
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    processed, rejected = clean_records(records)
    log.info("დამუშავდა: %d, გამოირიცხა: %d", len(processed), len(rejected))

    rates = RateProvider()
    for rec in processed:
        rate, source = rates.get_rate(rec["currency"], rec["date"])
        rec["rate"] = rate
        rec["rate_source"] = source
        rec["amount_gel"] = round(rec["amount"] * rate, 2) if rate is not None else None

    # ნაწილი 3: კლასიფიკაცია
    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    delay = float(os.environ.get("LLM_CALL_DELAY", "6"))
    if not api_key:
        log.warning("GEMINI_API_KEY არ არის დაყენებული, category იქნება null")
    for rec in processed:
        rec["category"] = classify(rec["text"], api_key, model) if api_key else None
        if api_key:
            time.sleep(delay)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "processed.json", processed)
    write_json(out / "rejected.json", rejected)
    write_json(out / "summary.json", build_summary(processed, len(records), len(rejected)))
    log.info("ფაილები ჩაიწერა: %s", out.resolve())


if __name__ == "__main__":
    main()
