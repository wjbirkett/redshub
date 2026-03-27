import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { getArticles } from "../utils/api";

const S = {
  surface: "#1a1a1a", surfaceHigh: "#242424",
  border: "rgba(255,255,255,0.08)", red: "#C6011F", redLight: "#e8284a",
  green: "#4ae176", text: "#f0ebe8", textMuted: "#c9b8ae",
};

const BADGE = {
  prediction: { bg: "#00508a", color: "#dbe9ff", label: "PREDICTION" },
  best_bet:   { bg: "#06bb55", color: "#00431a", label: "BEST BET" },
  prop:       { bg: "#93000a", color: "#ffdad6", label: "PROP BET" },
  lean_prop:  { bg: "#93000a", color: "#ffdad6", label: "LEAN PICK" },
  history:    { bg: "#4a1d96", color: "#d8b4fe", label: "HISTORY" },
  postgame:   { bg: "#1a1a1a", color: "#c9b8ae", label: "POSTGAME" },
};

const FILTERS = [
  { id: null,         label: "All" },
  { id: "best_bet",  label: "Best Bets" },
  { id: "prediction",label: "Predictions" },
  { id: "prop",      label: "Props" },
  { id: "lean_prop", label: "Lean Picks" },
  { id: "postgame",  label: "Postgame" },
  { id: "history",   label: "History" },
];

import { useState } from "react";

export default function PredictionsPage() {
  const [filter, setFilter] = useState(null);
  const { data: articles, isLoading } = useQuery({ queryKey: ["articles"], queryFn: () => getArticles(50) });

  const filtered = filter ? articles?.filter(a => a.article_type === filter) : articles;

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "1000px" }}>
      <Helmet>
        <title>Reds Predictions & Best Bets — RedsHub</title>
        <meta name="description" content="AI-powered Cincinnati Reds predictions, run line picks, over/under analysis, and player props." />
      </Helmet>

      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "1.5rem" }}>
        Predictions &amp; Analysis
      </h2>

      {/* Filter Pills */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        {FILTERS.map(({ id, label }) => (
          <button
            key={label}
            onClick={() => setFilter(id)}
            style={{ padding: "0.375rem 0.875rem", borderRadius: "999px", border: `1px solid ${filter === id ? S.red : S.border}`, background: filter === id ? S.red : "transparent", color: filter === id ? "#fff" : S.textMuted, fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em", cursor: "pointer" }}
          >
            {label}
          </button>
        ))}
      </div>

      {isLoading && <p style={{ color: S.textMuted }}>Loading predictions…</p>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
        {filtered?.map((a) => {
          const b = BADGE[a.article_type] ?? { bg: "#333", color: "#fff", label: a.article_type?.toUpperCase() ?? "ARTICLE" };
          return (
            <Link key={a.slug} to={`/predictions/${a.slug}`} style={{ textDecoration: "none" }}>
              <div
                style={{ background: S.surfaceHigh, padding: "1.25rem", borderRadius: "0.5rem", border: `1px solid ${S.border}`, height: "100%", display: "flex", flexDirection: "column", gap: "0.5rem", transition: "border-color 0.15s" }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = S.red)}
                onMouseLeave={e => (e.currentTarget.style.borderColor = S.border)}
              >
                <span style={{ background: b.bg, color: b.color, padding: "0.1875rem 0.5rem", fontSize: "0.5625rem", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.1em", borderRadius: "999px", width: "fit-content" }}>
                  {b.label}
                </span>
                <h4 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "1rem", lineHeight: 1.3, color: S.text, flex: 1 }}>
                  {a.title}
                </h4>
                {a.key_picks && (
                  <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap" }}>
                    {a.key_picks.spread_pick && (
                      <span style={{ fontSize: "0.625rem", fontWeight: 700, color: S.textMuted, background: "#2e2e2e", padding: "0.125rem 0.5rem", borderRadius: "999px" }}>{a.key_picks.spread_pick}</span>
                    )}
                    {a.key_picks.total_pick && (
                      <span style={{ fontSize: "0.625rem", fontWeight: 700, color: S.textMuted, background: "#2e2e2e", padding: "0.125rem 0.5rem", borderRadius: "999px" }}>{a.key_picks.total_pick}</span>
                    )}
                  </div>
                )}
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.625rem", fontWeight: 900, textTransform: "uppercase", color: S.red }}>
                  <span>{a.game_date ? new Date(a.game_date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" }) : ""}</span>
                  {a.key_picks?.confidence && (
                    <span style={{ color: a.key_picks.confidence === "High" ? S.green : S.textMuted }}>{a.key_picks.confidence} Conf</span>
                  )}
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {!isLoading && filtered?.length === 0 && (
        <p style={{ color: S.textMuted }}>No articles in this category yet.</p>
      )}
    </div>
  );
}
