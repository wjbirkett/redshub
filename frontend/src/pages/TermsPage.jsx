import { Helmet } from "react-helmet-async";
const S = { surface:"#1a1a1a",border:"rgba(255,255,255,0.08)",red:"#C6011F",text:"#f0ebe8",textMuted:"#c9b8ae" };
const Section = ({title,children}) => (
  <div style={{marginBottom:"1.25rem"}}>
    <h3 style={{fontFamily:"Space Grotesk,sans-serif",fontWeight:700,fontSize:"0.9375rem",color:S.red,textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:"0.5rem"}}>{title}</h3>
    <p style={{color:S.textMuted,fontSize:"0.875rem",lineHeight:1.7}}>{children}</p>
  </div>
);
export default function TermsPage() {
  return (
    <div style={{padding:"1.5rem 2rem",maxWidth:"720px"}}>
      <Helmet><title>Terms of Use — RedsHub</title></Helmet>
      <h2 style={{fontFamily:"Space Grotesk,sans-serif",fontWeight:900,fontSize:"1.75rem",textTransform:"uppercase",fontStyle:"italic",color:S.text,marginBottom:"1.5rem"}}>Terms of Use</h2>
      <div style={{background:S.surface,borderRadius:"0.75rem",padding:"1.5rem",border:`1px solid ${S.border}`}}>
        <Section title="Entertainment Only">All content on RedsHub, including predictions, best bets, run line picks, and player props, is provided for entertainment and informational purposes only. Nothing on this site constitutes professional gambling advice.</Section>
        <Section title="No Guarantee">AI predictions are generated algorithmically and may be inaccurate. Past performance does not guarantee future results. You should never bet more than you can afford to lose.</Section>
        <Section title="Responsible Gaming">If you or someone you know has a gambling problem, please call 1-800-GAMBLER or visit ncpgambling.org. Must be 21+ and in a jurisdiction where sports betting is legal.</Section>
        <Section title="Intellectual Property">All original content, layouts, and AI-generated analysis on RedsHub is owned by RedsHub. RedsHub is an independent fan site not affiliated with the Cincinnati Reds or MLB.</Section>
        <Section title="Changes">These terms may be updated at any time without notice. Continued use of the site constitutes acceptance of the current terms.</Section>
      </div>
    </div>
  );
}
