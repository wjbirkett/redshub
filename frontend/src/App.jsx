import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import NewsPage from "./pages/NewsPage";
import InjuriesPage from "./pages/InjuriesPage";
import BettingPage from "./pages/BettingPage";
import SchedulePage from "./pages/SchedulePage";
import StatsPage from "./pages/StatsPage";
import BettingRecordPage from "./pages/BettingRecordPage";
import PredictionsPage from "./pages/PredictionsPage";
import ArticlePage from "./pages/ArticlePage";
import GameHubPage from "./pages/GameHubPage";
import MatchupArchivePage from "./pages/MatchupArchivePage";
import PlayerPropsPage from "./pages/PlayerPropsPage";
import PlayerArchivePage from "./pages/PlayerArchivePage";
import OddsPage from "./pages/OddsPage";
import RosterPage from "./pages/RosterPage";
import AboutPage from "./pages/AboutPage";
import TermsPage from "./pages/TermsPage";
import PrivacyPage from "./pages/PrivacyPage";

export default function App() {
  return (
    <HelmetProvider>
      <BrowserRouter>
        <style>{`
          .reds-main {
            margin-left: 16rem;
            padding: 0 1.5rem 0;
            padding-bottom: 0;
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
          }
          .reds-content {
            flex: 1;
          }
          @media (max-width: 1023px) {
            .reds-main {
              margin-left: 0;
              padding: 1rem;
              padding-top: 4rem;
              padding-bottom: 4rem;
            }
          }
        `}</style>
        <div
          className="flex min-h-screen bg-reds-dark text-white"
          style={{ fontFamily: "Inter, sans-serif", background: "#0f0f0f" }}
        >
          <Sidebar />
          <main className="reds-main">
            <div className="reds-content">
              <Routes>
                <Route path="/"                        element={<Dashboard />} />
                <Route path="/news"                    element={<NewsPage />} />
                <Route path="/injuries"                element={<InjuriesPage />} />
                <Route path="/betting"                 element={<BettingPage />} />
                <Route path="/schedule"                element={<SchedulePage />} />
                <Route path="/stats"                   element={<StatsPage />} />
                <Route path="/reds-betting-record"     element={<BettingRecordPage />} />
                <Route path="/predictions"             element={<PredictionsPage />} />
                <Route path="/predictions/:slug"       element={<ArticlePage />} />
                <Route path="/game/:gameSlug"          element={<GameHubPage />} />
                <Route path="/matchup/:opponent"       element={<MatchupArchivePage />} />
                <Route path="/props"                   element={<PlayerPropsPage />} />
                <Route path="/props/:player"           element={<PlayerArchivePage />} />
                <Route path="/roster"                  element={<RosterPage />} />
                <Route path="/odds"                    element={<OddsPage />} />
                <Route path="/about"                   element={<AboutPage />} />
                <Route path="/terms"                   element={<TermsPage />} />
                <Route path="/privacy"                 element={<PrivacyPage />} />
              </Routes>
            </div>

            {/* Book Promo */}
            <a
              href="https://www.amazon.com/dp/B0GTC3T8X6"
              target="_blank"
              rel="noopener noreferrer"
              style={{ textDecoration: "none", display: "block", margin: "2rem 0 0" }}
            >
              <div style={{ background: "#161b22", border: "1px solid #C6011F", borderRadius: "0.5rem", padding: "0.75rem 1.25rem", display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap", cursor: "pointer" }}>
                <span style={{ fontSize: "1.25rem" }}>📖</span>
                <div style={{ flex: 1, minWidth: "200px" }}>
                  <span style={{ color: "#C6011F", fontWeight: 700, fontSize: "0.85rem", letterSpacing: "0.05em" }}>AI SPORTS BETTING</span>
                  <span style={{ color: "#9ca3af", fontSize: "0.75rem", marginLeft: "0.5rem" }}>The complete guide to AI-powered betting predictions</span>
                  <span style={{ color: "#6b7280", fontSize: "0.75rem", marginLeft: "0.5rem" }}>by Willie Birkett</span>
                </div>
                <span style={{ background: "#C6011F", color: "#fff", fontWeight: 700, fontSize: "0.75rem", padding: "0.4rem 0.9rem", borderRadius: "0.25rem", whiteSpace: "nowrap" }}>GET IT ON AMAZON →</span>
              </div>
            </a>
          </main>
        </div>
      </BrowserRouter>
    </HelmetProvider>
  );
}
