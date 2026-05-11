import T from '../constants/theme';

export const fmtM  = n => `${Math.round(n / 10000).toLocaleString()}만원`;
export const pct2  = n => `${(n * 100).toFixed(1)}%`;
export const sClr  = s => s === "양호" ? T.teal : s === "보통" ? T.amber : T.rose;
export const sBg   = s => s === "양호" ? T.tealL : s === "보통" ? T.amberL : T.roseL;
