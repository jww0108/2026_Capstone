import T from '../constants/theme';

export default function Tag({ children, color = T.slate }) {
  return (
    <span style={{ display:"inline-block", fontSize:11, fontFamily:T.sans, fontWeight:600, letterSpacing:".07em", textTransform:"uppercase", color, border:`1px solid ${color}`, borderRadius:3, padding:"2px 8px", lineHeight:1.6 }}>
      {children}
    </span>
  );
}
