"""Checks for merge joins, margin, vote backfill, and 3-2-1 assignment."""

import unittest

import pandas as pd

from brownlow.advanced import attach_advanced_stats, normalize_person_name, parse_advanced_round, team_code_from_name
from brownlow.features import engineer_features
from brownlow.merge import join_players_to_games, normalize_games, normalize_players
from brownlow.model import assign_321_votes, evaluate_vote_ranking, labeled_years, to_rank_dmatrix


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
    def test_drops_letter_finals_rounds(self):
        extra = _players_frame()
        extra["Round"] = extra["Round"].astype(str)
        extra.loc[0, "Round"] = "WF"
        extra.loc[1, "Round"] = "QF"
        players = normalize_players(extra)
        self.assertEqual(len(players), 0)

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
        self.assertIn("disposals_x_closeness", featured.columns)
        self.assertIn("clearances_when_losing", featured.columns)
        self.assertAlmostEqual(float(home["abs_margin"]), abs(float(home["margin"])))


class AdvancedJoinTests(unittest.TestCase):
    def test_name_and_team_normalization(self):
        self.assertEqual(normalize_person_name("Connor O'Sullivan"), "CONNOR OSULLIVAN")
        self.assertEqual(team_code_from_name("Greater Western Sydney"), "GW")
        self.assertEqual(team_code_from_name("Sydney Swans"), "SY")
        self.assertEqual(parse_advanced_round("Opening Round"), 0)
        self.assertEqual(parse_advanced_round("14"), 14)
        self.assertIsNone(parse_advanced_round("Grand Final"))

    def test_joins_on_date_when_round_labels_differ(self):
        players = normalize_players(_players_frame())
        games = normalize_games(_games_frame())
        merged = join_players_to_games(players, games)
        advanced = pd.DataFrame(
            {
                "year": [2024, 2024],
                "round": [0, 0],
                "date": ["2024-03-21", "2024-03-21"],
                "player_first_name": ["Home", "Away"],
                "player_last_name": ["Player", "Player"],
                "player_team": ["Richmond", "Carlton"],
                "player_position": ["C", "CHB"],
                "score_involvements": [8, 2],
                "metres_gained": [500, 120],
                "intercepts": [3, 6],
                "pressure_acts": [20, 10],
                "turnovers": [4, 2],
                "centre_clearances": [5, 0],
                "ground_ball_gets": [9, 3],
                "tackles_inside_fifty": [1, 0],
                "disposal_efficiency_percentage": [75.0, 60.0],
                "effective_disposals": [22, 8],
            }
        )
        joined = attach_advanced_stats(merged, advanced)
        home = joined.loc[joined["player"] == "HOME PLAYER"].iloc[0]
        self.assertEqual(home["metres_gained"], 500)
        self.assertEqual(home["score_involvements"], 8)
        self.assertEqual(home["is_midfielder"], 1.0)
        away = joined.loc[joined["player"] == "AWAY PLAYER"].iloc[0]
        self.assertEqual(away["metres_gained"], 120)
        self.assertEqual(away["is_midfielder"], 0.0)

    def test_last_name_fallback_and_apostrophes(self):
        players = pd.DataFrame(
            {
                "player": ["MITCH HINGE", "CONNOR OSULLIVAN"],
                "team": ["AD", "GE"],
                "date": ["2025-04-01", "2025-04-01"],
                "metres_gained": [pd.NA, pd.NA],
            }
        )
        advanced = pd.DataFrame(
            {
                "player_first_name": ["Mitchell", "Connor"],
                "player_last_name": ["Hinge", "O'Sullivan"],
                "player_team": ["Adelaide", "Geelong"],
                "date": ["2025-04-01", "2025-04-01"],
                "player_position": ["C", "C"],
                "score_involvements": [6, 4],
                "metres_gained": [400, 350],
                "intercepts": [1, 2],
                "pressure_acts": [15, 18],
                "turnovers": [3, 3],
                "centre_clearances": [2, 4],
                "ground_ball_gets": [7, 8],
                "tackles_inside_fifty": [0, 1],
                "disposal_efficiency_percentage": [70.0, 72.0],
                "effective_disposals": [18, 20],
            }
        )
        joined = attach_advanced_stats(players, advanced)
        by_player = joined.set_index("player")
        self.assertEqual(by_player.loc["MITCH HINGE", "metres_gained"], 400)
        self.assertEqual(by_player.loc["CONNOR OSULLIVAN", "metres_gained"], 350)


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

    def test_ranking_metrics_on_a_labeled_game(self):
        val = pd.DataFrame(
            {
                "game_id": [1, 1, 1, 1],
                "player": ["A", "B", "C", "D"],
                "team": ["X", "X", "Y", "Y"],
                "brownlow": [3, 2, 1, 0],
            }
        )
        # Same ranking as actual 3-2-1.
        metrics = evaluate_vote_ranking(val, [0.9, 0.8, 0.7, 0.1])
        self.assertEqual(metrics["games"], 1)
        self.assertEqual(metrics["top3_recall"], 1.0)
        self.assertEqual(metrics["exact_on_voters"], 1.0)
        self.assertEqual(metrics["bog_accuracy"], 1.0)

    def test_rank_dmatrix_groups_by_game(self):
        frame = pd.DataFrame(
            {
                "game_id": [10, 10, 11, 11, 11],
                "player_id": [1, 2, 3, 4, 5],
                "brownlow": [3, 0, 2, 1, 0],
                "kicks": [20, 5, 15, 10, 4],
            }
        )
        dmat, sorted_frame = to_rank_dmatrix(frame, ["kicks"])
        self.assertEqual(len(sorted_frame), 5)
        self.assertEqual(dmat.num_row(), 5)
        groups = sorted_frame.groupby("game_id", sort=False).size().tolist()
        self.assertEqual(groups, [2, 3])

    def test_labeled_years_skips_empty_seasons(self):
        frame = pd.DataFrame(
            {
                "year": [2024, 2024, 2025, 2025, 2026],
                "brownlow": [3, 0, 0, 0, 0],
            }
        )
        self.assertEqual(labeled_years(frame, before_year=2026), [2024])


if __name__ == "__main__":
    unittest.main()
