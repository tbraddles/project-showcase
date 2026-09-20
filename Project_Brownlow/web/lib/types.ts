export type CertaintyLabel = "LOCK" | "LEAN" | "TOSS-UP";

export type TeamMeta = {
  name: string;
  short: string;
  color: string;
  accent: string;
};

export type Leader = {
  rank: number;
  player: string;
  team: string;
  votes: number;
  threes: number;
  twos: number;
  ones: number;
};

export type ClubMarket = {
  team: string;
  name: string;
  short: string;
  color: string;
  accent: string;
  leader: string;
  leaderVotes: number;
  board: Leader[];
};

export type PodiumPlayer = {
  player: string;
  team: string;
  votes: number;
  score: number;
  disp: number;
  goals: number;
  tackles: number;
  clearances: number;
};

export type NightGame = {
  id: number;
  round: number;
  label: string;
  date: string;
  day: string;
  venue: string;
  home: { code: string; name: string; score: number };
  away: { code: string; name: string; score: number };
  certainty: {
    label: CertaintyLabel;
    pct: number;
    bogEdge: number;
    cutEdge: number;
    blurb: string;
  };
  podium: PodiumPlayer[];
  next: PodiumPlayer[];
};

export type NightData = {
  season: number;
  title: string;
  gamesCount: number;
  leaderboard: Leader[];
  clubs: ClubMarket[];
  rounds: { round: number; label: string; count: number }[];
  games: NightGame[];
  teams: Record<string, TeamMeta>;
};
