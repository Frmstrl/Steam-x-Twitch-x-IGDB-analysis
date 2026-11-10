# LE4 - Joining the data sources

import pandas as pd


def join_twitch_steam(twitch, steam, matches):
    # add the matched steam name and score to every twitch row
    twitch = twitch.copy()
    twitch["steam_clean_name"] = twitch["clean_name"].map(lambda x: matches[x][0] if x in matches else None)
    twitch["steam_match_score"] = twitch["clean_name"].map(lambda x: matches[x][1] if x in matches else None)

    # LEFT join: all twitch rows stay, the steam columns are empty if there is no match.
    # we use left (not inner) so we can still see which twitch games were NOT found (not_in_steam).
    # validate="many_to_one": every steam name is only once in steam -> the join can't make more rows
    steam = steam.rename(columns={"clean_name": "steam_clean_name"})
    df = twitch.merge(steam, how="left", on="steam_clean_name", validate="many_to_one")

    assert len(df) == len(twitch), "join changed the number of rows!"
    return df.drop(columns=["clean_name", "steam_clean_name"])


def split_matched(df):
    # matched rows -> our dataset, not matched -> a small report (one row per game)
    matched = df[df["appid"].notna()].copy()
    matched["appid"] = matched["appid"].astype(int)

    not_matched = df[df["appid"].isna()]
    not_in_steam = not_matched.groupby("Game").agg(months=("Month", "count"),
                                                   total_hours_watched=("Hours_watched", "sum"))
    not_in_steam = not_in_steam.sort_values("total_hours_watched", ascending=False).reset_index()

    rows_pct = len(matched) / len(df) * 100
    hours_pct = matched["Hours_watched"].sum() / df["Hours_watched"].sum() * 100
    print(f"matched: {rows_pct:.1f}% of twitch rows, {hours_pct:.1f}% of hours watched")
    return matched.reset_index(drop=True), not_in_steam


def add_steamcharts(df, steamcharts):
    # LEFT join on game + month: twitch rows stay, players are empty if steamcharts has no data
    # validate="many_to_one": steamcharts has only one row per game and month
    result = df.merge(steamcharts, how="left", on=["appid", "Year", "Month"], validate="many_to_one")

    assert len(result) == len(df), "join changed the number of rows!"
    print(f"steamcharts: {result['avg_players'].notna().sum()} of {len(result)} rows have player data")
    return result
