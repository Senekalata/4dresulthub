import csv
import io
import json
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


SOURCES = {
    "magnum": "https://raw.githubusercontent.com/deadboy18/malaysia-4d/main/data/magnum_draws.csv",
    "damacai": "https://raw.githubusercontent.com/deadboy18/malaysia-4d/main/data/damacai_draws.csv",
    "toto": "https://raw.githubusercontent.com/deadboy18/malaysia-4d/main/data/sportstoto_draws.csv",
    "singapore": "https://raw.githubusercontent.com/TheEverestLab/TOTO-SG-Data/main/4d/draws-all.json",
}


def download(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "4DResultHub/1.0"}
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def clean_number(value):
    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    # Keep 4-digit numbers such as 0039
    return value.zfill(4)


def convert_malaysia(csv_text, operator):
    reader = csv.DictReader(io.StringIO(csv_text))

    results = []

    for row in reader:
        results.append({
            "operator": operator,
            "draw_number": row.get("draw_seq", ""),
            "date": row.get("date", ""),

            "first": clean_number(row.get("prize_1")),
            "second": clean_number(row.get("prize_2")),
            "third": clean_number(row.get("prize_3")),

            "special": [
                clean_number(row.get(f"special_{i}"))
                for i in range(1, 11)
                if row.get(f"special_{i}")
            ],

            "consolation": [
                clean_number(row.get(f"consol_{i}"))
                for i in range(1, 11)
                if row.get(f"consol_{i}")
            ]
        })

    return results


def convert_singapore(json_text):
    source = json.loads(json_text)

    results = []

    for draw in source.get("draws", []):
        results.append({
            "operator": "singapore",
            "draw_number": str(draw.get("drawNumber", "")),
            "date": draw.get("drawDate", ""),

            "first": clean_number(draw.get("firstPrize")),
            "second": clean_number(draw.get("secondPrize")),
            "third": clean_number(draw.get("thirdPrize")),

            "special": [
                clean_number(n)
                for n in draw.get("starterPrizes", [])
            ],

            "consolation": [
                clean_number(n)
                for n in draw.get("consolationPrizes", [])
            ]
        })

    return results


def save_json(filename, data):
    path = DATA_DIR / filename

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Saved {len(data)} draws -> {path}")


def main():

    print("======================================")
    print("       4DResultHub Data Updater")
    print("======================================")

    # Malaysia operators
    for operator in ["magnum", "damacai", "toto"]:

        print(f"\nDownloading {operator}...")

        try:
            csv_text = download(SOURCES[operator])
            data = convert_malaysia(csv_text, operator)

            data.sort(
                key=lambda x: x["date"],
                reverse=True
            )

            save_json(
                f"{operator}.json",
                data
            )

        except Exception as error:
            print(f"ERROR updating {operator}: {error}")

    # Singapore
    print("\nDownloading singapore...")

    try:
        json_text = download(SOURCES["singapore"])

        data = convert_singapore(json_text)

        data.sort(
            key=lambda x: x["date"],
            reverse=True
        )

        save_json(
            "singapore.json",
            data
        )

    except Exception as error:
        print(f"ERROR updating singapore: {error}")

    print("\n======================================")
    print("           UPDATE COMPLETE")
    print("======================================")


if __name__ == "__main__":
    main()
