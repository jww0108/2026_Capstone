import { PORTFOLIO } from '../constants/portfolio';
import StatusPill from '../components/StatusPill';
import RadarChart from '../components/RadarChart';
import PageShell from '../components/PageShell';
import T from '../constants/theme';

export default function ProfilePage() {
  return (
    <PageShell label="프로필 진단" title="GitHub 레포지토리 품질 심층 분석">

      {/* 레이더 차트 + 포트폴리오 카드 */}
      <div style={{ display:"grid", gridTemplateColumns:"320px 1fr", gap:16, marginBottom:16 }}>

        {/* 레이더 차트 */}
        <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"18px 20px" }}>
          <div style={{ fontFamily:T.sans, fontSize:13, fontWeight:600, color:T.ink, marginBottom:4 }}>역량 레이더</div>
          <RadarChart data={PORTFOLIO} size={280}/>
          <div style={{ textAlign:"center", fontFamily:T.sans, fontSize:10, color:T.slate, lineHeight:1.6, marginTop:6 }}>
            테스트·CI/CD·배포 영역이<br/>현저히 낮음 — 즉각 보강 필요
          </div>
        </div>

        {/* 포트폴리오 카드 목록 */}
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {PORTFOLIO.map(p => (
            <div key={p.label} style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:12, padding:"14px 18px" }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:5 }}>
                <span style={{ fontFamily:T.sans, fontSize:13, fontWeight:500, color:T.ink }}>{p.label}</span>
                <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                  <span style={{ fontFamily:T.sans, fontSize:11, color:T.slate }}>{p.radar}점</span>
                  <StatusPill status={p.status}/>
                </div>
              </div>
              <p style={{ fontFamily:T.sans, fontSize:12, color:T.slate, margin:0, lineHeight:1.5 }}>{p.detail}</p>
              {p.rec && <p style={{ fontFamily:T.sans, fontSize:11, color:T.amber, marginTop:5, marginBottom:0, lineHeight:1.5 }}>→ {p.rec}</p>}
            </div>
          ))}
        </div>
      </div>

      {/* 기대 수준 */}
      <div style={{ background:T.ink, borderRadius:14, padding:"20px 24px" }}>
        <div style={{ fontFamily:T.sans, fontSize:11, fontWeight:600, color:"rgba(250,249,246,.5)", letterSpacing:".07em", textTransform:"uppercase", marginBottom:8 }}>기대 수준</div>
        <div style={{ fontFamily:T.font, fontSize:20, color:T.cream, marginBottom:6 }}>Entry</div>
        <p style={{ fontFamily:T.sans, fontSize:13, color:"rgba(250,249,246,.65)", lineHeight:1.7, margin:0 }}>중소·SI·일반 스타트업 지원에 적합한 기본 단계입니다. 테스트·CI/CD·배포를 보강하면 체감 평가 등급이 즉각 상승합니다.</p>
      </div>

    </PageShell>
  );
}
