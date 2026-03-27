const ESPN_BASE = "https://a.espncdn.com/i/headshots/mlb/players/full/";
const FALLBACK = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146";

const PLAYER_IMAGES = {
  "Elly De La Cruz":   `${ESPN_BASE}4917694.png`,
  "TJ Friedl":         `${ESPN_BASE}36020.png`,
  "Spencer Steer":     `${ESPN_BASE}4722857.png`,
  "Tyler Stephenson":  `${ESPN_BASE}34975.png`,
  "Jonathan India":    `${ESPN_BASE}40552.png`,
  "Matt McLain":       `${ESPN_BASE}4422899.png`,
  "Noelvi Marte":      `${ESPN_BASE}41307.png`,
  "Ke'Bryan Hayes":    `${ESPN_BASE}35020.png`,
  "Jake Fraley":       `${ESPN_BASE}37234.png`,
  "Jeimer Candelario": `${ESPN_BASE}33222.png`,
  "Santiago Espinal":  `${ESPN_BASE}33823.png`,
  "Stuart Fairchild":  `${ESPN_BASE}39764.png`,
  "Will Benson":       `${ESPN_BASE}39216.png`,
  "Sal Stewart":       `${ESPN_BASE}5080771.png`,
  "Andrew Abbott":     `${ESPN_BASE}4414528.png`,
  "Hunter Greene":     `${ESPN_BASE}4233555.png`,
  "Nick Lodolo":       `${ESPN_BASE}4297152.png`,
  "Graham Ashcraft":   `${ESPN_BASE}4084179.png`,
  "Chase Burns":       `${ESPN_BASE}4927516.png`,
  "Dane Myers":        `${ESPN_BASE}40048.png`,
  "Jose Trevino":      `${ESPN_BASE}35268.png`,
  "Caleb Ferguson":    `${ESPN_BASE}33710.png`,
  "Josh Staumont":     `${ESPN_BASE}36176.png`,
  "Alex Young":        `${ESPN_BASE}36194.png`,
  "Joel Alberto Valdez": `${ESPN_BASE}4917959.png`,
};

export const getPlayerImage = (name) => {
  if (!name) return FALLBACK;
  if (PLAYER_IMAGES[name]) return PLAYER_IMAGES[name];
  // Fuzzy last-name match
  const lastName = name.split(" ").pop()?.toLowerCase();
  const match = Object.keys(PLAYER_IMAGES).find(
    k => k.split(" ").pop().toLowerCase() === lastName
  );
  return match ? PLAYER_IMAGES[match] : FALLBACK;
};

export default PLAYER_IMAGES;
