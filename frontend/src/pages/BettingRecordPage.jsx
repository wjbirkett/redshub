import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { getResults } from "../utils/api";

const S = {
  surface: "#1a1a1a", surfaceHigh: "#242424",
  border: "rgba(255,255,255,0.08)", red: "#C6011F", redLight: "#e8284a",
  green: "#4ae176", greenBg: "#06bb55", hitGreen: "#00431a",
  missRed: "#ffb4ab", missBg: "#93000a",
  text: "#f0ebe8", textMuted: "#c9b8ae",
};

function StatBox({ hits, total, label }) {
  const miss = total - hits;
  const pct  = total > 0 ? ((hits / total) * 100).toFixed(1) : "—";
  const good = total > 0 && hits / total >= 0.5;
  return (
    <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "1.5rem", border: `1px solid ${S.border}`, textAlign: "center" }}>
      <span style={{ display: "block", fontSize: "0.5625rem", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.15em", color: S.textMuted, marginBottom: "0.75rem" }}>{label}</span>
      <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "2.5rem", color: good ? S.green : S.missRed, lineHeight: 1 }}>
        {hits}-{miss}
      </span>
      <span style={{ display: "block", fontSize: "0.75rem", color: S.textMuted, marginTop: "0.375rem" }}>{pct}{pct !== "—" ? "%" : ""}</span>
    </div>
  );
}

export default function BettingRecordPage() {
  const { data, isLoading } = useQuery({ queryKey: ["results"], queryFn: getResults });

  const preds   = data?.predictions ?? [];
  const propRes = data?.props ?? [];

  const rlHits  = preds.filter(r => r.spread_result === "HIT").length;
  const rlTotal = preds.filter(r => r.spread_result).length;
  const ouHits  = preds.filter(r => r.total_result === "HIT").length;
  const ouTotal = preds.filter(r => r.total_result).length;
  const phHits  = propRes.filter(r => r.result === "HIT").length;

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "960px" }}>
      <Helmet><title>Reds Betting Record — RedsHub</title></Helmet>

      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "0.5rem" }}>
        AI Betting Record
      </h2>
      <p style={{ color: S.textMuted, fontSize: "0.875rem", marginBottom: "1.5rem" }}>Season-to-date results for all AI predictions</p>

      {isLoading && <p style={{ color: S.textMuted }}>Loading record…</p>}

      {/* Summary boxes */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        <StatBox hits={rlHits}  total={rlTotal}       label="Run Line (RL)" />
        <StatBox hits={ouHits}  total={ouTotal}        label="Over/Under" />
        <StatBox hits={phHits}  total={propRes.length} label="Player Props" />
      </div>

      {/* Game-by-game log */}
      {preds.length > 0 && (
        <section>
          <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", textTransform: "uppercase", color: S.red, letterSpacing: "0.1em", marginBottom: "1rem" }}>
            Game Log
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {preds.map((r, i) => (
              <div key={i} style={{ background: S.surface, borderRadius: "0.5rem", padding: "0.875rem 1.25rem", border: `1px solid ${S.border}`, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                <div>
                  <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.9375rem", color: S.text }}>{r.home_team ?? "CIN"} vs {r.away_team ?? "OPP"}</span>
                  <span style={{ display: "block", fontSize: "0.625rem", color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em" }}>
                    {r.game_date ? new Date(r.game_date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" }) : ""}
                  </span>
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  {r.spread_result && (
                    <span style={{ background: r.spread_result === "HIT" ? S.greenBg : S.missBg, color: r.spread_result === "HIT" ? S.hitGreen : "#ffdad6", padding: "0.1875rem 0.625rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.6875rem", textTransform: "uppercase", letterSpacing: "0.1em", borderRadius: "0.25rem" }}>
                      RL: {r.spread_result}
                    </span>
                  )}
                  {r.total_result && (
                    <span style={{ background: r.total_result === "HIT" ? S.greenBg : S.missBg, color: r.total_result === "HIT" ? S.hitGreen : "#ffdad6", padding: "0.1875rem 0.625rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.6875rem", textTransform: "uppercase", letterSpacing: "0.1em", borderRadius: "0.25rem" }}>
                      O/U: {r.total_result}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {!isLoading && preds.length === 0 && (
        <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "2rem", border: `1px solid ${S.border}` }}>
          <p style={{ color: S.textMuted }}>No resolved predictions yet. Check back after the Reds play!</p>
        </div>
      )}
    </div>
  );
}
