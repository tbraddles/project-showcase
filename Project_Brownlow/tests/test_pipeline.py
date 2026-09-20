"""Checks for merge joins, margin, vote backfill, and 3-2-1 assignment."""

import unittest

import pandas as pd

from brownlow.features import engineer_features
from brownlow.merge import join_players_to_games, normalize_games, normalize_players
from brownlow.predict import assign_321_votes


def _players_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Player": ["HOME PLAYER", "AWAY PLAYER"],
            "ID": [1, 2],
            "Team": ["RI", "CA"],
            "Opponent": ["CA", "RI"],
            "Round": [1, 1],
            "Year": [2024, 2024],
            "Kicks": [20, 10],
            "Hand Balls": [10, 5],
            "Marks": [5, 2],
            "Goals": [1, 0],
            "Behinds": [0, 0],
            "Hit Outs": [0, 0],
            "Tackles": [4, 2],
            "Rebounds": [1, 3],
            "Inside 50": [6, 1],
            "Clearances": [5, 1],
            "Clangers": [2, 1],
            "Frees For": [1, 0],
            "Frees Against": [0, 1],
            "Brownlow": [3, 0],
            "Contested Possessions": [8, 4],
            "Uncontested Possessions": [12, 6],
            "Contested Marks": [1, 0],
            "Marks Inside 50": [2, 0],
            "One Percenters": [1, 2],
            "Bounces": [0, 0],
            "Goal Assists": [1, 0],
            "% Time Played": [90, 80],
        }
    )


def _games_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Game ID": [100],
            "Year": [2024],
            "Game_Type": ["HA"],
            "Round": [1],
            "Day": ["Thursday"],
            "Home_Team": ["Richmond"],
            "Away_Team": ["Carlton"],
            "Venue": ["M.C.G."],
            "Home_Goals": [17],
            "Home_Behinds": [19],
            "Home_Total": [121],
            "Away_Goals": [15],
            "Away_Behinds": [5],
            "Away_Total": [95],
            "Date": ["2024-03-21"],
        }
    )


class MergeTests(unittest.TestCase):
    def test_home_and_away_players_get_the_same_game(self):
        players = normalize_players(_players_frame())
        games = normalize_games(_games_frame())
        merged = join_players_to_games(players, games)

        self.assertEqual(len(merged), 2)
        self.assertTrue(merged["game_id"].notna().all())
        self.assertEqual(set(merged["game_id"]), {100})
        self.assertEqual(set(merged["home_team_code"]), {"RI"})
        self.assertEqual(set(merged["away_team_code"]), {"CA"})
        self.assertIn("kicks", merged.columns)
        self.assertIn("handballs", merged.columns)
        self.assertNotIn("Hand Balls", merged.columns)
        self.assertNotIn("Game ID", merged.columns)


class FeatureTests(unittest.TestCase):
    def test_margin_is_team_relative(self):
        players = normalize_players(_players_frame())
        games = normalize_games(_games_frame())
        merged = join_players_to_games(players, games)
        featured = engineer_features(
            merged,
            vote_backfills={2023: {"Home Player": 12}, 2017: {}},
        )

        home = featured.loc[featured["player"] == "HOME PLAYER"].iloc[0]
        away = featured.loc[featured["player"] == "AWAY PLAYER"].iloc[0]
        self.assertAlmostEqual(home["margin"], (121 - 95) / 121)
        self.assertAlmostEqual(away["margin"], (95 - 121) / 121)
        self.assertEqual(home["past_votes"], 12)
        self.assertEqual(home["disposals"], 30)
        self.assertIn("goals_x_clearances", featured.columns)


class VoteAssignmentTests(unittest.TestCase):
    def test_assigns_three_two_one_then_zero(self):
        games = pd.DataFrame(
            {
                "game_id": [1, 1, 1, 1, 2, 2],
                "player": ["A", "B", "C", "D", "E", "F"],
                "vote_probability": [0.9, 0.4, 0.8, 0.1, 0.2, 0.7],
            }
        )
        voted = assign_321_votes(games)
        by_player = voted.set_index("player")["votes"]
        self.assertEqual(by_player["A"], 3)
        self.assertEqual(by_player["C"], 2)
        self.assertEqual(by_player["B"], 1)
        self.assertEqual(by_player["D"], 0)
        self.assertEqual(by_player["F"], 3)
        self.assertEqual(by_player["E"], 2)


if __name__ == "__main__":
    unittest.main()
