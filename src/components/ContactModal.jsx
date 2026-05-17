import { useState } from "react";
import T from '../constants/theme';

const MOCK_POSTS = [
  { id:1, title:"매칭 정확도가 생각보다 높네요", author:"dev_kim", date:"2025-04-02", secret:false, body:"C# 위주인데도 프론트엔드 공고를 잘 잡아주더라고요. 신기했습니다." },
  { id:2, title:"연봉 데이터 출처 더 자세히 알 수 있나요?", author:"junior_lee", date:"2025-04-05", secret:false, body:"점핏 외에 다른 플랫폼 데이터도 추가될 예정인지 궁금합니다." },
  { id:3, title:"비밀 문의입니다", author:"anon_user", date:"2025-04-08", secret:true, body:"(비밀글)" },
];

export default function ContactModal({ onClose, isAdmin=false }) {
  const [tab,          setTab]          = useState("board");
  const [posts,        setPosts]        = useState(MOCK_POSTS);
  const [selectedPost, setSelectedPost] = useState(null);
  const [form,         setForm]         = useState({ title:"", body:"", secret:false, author:"" });
  const [submitted,    setSubmitted]    = useState(false);

  const handleSubmit = () => {
    if (!form.title.trim() || !form.body.trim()) return;
    const newPost = {
      id: posts.length + 1,
      title: form.title,
      author: form.author || "익명",
      date: new Date().toISOString().slice(0,10),
      secret: form.secret,
      body: form.secret ? "(비밀글)" : form.body,
      _realBody: form.body,
    };
    setPosts(prev => [newPost, ...prev]);
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setTab("board");
      setForm({ title:"", body:"", secret:false, author:"" });
    }, 1800);
  };

  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(27,31,59,.45)", zIndex:200, display:"flex", alignItems:"center", justifyContent:"center", padding:24 }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ background:"#fff", borderRadius:18, width:"100%", maxWidth:560, maxHeight:"82vh", overflow:"hidden", display:"flex", flexDirection:"column", boxShadow:"0 20px 60px rgba(27,31,59,.18)" }}>

        {/* 헤더 */}
        <div style={{ padding:"20px 24px 16px", borderBottom:`1px solid ${T.border}`, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <div>
            <div style={{ fontFamily:T.sans, fontSize:14, fontWeight:700, color:T.ink }}>고객 지원 · 피드백</div>
            <div style={{ fontFamily:T.sans, fontSize:11, color:T.slate, marginTop:2 }}>의견을 남겨주시면 팀에서 검토 후 답변드립니다.</div>
          </div>
          <button onClick={onClose} style={{ width:28, height:28, borderRadius:"50%", border:"none", background:T.sand2, cursor:"pointer", fontSize:14, color:T.slate, display:"flex", alignItems:"center", justifyContent:"center" }}>✕</button>
        </div>

        {/* 탭 */}
        <div style={{ display:"flex", borderBottom:`1px solid ${T.border}` }}>
          {[{ id:"board", label:"게시판" }, { id:"write", label:"글 쓰기" }].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{ flex:1, padding:"11px 0", border:"none", background:"transparent", cursor:"pointer", fontFamily:T.sans, fontSize:13, fontWeight: tab===t.id ? 600 : 400, color: tab===t.id ? T.ink : T.slate, borderBottom: tab===t.id ? `2px solid ${T.ink}` : "2px solid transparent" }}>{t.label}</button>
          ))}
        </div>

        {/* 콘텐츠 */}
        <div style={{ flex:1, overflowY:"auto" }}>

          {/* 게시판 */}
          {tab === "board" && (
            selectedPost ? (
              <div style={{ padding:"20px 24px" }}>
                <button onClick={() => setSelectedPost(null)} style={{ background:"none", border:"none", cursor:"pointer", fontFamily:T.sans, fontSize:12, color:T.slate, marginBottom:14, display:"flex", alignItems:"center", gap:4 }}>← 목록으로</button>
                <div style={{ fontFamily:T.sans, fontSize:15, fontWeight:700, color:T.ink, marginBottom:6 }}>{selectedPost.title}</div>
                <div style={{ fontFamily:T.sans, fontSize:11, color:T.slate, marginBottom:16 }}>{selectedPost.author} · {selectedPost.date}</div>
                <div style={{ fontFamily:T.sans, fontSize:13, color:T.ink, lineHeight:1.75 }}>
                  {selectedPost.secret && !isAdmin ? "(비밀글입니다.)" : (selectedPost._realBody || selectedPost.body)}
                </div>
              </div>
            ) : (
              <div>
                {posts.map(p => (
                  <div key={p.id} onClick={() => setSelectedPost(p)}
                    style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"13px 24px", borderBottom:`1px solid ${T.sand2}`, cursor:"pointer" }}
                    onMouseEnter={e => e.currentTarget.style.background = T.cream}
                    onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                    <div>
                      <div style={{ fontFamily:T.sans, fontSize:13, color:T.ink, display:"flex", alignItems:"center", gap:6 }}>
                        {p.secret && <span style={{ fontSize:10, background:T.amberL, color:T.amber, padding:"1px 6px", borderRadius:10, fontWeight:600 }}>비밀</span>}
                        {p.title}
                      </div>
                      <div style={{ fontFamily:T.sans, fontSize:11, color:T.slate, marginTop:2 }}>{p.author} · {p.date}</div>
                    </div>
                    <span style={{ fontSize:12, color:T.slate }}>›</span>
                  </div>
                ))}
              </div>
            )
          )}

          {/* 글 쓰기 */}
          {tab === "write" && (
            <div style={{ padding:"20px 24px" }}>
              {submitted ? (
                <div style={{ textAlign:"center", padding:"32px 0" }}>
                  <div style={{ fontSize:32, marginBottom:10 }}>✓</div>
                  <div style={{ fontFamily:T.sans, fontSize:14, fontWeight:600, color:T.teal }}>등록되었습니다</div>
                  <div style={{ fontFamily:T.sans, fontSize:12, color:T.slate, marginTop:4 }}>팀에서 검토 후 답변드립니다.</div>
                </div>
              ) : (
                <>
                  <div style={{ marginBottom:12 }}>
                    <label style={{ fontFamily:T.sans, fontSize:12, color:T.slate, display:"block", marginBottom:5 }}>닉네임</label>
                    <input value={form.author} onChange={e => setForm(f => ({...f, author:e.target.value}))} placeholder="익명" style={{ width:"100%", padding:"9px 12px", border:`1px solid ${T.border}`, borderRadius:8, fontFamily:T.sans, fontSize:13, color:T.ink, outline:"none", background:"#fff", boxSizing:"border-box" }}/>
                  </div>
                  <div style={{ marginBottom:12 }}>
                    <label style={{ fontFamily:T.sans, fontSize:12, color:T.slate, display:"block", marginBottom:5 }}>제목</label>
                    <input value={form.title} onChange={e => setForm(f => ({...f, title:e.target.value}))} placeholder="문의 또는 피드백 제목" style={{ width:"100%", padding:"9px 12px", border:`1px solid ${T.border}`, borderRadius:8, fontFamily:T.sans, fontSize:13, color:T.ink, outline:"none", background:"#fff", boxSizing:"border-box" }}/>
                  </div>
                  <div style={{ marginBottom:14 }}>
                    <label style={{ fontFamily:T.sans, fontSize:12, color:T.slate, display:"block", marginBottom:5 }}>내용</label>
                    <textarea value={form.body} onChange={e => setForm(f => ({...f, body:e.target.value}))} placeholder="자유롭게 의견을 남겨주세요." rows={5} style={{ width:"100%", padding:"9px 12px", border:`1px solid ${T.border}`, borderRadius:8, fontFamily:T.sans, fontSize:13, color:T.ink, outline:"none", background:"#fff", resize:"vertical", boxSizing:"border-box" }}/>
                  </div>
                  <label style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer", marginBottom:18 }}>
                    <input type="checkbox" checked={form.secret} onChange={e => setForm(f => ({...f, secret:e.target.checked}))} style={{ accentColor:T.ink }}/>
                    <span style={{ fontFamily:T.sans, fontSize:12, color:T.slate }}>비밀글로 등록 (운영팀만 열람 가능)</span>
                  </label>
                  <button onClick={handleSubmit} style={{ width:"100%", padding:"12px", background:T.ink, border:"none", borderRadius:10, color:T.cream, fontFamily:T.sans, fontSize:14, fontWeight:600, cursor:"pointer" }}>등록하기</button>
                </>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
