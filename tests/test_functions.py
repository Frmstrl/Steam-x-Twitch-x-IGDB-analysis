# tests for the single functions with small hand-made tables

import pandas as pd

from src.match import clean_name, find_matches
from src.clean import remove_double_months, fill_steamcharts_gaps
from src.join import add_steamcharts
from src.transform import add_date, add_shifted, make_wide_table, wide_to_long


def test_clean_name():
    assert clean_name("The Witcher® 3: Wild Hunt") == "witcher 3 wild hunt"
    assert clean_name("Final Fantasy VII") == clean_name("final fantasy 7")
    assert clean_name("Pokémon") == "pokemon"
    assert clean_name(None) == ""


def test_find_matches_exact_and_numbers():
    matches = find_matches(["dota 2", "madden nfl 20"], ["dota 2", "madden nfl 22"])
    assert matches["dota 2"] == ("dota 2", 100)
    assert "madden nfl 20" not in matches   # different number -> no match


def test_remove_double_months_keeps_bigger_row():
    df = pd.DataFrame({"appid": [730, 730], "Year": [2023, 2023], "Month": [9, 9], "Rank": [3, 5],
                       "Game": ["Counter-Strike", "Counter-Strike: Global Offensive"],
                       "Hours_watched": [100, 500]})
    result = remove_double_months(df)
    assert len(result) == 1
    assert result["Hours_watched"].iloc[0] == 500


def test_fill_steamcharts_gaps_only_inside():
    # march is missing -> interpolated between february and april
    steamcharts = pd.DataFrame({"appid": [1, 1, 1], "Year": [2020, 2020, 2020], "Month": [2, 4, 5],
                                "avg_players": [100.0, 300.0, 400.0], "peak_players": [10, 30, 40]})
    result = fill_steamcharts_gaps(steamcharts)
    assert len(result) == 4
    march = result[result["Month"] == 3].iloc[0]
    assert march["avg_players"] == 200.0
    assert march["players_imputed"]


def test_join_does_not_add_rows():
    df = pd.DataFrame({"appid": [1, 1, 2], "Year": [2020, 2020, 2020], "Month": [1, 2, 1]})
    steamcharts = pd.DataFrame({"appid": [1, 1], "Year": [2020, 2020], "Month": [1, 2],
                                "avg_players": [10.0, 20.0]})
    result = add_steamcharts(df, steamcharts)
    assert len(result) == len(df)
    assert result["avg_players"].isna().sum() == 1   # game 2 has no player data


def test_lag_uses_real_previous_month():
    # game 1 is missing in february -> the lag for march must be empty, not january
    df = pd.DataFrame({"appid": [1, 1], "Year": [2020, 2020], "Month": [1, 3], "Hours_watched": [10, 30]})
    df = add_date(df)
    result = add_shifted(df, df, "Hours_watched", 1, "prev")
    assert result["prev"].isna().all()


def test_wide_and_back_to_long():
    df = pd.DataFrame({"Game": ["A", "A", "B"], "Year": [2020, 2020, 2020], "Month": [1, 2, 1],
                       "Hours_watched": [1, 2, 3]})
    df = add_date(df)
    wide = make_wide_table(df)
    assert wide.shape == (2, 2)
    assert len(wide_to_long(wide)) == len(df)
