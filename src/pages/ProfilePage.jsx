import { PORTFOLIO } from '../constants/portfolio';
import StatusPill from '../components/StatusPill';
import PageShell from '../components/PageShell';
import T from '../constants/theme';

export default function ProfilePage() {
  return (
    <PageShell label="프로필 진단" title="GitHub 레포지토리 품질 심층 분석">
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginBottom:16 }}>
        {PORTFOLIO.map(p => (
          <div key={p.label} style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:12, padding:"16px 18px" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:7 }}>
              <span style={{ fontFamily:T.sans, fontSize:13, fontWeight:500, color:T.ink }}>{p.label}</span>
              <StatusPill status={p.status} />
            </div>
            <p style={{ fontFamily:T.sans, fontSize:12, color:T.slate, margin:0, lineHeight:1.55 }}>{p.detail}</p>
            {p.rec && <p style={{ fontFamily:T.sans, fontSize:11, color:T.amber, marginTop:7, marginBottom:0, lineHeight:1.5 }}>→ {p.rec}</p>}
          </div>
        ))}
      </div>
      <div style={{ background:T.ink, borderRadius:14, padding:"20px 24px" }}>
        <div style={{ fontFamily:T.sans, fontSize:11, fontWeight:600, color:"rgba(250,249,246,.5)", letterSpacing:".07em", textTransform:"uppercase", marginBottom:8 }}>기대 수준</div>
        <div style={{ fontFamily:T.font, fontSize:20, color:T.cream, marginBottom:6 }}>Entry</div>
        <p style={{ fontFamily:T.sans, fontSize:13, color:"rgba(250,249,246,.65)", lineHeight:1.7, margin:0 }}>중소·SI·일반 스타트업 지원에 적합한 기본 단계입니다. 테스트·CI/CD·배포를 보강하면 체감 평가 등급이 즉각 상승합니다.</p>
      </div>
    </PageShell>
  );
}
