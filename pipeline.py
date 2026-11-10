# The whole data wrangling pipeline: raw files in -> final dataset out.
#
# Run with default paths:   python pipeline.py
# Run with other paths:     python pipeline.py --twitch my_twitch.csv --output my_folder
# See all parameters:       python pipeline.py --help

import argparse
import os

from path import *
from src.load import load_twitch, load_steam, load_steamcharts, load_list, load_dict
from src.clean import clean_twitch, clean_steam, remove_double_months, fill_steamcharts_gaps, flag_outliers
from src.match import find_matches
from src.join import join_twitch_steam, split_matched, add_steamcharts
from src.transform import add_rolling_mean, add_features, add_groups, add_scaled, make_wide_table


def run_pipeline(twitch_path=Twitch_PATH,
                 steam_path=Steam_PATH,
                 steamcharts_folder=Steamcharts_FOLDER,
                 output_folder=OUTPUT_FOLDER,
                 not_games_path=Not_games_PATH,
                 renamed_path=Renamed_games_PATH,
                 match_cutoff=93):

    print("\n--- 1. import ---")
    twitch = load_twitch(twitch_path)
    steam = load_steam(steam_path)
    steamcharts = load_steamcharts(steamcharts_folder)
    not_games = load_list(not_games_path, "twitch_name")
    renamed = load_dict(renamed_path, "twitch_name", "steam_name")
    print(f"twitch {twitch.shape}, steam {steam.shape}, steamcharts {steamcharts.shape}")

    print("\n--- 2. clean ---")
    twitch = clean_twitch(twitch, not_games, renamed)
    steam = clean_steam(steam)
    steamcharts = fill_steamcharts_gaps(steamcharts)

    print("\n--- 3. match names + join twitch with steam ---")
    matches = find_matches(twitch["clean_name"], steam["clean_name"], cutoff=match_cutoff)
    df = join_twitch_steam(twitch, steam, matches)
    df, not_in_steam = split_matched(df)
    df = remove_double_months(df)

    # save this step, fetch_steamcharts.py needs the list of appids from here
    os.makedirs(output_folder, exist_ok=True)
    df.to_csv(os.path.join(output_folder, "twitch_steam_combined.csv"), index=False)
    not_in_steam.to_csv(os.path.join(output_folder, "not_in_steam.csv"), index=False)

    print("\n--- 4. join with steamcharts ---")
    steamcharts = add_rolling_mean(steamcharts, "avg_players", months=3)
    df = add_steamcharts(df, steamcharts)

    print("\n--- 5. transform ---")
    df = add_features(df, steamcharts)
    df = add_groups(df)
    df = add_scaled(df, "Hours_watched")
    df = add_scaled(df, "avg_players")
    df = flag_outliers(df, "Hours_watched")

    print("\n--- 6. save ---")
    df.to_csv(os.path.join(output_folder, "final_dataset.csv"), index=False)
    make_wide_table(df).to_csv(os.path.join(output_folder, "twitch_hours_wide.csv"))
    print(f"final dataset: {df.shape[0]} rows, {df.shape[1]} columns, {df['appid'].nunique()} games")
    print(f"saved in {output_folder}/")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Twitch x Steam data wrangling pipeline")
    parser.add_argument("--twitch", default=Twitch_PATH, help="twitch csv file")
    parser.add_argument("--steam", default=Steam_PATH, help="steam (kaggle) csv file")
    parser.add_argument("--steamcharts", default=Steamcharts_FOLDER, help="folder with steamcharts csv files")
    parser.add_argument("--output", default=OUTPUT_FOLDER, help="folder for the results")
    parser.add_argument("--cutoff", default=93, type=int, help="minimum fuzzy match score (0-100)")
    args = parser.parse_args()

    run_pipeline(twitch_path=args.twitch,
                 steam_path=args.steam,
                 steamcharts_folder=args.steamcharts,
                 output_folder=args.output,
                 match_cutoff=args.cutoff)
