import logging
import time

import requests

log = logging.getLogger(__name__)

API_URL = "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/"


class RateError(Exception):
    pass


class RateProvider:
    def __init__(self, timeout=10, retries=2, session=None):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.retries = retries
        self._cache = {}

    def _fetch(self, code, date=None):
        params = {"currencies": code}
        if date:
            params["date"] = date
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.get(API_URL, params=params, timeout=self.timeout)
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    raise RateError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                data = resp.json()
                for item in data[0]["currencies"]:
                    if item["code"] == code:
                        return float(item["rate"]) / float(item.get("quantity", 1) or 1)
                raise RateError(f"პასუხში {code} არ მოიძებნა")
            except RateError:
                raise
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1.5 * (attempt + 1))
        raise RateError(f"{code} {date or 'current'}: {last_error}")

    def get_rate(self, code, date):

        if code == "GEL":
            return 1.0, "n/a"
        key = (code, date)
        if key in self._cache:
            return self._cache[key]
        try:
            result = (self._fetch(code, date), "historical")
        except RateError as exc:
            log.warning("თარიღით კურსი ვერ მოიძებნა (%s), ვცდი მიმდინარეს", exc)
            try:
                result = (self._fetch(code), "current")
            except RateError as exc2:
                log.error("კურსის მიღება ვერ მოხერხდა: %s", exc2)
                result = (None, None)
        self._cache[key] = result
        return result
