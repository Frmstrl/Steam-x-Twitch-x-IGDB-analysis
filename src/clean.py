# LE2 - Cleaning
# duplicates, data errors, missing values and outliers

import numpy as np
import pandas as pd

from src.match import clean_name

# steam columns we don't use (long texts, links, images) + score_rank (always empty)
STEAM_DROP_COLUMNS = ["detailed_description", "about_the_game", "short_description", "reviews",
                      "header_image", "support_url", "support_email", "notes", "packages",
                      "screenshots", "movies", "website", "metacritic_url", "score_rank"]

# in the kaggle data -1 means "no value" in these columns -> real missing value (NaN)
STEAM_MINUS_ONE_COLUMNS = ["pct_pos_total", "num_reviews_total", "pct_pos_recent", "num_reviews_recent"]


def clean_twitch(twitch, not_games, renamed):
    # 0. missing value: one row has no game name -> we can't match it with anything, remove it
    print(f"twitch: removed {twitch['Game'].isna().sum()} rows without a game name")
    twitch = twitch[twitch["Game"].notna()]

    # 1. remove twitch categories that are not games ("Just Chatting", "Music", ...)
    is_not_game = twitch["Game"].isin(not_games)
    print(f"twitch: removed {is_not_game.sum()} rows of non-game categories")
    twitch = twitch[~is_not_game].copy()

    # 2. name for matching: some games have a different name on steam now (config/renamed_games.csv)
    twitch["clean_name"] = twitch["Game"].replace(renamed).apply(clean_name)
    return twitch


def clean_steam(steam):
    steam = steam.drop(columns=STEAM_DROP_COLUMNS)

    # data error: -1 is used instead of an empty value
    for column in STEAM_MINUS_ONE_COLUMNS:
        steam[column] = steam[column].replace(-1, np.nan)

    # data type: release date as text -> real date
    steam["release_date"] = pd.to_datetime(steam["release_date"], errors="coerce")

    steam["clean_name"] = steam["name"].apply(clean_name)
    steam = steam[steam["clean_name"] != ""]

    # duplicates: some names are in steam more than once
    #  - the same game as bundle / special edition (Rainbow Six Siege: 359550, 488821, 488822 ...)
    #  - different games with the same name ("Artifact" from Valve and a small game "The Artifact")
    # rule: keep the game with the most reviews (rounded to thousands, because editions
    # of the same game have almost the same number), and if it's a tie -> the smallest appid,
    # because the original game always gets its appid first
    before = len(steam)
    steam["reviews_k"] = steam["num_reviews_total"].fillna(0) // 1000
    steam = steam.sort_values(["reviews_k", "appid"], ascending=[False, True])
    steam = steam.drop_duplicates(subset="clean_name", keep="first")
    steam = steam.drop(columns="reviews_k")
    print(f"steam: removed {before - len(steam)} duplicate names")
    return steam


def remove_double_months(df):
    # after matching, one steam game can have 2 twitch rows in the same month:
    #  - twitch has 2 categories with the same name (old "Resident Evil 2" and the remake)
    #  - twitch renamed the category ("Counter-Strike: Global Offensive" -> "Counter-Strike")
    # we keep the row with more hours watched, it is the main category of this game
    before = len(df)
    df = df.sort_values("Hours_watched", ascending=False)
    df = df.drop_duplicates(subset=["appid", "Year", "Month"], keep="first")
    df = df.sort_values(["Year", "Month", "Rank"]).reset_index(drop=True)
    print(f"removed {before - len(df)} double game-months")
    return df


def fill_steamcharts_gaps(steamcharts):
    # steamcharts sometimes misses a month in the middle of a game's history (site was down).
    # missing months INSIDE the history -> linear interpolation between the month before and after.
    # months before the first / after the last month stay empty (game was not on steam yet / no data),
    # because there we would have to guess, not interpolate.
    filled_games = []
    for appid, game in steamcharts.groupby("appid"):
        game = game.copy()
        game["date"] = pd.to_datetime(dict(year=game["Year"], month=game["Month"], day=1))
        all_months = pd.date_range(game["date"].min(), game["date"].max(), freq="MS")

        game = game.set_index("date").reindex(all_months)
        game["players_imputed"] = game["avg_players"].isna()
        game["avg_players"] = game["avg_players"].interpolate()
        game["peak_players"] = game["peak_players"].interpolate().round()

        game["appid"] = appid
        game["Year"] = game.index.year
        game["Month"] = game.index.month
        filled_games.append(game.reset_index(drop=True))

    result = pd.concat(filled_games, ignore_index=True)
    print(f"steamcharts: filled {result['players_imputed'].sum()} missing months by interpolation")
    return result


def flag_outliers(df, column, group="appid"):
    # outlier = value above Q3 + 1.5 * IQR of the same game (for example a big esports event).
    # we only FLAG them and don't delete: these spikes are real and part of what we want to study
    q1 = df.groupby(group)[column].transform(lambda x: x.quantile(0.25))
    q3 = df.groupby(group)[column].transform(lambda x: x.quantile(0.75))
    months = df.groupby(group)[column].transform("count")

    df[column + "_outlier"] = (df[column] > q3 + 1.5 * (q3 - q1)) & (months >= 6)
    print(f"{column}: {df[column + '_outlier'].sum()} outliers flagged")
    return df
