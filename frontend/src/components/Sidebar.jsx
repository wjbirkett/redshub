import { Link, useLocation } from "react-router-dom";

const NAV = [
  { to: "/",                    label: "Dashboard",     icon: "dashboard" },
  { to: "/predictions",         label: "Predictions",   icon: "analytics" },
  { to: "/props",               label: "Player Props",  icon: "sports_baseball" },
  { to: "/reds-betting-record", label: "Betting Record",icon: "receipt_long" },
  { to: "/betting",             label: "Betting",       icon: "trending_up" },
  { to: "/news",                label: "News Feed",     icon: "newspaper" },
  { to: "/injuries",            label: "Injuries",      icon: "medical_services" },
  { to: "/schedule",            label: "Schedule",      icon: "calendar_month" },
  { to: "/stats",               label: "Stats",         icon: "leaderboard" },
];

const MOBILE_NAV = [
  { to: "/",            icon: "dashboard",       label: "Home" },
  { to: "/predictions", icon: "analytics",       label: "Picks" },
  { to: "/props",       icon: "sports_baseball", label: "Props" },
  { to: "/betting",     icon: "trending_up",     label: "Bet" },
  { to: "/news",        icon: "newspaper",        label: "News" },
];

// Reds color palette
const C = {
  red:     "#C6011F",
  redLight:"#e8284a",
  cream:   "#f5e6d3",
  bg:      "#0f0f0f",
  surface: "rgba(26,26,26,0.9)",
  text:    "#f0ebe8",
  muted:   "#c9b8ae",
  border:  "rgba(255,255,255,0.08)",
};

export default function Sidebar() {
  const { pathname } = useLocation();
  const isActive = (to) => to === "/" ? pathname === "/" : pathname.startsWith(to);

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        style={{
          display: "none",
          position: "fixed",
          left: 0,
          top: 0,
          height: "100vh",
          width: "16rem",
          borderRight: `1px solid ${C.border}`,
          background: C.surface,
          backdropFilter: "blur(20px)",
          zIndex: 50,
          flexDirection: "column",
          boxShadow: "24px 0 48px rgba(0,0,0,0.5)",
          overflow: "hidden",
        }}
        className="lg-sidebar"
      >
        <style>{`
          @media (min-width: 1024px) {
            .lg-sidebar { display: flex !important; }
            .mobile-header { display: none !important; }
            .mobile-bottom-nav { display: none !important; }
          }
          .reds-nav-item { transition: background 0.15s, color 0.15s; }
          .reds-nav-item:hover {
            background: rgba(255,255,255,0.05) !important;
            color: ${C.redLight} !important;
            opacity: 1 !important;
          }
        `}</style>

        {/* Logo */}
        <div style={{ padding: "2rem" }}>
          <Link to="/" style={{ textDecoration: "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
              {/* Reds "C" wordmark block */}
              <div style={{
                width: "2rem", height: "2rem", borderRadius: "50%",
                background: C.red, display: "flex", alignItems: "center",
                justifyContent: "center", flexShrink: 0,
              }}>
                <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 900, fontSize: "1.1rem", color: "#fff", fontStyle: "italic" }}>C</span>
              </div>
              <h1 style={{
                fontFamily: "Space Grotesk, sans-serif",
                fontWeight: 900,
                fontSize: "1.5rem",
                color: C.red,
                letterSpacing: "-0.03em",
                fontStyle: "italic",
                textTransform: "uppercase",
                margin: 0,
              }}>RedsHub</h1>
            </div>
          </Link>
        </div>

        {/* Nav Links */}
        <nav style={{
          flex: 1,
          padding: "0 1rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.125rem",
          overflowY: "auto",
        }}>
          {NAV.map(({ to, label, icon }) => {
            const active = isActive(to);
            return (
              <Link
                key={to}
                to={to}
                className="reds-nav-item"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.75rem 1rem",
                  textDecoration: "none",
                  fontFamily: "Space Grotesk, sans-serif",
                  fontWeight: 700,
                  fontSize: "0.8125rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  color: active ? C.redLight : C.muted,
                  opacity: active ? 1 : 0.75,
                  borderLeft: active ? `2px solid ${C.red}` : "2px solid transparent",
                  background: active
                    ? `linear-gradient(to right, rgba(198,1,31,0.12), transparent)`
                    : "transparent",
                  borderRadius: "0 0.25rem 0.25rem 0",
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: "1.25rem" }}>{icon}</span>
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div style={{ padding: "1.5rem", marginTop: "auto" }}>
          <div style={{ textAlign: "center", marginBottom: "0.75rem" }}>
            <a
              href="https://websitesbywillie.com"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontFamily: "Space Grotesk, sans-serif",
                fontSize: "0.625rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.2)",
                textDecoration: "none",
              }}
            >
              Built by websitesbywillie.com
            </a>
          </div>
          <a
            href="https://www.draftkings.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "block",
              width: "100%",
              padding: "1rem",
              background: `linear-gradient(135deg, ${C.red}, ${C.redLight})`,
              color: "#fff",
              fontFamily: "Space Grotesk, sans-serif",
              fontWeight: 900,
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              fontSize: "0.8125rem",
              textAlign: "center",
              textDecoration: "none",
              borderRadius: "0.25rem",
              boxShadow: "0 4px 16px rgba(198,1,31,0.35)",
              fontStyle: "italic",
            }}
          >
            Place Bet
          </a>
        </div>
      </aside>

      {/* Mobile Header */}
      <header
        className="mobile-header"
        style={{
          position: "fixed",
          top: 0,
          width: "100%",
          zIndex: 50,
          height: "4rem",
          background: "rgba(15,15,15,0.9)",
          backdropFilter: "blur(16px)",
          borderBottom: `1px solid ${C.border}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0 1.5rem",
        }}
      >
        <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div style={{
            width: "1.75rem", height: "1.75rem", borderRadius: "50%",
            background: C.red, display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ fontFamily: "Space Grotesk", fontWeight: 900, fontSize: "1rem", color: "#fff", fontStyle: "italic" }}>C</span>
          </div>
          <h1 style={{
            fontFamily: "Space Grotesk, sans-serif",
            fontWeight: 900,
            fontSize: "1.25rem",
            color: C.red,
            fontStyle: "italic",
            textTransform: "uppercase",
            margin: 0,
          }}>RedsHub</h1>
        </Link>
        <span className="material-symbols-outlined" style={{ color: C.redLight, fontSize: "1.5rem" }}>menu</span>
      </header>

      {/* Mobile Bottom Nav */}
      <nav
        className="mobile-bottom-nav"
        style={{
          position: "fixed",
          bottom: 0,
          width: "100%",
          zIndex: 50,
          height: "4rem",
          background: "rgba(15,15,15,0.9)",
          backdropFilter: "blur(16px)",
          borderTop: `1px solid ${C.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-around",
          padding: "0 0.5rem",
        }}
      >
        {MOBILE_NAV.map(({ to, icon, label }) => {
          const active = isActive(to);
          return (
            <Link
              key={to}
              to={to}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "0.125rem",
                color: active ? C.redLight : C.muted,
                opacity: active ? 1 : 0.5,
                textDecoration: "none",
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: "1.25rem" }}>{icon}</span>
              <span style={{
                fontSize: "0.5rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                fontFamily: "Space Grotesk, sans-serif",
              }}>{label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
