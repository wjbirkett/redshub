import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { getRoster } from "../utils/api";

const S = {
  surface: "#1a1a1a", surfaceHigh: "#242424", border: "rgba(255,255,255,0.08)",
  red: "#C6011F", redLight: "#e8284a", text: "#f0ebe8", textMuted: "#c9b8ae",
};

const NO_PHOTO = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146";

export default function RosterPage() {
  const { data, isLoading } = useQuery({ queryKey: ["roster"], queryFn: getRoster });

  const groups = data?.groups ?? [];
  const manager = data?.manager;
  const season = data?.season;

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "1100px" }}>
      <Helmet><title>Reds Roster — RedsHub</title></Helmet>

      <div style={{ display: "flex", alignItems: "baseline", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, margin: 0 }}>
          {season ? `${season} ` : ""}Roster
        </h2>
        {manager && (
          <span style={{ fontSize: "0.8125rem", color: S.textMuted, fontWeight: 600 }}>
            Manager: {manager}
          </span>
        )}
      </div>

      {isLoading && <p style={{ color: S.textMuted }}>Loading roster...</p>}

      {groups.map((group) => (
        <section key={group.position_group} style={{ marginBottom: "2.5rem" }}>
          <h3 style={{
            fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1rem",
            textTransform: "uppercase", color: S.red, letterSpacing: "0.1em", marginBottom: "1rem",
          }}>
            {group.position_group}
          </h3>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: "0.75rem",
          }}>
            {group.players.map((p) => (
              <div key={p.id} style={{
                background: S.surface, borderRadius: "0.75rem", border: `1px solid ${S.border}`,
                padding: "1rem", display: "flex", gap: "0.875rem", alignItems: "center",
                transition: "border-color 0.15s",
              }}
                onMouseEnter={e => e.currentTarget.style.borderColor = S.red}
                onMouseLeave={e => e.currentTarget.style.borderColor = S.border}
              >
                <div style={{ position: "relative", flexShrink: 0 }}>
                  <img
                    src={p.headshot}
                    alt={p.name}
                    style={{
                      width: 64, height: 64, borderRadius: "50%", objectFit: "cover",
                      border: `2px solid ${S.red}`, background: "#111",
                    }}
                    onError={e => { e.target.src = NO_PHOTO; }}
                  />
                  {p.jersey && (
                    <span style={{
                      position: "absolute", bottom: -2, right: -2,
                      background: S.red, color: "#fff",
                      fontSize: "0.625rem", fontWeight: 900,
                      fontFamily: "Space Grotesk, sans-serif",
                      padding: "0.125rem 0.375rem", borderRadius: "0.25rem",
                      lineHeight: 1.2,
                    }}>
                      #{p.jersey}
                    </span>
                  )}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 800, fontSize: "0.9375rem", color: S.text, marginBottom: "0.25rem" }}>
                    {p.name}
                  </div>
                  <div style={{ fontSize: "0.6875rem", color: S.redLight, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.375rem" }}>
                    {p.position_name || p.position}
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", fontSize: "0.6875rem", color: S.textMuted }}>
                    {p.height && <span>{p.height}</span>}
                    {p.weight && <span>{p.weight}</span>}
                    {p.age && <span>Age {p.age}</span>}
                    {(p.bats || p.throws) && (
                      <span>B/T: {p.bats}/{p.throws}</span>
                    )}
                  </div>
                  {(p.college || p.birth_place) && (
                    <div style={{ fontSize: "0.625rem", color: "rgba(255,255,255,0.35)", marginTop: "0.25rem" }}>
                      {p.college && <span>{p.college}</span>}
                      {p.college && p.birth_place && <span> · </span>}
                      {p.birth_place && <span>{p.birth_place}{p.birth_state ? `, ${p.birth_state}` : ""}</span>}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}

      {!isLoading && groups.length === 0 && (
        <p style={{ color: S.textMuted }}>Roster not yet available.</p>
      )}
    </div>
  );
}
