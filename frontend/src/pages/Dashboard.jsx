import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { getNews, getInjuries, getBirthdays, getSchedule, getStandings, getArticles, getResults } from "../utils/api";
import { getPlayerImage } from "../utils/playerImages";
import AdBanner from "../components/AdBanner";

// Reds design tokens
const S = {
  bg:           "#0f0f0f",
  surface:      "#1a1a1a",
  surfaceHigh:  "#242424",
  surfaceHighest:"#2e2e2e",
  border:       "rgba(255,255,255,0.08)",
  red:          "#C6011F",
  redLight:     "#e8284a",
  cream:        "#f5e6d3",
  gold:         "#d4a843",
  blue:         "#a0caff",
  green:        "#4ae176",
  greenBg:      "#06bb55",
  hitGreen:     "#00431a",
  missRed:      "#ffb4ab",
  missBg:       "#93000a",
  text:         "#f0ebe8",
  textMuted:    "#c9b8ae",
  textDim:      "rgba(201,184,174,0.5)",
};

const badge = (type) => {
  const map = {
    prediction: ["#00508a", "#dbe9ff"],
    best_bet:   ["#06bb55", "#00431a"],
    prop:       ["#93000a", "#ffdad6"],
    history:    ["#4a1d96", "#d8b4fe"],
    postgame:   ["#1a1a1a", "#c9b8ae"],
  };
  const labels = {
    prediction: "PREDICTION",
    best_bet:   "BEST BET",
    prop:       "PROP BET",
    history:    "HISTORY",
    postgame:   "POSTGAME",
  };
  return {
    bg:    map[type]?.[0] ?? "#333",
    color: map[type]?.[1] ?? "#fff",
    label: labels[type] ?? type.toUpperCase(),
  };
};

export default function Dashboard() {
  const { data: news }      = useQuery({ queryKey: ["news"],      queryFn: () => getNews(undefined) });
  const { data: injuries }  = useQuery({ queryKey: ["injuries"],  queryFn: getInjuries });
  const { data: birthdays } = useQuery({ queryKey: ["birthdays"], queryFn: getBirthdays });
  const { data: schedule }  = useQuery({ queryKey: ["schedule"],  queryFn: getSchedule });
  const { data: standings } = useQuery({ queryKey: ["standings"], queryFn: getStandings });
  const { data: articles }  = useQuery({ queryKey: ["articles"],  queryFn: () => getArticles(20) });
  const { data: resultsData}= useQuery({ queryKey: ["results"],   queryFn: getResults });

  const reds = standings?.find((t) =>
    (t.team_name || t.team || t.teamName || "").includes("Reds")
  );

  // Show postgame as hero if game is over, otherwise best bet/prediction
  const todayBestBet      = articles?.find((a) => a.article_type === "postgame")
    || articles?.find((a) => a.article_type === "best_bet")
    || articles?.find((a) => a.article_type === "prediction");
  const latestPredictions = articles?.filter((a) =>
    ["prediction", "best_bet", "prop", "postgame", "lean_prop"].includes(a.article_type)
  ).slice(0, 3);

  const nextGame = schedule?.find((g) => !g.home_score && g.status !== "Final");
  const lastGame = schedule?.filter((g) => g.status === "Final" || g.home_score).slice(-1)[0];
  const redsInj  = injuries?.slice(0, 4) ?? [];
  const bdays    = birthdays?.slice(0, 2) ?? [];

  const preds    = resultsData?.predictions ?? [];
  const propRes  = resultsData?.props ?? [];
  const atsHits  = preds.filter((r) => r.spread_result === "HIT").length;
  const atsTotal = preds.filter((r) => r.spread_result).length;
  const ouHits   = preds.filter((r) => r.total_result === "HIT").length;
  const ouTotal  = preds.filter((r) => r.total_result).length;
  const mlHits   = preds.filter((r) => r.moneyline_result === "HIT").length;
  const mlTotal  = preds.filter((r) => r.moneyline_result).length;
  const propHits = propRes.filter((r) => r.result === "HIT").length;

  const winPayout = 100 / 110;
  const atsProfit = atsHits * winPayout - (atsTotal - atsHits);
  const ouProfit = ouHits * winPayout - (ouTotal - ouHits);
  const propProfit = propHits * winPayout - (propRes.length - propHits);
  const totalUnits = +(atsProfit + ouProfit + propProfit).toFixed(1);

  const opp = (a) => {
    if (!a) return "TBD";
    return a.home_team?.includes("Reds") ? a.away_team : a.home_team;
  };
  const fmt = (d) =>
    new Date(d + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });

  return (
    <div className="main-content">
      <Helmet>
        <title>RedsHub — Reds Predictions, Best Bets & Player Props</title>
        <meta name="description" content="AI-powered Cincinnati Reds betting predictions, best bets, run line picks, and player props." />
        <link rel="canonical" href="https://redshub.vercel.app" />
      </Helmet>

      <h1 style={{ position: "absolute", width: "1px", height: "1px", padding: 0, margin: "-1px", overflow: "hidden", clip: "rect(0,0,0,0)", whiteSpace: "nowrap", border: 0 }}>
        RedsHub — Cincinnati Reds Predictions, Best Bets &amp; Player Props
      </h1>

      {/* Team Record Bar */}
      <div style={{
        background: S.surface,
        borderBottom: `1px solid ${S.border}`,
        padding: "0.75rem 2rem",
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "1rem",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {/* Reds "C" logo mark */}
          <div style={{
            width: "2.5rem", height: "2.5rem", borderRadius: "50%",
            background: S.red, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <span style={{ fontFamily: "Space Grotesk", fontWeight: 900, fontSize: "1.4rem", color: "#fff", fontStyle: "italic" }}>C</span>
          </div>
          <div>
            <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.1rem", letterSpacing: "-0.02em", textTransform: "uppercase", color: S.text }}>CINCINNATI REDS</span>
            <span style={{ fontSize: "0.625rem", color: S.textMuted, fontWeight: 700, letterSpacing: "0.2em", textTransform: "uppercase" }}>NL Central</span>
          </div>
        </div>

        <div style={{ display: "flex", gap: "2.5rem", alignItems: "center" }}>
          {reds && <>
            <div style={{ textAlign: "center" }}>
              <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.4rem" }}>{reds.wins}-{reds.losses}</span>
              <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>W-L RECORD</span>
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.4rem", color: S.redLight }}>#{reds.conference_rank || reds.conferenceRank || "—"}</span>
              <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>DIV RANK</span>
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.4rem", color: S.green }}>
                {reds.win_pct ? (reds.win_pct * 100).toFixed(1) + "%" : "—"}
              </span>
              <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>WIN %</span>
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.4rem", color: S.textMuted }}>
                {reds.games_back === 0 ? "—" : reds.games_back ?? "—"}
              </span>
              <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>GB</span>
            </div>
          </>}
          {(atsTotal > 0 || ouTotal > 0 || propRes.length > 0) && (
            <div style={{ textAlign: "center" }}>
              <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.4rem", color: totalUnits >= 0 ? S.green : S.missRed }}>
                {totalUnits >= 0 ? "+" : ""}{totalUnits}u
              </span>
              <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>UNITS</span>
            </div>
          )}
          {atsTotal > 0 && (
            <div style={{ textAlign: "center" }}>
              <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.4rem", color: atsHits / atsTotal >= 0.5 ? S.green : S.missRed }}>
                {atsHits}-{atsTotal - atsHits}
              </span>
              <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>RL</span>
            </div>
          )}
          {ouTotal > 0 && (
            <div style={{ textAlign: "center" }}>
              <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.4rem", color: ouHits / ouTotal >= 0.5 ? S.green : S.missRed }}>
                {ouHits}-{ouTotal - ouHits}
              </span>
              <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>O/U</span>
            </div>
          )}
          {mlTotal > 0 && (
            <div style={{ textAlign: "center" }}>
              <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.4rem", color: mlHits / mlTotal >= 0.5 ? S.green : S.missRed }}>
                {mlHits}-{mlTotal - mlHits}
              </span>
              <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>ML</span>
            </div>
          )}
          {propRes.length > 0 && (
            <div style={{ textAlign: "center" }}>
              <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.4rem", color: propHits / propRes.length >= 0.5 ? S.green : S.missRed }}>
                {propHits}-{propRes.length - propHits}
              </span>
              <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>PROPS</span>
            </div>
          )}
        </div>
      </div>

      <AdBanner style={{ margin: "0.75rem 2rem" }} />

      {/* Main Dashboard Grid */}
      <div style={{
        padding: "1.5rem 2rem 2rem",
        display: "grid",
        gridTemplateColumns: "1fr minmax(0, 320px)",
        gap: "0 1.5rem",
        maxWidth: "1400px",
        margin: "0 auto",
        alignItems: "start",
      }}>

        {/* AI Best Bet Hero */}
        {todayBestBet ? (
          <Link to={`/predictions/${todayBestBet.slug}`} style={{ textDecoration: "none" }}>
            <div style={{
              position: "relative",
              overflow: "hidden",
              background: `linear-gradient(135deg, ${S.surfaceHigh} 0%, #1f0308 100%)`,
              borderRadius: "0.75rem",
              padding: "1.25rem",
              borderLeft: `4px solid ${S.red}`,
              boxShadow: `0 25px 50px rgba(0,0,0,0.5), 0 0 80px rgba(198,1,31,0.08)`,
              minHeight: "0",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
            }}>
              <span style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                background: S.red,
                color: "#fff",
                padding: "0.25rem 0.75rem",
                fontSize: "0.6875rem",
                fontWeight: 900,
                letterSpacing: "0.15em",
                textTransform: "uppercase",
                borderRadius: "0.25rem",
                marginBottom: "1.25rem",
                fontFamily: "Space Grotesk, sans-serif",
                fontStyle: "italic",
                width: "fit-content",
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: "0.875rem" }}>auto_awesome</span>
                AI Recommended Best Bet
              </span>

              {todayBestBet.key_picks?.spread_pick ? (
                <h2 style={{
                  fontFamily: "Space Grotesk, sans-serif",
                  fontWeight: 900,
                  fontSize: "clamp(2rem, 4vw, 4rem)",
                  letterSpacing: "-0.04em",
                  lineHeight: 0.9,
                  marginBottom: "1rem",
                  color: S.text,
                  textTransform: "uppercase",
                }}>
                  {todayBestBet.key_picks.spread_lean === "COVER" ? "REDS" : opp(todayBestBet).split(" ").pop()}<br />
                  <span style={{ color: S.red }}>
                    {todayBestBet.key_picks.spread_pick.replace(/Redss*/i, "").replace(/.*?s/, "")}
                  </span> RUN LINE
                </h2>
              ) : (
                <h2 style={{
                  fontFamily: "Space Grotesk, sans-serif",
                  fontWeight: 900,
                  fontSize: "clamp(1.25rem, 2.5vw, 2rem)",
                  letterSpacing: "-0.02em",
                  lineHeight: 1.15,
                  marginBottom: "1rem",
                  color: S.text,
                }}>
                  {todayBestBet.title}
                </h2>
              )}

              {todayBestBet.key_picks && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
                  {todayBestBet.key_picks.spread_pick && (
                    <span style={{ background: S.surfaceHighest, padding: "0.375rem 0.75rem", borderRadius: "0.25rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.8125rem" }}>
                      {todayBestBet.key_picks.spread_pick}
                      <span style={{ marginLeft: "0.5rem", color: todayBestBet.key_picks.spread_lean === "COVER" ? S.green : S.missRed, fontSize: "0.6875rem" }}>
                        {todayBestBet.key_picks.spread_lean}
                      </span>
                    </span>
                  )}
                  {todayBestBet.key_picks.total_pick && (
                    <span style={{ background: S.surfaceHighest, padding: "0.375rem 0.75rem", borderRadius: "0.25rem", fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.8125rem" }}>
                      {todayBestBet.key_picks.total_pick}
                      <span style={{ marginLeft: "0.5rem", color: todayBestBet.key_picks.total_lean === "OVER" ? S.green : S.missRed, fontSize: "0.6875rem" }}>
                        {todayBestBet.key_picks.total_lean}
                      </span>
                    </span>
                  )}
                  {todayBestBet.key_picks.confidence && (
                    <span style={{
                      background: todayBestBet.key_picks.confidence === "High" ? S.greenBg : S.surfaceHighest,
                      color: todayBestBet.key_picks.confidence === "High" ? S.hitGreen : S.textMuted,
                      padding: "0.375rem 0.75rem",
                      borderRadius: "0.25rem",
                      fontFamily: "Space Grotesk, sans-serif",
                      fontWeight: 900,
                      fontSize: "0.6875rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.1em",
                    }}>
                      {todayBestBet.key_picks.confidence} Confidence
                    </span>
                  )}
                </div>
              )}

              <p style={{ color: S.textMuted, fontSize: "0.8125rem" }}>
                vs {opp(todayBestBet)} · {fmt(todayBestBet.game_date)} · Read full analysis →
              </p>
            </div>
          </Link>
        ) : (
          <div style={{
            background: S.surfaceHigh,
            borderRadius: "0.75rem",
            padding: "2rem",
            borderLeft: `4px solid rgba(198,1,31,0.3)`,
            minHeight: "280px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}>
            <span style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              background: "rgba(198,1,31,0.15)",
              color: S.redLight,
              padding: "0.25rem 0.75rem",
              fontSize: "0.6875rem",
              fontWeight: 900,
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              borderRadius: "0.25rem",
              marginBottom: "1.25rem",
              fontFamily: "Space Grotesk, sans-serif",
              fontStyle: "italic",
              width: "fit-content",
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: "0.875rem" }}>schedule</span>
              AI Picks Drop ~45 Min Before First Pitch
            </span>
            <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "clamp(1.75rem, 3vw, 3rem)", letterSpacing: "-0.03em", lineHeight: 1, marginBottom: "0.75rem", color: S.text }}>
              {nextGame ? `Next: vs ${opp(nextGame)}` : "No Upcoming Game"}
            </h2>
            <p style={{ color: S.textMuted, fontSize: "0.875rem", marginBottom: "1.5rem" }}>
              Best bet, prediction, and player props auto-generate before first pitch.
            </p>
            {atsTotal > 0 && (
              <div style={{ display: "flex", gap: "2rem" }}>
                {[["RL", atsHits, atsTotal], ["O/U", ouHits, ouTotal], ["ML", mlHits, mlTotal], ["PROPS", propHits, propRes.length]]
                  .filter(([, , t]) => t > 0)
                  .map(([label, h, t]) => (
                    <div key={label}>
                      <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", color: h / t >= 0.5 ? S.green : S.missRed }}>
                        {h}-{t - h}
                      </span>
                      <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>{label}</span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* Right Column: Next + Last Game */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem", alignSelf: "start", gridColumn: "2", gridRow: "1" }}>
          {nextGame && (
            <div style={{ background: S.surfaceHigh, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <span style={{ fontSize: "0.5625rem", fontWeight: 900, letterSpacing: "0.2rem", color: S.red, textTransform: "uppercase" }}>Next Game</span>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ textAlign: "center" }}>
                  <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem" }}>CIN</span>
                </div>
                <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.25rem", color: S.textDim, fontStyle: "italic" }}>VS</span>
                <div style={{ textAlign: "center" }}>
                  <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem" }}>
                    {opp(nextGame)?.split(" ").pop()}
                  </span>
                </div>
              </div>
              <p style={{ fontSize: "0.6875rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.15em" }}>
                {new Date(nextGame.game_date + "T12:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
              </p>
            </div>
          )}

          {lastGame && (
            <div style={{ background: S.surfaceHigh, borderRadius: "0.75rem", padding: "1.25rem", borderLeft: `4px solid ${S.green}`, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <span style={{ fontSize: "0.5625rem", fontWeight: 900, letterSpacing: "0.2rem", color: S.green, textTransform: "uppercase" }}>Last Result</span>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.5rem" }}>
                    {lastGame.home_team?.includes("Reds") ? lastGame.home_score : lastGame.away_score}
                    {" - "}
                    {lastGame.home_team?.includes("Reds") ? lastGame.away_score : lastGame.home_score}
                  </span>
                  <span style={{ fontSize: "0.5625rem", fontWeight: 700, color: S.textMuted, textTransform: "uppercase" }}>
                    vs {opp(lastGame)}
                  </span>
                </div>
                <span style={{
                  background: S.green, color: "#003915",
                  padding: "0.25rem 0.625rem",
                  fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.125rem",
                  borderRadius: "0.25rem", textTransform: "uppercase", fontStyle: "italic",
                }}>
                  {lastGame.result || "W"}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Left: Predictions + News */}
        <div style={{ display: "flex", flexDirection: "column", gap: "2.5rem", gridColumn: "1", gridRow: "2" }}>

          {/* Latest Predictions */}
          <section>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem" }}>
              <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.375rem", textTransform: "uppercase", fontStyle: "italic", letterSpacing: "-0.01em", color: S.text }}>
                Latest Predictions
              </h3>
              <Link to="/predictions" style={{ fontSize: "0.6875rem", fontWeight: 700, color: S.red, letterSpacing: "0.15em", textTransform: "uppercase", textDecoration: "none" }}>
                See All
              </Link>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
              {latestPredictions?.map((a) => {
                const b = badge(a.article_type);
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
                      <h4 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.9375rem", lineHeight: 1.3, color: S.text, flex: 1 }}>
                        {a.title.replace(/\s*(\d+-\d+)\s*$/, "").replace(/AI Prediction,?\s*/i, "").replace(/Best Bets & Player Props/i, "").trim()}
                      </h4>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.625rem", fontWeight: 900, textTransform: "uppercase", color: S.red }}>
                        <span>{fmt(a.game_date)}</span>
                        {a.key_picks?.confidence && (
                          <span style={{ color: a.key_picks.confidence === "High" ? S.green : S.textMuted }}>
                            {a.key_picks.confidence} Conf
                          </span>
                        )}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>

          <AdBanner style={{ margin: "0.5rem 0" }} />

          {/* News Feed */}
          <section>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem" }}>
              <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.375rem", textTransform: "uppercase", fontStyle: "italic", letterSpacing: "-0.01em", color: S.text }}>
                Editorial News Feed
              </h3>
              <Link to="/news" style={{ fontSize: "0.6875rem", fontWeight: 700, color: S.red, letterSpacing: "0.15em", textTransform: "uppercase", textDecoration: "none" }}>
                See All
              </Link>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              {news?.slice(0, 8).map((item, i) => (
                <a
                  key={i}
                  href={item.url || item.link || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ textDecoration: "none", display: "flex", gap: "1rem", padding: "0.75rem", borderRadius: "0.5rem", transition: "background 0.15s" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                >
                  <div style={{ flex: 1 }}>
                    <span style={{ fontSize: "0.5625rem", fontWeight: 900, color: S.red, letterSpacing: "0.15em", textTransform: "uppercase", display: "block", marginBottom: "0.25rem" }}>
                      {item.source || "ESPN"}
                    </span>
                    <h4 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "0.9375rem", lineHeight: 1.3, color: S.text }}>
                      {item.title}
                    </h4>
                  </div>
                </a>
              ))}
            </div>
          </section>
        </div>

        {/* Bottom Right: Injuries + Birthdays + AI Record */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", gridColumn: "2", gridRow: "2" }}>

          {/* Injury Report */}
          <section style={{ background: S.surface, padding: "1.5rem", borderRadius: "0.75rem", border: `1px solid ${S.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.25rem" }}>
              <span className="material-symbols-outlined" style={{ color: S.redLight, fontSize: "1.25rem" }}>medical_services</span>
              <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.0625rem", textTransform: "uppercase", fontStyle: "italic", color: S.text }}>Injury Report</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {redsInj.length > 0 ? redsInj.map((inj, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                    <img
                      src={getPlayerImage(inj.player_name || inj.name)}
                      alt={inj.player_name || inj.name}
                      style={{ width: 36, height: 36, borderRadius: "50%", objectFit: "cover", border: "2px solid #C6011F", flexShrink: 0 }}
                      onError={e => { e.target.src = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146"; }}
                    />
                    <div>
                      <span style={{ display: "block", fontWeight: 700, fontSize: "0.875rem", color: S.text }}>{inj.player_name || inj.name}</span>
                      <span style={{ fontSize: "0.625rem", color: S.textMuted, textTransform: "uppercase" }}>{inj.reason || inj.injury}</span>
                    </div>
                  </div>
                  <span style={{
                    background: (inj.status || "").toLowerCase().includes("out") ? S.missBg : S.surfaceHighest,
                    color: (inj.status || "").toLowerCase().includes("out") ? "#ffdad6" : S.red,
                    padding: "0.1875rem 0.5rem",
                    fontSize: "0.5625rem",
                    fontWeight: 900,
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    borderRadius: "0.25rem",
                  }}>{inj.status || "GTD"}</span>
                </div>
              )) : <p style={{ fontSize: "0.8125rem", color: S.textMuted }}>No injuries reported.</p>}
            </div>
            <Link to="/injuries" style={{ display: "block", marginTop: "1rem", fontSize: "0.625rem", fontWeight: 700, color: S.red, textTransform: "uppercase", letterSpacing: "0.15em", textDecoration: "none" }}>
              Full Report →
            </Link>
          </section>

          {/* Birthdays */}
          {bdays.length > 0 && (
            <section style={{ background: S.surface, padding: "1.5rem", borderRadius: "0.75rem", border: `1px solid ${S.border}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.25rem" }}>
                <span className="material-symbols-outlined" style={{ color: S.red, fontSize: "1.25rem" }}>cake</span>
                <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.0625rem", textTransform: "uppercase", fontStyle: "italic", color: S.text }}>Birthdays</h3>
              </div>
              {bdays.map((b, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.75rem", opacity: i > 0 ? 0.5 : 1, paddingTop: i > 0 ? "0.75rem" : 0, borderTop: i > 0 ? `1px solid ${S.border}` : "none", marginTop: i > 0 ? "0.75rem" : 0 }}>
                  <img
                    src={getPlayerImage(b.player_name)}
                    alt={b.player_name}
                    style={{ width: 36, height: 36, borderRadius: "50%", objectFit: "cover", border: "2px solid #C6011F", flexShrink: 0 }}
                    onError={e => { e.target.src = "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=200&h=146"; }}
                  />
                  <div>
                    <span style={{ display: "block", fontWeight: 700, fontSize: "0.875rem", color: S.text }}>{b.player_name}</span>
                    <span style={{ fontSize: "0.625rem", color: S.red, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.15em" }}>
                      {i === 0 ? "Today" : "Upcoming"} · {b.birth_date}
                    </span>
                  </div>
                </div>
              ))}
            </section>
          )}

          {/* AI Season Record */}
          {atsTotal > 0 && (
            <div style={{ background: `linear-gradient(135deg, ${S.surface}, ${S.bg})`, padding: "1.5rem", borderRadius: "0.75rem", borderLeft: `4px solid ${S.red}` }}>
              <h3 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "0.8125rem", textTransform: "uppercase", letterSpacing: "0.15em", color: S.text, marginBottom: "1rem" }}>
                AI Season Record
              </h3>
              <div style={{ display: "flex", gap: "1.5rem" }}>
                {[[atsHits, atsTotal - atsHits, "RL"], [ouHits, ouTotal - ouHits, "O/U"], [mlHits, mlTotal - mlHits, "ML"], [propHits, propRes.length - propHits, "PROPS"]]
                  .filter(([, , l]) => l === "PROPS" ? propRes.length > 0 : (l === "ML" ? mlTotal > 0 : (l === "O/U" ? ouTotal > 0 : atsTotal > 0)))
                  .map(([h, m, l]) => (
                    <div key={l}>
                      <span style={{ display: "block", fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.5rem", color: h / (h + m) >= 0.5 ? S.green : S.missRed }}>
                        {h}-{m}
                      </span>
                      <span style={{ fontSize: "0.5625rem", color: S.textMuted, fontWeight: 700, textTransform: "uppercase" }}>{l}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer style={{ background: S.bg, borderTop: `1px solid ${S.border}`, padding: "2.5rem 2rem", marginTop: "1rem" }}>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "1rem", maxWidth: "1400px" }}>
          <p style={{ fontSize: "0.625rem", fontFamily: "Inter, sans-serif", textTransform: "uppercase", letterSpacing: "0.05em", color: S.textMuted, opacity: 0.6 }}>
            © 2026 RedsHub. Responsible Gaming Only. Built by{" "}
            <a href="https://websitesbywillie.com" target="_blank" rel="noopener noreferrer" style={{ color: S.textMuted, opacity: 0.5, textDecoration: "none" }}>
              websitesbywillie.com
            </a>
          </p>
          <div style={{ display: "flex", gap: "1.5rem" }}>
            {[["About", "/about"], ["Privacy", "/privacy"], ["Terms", "/terms"]].map(([label, to]) => (
              <Link key={to} to={to} style={{ fontSize: "0.625rem", fontFamily: "Inter, sans-serif", textTransform: "uppercase", letterSpacing: "0.05em", color: S.textMuted, opacity: 0.5, textDecoration: "none" }}>
                {label}
              </Link>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
