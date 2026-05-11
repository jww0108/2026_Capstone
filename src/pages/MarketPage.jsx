import { fmtM } from '../utils/helpers';
import SalaryBars from '../components/SalaryBars';
import PageShell from '../components/PageShell';
import T from '../constants/theme';

export default function MarketPage({ data }) {
  return (
    <PageShell label="시장 가치" title="2025 채용 공고 기반 연봉 분석">
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:20 }}>
        {[
          { label:"점핏 중앙값 (신입~3년)", val:fmtM(data.salary.jumpfit), color:T.amber },
          { label:"원티드 평균 (신입~3년)",  val:fmtM(data.salary.wanted),  color:T.teal  },
        ].map(s => (
          <div key={s.label} style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"22px 24px" }}>
            <div style={{ fontFamily:T.sans, fontSize:12, color:T.slate, marginBottom:10 }}>{s.label}</div>
            <div style={{ fontFamily:T.font, fontSize:28, fontWeight:700, color:s.color }}>{s.val}</div>
            <div style={{ fontFamily:T.sans, fontSize:11, color:T.slate, marginTop:4 }}>프론트엔드</div>
          </div>
        ))}
      </div>
      <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"20px 24px", marginBottom:16 }}>
        <div style={{ fontFamily:T.sans, fontSize:13, fontWeight:600, color:T.ink, marginBottom:16 }}>직무별 연봉 비교 · 신입 구간</div>
        <SalaryBars />
      </div>
      <div style={{ background:T.amberL, border:`1px solid ${T.amber}`, borderRadius:10, padding:"13px 18px", fontFamily:T.sans, fontSize:12, color:T.amber }}>
        ※ 동일 직무 내에서 회사 규모, 지역, 협상력에 따라 실제 연봉은 상당히 다를 수 있습니다. 이 데이터는 참고 목적으로만 활용하세요.
      </div>
    </PageShell>
  );
}
