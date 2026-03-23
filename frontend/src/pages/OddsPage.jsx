import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { getOdds } from "../utils/api";

const S = {
  surface: "#1a1a1a", surfaceHigh: "#242424",
  border: "rgba(255,255,255,0.08)", red: "#C6011F", redLight: "#e8284a",
  green: "#4ae176", missRed: "#ffb4ab", text: "#f0ebe8", textMuted: "#c9b8ae",
};

export default function OddsPage() {
  const { data: odds, isLoading } = useQuery({ queryKey: ["odds"], queryFn: getOdds });
  const line = Array.isArray(odds) ? odds[0] : odds;

  const fmt = (ml) => ml == null ? "—" : ml > 0 ? `+${ml}` : `${ml}`;
  const isRedsHome = line && (line.home_team?.includes("Reds") || line.home_team?.includes("Cincinnati"));

  const rows = !line ? [] : [
    { label: "Run Line (Reds −1.5)",    value: line.spread != null ? (isRedsHome ? line.spread > 0 ? `+${line.spread}` : `${line.spread}` : `${-line.spread}`) : "—" },
    { label: "Moneyline — Reds",        value: fmt(isRedsHome ? line.moneyline_home : line.moneyline_away) },
    { label: `Moneyline — ${(isRedsHome ? line.away_team : line.home_team)?.split(" ").pop()}`, value: fmt(isRedsHome ? line.moneyline_away : line.moneyline_home) },
    { label: "Over/Under",              value: line.over_under ? `${line.over_under} runs` : "—" },
  ];

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "720px" }}>
      <Helmet><title>Live Odds — RedsHub</title></Helmet>
      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "0.5rem" }}>
        Live Odds
      </h2>
      <p style={{ color: S.textMuted, fontSize: "0.875rem", marginBottom: "1.5rem" }}>Via ESPN · Powered by DraftKings</p>

      {isLoading && <p style={{ color: S.textMuted }}>Fetching lines…</p>}

      {!line && !isLoading && (
        <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "2rem", border: `1px solid ${S.border}` }}>
          <p style={{ color: S.textMuted }}>No game today or lines not yet posted.</p>
        </div>
      )}

      {line && (
        <>
          <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "1.5rem", border: `1px solid ${S.border}`, marginBottom: "1rem" }}>
            <p style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.1rem", color: S.text, marginBottom: "0.25rem" }}>
              {line.away_team} @ {line.home_team}
            </p>
            <p style={{ fontSize: "0.625rem", color: S.textMuted, textTransform: "uppercase", letterSpacing: "0.1em" }}>
              {line.bookmaker ?? "DraftKings"} · {line.commence_time ? new Date(line.commence_time).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : ""}
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {rows.map(({ label, value }) => (
              <div key={label} style={{ background: S.surface, borderRadius: "0.5rem", padding: "1rem 1.25rem", border: `1px solid ${S.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.875rem", color: S.textMuted }}>{label}</span>
                <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.25rem", color: S.redLight }}>{value}</span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: "1.5rem", textAlign: "center" }}>
            <a href="https://www.draftkings.com" target="_blank" rel="noopener noreferrer"
              style={{ display: "inline-block", background: S.red, color: "#fff", padding: "0.75rem 2rem", borderRadius: "0.25rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.875rem", textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none" }}>
              Bet on DraftKings →
            </a>
          </div>
        </>
      )}
    </div>
  );
}
