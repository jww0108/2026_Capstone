import { pct2, fmtM } from '../utils/helpers';
import T from '../constants/theme';

export default function SummaryPage({ username, data, onDetail, onReset }) {
  const d = data;
  return (
    <div style={{ minHeight:"100vh", background:T.cream, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", fontFamily:T.sans, padding:"60px 24px" }}>
      <div style={{ width:"100%", maxWidth:580 }}>
        <div style={{ textAlign:"center", marginBottom:32 }}>
          <div style={{ fontFamily:T.sans, fontSize:11, fontWeight:600, color:T.teal, letterSpacing:".1em", textTransform:"uppercase", marginBottom:10 }}>분석 완료</div>
          <h2 style={{ fontFamily:T.font, fontSize:28, fontWeight:700, color:T.ink, margin:"0 0 6px", letterSpacing:"-.02em" }}>{username}</h2>
          <p style={{ fontFamily:T.sans, fontSize:13, color:T.slate, margin:0 }}>0년차 · {d.stacks[0].lang} {d.stacks[0].pct}%</p>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:14 }}>
          {[
            { label:"GitHub 점수",  val:`${d.score}`, unit:"/ 100", color:T.teal  },
            { label:"최고 매칭도",  val:pct2(d.matches[0].sim), unit:"",    color:T.amber },
            { label:"시장 연봉",    val:fmtM(d.salary.jumpfit), unit:"중앙", color:T.ink  },
          ].map(s => (
            <div key={s.label} style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:12, padding:18, textAlign:"center" }}>
              <div style={{ fontFamily:T.sans, fontSize:11, color:T.slate, marginBottom:6 }}>{s.label}</div>
              <div style={{ fontFamily:T.font, fontSize:22, fontWeight:700, color:s.color }}>{s.val} <span style={{ fontSize:12, color:T.slate }}>{s.unit}</span></div>
            </div>
          ))}
        </div>
        <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"18px 22px", marginBottom:14 }}>
          <div style={{ fontFamily:T.sans, fontSize:12, color:T.slate, marginBottom:8 }}>1순위 매칭 직무</div>
          <div style={{ fontFamily:T.sans, fontSize:14, fontWeight:600, color:T.ink }}>[{d.matches[0].company}] {d.matches[0].title}</div>
          <div style={{ fontFamily:T.sans, fontSize:12, color:T.slate, marginTop:4 }}>유사도 {pct2(d.matches[0].sim)} · {d.matches[0].tag}</div>
        </div>
        <div style={{ display:"flex", gap:10 }}>
          <button onClick={onDetail} style={{ flex:1, padding:13, background:T.ink, border:"none", borderRadius:11, color:T.cream, fontSize:14, fontFamily:T.sans, fontWeight:600, cursor:"pointer" }}>전체 전략 확인하기 →</button>
          <button onClick={onReset} style={{ padding:"13px 18px", background:"transparent", border:`1px solid ${T.border}`, borderRadius:11, color:T.slate, fontSize:13, fontFamily:T.sans, cursor:"pointer" }}>← 재분석</button>
        </div>
      </div>
    </div>
  );
}
