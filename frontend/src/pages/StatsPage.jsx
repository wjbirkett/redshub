import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { getStats } from "../utils/api";
import { getPlayerImage } from "../utils/playerImages";

const S = {
  surface: "#1a1a1a", surfaceHigh: "#242424", border: "rgba(255,255,255,0.08)",
  red: "#C6011F", redLight: "#e8284a", text: "#f0ebe8", textMuted: "#c9b8ae",
};

export default function StatsPage() {
  const { data: stats, isLoading } = useQuery({ queryKey: ["stats"], queryFn: getStats });

  const batters  = stats?.filter(p => p.at_bats > 0 || p.avg != null).slice(0, 15) ?? [];
  const pitchers = stats?.filter(p => p.era  != null).slice(0, 10) ?? [];

  const TH = ({ children }) => (
    <th style={{ padding: "0.625rem 0.75rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.625rem", textTransform: "uppercase", letterSpacing: "0.1em", color: S.textMuted, textAlign: "right", borderBottom: `1px solid ${S.border}` }}>
      {children}
    </th>
  );
  const TD = ({ children, highlight }) => (
    <td style={{ padding: "0.625rem 0.75rem", fontSize: "0.875rem", textAlign: "right", color: highlight ? S.redLight : S.text }}>
      {children ?? "—"}
    </td>
  );

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "1000px" }}>
      <Helmet><title>Reds Stats — RedsHub</title></Helmet>
      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "1.5rem" }}>
        Player Stats
      </h2>

      {isLoading && <p style={{ color: S.textMuted }}>Loading stats…</p>}

      {/* Batting */}
      {batters.length > 0 && (
        <section style={{ marginBottom: "2.5rem" }}>
          <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", textTransform: "uppercase", color: S.red, letterSpacing: "0.1em", marginBottom: "1rem" }}>
            Batting
          </h3>
          <div style={{ background: S.surface, borderRadius: "0.75rem", border: `1px solid ${S.border}`, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ padding: "0.625rem 0.75rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.625rem", textTransform: "uppercase", letterSpacing: "0.1em", color: S.textMuted, textAlign: "left", borderBottom: `1px solid ${S.border}` }}>Player</th>
                  <TH>G</TH><TH>AVG</TH><TH>HR</TH><TH>RBI</TH><TH>OPS</TH><TH>SB</TH>
                </tr>
              </thead>
              <tbody>
                {batters.map((p, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${S.border}` }}>
                    <td style={{ padding: "0.625rem 0.75rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.875rem", color: S.text }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <img src={getPlayerImage(p.player_name)} alt={p.player_name} style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover", border: "2px solid #C6011F", flexShrink: 0 }} onError={e => { e.target.src = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146"; }} />
                        {p.player_name}
                      </div>
                    </td>
                    <TD>{p.games_played}</TD>
                    <TD highlight>{p.avg?.toFixed(3) ?? p.batting_avg?.toFixed(3)}</TD>
                    <TD>{p.home_runs ?? p.hr}</TD>
                    <TD>{p.rbi}</TD>
                    <TD>{p.ops?.toFixed(3)}</TD>
                    <TD>{p.stolen_bases ?? p.sb}</TD>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Pitching */}
      {pitchers.length > 0 && (
        <section>
          <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem", textTransform: "uppercase", color: S.red, letterSpacing: "0.1em", marginBottom: "1rem" }}>
            Pitching
          </h3>
          <div style={{ background: S.surface, borderRadius: "0.75rem", border: `1px solid ${S.border}`, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ padding: "0.625rem 0.75rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.625rem", textTransform: "uppercase", letterSpacing: "0.1em", color: S.textMuted, textAlign: "left", borderBottom: `1px solid ${S.border}` }}>Player</th>
                  <TH>G</TH><TH>ERA</TH><TH>W-L</TH><TH>SO</TH><TH>WHIP</TH><TH>IP</TH>
                </tr>
              </thead>
              <tbody>
                {pitchers.map((p, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${S.border}` }}>
                    <td style={{ padding: "0.625rem 0.75rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.875rem", color: S.text }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <img src={getPlayerImage(p.player_name)} alt={p.player_name} style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover", border: "2px solid #C6011F", flexShrink: 0 }} onError={e => { e.target.src = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146"; }} />
                        {p.player_name}
                      </div>
                    </td>
                    <TD>{p.games_played}</TD>
                    <TD highlight>{p.era?.toFixed(2)}</TD>
                    <TD>{p.wins != null ? `${p.wins}-${p.losses}` : "—"}</TD>
                    <TD>{p.strikeouts ?? p.so}</TD>
                    <TD>{p.whip?.toFixed(2)}</TD>
                    <TD>{p.innings_pitched?.toFixed(1) ?? p.ip?.toFixed(1)}</TD>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {!isLoading && batters.length === 0 && pitchers.length === 0 && (
        <p style={{ color: S.textMuted }}>Stats not yet available for this season.</p>
      )}
    </div>
  );
}
