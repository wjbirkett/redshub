import { useQuery } from "@tanstack/react-query";
import { getRoster } from "./api";

const ESPN_BASE = "https://a.espncdn.com/i/headshots/mlb/players/full/";
const FALLBACK = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146";

// Static fallback map — used immediately while roster API loads
const STATIC_MAP = {
  "Elly De La Cruz":  `${ESPN_BASE}4917694.png`,
  "TJ Friedl":        `${ESPN_BASE}36020.png`,
  "Spencer Steer":    `${ESPN_BASE}4722857.png`,
  "Tyler Stephenson": `${ESPN_BASE}34975.png`,
  "Jonathan India":   `${ESPN_BASE}40552.png`,
  "Matt McLain":      `${ESPN_BASE}4422899.png`,
  "Noelvi Marte":     `${ESPN_BASE}41307.png`,
  "Ke'Bryan Hayes":   `${ESPN_BASE}35020.png`,
  "Jake Fraley":      `${ESPN_BASE}37234.png`,
  "Jeimer Candelario":`${ESPN_BASE}33222.png`,
  "Santiago Espinal": `${ESPN_BASE}33823.png`,
  "Stuart Fairchild": `${ESPN_BASE}39764.png`,
  "Will Benson":      `${ESPN_BASE}39216.png`,
  "Sal Stewart":      `${ESPN_BASE}5080771.png`,
  "Andrew Abbott":    `${ESPN_BASE}4414528.png`,
  "Hunter Greene":    `${ESPN_BASE}4233555.png`,
  "Nick Lodolo":      `${ESPN_BASE}4297152.png`,
  "Graham Ashcraft":  `${ESPN_BASE}4084179.png`,
  "Chase Burns":      `${ESPN_BASE}4927516.png`,
  "Dane Myers":       `${ESPN_BASE}40048.png`,
  "Jose Trevino":     `${ESPN_BASE}35268.png`,
};

/**
 * Hook that fetches the full roster once and returns a getPlayerImage function.
 * Falls back to static map while API loads or if it fails.
 */
export function usePlayerImages() {
  const { data } = useQuery({
    queryKey: ["roster"],
    queryFn: getRoster,
    staleTime: 1000 * 60 * 30,
  });

  const players = (data?.groups ?? []).flatMap(g => g.players ?? []);

  const getPlayerImage = (name) => {
    if (!name) return FALLBACK;
    const lower = name.toLowerCase();

    // Dynamic roster lookup
    if (players.length > 0) {
      const exact = players.find(p => p.name?.toLowerCase() === lower);
      if (exact?.headshot) return exact.headshot;
      const lastName = lower.split(" ").pop();
      const fuzzy = players.find(p => p.name?.toLowerCase().split(" ").pop() === lastName);
      if (fuzzy?.headshot) return fuzzy.headshot;
    }

    // Static fallback
    if (STATIC_MAP[name]) return STATIC_MAP[name];

    // Last-name fuzzy on static map
    const lastName = name.split(" ").pop()?.toLowerCase();
    const staticMatch = Object.keys(STATIC_MAP).find(
      k => k.split(" ").pop().toLowerCase() === lastName
    );
    if (staticMatch) return STATIC_MAP[staticMatch];

    return FALLBACK;
  };

  return { getPlayerImage, roster: players };
}

// Backwards-compatible static export
export const getPlayerImage = (name) => STATIC_MAP[name] || FALLBACK;

export default STATIC_MAP;
