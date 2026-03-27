import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { getInjuries } from "../utils/api";
import { usePlayerImages } from "../utils/playerImages";

const S = {
  bg: "#0f0f0f", surface: "#1a1a1a", surfaceHigh: "#242424",
  border: "rgba(255,255,255,0.08)", red: "#C6011F", redLight: "#e8284a",
  text: "#f0ebe8", textMuted: "#c9b8ae", missRed: "#ffb4ab", missBg: "#93000a",
};

const STATUS_COLOR = (status = "") => {
  const s = status.toLowerCase();
  if (s.includes("out"))        return { bg: S.missBg,    color: "#ffdad6" };
  if (s.includes("doubtful"))   return { bg: "#5c2b00",   color: "#ffb786" };
  if (s.includes("question"))   return { bg: "#1a2f00",   color: "#b5e48c" };
  return                               { bg: "#242424",   color: S.redLight };
};

export default function InjuriesPage() {
  const { data: injuries, isLoading } = useQuery({ queryKey: ["injuries"], queryFn: getInjuries });
  const { getPlayerImage } = usePlayerImages();

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "800px" }}>
      <Helmet><title>Reds Injuries — RedsHub</title></Helmet>

      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "1.5rem" }}>
        Injury Report
      </h2>

      {isLoading && <p style={{ color: S.textMuted }}>Loading injury report…</p>}

      {!isLoading && injuries?.length === 0 && (
        <div style={{ background: S.surface, borderRadius: "0.75rem", padding: "2rem", border: `1px solid ${S.border}` }}>
          <p style={{ color: S.textMuted, fontSize: "0.9375rem" }}>✅ No injuries reported. Full squad available.</p>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {injuries?.map((inj, i) => {
          const sc = STATUS_COLOR(inj.status);
          return (
            <div key={i} style={{ background: S.surface, borderRadius: "0.75rem", padding: "1.25rem", border: `1px solid ${S.border}`, display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <img
                  src={getPlayerImage(inj.player_name)}
                  alt={inj.player_name}
                  style={{ width: 36, height: 36, borderRadius: "50%", objectFit: "cover", border: "2px solid #C6011F", flexShrink: 0 }}
                  onError={e => { e.target.src = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146"; }}
                />
                <div>
                  <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "1rem", color: S.text }}>{inj.player_name}</span>
                  <span style={{ fontSize: "0.75rem", color: S.textMuted }}>{inj.reason || "Not specified"}</span>
                </div>
              </div>
              <span style={{ background: sc.bg, color: sc.color, padding: "0.25rem 0.75rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.6875rem", textTransform: "uppercase", letterSpacing: "0.1em", borderRadius: "0.25rem", whiteSpace: "nowrap" }}>
                {inj.status || "GTD"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
