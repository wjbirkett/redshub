import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { getNews } from "../utils/api";

const S = {
  bg: "#0f0f0f", surface: "#1a1a1a", surfaceHigh: "#242424",
  border: "rgba(255,255,255,0.08)", red: "#C6011F", redLight: "#e8284a",
  text: "#f0ebe8", textMuted: "#c9b8ae",
};

const SOURCES = [
  { id: undefined,   label: "All" },
  { id: "espn",      label: "ESPN" },
  { id: "bleacher",  label: "Bleacher Report" },
  { id: "cbs",       label: "CBS Sports" },
];

export default function NewsPage() {
  const [source, setSource] = window.React?.useState
    ? window.React.useState(undefined)
    : [undefined, () => {}];

  const { data: news, isLoading } = useQuery({
    queryKey: ["news", source],
    queryFn: () => getNews(source),
  });

  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "960px" }}>
      <Helmet>
        <title>Reds News — RedsHub</title>
      </Helmet>

      <h2 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.75rem", textTransform: "uppercase", fontStyle: "italic", color: S.text, marginBottom: "1.5rem" }}>
        Reds News Feed
      </h2>

      {/* Source Filter */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        {SOURCES.map(({ id, label }) => (
          <button
            key={label}
            onClick={() => setSource(id)}
            style={{
              padding: "0.375rem 0.875rem",
              borderRadius: "999px",
              border: `1px solid ${source === id ? S.red : S.border}`,
              background: source === id ? S.red : "transparent",
              color: source === id ? "#fff" : S.textMuted,
              fontFamily: "Space Grotesk, sans-serif",
              fontWeight: 700,
              fontSize: "0.75rem",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {isLoading && <p style={{ color: S.textMuted }}>Loading news…</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        {news?.map((item, i) => (
          <a
            key={i}
            href={item.url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            style={{ textDecoration: "none", display: "block", padding: "1rem", borderRadius: "0.5rem", border: `1px solid transparent`, transition: "all 0.15s" }}
            onMouseEnter={e => { e.currentTarget.style.background = S.surfaceHigh; e.currentTarget.style.borderColor = S.border; }}
            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "transparent"; }}
          >
            <span style={{ fontSize: "0.5625rem", fontWeight: 900, color: S.red, letterSpacing: "0.15em", textTransform: "uppercase", display: "block", marginBottom: "0.25rem" }}>
              {item.source || "ESPN"}
              {item.published_at && (
                <span style={{ color: S.textMuted, fontWeight: 400, marginLeft: "0.5rem" }}>
                  · {new Date(item.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                </span>
              )}
            </span>
            <h4 style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: "1rem", lineHeight: 1.35, color: S.text, marginBottom: "0.25rem" }}>
              {item.title}
            </h4>
            {item.summary && (
              <p style={{ fontSize: "0.8125rem", color: S.textMuted, lineHeight: 1.5 }}>{item.summary}</p>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
