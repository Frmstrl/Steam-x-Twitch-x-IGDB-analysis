# name matching between twitch and steam
# (the two datasets have no common id, only the game name)

import re
import unicodedata

import pandas as pd
from rapidfuzz import process, fuzz

# roman numerals -> numbers, so "Final Fantasy VII" and "Final Fantasy 7" look the same
ROMAN = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9",
         "xi": "11", "xii": "12", "xiii": "13", "xiv": "14", "xv": "15", "xvi": "16"}


def clean_name(name):
    # makes game names easier to compare: "The Witcher® 3: Wild Hunt" -> "witcher 3 wild hunt"
    if pd.isna(name):
        return ""
    name = str(name).lower()
    name = re.sub(r"[™®©]", " ", name)                                # remove TM, R, C symbols
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))   # remove accents
    name = name.replace("&", " and ")
    name = re.sub(r"[^\w\s]", " ", name)                              # remove punctuation
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"^the ", "", name)                                 # remove "the" at the start
    words = [ROMAN.get(w, w) for w in name.split()]
    return " ".join(words)


def get_numbers(name):
    # all numbers in a name, so "madden nfl 20" is not matched with "madden nfl 22"
    return re.findall(r"\d+", name)


def find_matches(twitch_names, steam_names, cutoff=93, short_cutoff=96):
    # for every twitch name find the steam name that fits: exact first, then fuzzy
    # returns a dict: twitch clean name -> (steam clean name, score)
    steam_names = list(steam_names)
    steam_names_set = set(steam_names)
    matches = {}

    for game in set(twitch_names):
        if game == "":
            continue

        if game in steam_names_set:
            matches[game] = (game, 100)
            continue

        # fuzzy: look at the 5 best candidates
        best = process.extract(game, steam_names, scorer=fuzz.ratio, score_cutoff=cutoff, limit=5)
        for steam_name, score, index in best:
            # short names need a higher score, otherwise "dreams" would match "dream"
            if len(game) < 12 and score < short_cutoff:
                continue
            if get_numbers(game) == get_numbers(steam_name):
                matches[game] = (steam_name, score)
                break

    return matches
