#!/usr/bin/env python3
"""Fetch the public GitHub contribution calendar and derive daily/monthly stats."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "contributions.json"
IST = ZoneInfo("Asia/Kolkata")


class CalendarParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.days: dict[str, dict[str, int | str]] = {}
        self.pending: dict[str, dict[str, object]] = {}
        self.tips: dict[str, str] = {}
        self._tip_for: str | None = None
        self._tip_buf: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        name = tag.lower()
        if name == "tool-tip":
            self._tip_for = attr.get("for", "")
            self._tip_buf = []
            return
        if name != "td":
            return
        day = attr.get("data-date", "")
        if not day:
            return

        level = attr.get("data-level", "")
        raw_count = attr.get("data-count", "")
        label = " ".join((attr.get("aria-label", ""), attr.get("title", ""))).strip()
        count: int | None = None

        if raw_count.isdigit():
            count = int(raw_count)
        else:
            match = re.search(r"([\d,]+)\s+contributions?\b", label, re.IGNORECASE)
            if match:
                count = int(match.group(1).replace(",", ""))
            elif re.search(r"no contributions", label, re.IGNORECASE) or level == "0":
                count = 0

        self.pending[attr.get("id", f"day-{day}")] = {
            "date": day,
            "level": int(level) if level.isdigit() else 0,
            "count": count,
        }

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text_parts.append(data.strip())
        if self._tip_for is not None:
            self._tip_buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "tool-tip" and self._tip_for is not None:
            self.tips[self._tip_for] = "".join(self._tip_buf).strip()
            self._tip_for = None
            self._tip_buf = []

    def resolve(self) -> None:
        """Join day cells with their tooltip counts. Refuses to guess."""
        for td_id, entry in self.pending.items():
            day = str(entry["date"])
            count = entry["count"]
            if count is None:
                body = self.tips.get(td_id, "")
                match = re.search(r"([\d,]+)\s+contributions?\b", body, re.IGNORECASE)
                if match:
                    count = int(match.group(1).replace(",", ""))
                elif re.search(r"no contributions", body, re.IGNORECASE):
                    count = 0
            if count is None:
                raise ValueError(
                    f"Could not read an exact contribution count for {day}. "
                    "GitHub's calendar markup may have changed; refusing to estimate counts."
                )
            self.days[day] = {"date": day, "count": int(count), "level": int(entry["level"])}


def month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def derive_stats(daily: list[dict[str, int | str]], total: int, username: str, start: date, end: date) -> dict:
    counts = {str(item["date"]): int(item["count"]) for item in daily}
    active = sum(1 for value in counts.values() if value > 0)

    current_streak = 0
    cursor = end
    if counts.get(cursor.isoformat(), 0) == 0:
        cursor -= timedelta(days=1)
    while cursor >= start and counts.get(cursor.isoformat(), 0) > 0:
        current_streak += 1
        cursor -= timedelta(days=1)

    longest_streak = 0
    streak = 0
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        if counts.get(day.isoformat(), 0) > 0:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0

    month_totals: dict[str, int] = {}
    for item in daily:
        key = month_key(date.fromisoformat(str(item["date"])))
        month_totals[key] = month_totals.get(key, 0) + int(item["count"])

    month_list: list[dict[str, int | str]] = []
    month_cursor = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while month_cursor <= end_month:
        key = month_key(month_cursor)
        month_list.append({
            "key": key,
            "label": month_cursor.strftime("%b"),
            "count": month_totals.get(key, 0),
        })
        if month_cursor.month == 12:
            month_cursor = date(month_cursor.year + 1, 1, 1)
        else:
            month_cursor = date(month_cursor.year, month_cursor.month + 1, 1)

    busiest = max(daily, key=lambda item: int(item["count"]), default=None)
    busiest_day = None
    if busiest and int(busiest["count"]) > 0:
        busy_date = date.fromisoformat(str(busiest["date"]))
        busiest_day = {
            "date": busy_date.isoformat(),
            "label": busy_date.strftime("%b %-d, %Y") if sys.platform != "win32" else busy_date.strftime("%b %#d, %Y"),
            "count": int(busiest["count"]),
        }

    return {
        "username": username,
        "source": f"https://github.com/users/{username}/contributions",
        "generated_at": datetime.now(IST).isoformat(timespec="seconds"),
        "range_start": start.isoformat(),
        "range_end": end.isoformat(),
        "total_contributions": total,
        "days": daily,
        "months": month_list,
        "active_days": active,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "busiest_day": busiest_day,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="1k24bytes")
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()

    end = datetime.now(IST).date()
    start = end - timedelta(days=364)
    url = f"https://github.com/users/{args.username}/contributions"
    params = {"from": start.isoformat(), "to": end.isoformat()}
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ProfileReadmeCards/1.0)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    calendar = CalendarParser()
    calendar.feed(response.text)
    calendar.resolve()
    if not calendar.days:
        raise RuntimeError("GitHub returned no contribution calendar cells.")

    daily: list[dict[str, int | str]] = []
    skipped: list[str] = []
    cursor = start
    while cursor <= end:
        item = calendar.days.get(cursor.isoformat())
        if item is None:
            # The endpoint sometimes returns a different span (e.g. the calendar
            # year) than the requested window. Skip dates it does not cover
            # rather than inventing counts for them.
            skipped.append(cursor.isoformat())
        else:
            daily.append({"date": cursor.isoformat(), "count": int(item["count"]), "level": int(item["level"])})
        cursor += timedelta(days=1)
    if skipped:
        print(f"Warning: {len(skipped)} day(s) not covered by GitHub's response; "
              f"stats use the {len(daily)} available day(s) ({skipped[0]}..{skipped[-1]} omitted).",
              file=sys.stderr)

    text = " ".join(calendar.text_parts)
    total_match = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", text, re.IGNORECASE)
    if total_match:
        total = int(total_match.group(1).replace(",", ""))
    else:
        total = sum(int(item["count"]) for item in daily)

    result = derive_stats(daily, total, args.username, start, end)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(daily)} daily entries and {total:,} displayed contributions to {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # concise failure message for GitHub Actions logs
        print(f"Contribution fetch failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
