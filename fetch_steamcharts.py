# Downloads the player history (online players per month) for every game
# in our combined Twitch + Steam dataset.
#
# Where the data comes from: https://steamcharts.com/app/<appid>
# On that page there is a table: Month | Avg. Players | Gain | % Gain | Peak Players
# We save this table for every game as data/raw/steamcharts/<appid>.csv
# After this, run main.ipynb again - the last part joins these files with the twitch data.
#
# Why not SteamSpy? SteamSpy only gives the numbers for "now" (owners, reviews, ccu),
# and those are already in the Kaggle Steam dataset. It has no history per month.
#
# If the script stops, just run it again - games that are already saved are skipped.
#
# Run:  python fetch_steamcharts.py

import os
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from path import COMBINED_Twitch_Steam_PATH, Steamcharts_FOLDER, Not_in_steamcharts_PATH

WAIT_SECONDS = 1  # pause between requests so we don't spam the site


def download_page(appid):
    # returns the html of the steamcharts page, or None if the game is not there
    url = f"https://steamcharts.com/app/{appid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
    except requests.RequestException as error:
        print("   connection error:", error)
        return None

    if response.status_code != 200:
        return None
    return response.text


def read_table(html):
    # takes the html and returns a dataframe with one row per month
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="common-table")
    if table is None:
        return None

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        month_text = cells[0]

        # the first row is "Last 30 Days" - it is not a real month, skip it
        if month_text == "Last 30 Days":
            continue

        # "October 2026" -> month = 10, year = 2026
        date = pd.to_datetime(month_text, format="%B %Y")

        rows.append({
            "Year": date.year,
            "Month": date.month,
            "avg_players": float(cells[1]),
            "gain": float(cells[2]) if cells[2] != "-" else None,
            "pct_gain": float(cells[3].replace("%", "").replace("+", "")) if cells[3] != "-" else None,
            "peak_players": int(cells[4]),
        })

    return pd.DataFrame(rows)


# ---- main part ----

os.makedirs(Steamcharts_FOLDER, exist_ok=True)

combined = pd.read_csv(COMBINED_Twitch_Steam_PATH)
appids = combined["appid"].dropna().astype(int).unique()
print("games in combined dataset:", len(appids))

saved = 0
not_found = []

for i, appid in enumerate(appids, start=1):
    file_path = f"{Steamcharts_FOLDER}/{appid}.csv"

    # already downloaded before -> skip
    if os.path.exists(file_path):
        continue

    print(f"[{i}/{len(appids)}] appid {appid}")

    html = download_page(appid)
    history = read_table(html) if html else None

    if history is None or len(history) == 0:
        print("   no data on steamcharts")
        not_found.append(appid)
    else:
        history.insert(0, "appid", appid)
        history.to_csv(file_path, index=False)
        saved += 1

    time.sleep(WAIT_SECONDS)

print("saved now:", saved)
print("not found on steamcharts:", len(not_found))

# remember which games were not found, so we can look at them later
pd.DataFrame({"appid": not_found}).to_csv(Not_in_steamcharts_PATH, index=False)
