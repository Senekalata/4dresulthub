        draw_date,
        first,
        second,
        third,
        special,
        consolation,
    )


def heading_to_operator(heading):
    if "magnum" in heading.lower():
        return "magnum"
    if "da ma cai" in heading.lower():
        return "damacai"
    return "toto"


def fetch_malaysia():
    text = page_text()

    rows = []

    magnum = parse_4d_section(
        text,
        "Magnum 4D",
        "Da Ma Cai 1+3D",
    )
    if magnum:
        rows.append(magnum)

    damacai = parse_4d_section(
        text,
        "Da Ma Cai 1+3D",
        "Da Ma Cai 3+3D",
    )
    if damacai:
        rows.append(damacai)

    toto = parse_4d_section(
        text,
        "SportsToto 4D",
        "SportsToto 5D, 6D, Lotto",
    )
    if toto:
        rows.append(toto)

    return rows


def fetch_singapore():
    response = requests.get(
        SINGAPORE_SOURCE,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    rows = []

    for item in data.get("draws", []):
        draw_date = str(item.get("drawDate", "")).strip()

        if not draw_date:
            continue

        row = normalize_row(
            "singapore",
            item.get("drawNumber", ""),
            draw_date,
            item.get("firstPrize"),
            item.get("secondPrize"),
            item.get("thirdPrize"),
            item.get("starterPrizes", []),
            item.get("consolationPrizes", []),
        )

        if row["first"] and row["second"] and row["third"]:
            rows.append(row)

    return rows


def run(name, func):
    try:
        rows = func()

        if rows:
            upsert(name, rows)
            print(f"[OK] {name}: {len(rows)} current row(s)")
        else:
            print(
                f"[INFO] {name}: no current result available for "
                f"{TODAY.isoformat()}"
            )

    except Exception as exc:
        print(f"[WARN] {name}: {exc}")


if __name__ == "__main__":
    print(f"4DResultHub updater date: {TODAY.isoformat()}")

    malaysia_rows = fetch_malaysia()

    for operator in ("magnum", "damacai", "toto"):
        matching = [
            row for row in malaysia_rows
            if row["operator"] == operator
        ]
        run(operator, lambda rows=matching: rows)

    run("singapore", fetch_singapore)
