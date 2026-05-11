import { useState, useEffect } from "react";
import T from '../constants/theme';

export default function ScoreArc({ score, size = 120 }) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let s = 0;
    const id = setInterval(() => {
      s = Math.min(s + 1.6, score);
      setVal(s);
      if (s >= score) clearInterval(id);
    }, 16);
    return () => clearInterval(id);
  }, [score]);
  const r = 46, circ = 2 * Math.PI * r;
  const filled = circ * (val / 100);
  const col = val >= 70 ? T.teal : val >= 50 ? T.amber : T.rose;
  return (
    <div style={{ position:"relative", width:size, height:size }}>
      <svg width={size} height={size} viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke={T.sand2} strokeWidth="8"/>
        <circle cx="60" cy="60" r={r} fill="none" stroke={col} strokeWidth="8"
          strokeLinecap="round" strokeDasharray={`${filled} ${circ-filled}`} strokeDashoffset={circ/4}/>
      </svg>
      <div style={{ position:"absolute", inset:0, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center" }}>
        <div style={{ fontSize:26, fontWeight:700, fontFamily:T.sans, color:T.ink, lineHeight:1 }}>{Math.round(val)}</div>
        <div style={{ fontSize:10, color:T.slate, fontFamily:T.sans }}>/ 100</div>
      </div>
    </div>
  );
}
