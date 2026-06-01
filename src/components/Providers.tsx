"use client"

import { AnalysisProvider } from "@/context/AnalysisContext"
import type { ReactNode } from "react"

export function Providers({ children }: { children: ReactNode }) {
  return <AnalysisProvider>{children}</AnalysisProvider>
}
