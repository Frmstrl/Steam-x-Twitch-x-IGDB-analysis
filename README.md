# Steam x Twitch - Data Wrangling Project (DAW)

**Question:** Is there a connection between how much a game is watched on Twitch and how many people play it on Steam?
Does Twitch popularity come *before* more players on Steam?

## Data sources

| Source | What | Format | How we get it |
|---|---|---|---|
| Twitch history | top 200 games per month 2016-2024 (hours watched, viewers, streamers) | CSV | Kaggle download *(TODO: add link)* |
| Steam games | all Steam games, snapshot March 2025 (price, reviews, genres, ...) | CSV | Kaggle download *(TODO: add link)* |
| SteamCharts | average / peak players **per month** for every game | HTML table | `fetch_steamcharts.py` (web scraping, https://steamcharts.com/app/<appid>) |

Why not SteamSpy: it only gives the numbers for "now" (owners, reviews), which are already in the Kaggle Steam data. It has no history per month.

## Project structure

```
pipeline.py            the whole pipeline: run_pipeline(...) - raw files in, final dataset out
fetch_steamcharts.py   downloads player history from steamcharts (one csv per game)
path.py                all default file paths
src/
  load.py              LE1 import: read files, encoding problems (utf-8 / cp1252)
  clean.py             LE2 clean: duplicates, -1 as missing value, gaps, outliers
  match.py             name matching twitch <-> steam (exact + fuzzy)
  join.py              LE4 join: twitch + steam + steamcharts (left joins with checks)
  transform.py         LE3 transform: date, lag/lead, rolling mean, binning, scaling, wide/long
config/
  not_games.csv        twitch categories that are not games ("Just Chatting", "Music", ...)
  renamed_games.csv    games that have a different name on steam now (GTA V -> GTA V Legacy)
tests/                 pytest: unit tests for the functions + data checks for the result
main.ipynb             step by step demo of the pipeline + first analysis
Makefile               make / make download / make test
```

## How to reproduce

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

1. Put the two Kaggle files in `data/raw/twich_history/Twitch_game_data.csv` and
   `data/raw/steam_games/steam_kaggle_games_march2025_full.csv`
2. First time only (steamcharts needs the list of matched games):
   ```bash
   make pipeline
   make download
   ```
3. Then every time:
   ```bash
   make
   ```
   This runs `pipeline.py` and the tests. Results are in `data/processed/`:
   - `final_dataset.csv` - one row = one game in one month (twitch + steam + steamcharts)
   - `twitch_hours_wide.csv` - hours watched, one row per game, one column per month
   - `not_in_steam.csv` - twitch games we could not find on steam
   - `not_in_steamcharts.csv` - steam games without player history

Pipeline parameters: `python pipeline.py --help`
(input files, output folder, minimum fuzzy match score).

## Data wrangling decisions

**Import (LE1)**
- The Twitch file is mostly UTF-8 but some names are in cp1252 (Windows). We read it with a custom
  error handler that decodes only the broken bytes as cp1252. R-style codes like `<U+00E9>` are turned back into `é`.
- `Year` + `Month` -> `date`, `release_date` -> datetime, price and rank -> ordered categories.

**Cleaning (LE2)**
- Twitch categories that are not games are removed (`config/not_games.csv`), otherwise
  "Just Chatting" is matched with a random Steam game called "Just Chatting".
- Kaggle uses `-1` for "no value" in the review columns -> replaced with NaN.
- Duplicates in Steam (same name more than once): keep the game with the most reviews
  (rounded to thousands), on a tie the smallest appid (original game, not the bundle).
- Two Twitch rows for the same game in the same month (two categories with one name, or Twitch renamed the
  category): keep the row with more hours watched.
- Missing months inside a game's SteamCharts history: linear interpolation (flag `players_imputed`).
  Months before the first SteamCharts month stay empty - the game was not on Steam yet, so 0 or a mean would be wrong.
- Outliers in hours watched (above Q3 + 1.5 IQR of the same game): only flagged (`Hours_watched_outlier`),
  not removed, because big events and releases are real and part of what we study.

**Matching + joins (LE4)**
- There is no common id between Twitch and Steam, only names. Names are normalized (`clean_name`:
  lowercase, no ™/®, no accents, roman numbers -> numbers), then exact match, then fuzzy match
  (score >= 93, short names >= 96, numbers in the name must be the same).
- We do not fix every single wrong match by hand. Only the biggest games that Steam renamed are in
  `config/renamed_games.csv`. `not_in_steam.csv` shows what is left.
- All joins are **left joins** with `validate="many_to_one"` and a row count check, so a join can never create extra rows.

**Transform (LE3)**
- lag / lead via a merge on the shifted date (not `.shift()`, because a game is not in the top 200 every month):
  `hours_watched_prev_month`, `players_prev_month`, `players_next_month` and the changes in %
- `avg_players_rolling_3m`: moving average over 3 months
- `hours_watched_per_player`, `months_since_release`
- binning: `price_group`, `rank_group`
- min-max scaling per game: `Hours_watched_scaled`, `avg_players_scaled` (compare small and big games)
- long -> wide: `twitch_hours_wide.csv`

## Known limitations
- Only games that are on Steam: League of Legends, Fortnite, Valorant, Minecraft are missing.
  We match ~59% of the Twitch game rows and ~52% of the hours watched (without non-game categories).
- The Kaggle Steam numbers (reviews, owners, price) are from March 2025, not from the month of the Twitch row.
  For time analysis use the SteamCharts columns.
- Twitch data has only the top 200 games of every month - a game is only in the data when it is popular.
- Call of Duty games after 2022 share one Steam page, so there are no separate player numbers.
