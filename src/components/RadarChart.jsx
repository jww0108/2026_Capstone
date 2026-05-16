import { useState, useEffect } from "react";
import T from '../constants/theme';

export default function RadarChart({ data, size=300, animated=true }) {
  const [opacity, setOpacity] = useState(animated ? 0 : 1);
  const [sc,     setSc]       = useState(animated ? 0.7 : 1);

  useEffect(() => {
    const t = setTimeout(() => { setOpacity(1); setSc(1); }, 300);
    return () => clearTimeout(t);
  }, []);

  const VB  = 300;
  const pad = 50;
  const cx  = VB / 2;
  const cy  = VB / 2;
  const r   = (VB / 2) - pad - 6;
  const lbR = (VB / 2) - pad + 18;

  const labels = ["README","구조","테스트","CI/CD","커밋","리듬","배포","협업","성장"];
  const n = labels.length;
  const angle = i => (Math.PI * 2 * i / n) - Math.PI / 2;
  const pt = (i, pct) => {
    const a = angle(i), d = r * (pct / 100);
    return [cx + d * Math.cos(a), cy + d * Math.sin(a)];
  };
  const lbPt = i => {
    const a = angle(i);
    return [cx + lbR * Math.cos(a), cy + lbR * Math.sin(a)];
  };

  const labelProps = [
    { anchor:"middle", dy:-4 },
    { anchor:"start",  dy:-2 },
    { anchor:"start",  dy: 9 },
    { anchor:"start",  dy: 9 },
    { anchor:"middle", dy:13 },
    { anchor:"end",    dy: 9 },
    { anchor:"end",    dy: 9 },
    { anchor:"end",    dy:-2 },
    { anchor:"middle", dy:-4 },
  ];

  const dataPoly = data.map((d, i) => pt(i, d.radar).join(",")).join(" ");

  return (
    <svg
      width="100%" height={size}
      viewBox={`0 0 ${VB} ${VB}`}
      style={{ display:"block", transition:"opacity .6s, transform .6s", opacity, transform:`scale(${sc})`, transformOrigin:"center" }}
    >
      {[20,40,60,80,100].map(lvl => (
        <polygon key={lvl}
          points={data.map((_,i) => pt(i,lvl).join(",")).join(" ")}
          fill="none" stroke={T.sand2} strokeWidth="1"
        />
      ))}
      {data.map((_,i) => {
        const [x,y] = pt(i,100);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke={T.sand2} strokeWidth="1"/>;
      })}
      <polygon points={dataPoly} fill={`${T.teal}22`} stroke={T.teal} strokeWidth="1.8" strokeLinejoin="round"/>
      {data.map((d,i) => {
        const [x,y] = pt(i, d.radar);
        return <circle key={i} cx={x} cy={y} r="3" fill={T.teal} stroke="#fff" strokeWidth="1.5"/>;
      })}
      {labels.map((lbl, i) => {
        const [x,y] = lbPt(i);
        const { anchor, dy } = labelProps[i] || { anchor:"middle", dy:5 };
        return (
          <text key={i} x={x} y={y+dy} textAnchor={anchor}
            fontSize="11" fill={T.slate} fontFamily={T.sans} fontWeight="500">
            {lbl}
          </text>
        );
      })}
    </svg>
  );
}
