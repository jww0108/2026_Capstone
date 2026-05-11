import T from '../constants/theme';
import Tag from '../components/Tag';

export default function LandingPage({ username, setUsername, onStart }) {
  return (
    <div style={{ background:T.cream, color:T.ink, fontFamily:T.sans, minHeight:"100vh" }}>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />

      {/* nav */}
      <nav style={{ position:"sticky", top:0, zIndex:50, background:"rgba(250,249,246,.94)", backdropFilter:"blur(12px)", borderBottom:`1px solid ${T.border}`, padding:"0 48px", display:"flex", justifyContent:"space-between", alignItems:"center", height:58 }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ width:28, height:28, borderRadius:7, background:T.ink, display:"flex", alignItems:"center", justifyContent:"center" }}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 12C2 8.68 4.68 6 8 6s6 2.68 6 6" stroke="#FAF9F6" strokeWidth="1.5" strokeLinecap="round"/><circle cx="8" cy="4" r="2" fill="#E8892B"/></svg>
          </div>
          <span style={{ fontSize:14, fontWeight:700, color:T.ink, fontFamily:T.sans }}>Git2Value</span>
        </div>
        <div style={{ display:"flex", gap:32, fontSize:13, color:T.slate }}>
          {["워크플로우","활용 사례","데이터 출처"].map(l => <a key={l} href="#" style={{ color:T.slate, textDecoration:"none" }}>{l}</a>)}
        </div>
        <button onClick={() => document.getElementById("hero-input").focus()} style={{ padding:"8px 18px", background:T.ink, border:"none", borderRadius:8, color:T.cream, fontSize:13, fontWeight:500, cursor:"pointer", fontFamily:T.sans }}>분석 시작</button>
      </nav>

      {/* hero */}
      <section style={{ maxWidth:860, margin:"0 auto", padding:"96px 48px 80px" }}>
        <div style={{ fontFamily:T.sans, fontSize:11, fontWeight:600, color:T.slate, letterSpacing:".1em", textTransform:"uppercase", marginBottom:20 }}>GitHub Career Intelligence · v5.1</div>
        <h1 style={{ fontFamily:T.font, fontSize:"clamp(38px,5vw,60px)", fontWeight:700, lineHeight:1.08, letterSpacing:"-.03em", margin:"0 0 24px", maxWidth:680 }}>
          당신의 코드가<br/><span style={{ color:T.amber }}>시장에서 말하는</span> 가치
        </h1>
        <p style={{ fontFamily:T.sans, fontSize:16, color:T.slate, maxWidth:520, lineHeight:1.75, margin:"0 0 44px" }}>
          GitHub 레포지토리를 분석해 실제 채용 공고와 의미론적으로 매칭하고, 시장 연봉 밴드와 포트폴리오 개선 방향을 함께 제공합니다.
        </p>
        <div style={{ display:"flex", gap:10, alignItems:"center" }}>
          <input id="hero-input" value={username} onChange={e => setUsername(e.target.value)} onKeyDown={e => e.key === "Enter" && onStart()} placeholder="GitHub 사용자명" style={{ width:230, padding:"12px 16px", background:"#fff", border:`1px solid ${T.border}`, borderRadius:9, color:T.ink, fontSize:14, fontFamily:T.sans, outline:"none" }} />
          <button onClick={onStart} style={{ padding:"12px 26px", background:T.ink, border:"none", borderRadius:9, color:T.cream, fontSize:14, fontFamily:T.sans, fontWeight:600, cursor:"pointer" }}>분석하기 →</button>
        </div>
      </section>

      {/* stats */}
      <section style={{ background:T.ink, padding:"36px 48px" }}>
        <div style={{ maxWidth:860, margin:"0 auto", display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:32 }}>
          {[
            { val:"73.8점",  label:"평균 GitHub 점수 (2025 신입 기준)" },
            { val:"3,480만", label:"프론트엔드 신입 연봉 중앙값" },
            { val:"78.1%",   label:"최상위 유사도 매칭 달성" },
            { val:"5개",     label:"직무 매칭 Top-5 자동 추출" },
          ].map(s => (
            <div key={s.val}>
              <div style={{ fontFamily:T.font, fontSize:28, fontWeight:700, color:T.cream, marginBottom:6 }}>{s.val}</div>
              <div style={{ fontFamily:T.sans, fontSize:12, color:"rgba(250,249,246,.5)", lineHeight:1.5 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* workflow */}
      <section style={{ maxWidth:860, margin:"0 auto", padding:"88px 48px" }}>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 2fr", gap:48 }}>
          <div>
            <Tag color={T.slate}>워크플로우</Tag>
            <h2 style={{ fontFamily:T.font, fontSize:30, fontWeight:700, color:T.ink, margin:"14px 0 16px", lineHeight:1.15, letterSpacing:"-.02em" }}>세 단계로<br/>완성되는 분석</h2>
            <p style={{ fontFamily:T.sans, fontSize:13, color:T.slate, lineHeight:1.7 }}>단순 키워드 검색을 넘어, 기술 스택을 임베딩 벡터로 변환해 채용 공고와 의미론적으로 연결합니다.</p>
          </div>
          <div>
            {[
              { n:"01", title:"GitHub 정량화",  body:"커밋 히스토리, LOC, 기술 스택, 코드 품질 지표를 자동으로 수집하고 100점 기준으로 환산합니다." },
              { n:"02", title:"FAISS 직무 매칭", body:"fine-tuned 임베딩 모델로 기술 프로필을 벡터화한 뒤 FAISS 인덱스에서 유사도 높은 공고 Top-5를 추출합니다." },
              { n:"03", title:"연봉 밴드 산출",  body:"점핏·원티드 2025 채용 공고 데이터를 교차검증해 직무·연차별 시장 연봉 범위를 제공합니다." },
            ].map((s,i) => (
              <div key={s.n} style={{ display:"flex", gap:20, padding:"22px 0", borderBottom: i<2 ? `1px solid ${T.border}` : "none" }}>
                <div style={{ fontFamily:T.font, fontSize:20, fontWeight:700, color:T.amber, minWidth:32 }}>{s.n}</div>
                <div>
                  <div style={{ fontFamily:T.sans, fontSize:14, fontWeight:600, color:T.ink, marginBottom:6 }}>{s.title}</div>
                  <p style={{ fontFamily:T.sans, fontSize:13, color:T.slate, lineHeight:1.65, margin:0 }}>{s.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* use cases */}
      <section style={{ background:T.sand, padding:"72px 48px" }}>
        <div style={{ maxWidth:860, margin:"0 auto" }}>
          <div style={{ textAlign:"center", marginBottom:48 }}>
            <Tag color={T.slate}>활용 사례</Tag>
            <h2 style={{ fontFamily:T.font, fontSize:26, fontWeight:700, color:T.ink, margin:"14px 0 0", letterSpacing:"-.02em" }}>이런 분들이 활용합니다</h2>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:16 }}>
            {[
              { who:"주니어 개발자",    desc:"내 GitHub가 실제로 어느 수준인지, 어떤 직무에 어울리는지 객관적으로 파악하고 싶을 때" },
              { who:"취업 준비생",      desc:"포트폴리오의 구체적인 약점을 찾고, 채용 담당자 눈에 보이는 부분을 개선하고 싶을 때" },
              { who:"IT 리크루터",     desc:"이력서 텍스트가 아닌 실제 코드 역량 기반으로 지원자를 스크리닝하고 싶을 때" },
            ].map(c => (
              <div key={c.who} style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"22px 20px" }}>
                <div style={{ fontFamily:T.font, fontSize:16, fontWeight:700, color:T.ink, marginBottom:10 }}>{c.who}</div>
                <p style={{ fontFamily:T.sans, fontSize:13, color:T.slate, lineHeight:1.65, margin:0 }}>{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* data note */}
      <section style={{ maxWidth:860, margin:"0 auto", padding:"64px 48px" }}>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:48 }}>
          {[
            { tag:"데이터 출처", title:"신뢰할 수 있는 데이터", body:"연봉 데이터는 점핏·원티드의 2025년 채용 공고를 직접 수집해 정규화했습니다. 직무 매칭 모델은 ko-sroberta-multitask 기반으로 AI·IT 도메인 JD 데이터셋에 대조 학습(Contrastive Learning)으로 fine-tuning했습니다." },
            { tag:"주의 사항",  title:"참고 자료로 활용하세요", body:"이 분석은 공개된 GitHub 데이터와 채용 공고 통계를 기반으로 합니다. 실제 채용 결과는 면접, 팀 컬처 핏, 개인 협상력 등 다양한 요소에 영향을 받으며, 본 결과는 경력 설계의 참고 자료로 활용하기를 권장합니다." },
          ].map(s => (
            <div key={s.tag}>
              <Tag color={T.slate}>{s.tag}</Tag>
              <h3 style={{ fontFamily:T.font, fontSize:22, fontWeight:700, color:T.ink, margin:"14px 0 12px", letterSpacing:"-.02em" }}>{s.title}</h3>
              <p style={{ fontFamily:T.sans, fontSize:13, color:T.slate, lineHeight:1.7, margin:0 }}>{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* footer CTA */}
      <section style={{ background:T.ink, padding:"64px 48px" }}>
        <div style={{ maxWidth:860, margin:"0 auto", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <div>
            <h2 style={{ fontFamily:T.font, fontSize:26, fontWeight:700, color:T.cream, margin:"0 0 8px", letterSpacing:"-.02em" }}>지금 바로 분석해보세요</h2>
            <p style={{ fontFamily:T.sans, fontSize:14, color:"rgba(250,249,246,.6)", margin:0 }}>GitHub 사용자명만 입력하면 1분 내 리포트가 완성됩니다.</p>
          </div>
          <div style={{ display:"flex", gap:10 }}>
            <input value={username} onChange={e => setUsername(e.target.value)} onKeyDown={e => e.key === "Enter" && onStart()} placeholder="GitHub 사용자명" style={{ width:200, padding:"11px 16px", background:"rgba(250,249,246,.08)", border:`1px solid rgba(250,249,246,.2)`, borderRadius:9, color:T.cream, fontSize:14, fontFamily:T.sans, outline:"none" }} />
            <button onClick={onStart} style={{ padding:"11px 22px", background:T.amber, border:"none", borderRadius:9, color:T.ink, fontSize:14, fontFamily:T.sans, fontWeight:600, cursor:"pointer" }}>분석하기 →</button>
          </div>
        </div>
      </section>
    </div>
  );
}
