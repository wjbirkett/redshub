import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { getBetting, getOdds } from "../utils/api";

const S = {
  surface: "#1a1a1a", surfaceHigh: "#242424", surfaceHighest: "#2e2e2e",
  border: "rgba(255,255,255,0.08)", red: "#C6011F", redLight: "#e8284a",
  green: "#4ae176", missRed: "#ffb4ab", text: "#f0ebe8", textMuted: "#c9b8ae",
};

function OddsCard({ label, value, sublabel }) {
  return (
    <div style={{ background: S.surfaceHigh, borderRadius: "0.5rem", padding: "1.25rem", textAlign: "center", border: `1px solid ${S.border}` }}>
      <span style={{ display: "block", fontSize: "0.5625rem", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.15em", color: S.textMuted, marginBottom: "0.5rem" }}>{label}</span>
      <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", color: S.redLight }}>{value ?? "—"}</span>
      {sublabel && <span style={{ display: "block", fontSize: "0.625rem", color: S.textMuted, marginTop: "0.25rem" }}>{sublabel}</span>}
    </div>
  );
}

export default function BettingPage() {
  const { data: odds, isLoading } = useQuery({ queryKey: ["odds"], queryFn: getOdds });

  const line = Array.isArray(odds) ? odds[0] : odds;

  const formatML = (ml) => {
    if (ml == null) return "—";
    return ml > 0 ? `+${ml}` : `${ml}`;
  };

  const isRedsHome = line && (line.home_team?.includes("Reds") || line.home_team?.includes("Cincinnati"));
  const redsML     = isRedsHome ? line?.moneyline_home : line?.moneyline_away;
  const oppML      = isRedsHome ? line?.moneyline_away : line?.moneyline_home;
  const redsSpread = line?.spread != null ? (isRedsHome ? line.spread : -line.spread) : null;

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "860px" }}>
      <Helmet><title>Reds Betting Lines — RedsHub</title></Helmet>

      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "0.5rem" }}>
        Today's Lines
      </h2>
      <p style={{ color: S.textMuted, fontSize: "0.875rem", marginBottom: "1.5rem" }}>Live odds via ESPN · Updates hourly</p>

      {isLoading && <p style={{ color: S.textMuted }}>Fetching live odds…</p>}

      {!isLoading && !line && (
        <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "2rem", border: `1px solid ${S.border}` }}>
          <p style={{ color: S.textMuted }}>No odds available — the Reds may be off today or lines haven't posted yet.</p>
        </div>
      )}

      {line && (
        <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "1.5rem", border: `1px solid ${S.border}`, marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
            <div>
              <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.125rem", color: S.text }}>
                {line.away_team} @ {line.home_team}
              </span>
              <span style={{ display: "block", fontSize: "0.625rem", color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em", marginTop: "0.25rem" }}>
                {line.bookmaker ?? "DraftKings"}
              </span>
            </div>
            <a
              href="https://www.draftkings.com"
              target="_blank"
              rel="noopener noreferrer"
              style={{ background: S.red, color: "#fff", padding: "0.5rem 1.25rem", borderRadius: "0.25rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none" }}
            >
              Bet Now
            </a>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem" }}>
            <OddsCard
              label="Run Line (Reds)"
              value={redsSpread != null ? (redsSpread > 0 ? `+${redsSpread}` : `${redsSpread}`) : "—"}
              sublabel="−1.5 standard"
            />
            <OddsCard
              label="Reds Moneyline"
              value={formatML(redsML)}
              sublabel={isRedsHome ? "Home" : "Away"}
            />
            <OddsCard
              label="Total (O/U)"
              value={line.over_under ? `${line.over_under}` : "—"}
              sublabel="Runs"
            />
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <p style={{ fontSize: "0.625rem", color: S.textMuted, opacity: 0.5, lineHeight: 1.6 }}>
        Odds are for informational purposes only. Must be 21+ and in a legal state to bet. Gamble responsibly. If you or someone you know has a gambling problem, call 1-800-GAMBLER.
      </p>
    </div>
  );
}
