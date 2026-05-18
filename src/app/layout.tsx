import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Git2Value",
  description: "GitHub 포트폴리오 진단, 직무 매칭, 시장 연봉 밴드 분석 서비스",
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko"><body>{children}</body></html>
}
