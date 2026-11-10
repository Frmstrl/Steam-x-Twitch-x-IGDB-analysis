# LE3 - Transforming
# new columns that help to answer our question:
# "is there a connection between popularity on twitch and players on steam?"

import pandas as pd


def add_date(df):
    # Year + Month -> one real date (first day of the month), easier for time calculations
    df["date"] = pd.to_datetime(dict(year=df["Year"], month=df["Month"], day=1))
    return df


def add_rolling_mean(steamcharts, column, months=3):
    # moving average over the last 3 months of the same game (smooths short spikes).
    # works on the steamcharts table, because there every month of a game exists (after fill_steamcharts_gaps)
    steamcharts = steamcharts.sort_values(["appid", "Year", "Month"])
    steamcharts[f"{column}_rolling_{months}m"] = (
        steamcharts.groupby("appid")[column].transform(lambda x: x.rolling(months).mean())
    )
    return steamcharts


def add_shifted(df, source, column, months, new_name):
    # takes the value of `column` from `months` months before (lag, months > 0)
    # or after (lead, months < 0) for the same game.
    # we do it with a merge on the date and not with .shift(), because a game is not in the
    # twitch top 200 every month -> the row before is not always the month before
    shifted = source[["appid", "Year", "Month", column]].copy()
    shifted = add_date(shifted)
    shifted["date"] = shifted["date"] + pd.DateOffset(months=months)
    shifted = shifted[["appid", "date", column]].rename(columns={column: new_name})

    result = df.merge(shifted, how="left", on=["appid", "date"], validate="many_to_one")
    assert len(result) == len(df)
    return result


def add_features(df, steamcharts):
    df = add_date(df)

    # twitch: hours watched last month and the change in %
    df = add_shifted(df, df, "Hours_watched", 1, "hours_watched_prev_month")
    df["hours_watched_change"] = (df["Hours_watched"] - df["hours_watched_prev_month"]) / df["hours_watched_prev_month"]

    # steam: players last month and next month (lag and lead)
    # with "players_next_change" we can check if twitch is ahead of steam
    df = add_shifted(df, steamcharts, "avg_players", 1, "players_prev_month")
    df = add_shifted(df, steamcharts, "avg_players", -1, "players_next_month")
    df["players_change"] = (df["avg_players"] - df["players_prev_month"]) / df["players_prev_month"]
    df["players_next_change"] = (df["players_next_month"] - df["avg_players"]) / df["avg_players"]

    # how many hours of twitch per steam player (big = game is more watched than played)
    df["hours_watched_per_player"] = df["Hours_watched"] / df["avg_players"]

    # how old the game is in this month (negative = twitch month before the steam release)
    df["months_since_release"] = ((df["date"].dt.year - df["release_date"].dt.year) * 12
                                  + (df["date"].dt.month - df["release_date"].dt.month))
    return df


def add_groups(df):
    # binning: continuous price -> ordered categories (ordinal variable)
    df["price_group"] = pd.cut(df["price"],
                               bins=[-1, 0, 10, 30, 60, 1000],
                               labels=["free", "under 10", "10-30", "30-60", "over 60"],
                               ordered=True)

    # rank on twitch -> groups
    df["rank_group"] = pd.cut(df["Rank"],
                              bins=[0, 10, 50, 200],
                              labels=["top 10", "top 11-50", "top 51-200"],
                              ordered=True)
    return df


def add_scaled(df, column):
    # min-max scaling per game: 0 = worst month of this game, 1 = best month.
    # so we can compare the curve of a small game with the curve of a huge game
    minimum = df.groupby("appid")[column].transform("min")
    maximum = df.groupby("appid")[column].transform("max")
    df[column + "_scaled"] = (df[column] - minimum) / (maximum - minimum)
    return df


def make_wide_table(df, column="Hours_watched"):
    # long -> wide: one row per game, one column per month
    wide = df.pivot(index="Game", columns="date", values=column)
    wide.columns = wide.columns.strftime("%Y-%m")
    return wide


def wide_to_long(wide, column="Hours_watched"):
    # wide -> long again (the opposite of make_wide_table), empty months are dropped
    long = wide.reset_index().melt(id_vars="Game", var_name="month", value_name=column)
    return long.dropna(subset=[column])
