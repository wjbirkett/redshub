import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { getArticles, getResults } from "../utils/api";
import { getPlayerImage } from "../utils/playerImages";

const S = {
  surface: "#1a1a1a", surfaceHigh: "#242424",
  border: "rgba(255,255,255,0.08)", red: "#C6011F", redLight: "#e8284a",
  green: "#4ae176", greenBg: "#06bb55", hitGreen: "#00431a",
  missRed: "#ffb4ab", missBg: "#93000a",
  text: "#f0ebe8", textMuted: "#c9b8ae",
};

// Key Reds players for props
const REDS_PLAYERS = [
  "Elly De La Cruz", "TJ Friedl", "Spencer Steer",
  "Tyler Stephenson", "Jonathan India", "Jake Fraley",
  "Hunter Greene", "Nick Lodolo", "Graham Ashcraft",
];

export default function PlayerPropsPage() {
  const { data: articles } = useQuery({ queryKey: ["articles"], queryFn: () => getArticles(50) });
  const { data: results  } = useQuery({ queryKey: ["results"],  queryFn: getResults });

  const propArticles = articles?.filter(a => a.article_type === "prop") ?? [];
  const propResults  = results?.props ?? [];

  // Group by player
  const byPlayer = {};
  REDS_PLAYERS.forEach(name => {
    const playerArticles = propArticles.filter(a =>
      a.player?.toLowerCase().includes(name.split(" ").pop().toLowerCase()) ||
      a.title?.toLowerCase().includes(name.split(" ").pop().toLowerCase())
    );
    const playerResults = propResults.filter(r =>
      (r.player ?? "").toLowerCase().includes(name.split(" ").pop().toLowerCase())
    );
    const hits  = playerResults.filter(r => r.result === "HIT").length;
    const total = playerResults.length;
    byPlayer[name] = { articles: playerArticles, hits, total };
  });

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "960px" }}>
      <Helmet>
        <title>Reds Player Props — RedsHub</title>
        <meta name="description" content="AI-powered Cincinnati Reds player prop predictions — hits, home runs, strikeouts, RBI." />
      </Helmet>

      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "0.5rem" }}>
        Player Props
      </h2>
      <p style={{ color: S.textMuted, fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        AI-generated prop picks for key Reds players · Hits, HR, K's, RBI
      </p>

      {/* Latest prop articles */}
      {propArticles.length > 0 && (
        <section style={{ marginBottom: "2rem" }}>
          <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", textTransform: "uppercase", color: S.red, letterSpacing: "0.1em", marginBottom: "1rem" }}>
            Latest Prop Picks
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "0.75rem" }}>
            {propArticles.slice(0, 6).map((a) => (
              <Link key={a.slug} to={`/predictions/${a.slug}`} style={{ textDecoration: "none" }}>
                <div
                  style={{ background: S.surfaceHigh, padding: "1.25rem", borderRadius: "0.5rem", border: `1px solid ${S.border}`, height: "100%", display: "flex", flexDirection: "column", gap: "0.5rem", transition: "border-color 0.15s" }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = S.red)}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = S.border)}
                >
                  <span style={{ background: S.missBg, color: "#ffdad6", padding: "0.1875rem 0.5rem", fontSize: "0.5625rem", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.1em", borderRadius: "999px", width: "fit-content" }}>
                    PROP BET
                  </span>
                  <h4 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.9375rem", lineHeight: 1.3, color: S.text, flex: 1 }}>
                    {a.title}
                  </h4>
                  <span style={{ fontSize: "0.625rem", fontWeight: 900, color: S.red, textTransform: "uppercase" }}>
                    {a.game_date ? new Date(a.game_date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" }) : ""}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Player archive links */}
      <section>
        <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", textTransform: "uppercase", color: S.red, letterSpacing: "0.1em", marginBottom: "1rem" }}>
          Player Archives
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "0.75rem" }}>
          {REDS_PLAYERS.map(name => {
            const { hits, total } = byPlayer[name];
            const slug = name.toLowerCase().replace(/\s+/g, "-");
            const good = total > 0 && hits / total >= 0.5;
            return (
              <Link key={name} to={`/props/${slug}`} style={{ textDecoration: "none" }}>
                <div
                  style={{ background: S.surface, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${S.border}`, display: "flex", justifyContent: "space-between", alignItems: "center", transition: "border-color 0.15s" }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = S.red)}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = S.border)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <img src={getPlayerImage(name)} alt={name} style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover", border: "2px solid #C6011F", flexShrink: 0 }} onError={e => { e.target.src = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146"; }} />
                    <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.875rem", color: S.text }}>{name}</span>
                  </div>
                  {total > 0 ? (
                    <span style={{ background: good ? S.greenBg : S.missBg, color: good ? S.hitGreen : "#ffdad6", padding: "0.125rem 0.5rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.625rem", textTransform: "uppercase", borderRadius: "999px" }}>
                      {hits}-{total - hits}
                    </span>
                  ) : (
                    <span style={{ fontSize: "0.625rem", color: S.textMuted }}>→</span>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
