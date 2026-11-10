# data consistency checks for the result of the pipeline (run `python pipeline.py` first)

import os

import pandas as pd
import pytest

from path import FINAL_PATH, Twitch_PATH

if not os.path.exists(FINAL_PATH):
    pytest.skip("final dataset not found - run pipeline.py first", allow_module_level=True)

df = pd.read_csv(FINAL_PATH)


def test_one_row_per_game_and_month():
    assert not df.duplicated(subset=["appid", "Year", "Month"]).any()


def test_not_more_rows_than_twitch():
    twitch_rows = len(pd.read_csv(Twitch_PATH, usecols=["Game"], encoding="latin-1"))
    assert len(df) <= twitch_rows


def test_every_row_has_a_steam_game():
    assert df["appid"].notna().all()
    assert df["name"].notna().all()


def test_value_ranges():
    assert (df["Hours_watched"] > 0).all()
    assert df["Rank"].between(1, 200).all()
    assert df["Month"].between(1, 12).all()
    assert df["steam_match_score"].between(90, 100).all()
    assert df["pct_pos_total"].dropna().between(0, 100).all()
    assert (df["avg_players"].dropna() >= 0).all()
    assert (df["peak_players"].dropna() >= df["avg_players"].dropna()).all()


def test_scaled_columns_between_0_and_1():
    for column in ["Hours_watched_scaled", "avg_players_scaled"]:
        assert df[column].dropna().between(0, 1).all()


def test_no_minus_one_as_missing_value():
    for column in ["pct_pos_total", "num_reviews_total", "pct_pos_recent", "num_reviews_recent"]:
        assert not (df[column] == -1).any()
