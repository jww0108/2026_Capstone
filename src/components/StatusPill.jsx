import { sClr, sBg } from '../utils/helpers';
import T from '../constants/theme';

export default function StatusPill({ status }) {
  return (
    <span style={{ fontSize:11, fontFamily:T.sans, fontWeight:600, color:sClr(status), background:sBg(status), padding:"3px 10px", borderRadius:20 }}>
      {status}
    </span>
  );
}
