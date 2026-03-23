import { Helmet } from "react-helmet-async";
const S = { surface:"#1a1a1a",border:"rgba(255,255,255,0.08)",red:"#C6011F",text:"#f0ebe8",textMuted:"#c9b8ae" };
const Section = ({title,children}) => (
  <div style={{marginBottom:"1.25rem"}}>
    <h3 style={{fontFamily:"Space Grotesk,sans-serif",fontWeight:700,fontSize:"0.9375rem",color:S.red,textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:"0.5rem"}}>{title}</h3>
    <p style={{color:S.textMuted,fontSize:"0.875rem",lineHeight:1.7}}>{children}</p>
  </div>
);
export default function PrivacyPage() {
  return (
    <div style={{padding:"1.5rem 2rem",maxWidth:"720px"}}>
      <Helmet><title>Privacy Policy — RedsHub</title></Helmet>
      <h2 style={{fontFamily:"Space Grotesk,sans-serif",fontWeight:900,fontSize:"1.75rem",textTransform:"uppercase",fontStyle:"italic",color:S.text,marginBottom:"1.5rem"}}>Privacy Policy</h2>
      <div style={{background:S.surface,borderRadius:"0.75rem",padding:"1.5rem",border:`1px solid ${S.border}`}}>
        <Section title="Data We Collect">RedsHub does not collect personal information. We do not require accounts, logins, or payment. Standard server logs (IP addresses, browser type) may be retained for security purposes.</Section>
        <Section title="Third-Party Services">We use ESPN's public API for sports data, The Odds API for betting lines, and Anthropic's Claude for AI content generation. Affiliate links to DraftKings are present on the site.</Section>
        <Section title="Cookies">We do not use tracking cookies. Basic session data may be stored locally in your browser.</Section>
        <Section title="Contact">Questions about privacy? Email us via websitesbywillie.com.</Section>
      </div>
    </div>
  );
}
