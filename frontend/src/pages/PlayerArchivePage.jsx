import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
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

export default function PlayerArchivePage() {
  const { player } = useParams();
  const displayName = player?.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
  const lastName    = displayName?.split(" ").pop()?.toLowerCase() ?? "";

  const { data: articles } = useQuery({ queryKey: ["articles"], queryFn: () => getArticles(100) });
  const { data: results  } = useQuery({ queryKey: ["results"],  queryFn: getResults });

  const playerArticles = articles?.filter(a =>
    a.article_type === "prop" &&
    (a.player?.toLowerCase().includes(lastName) || a.title?.toLowerCase().includes(lastName))
  ) ?? [];

  const playerResults = results?.props?.filter(r =>
    (r.player ?? "").toLowerCase().includes(lastName)
  ) ?? [];

  const hits  = playerResults.filter(r => r.result === "HIT").length;
  const total = playerResults.length;
  const pct   = total > 0 ? ((hits / total) * 100).toFixed(1) : null;
  const good  = total > 0 && hits / total >= 0.5;

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "780px" }}>
      <Helmet><title>{displayName} Props — RedsHub</title></Helmet>

      <Link to="/props" style={{ fontSize: "0.75rem", fontWeight: 700, color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none", display: "inline-block", marginBottom: "1.25rem" }}>
        ← Player Props
      </Link>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <img src={getPlayerImage(displayName)} alt={displayName} style={{ width: 48, height: 48, borderRadius: "50%", objectFit: "cover", border: "2px solid #C6011F", flexShrink: 0 }} onError={e => { e.target.src = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146"; }} />
          <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text }}>
            {displayName}
          </h2>
        </div>
        {total > 0 && (
          <div style={{ textAlign: "center" }}>
            <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "2rem", color: good ? S.green : S.missRed }}>
              {hits}-{total - hits}
            </span>
            <span style={{ fontSize: "0.625rem", color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em" }}>
              {pct}% Hit Rate
            </span>
          </div>
        )}
      </div>

      {/* Result log */}
      {playerResults.length > 0 && (
        <section style={{ marginBottom: "2rem" }}>
          <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", textTransform: "uppercase", color: S.red, letterSpacing: "0.1em", marginBottom: "1rem" }}>
            Results
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {playerResults.map((r, i) => (
              <div key={i} style={{ background: S.surface, borderRadius: "0.5rem", padding: "0.875rem 1.25rem", border: `1px solid ${S.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.875rem", color: S.text }}>
                    {r.prop_type ?? "Prop"}: {r.line ?? "—"}
                  </span>
                  <span style={{ display: "block", fontSize: "0.625rem", color: S.textMuted, textTransform: "uppercase" }}>
                    {r.game_date ? new Date(r.game_date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" }) : ""}
                    {r.actual_value != null ? ` · Actual: ${r.actual_value}` : ""}
                  </span>
                </div>
                <span style={{ background: r.result === "HIT" ? S.greenBg : S.missBg, color: r.result === "HIT" ? S.hitGreen : "#ffdad6", padding: "0.1875rem 0.625rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.6875rem", textTransform: "uppercase", letterSpacing: "0.1em", borderRadius: "0.25rem" }}>
                  {r.result}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Article archive */}
      {playerArticles.length > 0 && (
        <section>
          <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", textTransform: "uppercase", color: S.red, letterSpacing: "0.1em", marginBottom: "1rem" }}>
            Prop Articles
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {playerArticles.map((a) => (
              <Link key={a.slug} to={`/predictions/${a.slug}`} style={{ textDecoration: "none" }}>
                <div style={{ background: S.surface, borderRadius: "0.5rem", padding: "0.875rem 1.25rem", border: `1px solid ${S.border}`, transition: "border-color 0.15s" }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = S.red)}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = S.border)}
                >
                  <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.9375rem", color: S.text, display: "block" }}>{a.title}</span>
                  <span style={{ fontSize: "0.625rem", color: S.red, fontWeight: 900, textTransform: "uppercase" }}>
                    {a.game_date ? new Date(a.game_date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" }) : ""}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {playerArticles.length === 0 && playerResults.length === 0 && (
        <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "2rem", border: `1px solid ${S.border}` }}>
          <p style={{ color: S.textMuted }}>No prop history yet for {displayName}.</p>
        </div>
      )}
    </div>
  );
}
