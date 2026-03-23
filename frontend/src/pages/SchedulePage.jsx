import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { getSchedule } from "../utils/api";

const S = {
  bg: "#0f0f0f", surface: "#1a1a1a", surfaceHigh: "#242424",
  border: "rgba(255,255,255,0.08)", red: "#C6011F", redLight: "#e8284a",
  green: "#4ae176", text: "#f0ebe8", textMuted: "#c9b8ae",
};

export default function SchedulePage() {
  const { data: games, isLoading } = useQuery({ queryKey: ["schedule"], queryFn: getSchedule });

  const upcoming = games?.filter(g => g.status !== "Final") ?? [];
  const results  = games?.filter(g => g.status === "Final").slice(-10).reverse() ?? [];

  const isRedsHome = (g) => g.home_team?.includes("Reds");
  const oppTeam = (g) => isRedsHome(g) ? g.away_team : g.home_team;
  const redsScore = (g) => isRedsHome(g) ? g.home_score : g.away_score;
  const oppScore  = (g) => isRedsHome(g) ? g.away_score : g.home_score;

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "900px" }}>
      <Helmet><title>Reds Schedule — RedsHub</title></Helmet>

      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "1.5rem" }}>
        Schedule
      </h2>

      {isLoading && <p style={{ color: S.textMuted }}>Loading schedule…</p>}

      {/* Upcoming */}
      {upcoming.length > 0 && (
        <section style={{ marginBottom: "2rem" }}>
          <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", textTransform: "uppercase", color: S.red, letterSpacing: "0.1em", marginBottom: "1rem" }}>
            Upcoming Games
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {upcoming.slice(0, 10).map((g, i) => {
              const slug = `${oppTeam(g).toLowerCase().replace(/\s+/g, "-")}-${g.game_date}`;
              return (
                <Link key={i} to={`/game/${slug}`} style={{ textDecoration: "none" }}>
                  <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "1rem 1.25rem", border: `1px solid ${S.border}`, display: "flex", alignItems: "center", justifyContent: "space-between", transition: "border-color 0.15s" }}
                    onMouseEnter={e => (e.currentTarget.style.borderColor = S.red)}
                    onMouseLeave={e => (e.currentTarget.style.borderColor = S.border)}
                  >
                    <div>
                      <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.9375rem", color: S.text }}>
                        {isRedsHome(g) ? "vs" : "@"} {oppTeam(g)}
                      </span>
                      <span style={{ display: "block", fontSize: "0.625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", marginTop: "0.125rem" }}>
                        {new Date(g.game_date + "T12:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
                        {g.arena && ` · ${g.arena}`}
                      </span>
                    </div>
                    <span style={{ fontSize: "0.5625rem", fontWeight: 900, color: S.red, textTransform: "uppercase", letterSpacing: "0.1em" }}>Preview →</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      {/* Recent Results */}
      {results.length > 0 && (
        <section>
          <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", textTransform: "uppercase", color: S.textMuted, letterSpacing: "0.1em", marginBottom: "1rem" }}>
            Recent Results
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {results.map((g, i) => {
              const rs = redsScore(g);
              const os = oppScore(g);
              const won = rs > os;
              return (
                <div key={i} style={{ background: S.surface, borderRadius: "0.75rem", padding: "1rem 1.25rem", border: `1px solid ${S.border}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.9375rem", color: S.text }}>
                      {isRedsHome(g) ? "vs" : "@"} {oppTeam(g)}
                    </span>
                    <span style={{ display: "block", fontSize: "0.625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", marginTop: "0.125rem" }}>
                      {new Date(g.game_date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.25rem", color: S.text }}>
                      {rs} – {os}
                    </span>
                    <span style={{ background: won ? S.green : S.missBg ?? "#93000a", color: won ? "#003915" : "#ffdad6", padding: "0.1875rem 0.625rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.8125rem", borderRadius: "0.25rem", textTransform: "uppercase", fontStyle: "italic" }}>
                      {won ? "W" : "L"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
