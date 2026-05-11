import T from '../constants/theme';

const NAV = [
  { id:"overview", icon:"◈", label:"개요" },
  { id:"profile",  icon:"◇", label:"프로필 진단" },
  { id:"market",   icon:"◎", label:"시장 가치" },
  { id:"career",   icon:"⬡", label:"커리어 경로" },
];

export default function Sidebar({ active, onSelect }) {
  return (
    <aside style={{ width:216, minWidth:216, background:T.cream, borderRight:`1px solid ${T.border}`, display:"flex", flexDirection:"column", height:"100vh", position:"sticky", top:0, fontFamily:T.sans }}>
      <div style={{ padding:"22px 20px 18px", borderBottom:`1px solid ${T.border}` }}>
        <div style={{ display:"flex", alignItems:"center", gap:9, marginBottom:16 }}>
          <div style={{ width:30, height:30, borderRadius:7, background:T.ink, display:"flex", alignItems:"center", justifyContent:"center" }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 12C2 8.68 4.68 6 8 6s6 2.68 6 6" stroke="#FAF9F6" strokeWidth="1.5" strokeLinecap="round"/><circle cx="8" cy="4" r="2" fill="#E8892B"/></svg>
          </div>
          <span style={{ fontSize:14, fontWeight:700, color:T.ink }}>Git2Value</span>
        </div>
        <p style={{ fontSize:11, color:T.slate, margin:0, lineHeight:1.5 }}>GitHub 역량 · 직무 매칭 · 연봉 인텔리전스</p>
      </div>
      <nav style={{ flex:1, padding:"14px 10px" }}>
        {NAV.map(n => {
          const on = active === n.id;
          return (
            <button key={n.id} onClick={() => onSelect(n.id)} style={{ width:"100%", display:"flex", alignItems:"center", gap:10, padding:"9px 12px", borderRadius:7, border:"none", cursor:"pointer", background: on ? T.ink : "transparent", color: on ? T.cream : T.slate, fontSize:13, fontFamily:T.sans, fontWeight: on ? 500 : 400, marginBottom:2, textAlign:"left", transition:"all .15s" }}>
              <span style={{ fontSize:13, opacity:.8 }}>{n.icon}</span>{n.label}
            </button>
          );
        })}
      </nav>
      <div style={{ padding:"10px", borderTop:`1px solid ${T.border}` }}>
        {["설정","고객 지원","피드백"].map(l => (
          <button key={l} style={{ width:"100%", textAlign:"left", padding:"7px 12px", border:"none", background:"transparent", fontSize:12, color:T.slate, fontFamily:T.sans, cursor:"pointer", borderRadius:6 }}>{l}</button>
        ))}
      </div>
    </aside>
  );
}
