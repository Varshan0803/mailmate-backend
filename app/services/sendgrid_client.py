# app/services/sendgrid_client.py
import asyncio
import logging
from typing import Dict, Optional, List, Any

import httpx

logger = logging.getLogger(__name__)

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
SENDGRID_STATS_URL = "https://api.sendgrid.com/v3/categories/stats"
SENDGRID_STATS_SUMS_URL = "https://api.sendgrid.com/v3/categories/stats/sums"


class SendGridClient:
    def __init__(self, api_key: str, timeout: int = 10, max_retries: int = 4):
        self.api_key = api_key
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self._client.aclose()

    async def _sleep_for_retry_after(self, response: httpx.Response, attempt: int) -> None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                wait = int(retry_after)
                logger.warning("SendGrid returned Retry-After=%s, sleeping", wait)
                await asyncio.sleep(wait)
                return
            except Exception:
                pass
        wait = min(2 ** attempt, 30)
        logger.warning("Sleeping for %s s before retry (exponential backoff)", wait)
        await asyncio.sleep(wait)

    async def send(self, payload: Dict) -> Dict[str, Any]:
        """
        Send a single mail payload (SendGrid v3 format).
        Returns a dict with:
          success: bool
          status_code: int or None
          body: str | None
          attempts: int
          attempt_details: list[{attempt: int, status: int|None, body: str|None, error: str|None}]
          error: last error message or None
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        last_error = None
        attempt_details: List[Dict[str, Optional[str]]] = []

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("SendGrid attempt %s for to=%s", attempt, payload.get("personalizations"))
                resp = await self._client.post(SENDGRID_URL, json=payload, headers=headers)
                status = resp.status_code
                body = resp.text

                attempt_details.append({
                    "attempt": attempt,
                    "status": status,
                    "body": body,
                    "error": None
                })

                # success codes per SendGrid are 202 (accepted) typically, and sometimes 200
                if status in (200, 202):
                    logger.info("SendGrid accepted message (status=%s).", status)
                    return {
                        "success": True,
                        "status_code": status,
                        "body": body,
                        "attempts": attempt,
                        "attempt_details": attempt_details,
                        "error": None
                    }

                # Retry on 429 and 5xx
                if status == 429 or 500 <= status < 600:
                    logger.warning("SendGrid returned %s. Attempt %s/%s", status, attempt, self.max_retries)
                    await self._sleep_for_retry_after(resp, attempt)
                    last_error = body
                    continue

                # Permanent client-side failure (4xx other than 429)
                logger.error("SendGrid permanent error (%s): %s", status, body)
                return {
                    "success": False,
                    "status_code": status,
                    "body": body,
                    "attempts": attempt,
                    "attempt_details": attempt_details,
                    "error": body
                }

            except httpx.RequestError as exc:
                last_error = str(exc)
                attempt_details.append({
                    "attempt": attempt,
                    "status": None,
                    "body": None,
                    "error": last_error
                })
                logger.exception("Network error while calling SendGrid (attempt %s): %s", attempt, exc)
                # exponential backoff
                await asyncio.sleep(min(2 ** attempt, 30))
                continue

        return {
            "success": False,
            "status_code": None,
            "body": None,
            "attempts": self.max_retries,
            "attempt_details": attempt_details,
            "error": last_error or "max retries exceeded"
        }

    async def get_category_stats(self, category: str, start_date: str, end_date: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        params = {
            "categories": category,
            "start_date": start_date,
            "end_date": end_date,
            "aggregated_by": "day"
        }
        try:
            resp = await self._client.get(SENDGRID_STATS_URL, headers=headers, params=params)
            status = resp.status_code
            if status != 200:
                return {"success": False, "status_code": status, "error": resp.text}
            data = resp.json()
            totals: Dict[str, int] = {
                "requests": 0,
                "delivered": 0,
                "opens": 0,
                "unique_opens": 0,
                "clicks": 0,
                "unique_clicks": 0,
                "bounces": 0,
                "spam_reports": 0
            }
            for day in data or []:
                for stat in day.get("stats", []) or []:
                    m = stat.get("metrics") or {}
                    for k in totals.keys():
                        v = int(m.get(k, 0) or 0)
                        totals[k] += v
            return {"success": True, "metrics": totals}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_category_stats_all_time(self, category: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Try the sums endpoint first (returns totals across window)
        params_sums = {
            "categories": category,
            "start_date": "2010-01-01"  # sufficiently early to cover all time
        }
        try:
            resp = await self._client.get(SENDGRID_STATS_SUMS_URL, headers=headers, params=params_sums)
            if resp.status_code == 200:
                data = resp.json() or {}
                results = data.get("results") or []
                # some responses may return a single object instead of list
                if isinstance(results, dict):
                    results = [results]
                totals: Dict[str, int] = {
                    "requests": 0,
                    "delivered": 0,
                    "opens": 0,
                    "unique_opens": 0,
                    "clicks": 0,
                    "unique_clicks": 0,
                    "bounces": 0,
                    "spam_reports": 0
                }
                for item in results:
                    m = item.get("metrics") or {}
                    for k in totals.keys():
                        totals[k] += int(m.get(k, 0) or 0)
                return {"success": True, "metrics": totals}
        except Exception:
            pass

        # Fallback to daily stats summed up
        from datetime import date
        end_date = date.today().isoformat()
        return await self.get_category_stats(category, "2010-01-01", end_date)
