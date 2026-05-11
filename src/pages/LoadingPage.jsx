import { STEPS } from '../constants/steps';
import T from '../constants/theme';

export default function LoadingPage({ username, loadPct, loadStep }) {
  const step = STEPS[Math.min(loadStep, STEPS.length - 1)];
  const circ = 2 * Math.PI * 46;
  const filled = circ * (loadPct / 100);
  return (
    <div style={{ minHeight:"100vh", background:T.cream, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", fontFamily:T.sans, padding:24 }}>
      <div style={{ width:"100%", maxWidth:480, textAlign:"center" }}>
        <div style={{ fontFamily:T.sans, fontSize:13, color:T.slate, marginBottom:28 }}>
          <span style={{ color:T.ink, fontWeight:600 }}>{username}</span> 분석 중...
        </div>
        <div style={{ position:"relative", width:140, height:140, margin:"0 auto 28px" }}>
          <svg width="140" height="140" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="46" fill="none" stroke={T.sand2} strokeWidth="7"/>
            <circle cx="60" cy="60" r="46" fill="none" stroke={T.ink} strokeWidth="7" strokeLinecap="round" strokeDasharray={`${filled} ${circ-filled}`} strokeDashoffset={circ/4}/>
          </svg>
          <div style={{ position:"absolute", inset:0, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center" }}>
            <div style={{ fontFamily:T.sans, fontSize:26, fontWeight:700, color:T.ink }}>{Math.round(loadPct)}</div>
            <div style={{ fontFamily:T.sans, fontSize:10, color:T.slate }}>%</div>
          </div>
        </div>
        <div style={{ fontFamily:T.font, fontSize:18, fontWeight:700, color:T.ink, marginBottom:5 }}>{step.label}</div>
        <div style={{ fontFamily:T.sans, fontSize:12, color:T.slate, marginBottom:28 }}>{step.detail}</div>
        <div style={{ width:"100%", height:3, background:T.sand2, borderRadius:2, overflow:"hidden", marginBottom:24 }}>
          <div style={{ width:loadPct+"%", height:"100%", background:T.ink, borderRadius:2, transition:"width .3s ease" }} />
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:7, textAlign:"left" }}>
          {STEPS.map((s,i) => (
            <div key={i} style={{ display:"flex", alignItems:"center", gap:10, opacity: i<=loadStep ? 1 : 0.3, transition:"opacity .3s" }}>
              <div style={{ width:18, height:18, borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", fontSize:10, fontWeight:700, background: i<loadStep ? T.teal : i===loadStep ? T.ink : T.sand2, color: i<=loadStep ? "#fff" : T.slate, flexShrink:0, fontFamily:T.sans }}>
                {i < loadStep ? "✓" : i+1}
              </div>
              <span style={{ fontFamily:T.sans, fontSize:12, color: i===loadStep ? T.ink : i<loadStep ? T.teal : T.slate }}>{s.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
