import { PORTFOLIO } from '../constants/portfolio';
import { fmtM, pct2 } from './helpers';

export function pdfHTML(username, d) {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Git2Value · ${username}</title>
<style>body{font-family:Georgia,serif;background:#FAF9F6;color:#1B1F3B;padding:44px;max-width:860px;margin:0 auto;-webkit-print-color-adjust:exact;print-color-adjust:exact}
h1{font-size:26px;margin:0 0 4px}h2{font-size:16px;margin:24px 0 10px;border-bottom:1px solid #DDD9CF;padding-bottom:6px}
.score{font-size:40px;font-weight:700;color:#1A6B5C}.sub{font-size:12px;color:#6B7280;margin-bottom:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:12px 0}
.card{background:#fff;border:1px solid #DDD9CF;border-radius:10px;padding:14px 16px}
.good{color:#1A6B5C}.ok{color:#E8892B}.bad{color:#C4414A}
table{width:100%;border-collapse:collapse;margin:10px 0}td,th{padding:7px 10px;font-size:12px;border-bottom:1px solid #E8E4DA;text-align:left}th{color:#6B7280;font-weight:400}
</style></head><body>
<h1>Git2Value · ${username}</h1>
<p class="sub">분석 완료 · ${new Date().toLocaleDateString("ko-KR")} · v5.1</p>
<div class="card"><div class="score">${d.score}<span style="font-size:18px;color:#6B7280"> / 100</span></div>
<div style="font-size:13px;color:#6B7280;margin-top:6px">기여도 ${d.contribution} / 성숙도 ${d.quality} / 일관성 ${d.consistency} · LOC ${(d.loc/1000).toFixed(1)}k · 커밋 ${d.commits}개</div></div>
<h2>직무 매칭 결과</h2>
<table><tr><th>순위</th><th>회사</th><th>직무</th><th>유사도</th></tr>
${d.matches.map((m,i)=>`<tr><td>#${i+1}</td><td>${m.company}</td><td>${m.title}</td><td>${pct2(m.sim)}</td></tr>`).join("")}
</table>
<h2>포트폴리오 진단</h2>
<div class="grid">${PORTFOLIO.map(p=>`<div class="card"><b>${p.label}</b><span class="${p.status==="양호"?"good":p.status==="보통"?"ok":"bad"}" style="float:right">${p.status}</span><p style="font-size:12px;color:#6B7280;margin:6px 0 0">${p.detail}</p>${p.rec?`<p style="font-size:11px;color:#E8892B;margin:5px 0 0">→ ${p.rec}</p>`:""}</div>`).join("")}</div>
<h2>시장 연봉 밴드 · 프론트엔드 · 신입</h2>
<div class="card"><b style="font-size:20px;color:#E8892B">${fmtM(d.salary.min)} — ${fmtM(d.salary.max)}</b>
<p style="font-size:12px;color:#6B7280;margin:6px 0 0">점핏·원티드 2025 채용공고 기반. 개인 협상력에 따라 차이 발생 가능.</p></div>
<h2>AI 종합 분석</h2>
<div class="card"><p style="font-size:13px;line-height:1.8;margin:0">${d.aiComment}</p></div>
</body></html>`;
}
