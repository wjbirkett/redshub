import { useQuery } from "@tanstack/react-query";
import { getRoster } from "./api";

const FALLBACK = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146";

/**
 * Hook that fetches the full roster once and returns a getPlayerImage function.
 * Usage: const { getPlayerImage, roster } = usePlayerImages();
 */
export function usePlayerImages() {
  const { data } = useQuery({
    queryKey: ["roster"],
    queryFn: getRoster,
    staleTime: 1000 * 60 * 30, // cache 30 min
  });

  const players = (data?.groups ?? []).flatMap(g => g.players ?? []);

  const getPlayerImage = (name) => {
    if (!name) return FALLBACK;
    const lower = name.toLowerCase();
    const match = players.find(p => p.name?.toLowerCase() === lower);
    if (match?.headshot) return match.headshot;
    // Fuzzy: match by last name
    const lastName = lower.split(" ").pop();
    const fuzzy = players.find(p => p.name?.toLowerCase().split(" ").pop() === lastName);
    if (fuzzy?.headshot) return fuzzy.headshot;
    return FALLBACK;
  };

  return { getPlayerImage, roster: players };
}

// Backwards-compatible static export for any remaining non-component usage
export const getPlayerImage = () => FALLBACK;

export default {};
