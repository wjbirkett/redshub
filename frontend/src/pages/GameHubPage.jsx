// GameHubPage.jsx
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { getArticles, getSchedule } from "../utils/api";

const S = { surface:"#1a1a1a",border:"rgba(255,255,255,0.08)",red:"#C6011F",redLight:"#e8284a",text:"#f0ebe8",textMuted:"#c9b8ae",surfaceHigh:"#242424" };

export function GameHubPage() {
  const { gameSlug } = useParams();
  const { data: articles } = useQuery({ queryKey: ["articles"], queryFn: () => getArticles(50) });
  const { data: schedule } = useQuery({ queryKey: ["schedule"], queryFn: getSchedule });

  const parts     = gameSlug?.split("-") ?? [];
  const dateStr   = parts.slice(-3).join("-");
  const oppSlug   = parts.slice(0, -3).join(" ");
  const gameArticles = articles?.filter(a => a.game_date === dateStr) ?? [];

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "780px" }}>
      <Helmet><title>Game Hub — RedsHub</title></Helmet>
      <Link to="/schedule" style={{ fontSize: "0.75rem", fontWeight: 700, color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none", display: "inline-block", marginBottom: "1.25rem" }}>← Schedule</Link>
      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "1.5rem" }}>
        Game Hub · {dateStr}
      </h2>
      {gameArticles.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {gameArticles.map(a => (
            <Link key={a.slug} to={`/predictions/${a.slug}`} style={{ textDecoration: "none" }}>
              <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "1.25rem", border: `1px solid ${S.border}`, transition: "border-color 0.15s" }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = S.red)}
                onMouseLeave={e => (e.currentTarget.style.borderColor = S.border)}>
                <span style={{ fontSize: "0.5625rem", fontWeight: 900, color: S.red, textTransform: "uppercase", letterSpacing: "0.15em" }}>{a.article_type?.replace("_", " ").toUpperCase()}</span>
                <h4 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "1rem", color: S.text, marginTop: "0.25rem" }}>{a.title}</h4>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <p style={{ color: S.textMuted }}>No articles yet for this game.</p>
      )}
    </div>
  );
}

export default GameHubPage;
