# LE1 - Import
# functions that read the raw files and return pandas dataframes

import codecs
import os

import pandas as pd


def cp1252_fallback(error):
    # the twitch file is mostly utf-8, but some game names were saved in cp1252 (windows encoding).
    # when utf-8 can't read a byte, we read this byte as cp1252 instead of crashing
    if isinstance(error, UnicodeDecodeError):
        bad_bytes = error.object[error.start:error.end]
        return (bad_bytes.decode("cp1252"), error.end)
    raise error


codecs.register_error("cp1252_fallback", cp1252_fallback)


def load_twitch(path):
    # one row = one game in one month (top 200 games of every month)
    twitch = pd.read_csv(path, encoding="utf-8", encoding_errors="cp1252_fallback")

    # some names have R-style unicode codes, for example "Pok<U+00E9>mon" -> "Pokémon"
    twitch["Game"] = twitch["Game"].str.replace(
        r"<U\+([0-9A-Fa-f]{4})>", lambda m: chr(int(m.group(1), 16)), regex=True
    )
    return twitch


def load_steam(path):
    # one row = one steam game (kaggle snapshot from march 2025)
    return pd.read_csv(path, encoding="utf-8", encoding_errors="cp1252_fallback")


def load_steamcharts(folder):
    # one csv per game made by fetch_steamcharts.py -> we put them all in one table
    tables = []
    for file_name in os.listdir(folder):
        if file_name.endswith(".csv"):
            tables.append(pd.read_csv(os.path.join(folder, file_name)))

    if len(tables) == 0:
        print("WARNING: no steamcharts files found, run fetch_steamcharts.py first")
        return pd.DataFrame(columns=["appid", "Year", "Month", "avg_players", "gain", "pct_gain", "peak_players"])

    return pd.concat(tables, ignore_index=True)


def load_list(path, column):
    # reads one column of a small config csv as a python list
    return pd.read_csv(path)[column].tolist()


def load_dict(path, key_column, value_column):
    # reads two columns of a small config csv as a python dict
    table = pd.read_csv(path)
    return dict(zip(table[key_column], table[value_column]))
