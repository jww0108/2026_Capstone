import { useState, useEffect } from "react";
import T from '../constants/theme';

export default function AnimBar({ value, max, color, delay = 0 }) {
  const [w, setW] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setW((value / max) * 100), delay + 350);
    return () => clearTimeout(t);
  }, [value, max, delay]);
  return (
    <div style={{ height:5, background:T.sand2, borderRadius:3, overflow:"hidden" }}>
      <div style={{ width:w+"%", height:"100%", background:color, borderRadius:3, transition:"width 1s cubic-bezier(.4,0,.2,1)" }} />
    </div>
  );
}
