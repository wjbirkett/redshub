import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { getSchedule, getArticles } from "../utils/api";

const S = { surface:"#1a1a1a",surfaceHigh:"#242424",border:"rgba(255,255,255,0.08)",red:"#C6011F",redLight:"#e8284a",green:"#4ae176",missRed:"#ffb4ab",text:"#f0ebe8",textMuted:"#c9b8ae" };

export default function MatchupArchivePage() {
  const { opponent } = useParams();
  const displayOpp   = opponent?.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");

  const { data: schedule } = useQuery({ queryKey: ["schedule"], queryFn: getSchedule });
  const { data: articles } = useQuery({ queryKey: ["articles"], queryFn: () => getArticles(100) });

  const oppLower = displayOpp?.toLowerCase() ?? "";
  const matchupGames = schedule?.filter(g =>
    g.home_team?.toLowerCase().includes(oppLower) || g.away_team?.toLowerCase().includes(oppLower)
  ) ?? [];

  const wins   = matchupGames.filter(g => { const rs = g.home_team?.includes("Reds") ? g.home_score : g.away_score; const os = g.home_team?.includes("Reds") ? g.away_score : g.home_score; return g.status === "Final" && rs > os; }).length;
  const losses = matchupGames.filter(g => g.status === "Final").length - wins;

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "780px" }}>
      <Helmet><title>Reds vs {displayOpp} — RedsHub</title></Helmet>
      <Link to="/schedule" style={{ fontSize: "0.75rem", fontWeight: 700, color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none", display: "inline-block", marginBottom: "1.25rem" }}>← Schedule</Link>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text }}>
          Reds vs {displayOpp}
        </h2>
        {matchupGames.filter(g => g.status === "Final").length > 0 && (
          <div style={{ textAlign: "center" }}>
            <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "2rem", color: wins > losses ? S.green : S.missRed }}>{wins}-{losses}</span>
            <span style={{ fontSize: "0.625rem", color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em" }}>Season Series</span>
          </div>
        )}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {matchupGames.length === 0 && <p style={{ color: S.textMuted }}>No matchup data found.</p>}
        {matchupGames.map((g, i) => {
          const isHome = g.home_team?.includes("Reds");
          const rs = isHome ? g.home_score : g.away_score;
          const os = isHome ? g.away_score : g.home_score;
          const won = g.status === "Final" && rs > os;
          return (
            <div key={i} style={{ background: S.surface, borderRadius: "0.5rem", padding: "1rem 1.25rem", border: `1px solid ${S.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.9375rem", color: S.text }}>{isHome ? "vs" : "@"} {displayOpp}</span>
                <span style={{ display: "block", fontSize: "0.625rem", color: S.textMuted, textTransform: "uppercase" }}>
                  {new Date(g.game_date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                </span>
              </div>
              {g.status === "Final" ? (
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, color: S.text }}>{rs} – {os}</span>
                  <span style={{ background: won ? "#06bb55" : "#93000a", color: won ? "#00431a" : "#ffdad6", padding: "0.125rem 0.5rem", fontWeight: 900, fontSize: "0.75rem", borderRadius: "0.25rem", fontStyle: "italic", fontFamily: "Space Grotesk, sans-serif" }}>{won ? "W" : "L"}</span>
                </div>
              ) : (
                <span style={{ fontSize: "0.625rem", color: S.red, fontWeight: 900, textTransform: "uppercase" }}>Upcoming</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
