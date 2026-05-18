import { ReactNode } from "react"
import { WorkHeader } from "@/components/Header"
import { Sidebar } from "@/components/Sidebar"

export function PageShell({ active, children }: { active: string; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <WorkHeader />
      <Sidebar active={active} />
      <main className="ml-[270px] pt-16">
        <div data-pdf-content className="mx-auto max-w-[1600px] px-9 py-6">{children}</div>
      </main>
    </div>
  )
}
