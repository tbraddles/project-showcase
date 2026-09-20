"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import raw from "../data/night.json";
import type { Leader, NightData, NightGame } from "@/lib/types";

const night = raw as NightData;

type Tab = "board" | "slip" | "clubs";

function formatDate(iso: string, day: string) {
  const date = new Date(`${iso}T12:00:00`);
  const month = date.toLocaleString("en-AU", { month: "short" });
  return `${day.slice(0, 3)} ${date.getDate()} ${month}`;
}

function runningRace(games: NightGame[], through: number): Leader[] {
  const tally = new Map<string, Leader>();
  for (let i = 0; i <= through; i += 1) {
    for (const player of games[i].podium) {
      const key = `${player.player}|${player.team}`;
      const current = tally.get(key) ?? {
        rank: 0,
        player: player.player,
        team: player.team,
        votes: 0,
        threes: 0,
        twos: 0,
        ones: 0,
      };
      current.votes += player.votes;
      if (player.votes === 3) current.threes += 1;
      if (player.votes === 2) current.twos += 1;
      if (player.votes === 1) current.ones += 1;
      tally.set(key, current);
    }
  }
  return [...tally.values()]
    .sort((a, b) => b.votes - a.votes || b.threes - a.threes)
    .map((row, index) => ({ ...row, rank: index + 1 }));
}

function TeamPill({ code }: { code: string }) {
  const team = night.teams[code];
  return (
    <span className="pill" style={{ background: team?.color ?? "#222", color: team?.accent ?? "#fff" }}>
      {code}
    </span>
  );
}

function matchesPlayer(row: Leader, needle: string) {
  if (row.player.toLowerCase().includes(needle) || row.team.toLowerCase().includes(needle)) {
    return true;
  }
  const team = night.teams[row.team];
  if (!team) return false;
  return team.name.toLowerCase().includes(needle) || team.short.toLowerCase().includes(needle);
}

function VoteChip({ votes }: { votes: number }) {
  return <span className={`chip chip-${votes}`}>{votes}</span>;
}

function CertaintyBadge({ game }: { game: NightGame }) {
  const tone = game.certainty.label.toLowerCase().replace("-", "");
  return (
    <div className={`cert cert-${tone}`}>
      <span className="cert-kicker">{game.certainty.label}</span>
      <span className="cert-pct">{game.certainty.pct}</span>
    </div>
  );
}

function Ticket({ game }: { game: NightGame }) {
  return (
    <article className="ticket">
      <div className="ticket-top">
        <div>
          <p className="kicker">
            {game.label} · {formatDate(game.date, game.day)}
          </p>
          <h3>
            {game.home.name} <span>{game.home.score}</span>
          </h3>
          <h3>
            {game.away.name} <span>{game.away.score}</span>
          </h3>
          <p className="venue">{game.venue}</p>
        </div>
        <CertaintyBadge game={game} />
      </div>
      <p className="blurb">{game.certainty.blurb}</p>
      <ol className="podium">
        {game.podium.map((player) => (
          <li key={`${player.player}-${player.votes}`}>
            <VoteChip votes={player.votes} />
            <div className="podium-who">
              <strong>{player.player}</strong>
              <span>
                <TeamPill code={player.team} /> {player.disp} disp · {player.goals}g · {player.clearances} cl
              </span>
            </div>
          </li>
        ))}
      </ol>
      <div className="next-best">
        <p className="kicker">Just missed</p>
        <p>
          {game.next
            .map(
              (player) =>
                `${player.player.split(" ").slice(-1)[0]} (${night.teams[player.team]?.short ?? player.team})`,
            )
            .join(" · ")}
        </p>
      </div>
    </article>
  );
}

function TicketPane({ game }: { game: NightGame | undefined }) {
  if (!game) return <div className="ticket ticket-empty" />;
  return <Ticket game={game} />;
}

export default function NightApp() {
  const [tab, setTab] = useState<Tab>("board");
  const [query, setQuery] = useState("");
  const [gameIndex, setGameIndex] = useState(0);
  const [incoming, setIncoming] = useState<number | null>(null);
  const [slide, setSlide] = useState<0 | 1 | -1>(0);
  const roundsRef = useRef<HTMLDivElement>(null);
  const moving = useRef(false);
  const touchX = useRef<number | null>(null);

  const shownIndex = incoming ?? gameIndex;
  const favourite = night.leaderboard[0];
  const game = night.games[shownIndex];
  const race = useMemo(() => runningRace(night.games, shownIndex).slice(0, 5), [shownIndex]);

  const filteredBoard = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return night.leaderboard;
    return night.leaderboard.filter((row) => matchesPlayer(row, needle));
  }, [query]);

  function goTo(index: number) {
    const next = Math.max(0, Math.min(night.games.length - 1, index));
    if (next === gameIndex || moving.current) return;
    moving.current = true;
    setIncoming(next);
    setSlide(next > gameIndex ? 1 : -1);
  }

  function finishSlide() {
    if (incoming === null) return;
    setGameIndex(incoming);
    setIncoming(null);
    setSlide(0);
    moving.current = false;
  }

  function nudgeRounds(direction: -1 | 1) {
    roundsRef.current?.scrollBy({ left: direction * 240, behavior: "smooth" });
  }

  function goRound(round: number) {
    const index = night.games.findIndex((item) => item.round === round);
    if (index < 0) return;
    if (tab !== "slip") {
      setGameIndex(index);
      setTab("slip");
      return;
    }
    goTo(index);
  }

  useEffect(() => {
    if (tab !== "slip") return;
    const rail = roundsRef.current;
    const active = rail?.querySelector<HTMLButtonElement>("button.on");
    if (!rail || !active) return;
    const firstRound = night.rounds[0]?.round;
    if (game.round === firstRound) {
      rail.scrollTo({ left: 0 });
      return;
    }
    const chip = active.getBoundingClientRect();
    const box = rail.getBoundingClientRect();
    const left = chip.left - box.left + rail.scrollLeft - box.width / 2 + chip.width / 2;
    rail.scrollTo({ left: Math.max(0, left) });
  }, [tab, game.round]);

  const leftGame = slide === -1 && incoming !== null ? night.games[incoming] : night.games[gameIndex - 1];
  const rightGame = slide === 1 && incoming !== null ? night.games[incoming] : night.games[gameIndex + 1];
  const shift = slide === 1 ? "-66.666%" : slide === -1 ? "0%" : "-33.333%";

  return (
    <div className="desk">
      <header className="top">
        <div className="brand">
          <p className="kicker">Brownlow night · {night.season}</p>
          <h1>Sizzle Card</h1>
        </div>
        <div className="fav">
          <span>Favourite</span>
          <strong>
            {favourite.player.split(" ").slice(-1)[0]} {favourite.votes}
          </strong>
        </div>
      </header>

      {tab === "board" && (
        <section className="panel">
          <div className="headline">
            <div>
              <p className="kicker">The board</p>
              <h2>Season card</h2>
            </div>
            <p className="lede">
              Full predicted 3-2-1. This is the medal table if the model called every game.
              {query.trim() ? ` ${filteredBoard.length} hits.` : ` ${night.leaderboard.length} listed.`}
            </p>
          </div>
          <label className="search">
            <span>Find a player</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Daicos, Richmond, Crows..."
              enterKeyHint="search"
            />
          </label>
          <div className="table-wrap">
            <table className="board">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Player</th>
                  <th>3-2-1</th>
                  <th>Votes</th>
                </tr>
              </thead>
              <tbody>
                {filteredBoard.map((row) => (
                  <tr key={`${row.player}-${row.team}`} className={row.rank <= 3 ? "podium-row" : undefined}>
                    <td className="mono">{row.rank}</td>
                    <td>
                      <div className="who">
                        <TeamPill code={row.team} />
                        <span>{row.player}</span>
                      </div>
                    </td>
                    <td className="ticks">
                      <span>{row.threes}×3</span>
                      <span>{row.twos}×2</span>
                      <span>{row.ones}×1</span>
                    </td>
                    <td className="votes">{row.votes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === "slip" && (
        <section className="panel slip-panel">
          <div className="headline slip-head">
            <div>
              <p className="kicker">The slip</p>
              <h2>
                {game.label} · {shownIndex + 1}/{night.games.length}
              </h2>
            </div>
            <div className="stepper">
              <button type="button" onClick={() => goTo(gameIndex - 1)} disabled={gameIndex === 0 || incoming !== null}>
                Prev
              </button>
              <button
                type="button"
                onClick={() => goTo(gameIndex + 1)}
                disabled={gameIndex === night.games.length - 1 || incoming !== null}
              >
                Next
              </button>
            </div>
          </div>
          <p className="legend">LOCK 72–99 · LEAN 50–71 · TOSS-UP under 50.</p>
          <div className="round-rail">
            <button type="button" className="round-nudge" aria-label="Earlier rounds" onClick={() => nudgeRounds(-1)}>
              ‹
            </button>
            <div className="rounds" ref={roundsRef} role="tablist" aria-label="Rounds">
              {night.rounds.map((round) => (
                <button
                  key={round.round}
                  type="button"
                  className={game.round === round.round ? "on" : undefined}
                  onClick={() => goRound(round.round)}
                >
                  {round.label}
                </button>
              ))}
            </div>
            <button type="button" className="round-nudge" aria-label="Later rounds" onClick={() => nudgeRounds(1)}>
              ›
            </button>
          </div>
          <div
            className="slip-viewport"
            onPointerDown={(event) => {
              touchX.current = event.clientX;
            }}
            onPointerUp={(event) => {
              if (touchX.current === null) return;
              const delta = event.clientX - touchX.current;
              touchX.current = null;
              if (delta < -40) goTo(gameIndex + 1);
              if (delta > 40) goTo(gameIndex - 1);
            }}
          >
            <div
              className={slide === 0 ? "slip-strip" : "slip-strip is-moving"}
              style={{ transform: `translate3d(${shift}, 0, 0)` }}
              onTransitionEnd={(event) => {
                if (event.propertyName === "transform") finishSlide();
              }}
            >
              <TicketPane game={leftGame} />
              <TicketPane game={night.games[gameIndex]} />
              <TicketPane game={rightGame} />
            </div>
          </div>
          <div className="race">
            <p className="kicker">Race through this game</p>
            <ol>
              {race.map((row) => (
                <li key={`${row.player}-${row.team}`}>
                  <span className="mono">{row.rank}</span>
                  <TeamPill code={row.team} />
                  <span className="race-name">{row.player}</span>
                  <strong>{row.votes}</strong>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {tab === "clubs" && (
        <section className="panel">
          <div className="headline">
            <div>
              <p className="kicker">Club markets</p>
              <h2>Most votes per team</h2>
            </div>
            <p className="lede">Each club&apos;s vote horse, then the rest of the stable.</p>
          </div>
          <div className="club-grid">
            {night.clubs.map((club) => (
              <article key={club.team} className="club" style={{ borderColor: club.accent }}>
                <header style={{ background: club.color, color: club.accent }}>
                  <p>{club.short}</p>
                  <h3>{club.leader}</h3>
                  <strong>{club.leaderVotes}</strong>
                </header>
                <ol>
                  {club.board.map((player, index) => (
                    <li key={player.player} className={index === 0 ? "horse" : undefined}>
                      <span>{player.player}</span>
                      <b>{player.votes}</b>
                    </li>
                  ))}
                </ol>
              </article>
            ))}
          </div>
        </section>
      )}

      <nav className="dock">
        <button type="button" className={tab === "board" ? "on" : undefined} onClick={() => setTab("board")}>
          Board
        </button>
        <button type="button" className={tab === "slip" ? "on" : undefined} onClick={() => setTab("slip")}>
          Slip
        </button>
        <button type="button" className={tab === "clubs" ? "on" : undefined} onClick={() => setTab("clubs")}>
          Clubs
        </button>
      </nav>
    </div>
  );
}
