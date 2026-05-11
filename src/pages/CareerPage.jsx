import Tag from '../components/Tag';
import PageShell from '../components/PageShell';
import T from '../constants/theme';

export default function CareerPage({ data }) {
  return (
    <PageShell label="커리어 경로" title="현재 스킬셋 기준 성장 로드맵">
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14, marginBottom:20 }}>
        {[
          { step:"Step 1", time:"1~2개월", title:"TypeScript + React",       desc:"C# 강점을 살리며 프론트엔드 포지셔닝 전환. 타입 시스템 전이가 빠름.", color:T.ink },
          { step:"Step 2", time:"1개월",   title:"테스트 + CI/CD",            desc:"xUnit 테스트 10개 이상 + GitHub Actions lint/test 워크플로우.", color:T.teal },
          { step:"Step 3", time:"3개월",   title:"Unity 게임 클라이언트",     desc:"C# 역량을 게임사 취업으로 전환. 포트폴리오 차별화 극대화.", color:T.amber },
          { step:"Step 4", time:"지속",    title:"포트폴리오 2~3개 강화",    desc:"각 레포에 배포 링크, README 스크린샷, CI 배지 부착 필수.", color:T.rose },
        ].map(c => (
          <div key={c.step} style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"20px 22px" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
              <Tag color={c.color}>{c.step}</Tag>
              <span style={{ fontFamily:T.sans, fontSize:11, color:T.slate }}>{c.time}</span>
            </div>
            <div style={{ fontFamily:T.font, fontSize:17, fontWeight:700, color:T.ink, marginBottom:8 }}>{c.title}</div>
            <p style={{ fontFamily:T.sans, fontSize:12, color:T.slate, lineHeight:1.6, margin:0 }}>{c.desc}</p>
          </div>
        ))}
      </div>
      <div style={{ background:T.ink, borderRadius:14, padding:"24px 28px" }}>
        <div style={{ fontFamily:T.sans, fontSize:11, fontWeight:600, color:"rgba(250,249,246,.5)", letterSpacing:".07em", textTransform:"uppercase", marginBottom:12 }}>AI 종합 코멘트</div>
        <p style={{ fontFamily:T.sans, fontSize:13, color:"rgba(250,249,246,.8)", lineHeight:1.85, margin:0 }}>
          {data.aiComment} <span style={{ color:T.amber }}>위 로드맵의 Step 1–2만 완료해도</span> FAISS 매칭 유사도 0.75 이상 직무 매칭이 기대되며, Entry → Junior 등급 전환이 충분히 가능합니다.
        </p>
      </div>
    </PageShell>
  );
}
