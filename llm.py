import json
import logging
import time

import requests

log = logging.getLogger(__name__)

CATEGORIES = ["ზარალი", "საჩივარი", "ინფორმაციის მოთხოვნა", "სხვა"]


ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


PROMPT = """You classify customer requests of an insurance company (written in Georgian).
Assign exactly ONE category:
- ზარალი: the customer reports an insured event (accident, theft, damage, loss, medical expense) or asks for compensation/reimbursement for it.
- საჩივარი: the customer expresses dissatisfaction (delays, rude service, wrong payout, double charge, unanswered claim).
- ინფორმაციის მოთხოვნა: the customer asks a question about terms, prices, coverage, deadlines or procedures.
- სხვა: everything else (contact data change, contract cancellation, thanks, technical app problems, document language, empty/unclear).
If the customer reports an event AND complains, choose the main intent of the text.

Request: \"\"\"{text}\"\"\""""


def classify(text, api_key, model, session=None, max_retries=4):
    session = session or requests
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(text=text)}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {"category": {"type": "STRING", "enum": CATEGORIES}},
                "required": ["category"],
            },
        },
    }
    headers = {"Content-Type": "application/json"}
    for attempt in range(max_retries):
        try:
            resp = session.post(ENDPOINT.format(model=model, key=api_key), headers=headers, json=body, timeout=180)
            if resp.status_code in (429, 500, 503):
                wait = 5 * (attempt + 1)
                log.warning("LLM API: %s, ველოდები %s წმ", resp.status_code, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            category = json.loads(raw)["category"]
            if category in CATEGORIES:
                return category
            log.error("მოდელმა უცნობი კატეგორია დააბრუნა: %r", category)
            return None
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            log.error("LLM გამოძახება ვერ მოხერხდა: %s", exc)
            return None
    return None
