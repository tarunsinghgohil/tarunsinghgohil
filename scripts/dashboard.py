"""Build profile/dashboard.svg from the GitHub GraphQL API.

Standard library only, so the workflow needs no pip install.

    GH_TOKEN=<token> python3 scripts/dashboard.py --user tarunsinghgohil
    python3 scripts/dashboard.py --demo          # synthetic data, no token

Token: the workflow's GITHUB_TOKEN works. A personal token (classic, read:user)
makes the counts match your profile when "Include private contributions" is on.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from theme import (
    FONT_STACK, IVORY, LEVEL_0, LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4, LILAC,
    MARIGOLD, NIGHT, NIGHT_2, esc, font_face_css,
)

API = "https://api.github.com/graphql"

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo(os.environ.get("DASHBOARD_TZ", "Asia/Kolkata"))
except Exception:  # tzdata missing: fall back to IST
    LOCAL_TZ = timezone(timedelta(hours=5, minutes=30))

YEARS_QUERY = """
query($login: String!) {
  user(login: $login) { contributionsCollection { contributionYears } }
}"""

CALENDAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}"""


# ---------------------------------------------------------------- data ----

def graphql(query: str, variables: dict, token: str, attempts: int = 4) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-dashboard",
        },
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
            if payload.get("errors"):
                raise RuntimeError(payload["errors"][0].get("message", "GraphQL error"))
            return payload["data"]
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            if attempt == attempts:
                raise SystemExit(f"GitHub API request failed after {attempts} attempts: {exc}")
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def fetch_days(login: str, token: str, today: date) -> dict[date, int]:
    years = graphql(YEARS_QUERY, {"login": login}, token)["user"]
    if years is None:
        raise SystemExit(f"GitHub user '{login}' not found.")
    days: dict[date, int] = {}
    for year in years["contributionsCollection"]["contributionYears"]:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = min(datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                  datetime.now(timezone.utc))
        data = graphql(CALENDAR_QUERY, {
            "login": login, "from": start.isoformat(), "to": end.isoformat(),
        }, token)
        weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for week in weeks:
            for day in week["contributionDays"]:
                d = date.fromisoformat(day["date"])
                if d <= today:
                    days[d] = day["contributionCount"]
    return days


def demo_days(today: date) -> dict[date, int]:
    """Synthetic history shaped like a busy winter and a quieter summer."""
    rng = random.Random(7)
    days = {}
    d = today - timedelta(days=4 * 365)
    while d <= today:
        season = 1.4 if d.month in (1, 2, 3) else 0.5
        busy = rng.random() < 0.55 * season
        days[d] = rng.randint(1, 9) if busy and d.weekday() < 6 else 0
        d += timedelta(days=1)
    return days


@dataclass
class Stats:
    all_time: int
    past_year: int
    current_streak: int
    longest_streak: int
    longest_range: tuple[date, date] | None
    best_count: int
    best_day: date | None
    weeks: list[tuple[date, int]]      # (week start, total), oldest first, 52 items
    weekdays: list[int]                # Mon..Sun totals over the past year


def compute(days: dict[date, int], today: date) -> Stats:
    year_ago = today - timedelta(days=364)
    past = {d: n for d, n in days.items() if d >= year_ago}

    # Current streak: a zero today doesn't break it, the day isn't over yet.
    streak, d = 0, today
    if days.get(d, 0) == 0:
        d -= timedelta(days=1)
    while days.get(d, 0) > 0:
        streak += 1
        d -= timedelta(days=1)

    longest, run, run_start, best_range = 0, 0, None, None
    for d in sorted(days):
        if days[d] > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > longest:
                longest, best_range = run, (run_start, d)
        else:
            run = 0

    best_day = max(past, key=lambda k: (past[k], k), default=None)
    best_count = past.get(best_day, 0) if best_day else 0

    this_monday = today - timedelta(days=today.weekday())
    weeks = []
    for i in range(51, -1, -1):
        start = this_monday - timedelta(weeks=i)
        total = sum(days.get(start + timedelta(days=k), 0) for k in range(7))
        weeks.append((start, total))

    weekdays = [0] * 7
    for d, n in past.items():
        weekdays[d.weekday()] += n

    return Stats(
        all_time=sum(days.values()),
        past_year=sum(past.values()),
        current_streak=streak,
        longest_streak=longest,
        longest_range=best_range,
        best_count=best_count,
        best_day=best_day if best_count else None,
        weeks=weeks,
        weekdays=weekdays,
    )


# ---------------------------------------------------------------- render --

W, H = 1200, 470
PAD = 48


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_day(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def level_for(fraction: float) -> str:
    if fraction > 0.8:
        return LEVEL_4
    if fraction > 0.55:
        return LEVEL_3
    if fraction > 0.3:
        return LEVEL_2
    return LEVEL_1


def render(stats: Stats, today: date) -> str:
    parts: list[str] = []
    add = parts.append

    # Header
    add(f'<text x="{PAD}" y="62" class="h1">Commit activity</text>')
    add(f'<text x="{W - PAD}" y="62" class="muted" text-anchor="end">'
        f'Updated {esc(fmt_day(today))}</text>')

    # KPI row: (value, unit, label)
    days_unit = lambda n: "day" if n == 1 else "days"
    kpis = [
        (fmt_int(stats.all_time), "", "Contributions, all time"),
        (fmt_int(stats.past_year), "", "Contributions, past year"),
        (str(stats.current_streak), days_unit(stats.current_streak), "Current streak"),
        (str(stats.longest_streak), days_unit(stats.longest_streak),
         f"Longest streak, {stats.longest_range[0].strftime('%b %Y')}"
         if stats.longest_range else "Longest streak"),
        (str(stats.best_count), "",
         f"Best day, {fmt_day(stats.best_day)}" if stats.best_day else "Best day"),
    ]
    col_w = (W - 2 * PAD) / len(kpis)
    for i, (value, unit, label) in enumerate(kpis):
        x = PAD + i * col_w + (0 if i == 0 else 24)
        if i:
            add(f'<rect x="{PAD + i * col_w:.1f}" y="98" width="1" height="74" fill="{NIGHT_2}"/>')
        unit_svg = f'<tspan class="unit" dx="6">{unit}</tspan>' if unit else ""
        add(f'<g class="kpi" style="animation-delay:{0.08 * i:.2f}s">'
            f'<text x="{x:.1f}" y="146" class="num">{esc(value)}{unit_svg}</text>'
            f'<text x="{x:.1f}" y="170" class="label">{esc(label)}</text></g>')

    # Weekly skyline: each column is a stack of squares
    chart_x0, chart_x1 = PAD, 820
    chart_base = 408
    max_stack = 11
    cell, gap = 10, 3
    pitch_y = cell + gap
    peak = max((t for _, t in stats.weeks), default=0)
    per_square = max(1, math.ceil(peak / max_stack)) if peak else 1
    col_pitch = (chart_x1 - chart_x0) / len(stats.weeks)
    peak_index = max(range(len(stats.weeks)), key=lambda i: stats.weeks[i][1]) if peak else None

    add(f'<text x="{chart_x0}" y="226" class="label">Weekly contributions, past 52 weeks</text>')
    add(f'<text x="{chart_x1}" y="226" class="label" text-anchor="end">'
        f'Each square is {per_square} contribution{"s" if per_square > 1 else ""}</text>')

    last_month = None
    for i, (start, total) in enumerate(stats.weeks):
        cx = chart_x0 + i * col_pitch + (col_pitch - cell) / 2
        squares = math.ceil(total / per_square) if total else 0
        rects = []
        if squares == 0:
            rects.append(f'<rect x="{cx:.1f}" y="{chart_base - cell}" width="{cell}" '
                         f'height="{cell}" rx="2" fill="{LEVEL_0}"/>')
        for s in range(squares):
            y = chart_base - (s + 1) * pitch_y + gap
            colour = level_for((s + 1) / max_stack)
            if i == peak_index and s == squares - 1:
                colour = MARIGOLD
            rects.append(f'<rect x="{cx:.1f}" y="{y}" width="{cell}" height="{cell}" '
                         f'rx="2" fill="{colour}"/>')
        add(f'<g class="col" style="animation-delay:{0.3 + i * 0.012:.3f}s">{"".join(rects)}</g>')
        if i == peak_index:
            ty = chart_base - squares * pitch_y - 8
            add(f'<text x="{cx + cell / 2:.1f}" y="{ty}" class="peak" text-anchor="middle">'
                f'{total}</text>')
        # Month label under the first week that starts in a new month
        if start.month != last_month and i < len(stats.weeks) - 1:
            if last_month is not None or start.day <= 7:
                add(f'<text x="{cx:.1f}" y="{chart_base + 24}" class="tick">'
                    f'{start.strftime("%b")}</text>')
            last_month = start.month

    # Weekday rhythm
    wx0 = 872
    bar_x0, bar_x1 = wx0 + 48, W - PAD - 40
    add(f'<text x="{wx0}" y="226" class="label">By weekday, past year</text>')
    top = max(stats.weekdays) or 1
    busiest = stats.weekdays.index(max(stats.weekdays)) if any(stats.weekdays) else None
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, (name, total) in enumerate(zip(names, stats.weekdays)):
        y = 256 + i * 23
        width = max(4, (bar_x1 - bar_x0) * total / top)
        colour = MARIGOLD if i == busiest else LEVEL_3
        add(f'<text x="{wx0}" y="{y + 10}" class="tick">{name}</text>')
        add(f'<rect x="{bar_x0}" y="{y}" width="{bar_x1 - bar_x0}" height="12" rx="3" fill="{LEVEL_0}"/>')
        add(f'<rect class="bar" style="animation-delay:{0.5 + i * 0.05:.2f}s" x="{bar_x0}" '
            f'y="{y}" width="{width:.1f}" height="12" rx="3" fill="{colour}"/>')
        add(f'<text x="{W - PAD}" y="{y + 10}" class="tick val" text-anchor="end">{total}</text>')

    body = "".join(parts)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Commit activity</title>
<desc id="d">{fmt_int(stats.all_time)} contributions all time, {fmt_int(stats.past_year)} in the past year. Current streak {stats.current_streak} days, longest {stats.longest_streak} days.</desc>
<style>
{font_face_css()}
text{{font-family:{FONT_STACK}}}
.h1{{font-size:26px;font-weight:700;fill:{IVORY}}}
.muted{{font-size:15px;fill:{LILAC}}}
.num{{font-size:40px;font-weight:700;fill:{IVORY};letter-spacing:-.5px}}
.unit{{font-size:17px;font-weight:400;fill:{LILAC};letter-spacing:0}}
.label{{font-size:15px;fill:{LILAC}}}
.tick{{font-size:13px;fill:{LILAC}}}
.val{{fill:{IVORY}}}
.peak{{font-size:14px;font-weight:700;fill:{MARIGOLD}}}
.kpi,.col{{animation:rise .5s cubic-bezier(.2,.7,.2,1) both}}
.bar{{animation:grow .7s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box;transform-origin:left}}
@keyframes rise{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:none}}}}
@media (prefers-reduced-motion:reduce){{.kpi,.col,.bar{{animation:none}}}}
</style>
<rect width="{W}" height="{H}" rx="18" fill="{NIGHT}"/>
{body}
</svg>
"""


# ------------------------------------------------------------------ main --

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--user", default=os.environ.get("GH_USER", "tarunsinghgohil"))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "profile" / "dashboard.svg"))
    ap.add_argument("--demo", action="store_true", help="render synthetic data, no API calls")
    args = ap.parse_args()

    today = datetime.now(LOCAL_TZ).date()
    if args.demo:
        days = demo_days(today)
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("Set GH_TOKEN (or run with --demo).")
        days = fetch_days(args.user, token, today)

    stats = compute(days, today)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(stats, today), encoding="utf-8")
    print(f"wrote {out}: {stats.past_year} contributions in the past year, "
          f"streak {stats.current_streak}, longest {stats.longest_streak}")


if __name__ == "__main__":
    main()
