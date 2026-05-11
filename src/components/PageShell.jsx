import T from '../constants/theme';

export default function PageShell({ label, title, children }) {
  return (
    <main style={{ flex:1, padding:"36px 40px", overflowY:"auto", background:T.cream, minHeight:"100vh" }}>
      <div style={{ marginBottom:28 }}>
        <div style={{ fontFamily:T.sans, fontSize:11, fontWeight:600, color:T.slate, letterSpacing:".07em", textTransform:"uppercase", marginBottom:6 }}>{label}</div>
        <h2 style={{ fontFamily:T.font, fontSize:24, fontWeight:700, color:T.ink, margin:0, letterSpacing:"-.02em" }}>{title}</h2>
      </div>
      {children}
    </main>
  );
}
