// AboutPage.jsx
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";

const S = { surface:"#1a1a1a",border:"rgba(255,255,255,0.08)",red:"#C6011F",text:"#f0ebe8",textMuted:"#c9b8ae" };

export function AboutPage() {
  return (
    <div style={{ padding: "1.5rem 2rem", maxWidth: "720px" }}>
      <Helmet><title>About RedsHub</title></Helmet>
      <h2 style={{ fontFamily:"Space Grotesk,sans-serif",fontWeight:900,fontSize:"1.75rem",textTransform:"uppercase",fontStyle:"italic",color:S.text,marginBottom:"1.5rem" }}>About RedsHub</h2>
      <div style={{ background:S.surface,borderRadius:"0.75rem",padding:"1.5rem",border:`1px solid ${S.border}`,lineHeight:1.75,color:S.textMuted,fontSize:"0.9375rem",display:"flex",flexDirection:"column",gap:"1rem" }}>
        <p><strong style={{color:S.text}}>RedsHub</strong> is an AI-powered fan dashboard for the Cincinnati Reds, delivering daily predictions, best bets, run line picks, and player props before every game.</p>
        <p>Our AI model analyzes pitching matchups, batting splits, bullpen usage, injuries, and historical trends to generate data-driven picks — automatically, every game day.</p>
        <p style={{fontSize:"0.75rem",opacity:0.6}}>RedsHub is an independent fan site and is not affiliated with the Cincinnati Reds or Major League Baseball. All predictions are for entertainment purposes only.</p>
        <p>Built by <a href="https://websitesbywillie.com" target="_blank" rel="noopener noreferrer" style={{color:S.red,textDecoration:"none"}}>Websites by Willie</a></p>
      </div>
    </div>
  );
}

export default AboutPage;
