import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import ReactMarkdown from "react-markdown";
import { getArticle } from "../utils/api";

const S = {
  surface: "#1a1a1a", surfaceHigh: "#242424",
  border: "rgba(255,255,255,0.08)", red: "#C6011F", redLight: "#e8284a",
  green: "#4ae176", greenBg: "#06bb55", hitGreen: "#00431a",
  missRed: "#ffb4ab", text: "#f0ebe8", textMuted: "#c9b8ae",
};

const BADGE = {
  prediction: { bg: "#00508a", color: "#dbe9ff", label: "PREDICTION" },
  best_bet:   { bg: "#06bb55", color: "#00431a", label: "BEST BET" },
  prop:       { bg: "#93000a", color: "#ffdad6", label: "PROP BET" },
  history:    { bg: "#4a1d96", color: "#d8b4fe", label: "HISTORY" },
  postgame:   { bg: "#1a1a1a", color: "#c9b8ae", label: "POSTGAME" },
};

export default function ArticlePage() {
  const { slug } = useParams();
  const { data: article, isLoading, error } = useQuery({
    queryKey: ["article", slug],
    queryFn: () => getArticle(slug),
    enabled: !!slug,
  });

  if (isLoading) return <div style={{ padding: "2rem", color: S.textMuted }}>Loading article…</div>;
  if (error || !article) return (
    <div style={{ padding: "2rem" }}>
      <p style={{ color: S.missRed }}>Article not found.</p>
      <Link to="/predictions" style={{ color: S.red, fontSize: "0.875rem" }}>← Back to Predictions</Link>
    </div>
  );

  const b = BADGE[article.article_type] ?? { bg: "#333", color: "#fff", label: "ARTICLE" };
  const fmt = (d) => d ? new Date(d + "T12:00:00").toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" }) : "";

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "780px" }}>
      <Helmet>
        <title>{article.title} — RedsHub</title>
        <meta name="description" content={article.summary ?? article.title} />
      </Helmet>

      <Link to="/predictions" style={{ fontSize: "0.75rem", fontWeight: 700, color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none", display: "inline-block", marginBottom: "1.25rem" }}>
        ← Predictions
      </Link>

      {/* Article Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <span style={{ background: b.bg, color: b.color, padding: "0.1875rem 0.625rem", fontSize: "0.5625rem", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.1em", borderRadius: "999px", display: "inline-block", marginBottom: "0.75rem" }}>
          {b.label}
        </span>
        <h1 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "clamp(1.5rem, 3vw, 2.25rem)", lineHeight: 1.15, letterSpacing: "-0.02em", color: S.text, marginBottom: "0.75rem" }}>
          {article.title}
        </h1>
        <p style={{ fontSize: "0.75rem", color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700 }}>
          {fmt(article.game_date)}
          {article.home_team && ` · ${article.away_team} @ ${article.home_team}`}
        </p>
      </div>

      {/* Key Picks Panel */}
      {article.key_picks && Object.keys(article.key_picks).length > 0 && (
        <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "1.25rem", border: `1px solid ${S.border}`, marginBottom: "1.5rem" }}>
          <p style={{ fontSize: "0.5625rem", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.15em", color: S.red, marginBottom: "0.75rem" }}>AI Picks</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.625rem" }}>
            {article.key_picks.spread_pick && (
              <div style={{ background: S.surfaceHigh, padding: "0.5rem 0.875rem", borderRadius: "0.375rem" }}>
                <span style={{ fontSize: "0.625rem", color: S.textMuted, display: "block" }}>RUN LINE</span>
                <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", color: S.text }}>{article.key_picks.spread_pick}</span>
                {article.key_picks.spread_lean && (
                  <span style={{ fontSize: "0.625rem", fontWeight: 700, color: article.key_picks.spread_lean === "COVER" ? S.green : S.missRed }}>{article.key_picks.spread_lean}</span>
                )}
              </div>
            )}
            {article.key_picks.total_pick && (
              <div style={{ background: S.surfaceHigh, padding: "0.5rem 0.875rem", borderRadius: "0.375rem" }}>
                <span style={{ fontSize: "0.625rem", color: S.textMuted, display: "block" }}>TOTAL</span>
                <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", color: S.text }}>{article.key_picks.total_pick}</span>
                {article.key_picks.total_lean && (
                  <span style={{ fontSize: "0.625rem", fontWeight: 700, color: article.key_picks.total_lean === "OVER" ? S.green : S.missRed }}>{article.key_picks.total_lean}</span>
                )}
              </div>
            )}
            {article.key_picks.confidence && (
              <div style={{ background: article.key_picks.confidence === "High" ? S.greenBg : S.surfaceHigh, padding: "0.5rem 0.875rem", borderRadius: "0.375rem", display: "flex", alignItems: "center" }}>
                <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.875rem", color: article.key_picks.confidence === "High" ? S.hitGreen : S.textMuted, textTransform: "uppercase" }}>
                  {article.key_picks.confidence} Confidence
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Article Body */}
      <div style={{ lineHeight: 1.75, color: S.text, fontSize: "0.9375rem" }}>
        <style>{`
          .article-body h2 { font-family: 'Space Grotesk', sans-serif; font-weight: 900; font-size: 1.25rem; margin: 1.5rem 0 0.75rem; color: #f0ebe8; text-transform: uppercase; letter-spacing: -0.01em; }
          .article-body h3 { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1rem; margin: 1.25rem 0 0.5rem; color: #C6011F; text-transform: uppercase; letter-spacing: 0.05em; }
          .article-body p  { margin-bottom: 1rem; color: #c9b8ae; }
          .article-body ul, .article-body ol { padding-left: 1.5rem; margin-bottom: 1rem; color: #c9b8ae; }
          .article-body li { margin-bottom: 0.375rem; }
          .article-body strong { color: #f0ebe8; font-weight: 700; }
          .article-body hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1.5rem 0; }
        `}</style>
        <div className="article-body">
          <ReactMarkdown>{article.content || article.body || "_No content available._"}</ReactMarkdown>
        </div>
      </div>

      {/* Footer CTA */}
      <div style={{ marginTop: "2rem", padding: "1.25rem", background: S.surface, borderRadius: "0.75rem", border: `1px solid ${S.border}`, display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
        <p style={{ fontSize: "0.75rem", color: S.textMuted }}>Ready to bet? Place your wager on DraftKings.</p>
        <a href="https://www.draftkings.com" target="_blank" rel="noopener noreferrer"
          style={{ background: S.red, color: "#fff", padding: "0.5rem 1.25rem", borderRadius: "0.25rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none" }}>
          Place Bet →
        </a>
      </div>
    </div>
  );
}
