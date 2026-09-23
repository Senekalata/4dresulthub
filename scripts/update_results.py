"""
4DResultHub automatic updater.

Updates:
- Magnum 4D from Magnum's public JSON endpoint
- Da Ma Cai 1+3D from Da Ma Cai's public JSON endpoints
- Sports Toto 4D from the official Sports Toto results page
- Singapore 4D from the public TheEverestLab dataset

The script keeps the existing JSON history and adds new draws.
"""

import json
import re
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

MY_TZ = ZoneInfo("Asia/Kuala_Lumpur")
TODAY = datetime.now(MY_TZ).date()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SOURCES = {
    "magnum": "https://www.magnum4d.my/results/past/between-dates/null/{date}/50",
    "damacai_dates": "https://www.damacai.com.my/ListPastResult",
    "damacai_result": "https://www.damacai.com.my/callpassresult?pastdate={date}",
    "toto": "https://www.sportstoto.com.my/results_past.asp?date={month}/15/{year}",
    "singapore": "https://raw.githubusercontent.com/TheEverestLab/TOTO-SG-Data/main/4d/latest.json",
}


def load_json(name):
    path = DATA_DIR / f"{name}.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_json(name, rows):
    path = DATA_DIR / f"{name}.json"
    rows.sort(key=lambda x: str(x.get("date", "")), reverse=True)
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize_row(operator, draw_seq, draw_date, first, second, third, special, consolation):
    def four(value):
        if value is None:
            return ""
        return str(value).strip().zfill(4)

    return {
        "operator": operator,
        "draw_number": str(draw_seq),
        "date": draw_date,
        "first": four(first),
        "second": four(second),
        "third": four(third),
        "special": [four(x) for x in special if str(x).strip()][:10],
        "consolation": [four(x) for x in consolation if str(x).strip()][:10],
    }


def upsert(name, rows):
    old = load_json(name)
    by_key = {
        (str(x.get("date")), str(x.get("draw_number"))): x
        for x in old
    }
    for row in rows:
        by_key[(str(row["date"]), str(row["draw_number"]))] = row
    save_json(name, list(by_key.values()))


def fetch_magnum():
    url = SOURCES["magnum"].format(date=TODAY.isoformat())
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    items = r.json()
    rows = []

    for item in items:
        dd = str(item.get("DrawDate", ""))
        m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", dd)
        if not m:
            continue
        draw_date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        if draw_date != TODAY.isoformat():
            continue

        draw_id = str(item.get("DrawID", ""))
        seq = draw_id.split("/")[0] if draw_id else ""
        row = normalize_row(
            "magnum",
            seq,
            draw_date,
            item.get("FirstPrize"),
            item.get("SecondPrize"),
            item.get("ThirdPrize"),
            [item.get(f"Special{i}", "") for i in range(1, 11)],
            [item.get(f"Console{i}", "") for i in range(1, 11)],
        )
        if row["first"] and row["second"] and row["third"]:
            rows.append(row)

    return rows


def fetch_damacai():
    dates_r = requests.get(
        SOURCES["damacai_dates"],
        headers=HEADERS,
        timeout=30,
    )
    dates_r.raise_for_status()
    dates = dates_r.json().get("drawdate", "").split()

    target = TODAY.strftime("%Y%m%d")
    candidates = [d for d in dates if d <= target]
    if not candidates:
        return []

    # Try the most recent date first. Normally this is today's draw date.
    for date_str in sorted(candidates, reverse=True)[:3]:
        r = requests.get(
            SOURCES["damacai_result"].format(date=date_str),
            headers=HEADERS,
            timeout=30,
        )
        if r.status_code != 200:
            continue

        link = r.json().get("link", "")
        if not link:
            continue

        rr = requests.get(link, timeout=30)
        if rr.status_code != 200:
            continue

        result = rr.json()
        p1, p2, p3 = result.get("p1"), result.get("p2"), result.get("p3")
        if not (p1 and p2 and p3):
            continue

        draw_no = str(result.get("drawNo", ""))
        seq = draw_no.split("/")[0] if draw_no else ""

        row = normalize_row(
            "damacai",
            seq,
            f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
            p1,
            p2,
            p3,
            result.get("starterList", []),
            result.get("consolidateList", []),
        )
        return [row]

    return []


def parse_toto_month(html):
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        return []

    full_text = tables[1].get_text("\n")
    blocks = re.split(
        r"(\d+/\d{2}\s*Draw Date\s*:\s*\d+/\d+/\d+)",
        full_text,
    )

    rows = []
    i = 1
    while i < len(blocks) - 1:
        header, body = blocks[i], blocks[i + 1]
        i += 2

        no = re.search(r"(\d+)/(\d{2})", header)
        dt = re.search(r"Draw Date\s*:\s*(\d+)/(\d+)/(\d+)", header)
        if not no or not dt:
            continue

        draw_seq = no.group(1)
        draw_date = f"{dt.group(3):0>4}-{int(dt.group(2)):02d}-{int(dt.group(1)):02d}"

        prizes = re.search(
            r"First Prize\s+Second Prize\s+Third Prize\s+(\d{4})\s+(\d{4})\s+(\d{4})",
            body,
        )
        if not prizes:
            continue

        sp = re.search(
            r"Special Prize\s+([\d\s]+?)Consolation Prize",
            body,
        )
        co = re.search(
            r"Consolation Prize\s+([\d\s]+?)TOTO 4D JACKPOT",
            body,
        )

        special = re.findall(r"\d{4}", sp.group(1))[:10] if sp else []
        consolation = re.findall(r"\d{4}", co.group(1))[:10] if co else []

        rows.append(
            normalize_row(
                "toto",
                draw_seq,
                draw_date,
                prizes.group(1),
                prizes.group(2),
                prizes.group(3),
                special,
                consolation,
            )
        )

    return rows


def fetch_toto():
    url = SOURCES["toto"].format(
        month=TODAY.month,
        year=TODAY.year,
    )
    r = requests.get(
        url,
        headers={
            **HEADERS,
            "Referer": "https://www.sportstoto.com.my/",
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=30,
    )
    r.raise_for_status()

    return [
        row for row in parse_toto_month(r.text)
        if row["date"] == TODAY.isoformat()
    ]


def fetch_singapore():
    r = requests.get(SOURCES["singapore"], timeout=30)
    r.raise_for_status()
    data = r.json()

    rows = []
    for item in data.get("draws", []):
        draw_date = str(item.get("drawDate", ""))
        if not draw_date:
            continue

        rows.append(
            normalize_row(
                "singapore",
                item.get("drawNumber", ""),
                draw_date,
                item.get("firstPrize"),
                item.get("secondPrize"),
                item.get("thirdPrize"),
                item.get("starterPrizes", []),
                item.get("consolationPrizes", []),
            )
        )

    return rows


def run(name, func):
    try:
        rows = func()
        if rows:
            upsert(name, rows)
            print(f"[OK] {name}: {len(rows)} current row(s)")
        else:
            print(f"[INFO] {name}: no new current result available")
    except Exception as exc:
        print(f"[WARN] {name}: {exc}")


if __name__ == "__main__":
    print(f"4DResultHub updater date: {TODAY.isoformat()}")

    run("magnum", fetch_magnum)
    run("damacai", fetch_damacai)
    run("toto", fetch_toto)
    run("singapore", fetch_singapore)
