# all file paths of the project in one place (default values for the pipeline)

# raw data (input)
Twitch_PATH = "data/raw/twich_history/Twitch_game_data.csv"
Steam_PATH = "data/raw/steam_games/steam_kaggle_games_march2025_full.csv"
Steamcharts_FOLDER = "data/raw/steamcharts"   # one csv per game: <appid>.csv (made by fetch_steamcharts.py)

# manual lists (small, written by us, in git)
Not_games_PATH = "config/not_games.csv"
Renamed_games_PATH = "config/renamed_games.csv"

# processed data (output)
OUTPUT_FOLDER = "data/processed"
COMBINED_Twitch_Steam_PATH = "data/processed/twitch_steam_combined.csv"   # twitch + steam (used by fetch_steamcharts.py)
Not_in_steam_PATH = "data/processed/not_in_steam.csv"
Not_in_steamcharts_PATH = "data/processed/not_in_steamcharts.csv"
FINAL_PATH = "data/processed/final_dataset.csv"                          # twitch + steam + steamcharts
