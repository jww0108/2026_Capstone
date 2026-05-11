import { SALARY_ALL } from '../constants/salary';
import { fmtM } from '../utils/helpers';
import T from '../constants/theme';

export default function SalaryBars({ data = SALARY_ALL }) {
  const mx = Math.max(...data.map(d => d.max));
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:9 }}>
      {data.map(d => (
        <div key={d.role} style={{ display:"grid", gridTemplateColumns:"108px 1fr 88px", gap:10, alignItems:"center" }}>
          <span style={{ fontSize:12, fontFamily:T.sans, color: d.highlight ? T.ink : T.slate, fontWeight: d.highlight ? 600 : 400 }}>{d.role}</span>
          <div style={{ height:7, background:T.sand2, borderRadius:4, position:"relative" }}>
            <div style={{ position:"absolute", left:(d.min/mx*100)+"%", width:((d.max-d.min)/mx*100)+"%", height:"100%", background: d.highlight ? T.amber : T.sand2, border: d.highlight ? "none" : `1px solid ${T.border}`, borderRadius:4 }} />
          </div>
          <span style={{ fontSize:11, color:T.slate, fontFamily:T.sans, textAlign:"right" }}>{fmtM(d.min)}~</span>
        </div>
      ))}
    </div>
  );
}
