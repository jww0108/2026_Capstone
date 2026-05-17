import T from '../constants/theme';

const NAV = [
  { id:"overview", icon:"◈", label:"개요" },
  { id:"profile",  icon:"◇", label:"프로필 진단" },
  { id:"market",   icon:"◎", label:"시장 가치" },
  { id:"career",   icon:"⬡", label:"커리어 경로" },
];

export default function Sidebar({ active, onSelect, username, onContact }) {
  return (
    <aside style={{ width:216, minWidth:216, background:T.cream, borderRight:`1px solid ${T.border}`, display:"flex", flexDirection:"column", height:"100vh", position:"sticky", top:0, fontFamily:T.sans }}>

      {/* 로고 + 사용자 카드 */}
      <div style={{ padding:"22px 20px 18px", borderBottom:`1px solid ${T.border}` }}>
        <div style={{ display:"flex", alignItems:"center", gap:9, marginBottom:16 }}>
          <div style={{ width:30, height:30, borderRadius:7, background:T.ink, display:"flex", alignItems:"center", justifyContent:"center" }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 12C2 8.68 4.68 6 8 6s6 2.68 6 6" stroke="#FAF9F6" strokeWidth="1.5" strokeLinecap="round"/><circle cx="8" cy="4" r="2" fill="#E8892B"/></svg>
          </div>
          <span style={{ fontSize:14, fontWeight:700, color:T.ink }}>Git2Value</span>
        </div>

        {/* 사용자 아바타 + 이름 */}
        <div style={{ display:"flex", alignItems:"center", gap:9, padding:"10px 12px", background:T.sand, borderRadius:9, border:`1px solid ${T.border}` }}>
          <div style={{ width:28, height:28, borderRadius:"50%", background:T.ink, display:"flex", alignItems:"center", justifyContent:"center", fontSize:12, color:T.cream, fontWeight:700, flexShrink:0 }}>
            {username ? username.charAt(0).toUpperCase() : "?"}
          </div>
          <div>
            <div style={{ fontSize:12, fontWeight:600, color:T.ink, lineHeight:1.3 }}>{username}</div>
            <div style={{ fontSize:10, color:T.slate }}>0년차 · C# 개발자</div>
          </div>
        </div>
      </div>

      {/* 네비게이션 */}
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

      {/* 하단 */}
      <div style={{ padding:"10px", borderTop:`1px solid ${T.border}` }}>
        <button onClick={onContact} style={{ width:"100%", textAlign:"left", padding:"8px 12px", border:"none", background:"transparent", fontSize:12, color:T.slate, fontFamily:T.sans, cursor:"pointer", borderRadius:6, display:"flex", alignItems:"center", gap:8 }}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink:0 }}>
            <path d="M2 3a1 1 0 011-1h10a1 1 0 011 1v7a1 1 0 01-1 1H9l-3 2v-2H3a1 1 0 01-1-1V3z" stroke={T.slate} strokeWidth="1.4" strokeLinejoin="round"/>
          </svg>
          고객 지원 · 피드백
        </button>
        <div style={{ padding:"8px 12px", marginTop:6, background:T.sand, borderRadius:6 }}>
          <div style={{ fontSize:10, color:T.slate, lineHeight:1.5 }}>점핏·원티드 2025 데이터 기반<br/>참고 목적으로만 활용하세요</div>
        </div>
      </div>

    </aside>
  );
}
