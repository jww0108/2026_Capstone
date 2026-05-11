import { PORTFOLIO } from '../constants/portfolio';
import { SALARY_ALL } from '../constants/salary';
import { fmtM, pct2 } from '../utils/helpers';
import { pdfHTML } from '../utils/pdfHTML';
import ScoreArc from '../components/ScoreArc';
import AnimBar from '../components/AnimBar';
import Tag from '../components/Tag';
import StatusPill from '../components/StatusPill';
import SalaryBars from '../components/SalaryBars';
import T from '../constants/theme';

export default function OverviewPage({ username, data }) {
  const handlePDF = () => {
    const w = window.open("","_blank");
    w.document.write(pdfHTML(username, data));
    w.document.close();
    setTimeout(() => w.print(), 500);
  };
  return (
    <main style={{ flex:1, padding:"36px 40px", overflowY:"auto", background:T.cream, minHeight:"100vh" }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:32 }}>
        <div>
          <div style={{ fontFamily:T.sans, fontSize:11, fontWeight:600, color:T.slate, letterSpacing:".07em", textTransform:"uppercase", marginBottom:6 }}>분석 리포트</div>
          <h1 style={{ fontFamily:T.font, fontSize:28, fontWeight:700, color:T.ink, margin:0, letterSpacing:"-.02em" }}>{username}</h1>
          <p style={{ fontFamily:T.sans, fontSize:13, color:T.slate, margin:"4px 0 0" }}>Git2Value v5.1 · 0년차 · C# 기반</p>
        </div>
        <button onClick={handlePDF} style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 18px", background:T.ink, border:"none", borderRadius:8, color:T.cream, fontSize:13, fontFamily:T.sans, fontWeight:500, cursor:"pointer" }}>↓ PDF 저장</button>
      </div>

      {/* score + metrics */}
      <div style={{ display:"grid", gridTemplateColumns:"160px 1fr", gap:16, marginBottom:16 }}>
        <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:20, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", gap:8 }}>
          <ScoreArc score={data.score} />
          <div style={{ fontFamily:T.sans, fontSize:11, color:T.slate, textAlign:"center" }}>GitHub 종합 점수</div>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10 }}>
          {[
            { label:"기여도", val:data.contribution, of:"/ 60",  color:T.teal,  pct:(data.contribution/60)*100 },
            { label:"성숙도", val:data.quality,      of:"/ 30",  color:T.amber, pct:(data.quality/30)*100 },
            { label:"일관성", val:data.consistency,  of:"/ 10",  color:T.ink,   pct:(data.consistency/10)*100 },
            { label:"레포 수",  val:data.repos,    of:"개",   color:T.slate },
            { label:"총 커밋",  val:data.commits,  of:"개",   color:T.slate },
            { label:"유효 LOC", val:(data.loc/1000).toFixed(1)+"k", of:"lines", color:T.slate },
          ].map((s,i) => (
            <div key={i} style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:12, padding:"14px 16px" }}>
              <div style={{ fontFamily:T.sans, fontSize:11, color:T.slate, marginBottom:6 }}>{s.label}</div>
              <div style={{ fontFamily:T.sans, fontSize:20, fontWeight:700, color:s.color }}>
                {s.val} <span style={{ fontSize:12, color:T.slate, fontWeight:400 }}>{s.of}</span>
              </div>
              {s.pct !== undefined && <AnimBar value={s.pct} max={100} color={s.color} delay={i*100} />}
            </div>
          ))}
        </div>
      </div>

      {/* job matching */}
      <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"20px 24px", marginBottom:16 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:16 }}>
          <div style={{ fontFamily:T.sans, fontSize:13, fontWeight:600, color:T.ink }}>직무 매칭 결과</div>
          <div style={{ fontFamily:T.sans, fontSize:11, color:T.slate }}>FAISS 코사인 유사도 · Top-5</div>
        </div>
        {data.matches.map((m, i) => (
          <div key={i} style={{ display:"grid", gridTemplateColumns:"18px 1fr 76px 56px", gap:12, alignItems:"center", marginBottom: i<4 ? 10 : 0, paddingBottom: i<4 ? 10 : 0, borderBottom: i<4 ? `1px solid ${T.sand2}` : "none" }}>
            <span style={{ fontFamily:T.sans, fontSize:11, color:T.slate, fontWeight:600 }}>#{i+1}</span>
            <div>
              <span style={{ fontFamily:T.sans, fontSize:13, color:T.ink }}>{m.company}</span>
              <span style={{ fontFamily:T.sans, fontSize:12, color:T.slate, marginLeft:8 }}>{m.title}</span>
            </div>
            <Tag color={T.ink2}>{m.tag}</Tag>
            <div style={{ textAlign:"right" }}>
              <div style={{ fontFamily:T.sans, fontSize:13, fontWeight:700, color: m.sim>=.75 ? T.teal : m.sim>=.70 ? T.amber : T.slate }}>{pct2(m.sim)}</div>
              <div style={{ height:3, background:T.sand2, borderRadius:2, marginTop:3 }}>
                <div style={{ width:pct2(m.sim), height:"100%", background: m.sim>=.75 ? T.teal : T.amber, borderRadius:2 }} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* portfolio + salary */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:16 }}>
        <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"20px 24px" }}>
          <div style={{ fontFamily:T.sans, fontSize:13, fontWeight:600, color:T.ink, marginBottom:14 }}>포트폴리오 진단</div>
          {PORTFOLIO.slice(0,7).map(p => (
            <div key={p.label} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:9 }}>
              <span style={{ fontFamily:T.sans, fontSize:12, color:T.slate }}>{p.label}</span>
              <StatusPill status={p.status} />
            </div>
          ))}
        </div>
        <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"20px 24px" }}>
          <div style={{ fontFamily:T.sans, fontSize:13, fontWeight:600, color:T.ink, marginBottom:4 }}>시장 연봉 밴드</div>
          <div style={{ fontFamily:T.sans, fontSize:11, color:T.slate, marginBottom:14 }}>매칭 직무 · 신입 (0~3년)</div>
          <div style={{ fontFamily:T.font, fontSize:22, fontWeight:700, color:T.amber, marginBottom:16 }}>
            {fmtM(data.salary.min)} — {fmtM(data.salary.max)}
          </div>
          <SalaryBars data={SALARY_ALL.slice(0,4)} />
        </div>
      </div>

      {/* insights + stack */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:16 }}>
        <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"20px 24px" }}>
          <div style={{ fontFamily:T.sans, fontSize:13, fontWeight:600, color:T.ink, marginBottom:14 }}>최근 인사이트</div>
          {[
            { icon:"↑", text:"커밋 메시지 길이 최근 1.43배 개선", color:T.teal },
            { icon:"·", text:"CI/CD 추가 시 체감 등급 Entry → Junior", color:T.amber },
            { icon:"→", text:"TS + React 토이 프로젝트 1개 신설 권장", color:T.ink2 },
            { icon:"○", text:"추가 공개 레포 등록으로 분석 신뢰도 향상", color:T.slate },
          ].map((ins,i) => (
            <div key={i} style={{ display:"flex", gap:10, marginBottom:10, alignItems:"flex-start" }}>
              <span style={{ fontFamily:T.sans, fontSize:14, color:ins.color, minWidth:14, marginTop:1 }}>{ins.icon}</span>
              <span style={{ fontFamily:T.sans, fontSize:12, color:T.slate, lineHeight:1.55 }}>{ins.text}</span>
            </div>
          ))}
        </div>
        <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:14, padding:"20px 24px" }}>
          <div style={{ fontFamily:T.sans, fontSize:13, fontWeight:600, color:T.ink, marginBottom:16 }}>기술 스택 분포</div>
          {data.stacks.map((s,i) => (
            <div key={s.lang} style={{ marginBottom:14 }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
                <span style={{ fontFamily:T.sans, fontSize:12, color:T.ink }}>{s.lang}</span>
                <span style={{ fontFamily:T.sans, fontSize:12, color:T.slate }}>{s.pct}%</span>
              </div>
              <AnimBar value={s.pct} max={100} color={s.color} delay={i*80} />
            </div>
          ))}
          {data.stackNote && (
            <div style={{ marginTop:12, padding:"9px 12px", background:T.amberL, borderLeft:`3px solid ${T.amber}`, borderRadius:4, fontFamily:T.sans, fontSize:11, color:T.amber }}>
              {data.stackNote}
            </div>
          )}
        </div>
      </div>

      {/* AI comment */}
      <div style={{ background:T.sand, border:`1px solid ${T.border}`, borderRadius:14, padding:"22px 26px" }}>
        <div style={{ fontFamily:T.sans, fontSize:11, fontWeight:600, color:T.slate, letterSpacing:".07em", textTransform:"uppercase", marginBottom:10 }}>AI 종합 분석</div>
        <p style={{ fontFamily:T.sans, fontSize:13, color:T.ink, lineHeight:1.85, margin:0 }}>{data.aiComment}</p>
      </div>
    </main>
  );
}
