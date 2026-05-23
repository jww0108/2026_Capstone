import Image from "next/image"
import {
  Link as LinkIcon,
  Lock,
  RotateCcw,
  UserRound,
  FolderOpen,
  AlertCircle,
  Database,
  Settings,
  KeyRound,
  UsersRound,
} from "lucide-react"
import { WorkHeader } from "@/components/Header"
import { HelpSidebar } from "@/components/Sidebar"
import { Card } from "@/components/ui/card"

type GuideTone = "green" | "blue" | "purple" | "orange"

type ProblemRow = {
  icon: React.ReactNode
  title: string
  items: string[]
}

const problems: ProblemRow[] = [
  {
    icon: <AlertCircle className="h-7 w-7 text-red-500" />,
    title: "분석이 너무 오래 걸려요.",
    items: [
      "GitHub API 요청이 많아 시간이 오래 걸릴 수 있습니다.",
      "레포 크기나 커밋 수가 많을수록 시간이 더 걸립니다.",
    ],
  },
  {
    icon: <AlertCircle className="h-7 w-7 text-orange-500" />,
    title: "GitHub 정보를 가져오지 못했어요.",
    items: [
      "GitHub ID 또는 레포 URL이 올바른지 확인하세요.",
      "레포가 비공개이거나 삭제되었을 수 있습니다.",
      "네트워크 연결 상태를 확인하세요.",
    ],
  },
  {
    icon: <Database className="h-7 w-7 text-purple-500" />,
    title: "직무 매칭 결과가 없어요.",
    items: [
      "입력한 기술 스택이나 README 내용이 부족할 수 있습니다.",
      "더 많은 기술 스택과 프로젝트 설명을 추가하면 매칭 정확도가 올라갑니다.",
      "경력 조건을 변경해보세요.",
    ],
  },
  {
    icon: <Settings className="h-7 w-7 text-blue-500" />,
    title: "연봉 데이터가 표시되지 않아요.",
    items: [
      "데이터 소스가 일시적으로 업데이트 중일 수 있습니다.",
      "잠시 후 다시 시도해주세요.",
      "그래도 문제가 지속되면 문의하기를 이용해주세요.",
    ],
  },
]

export default function HelpPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <WorkHeader mode="help" />
      <HelpSidebar />

      <main className="ml-[270px] pt-16">
        <div className="mx-auto max-w-[1600px] px-9 py-5">
          <h1 className="text-[40px] font-black tracking-[-0.045em]">문제해결 가이드</h1>
          <p className="mt-2 text-lg font-extrabold text-slate-600">
            분석 과정에서 발생할 수 있는 문제와 해결 방법을 확인해보세요.
          </p>

          <Card className="mt-5 px-5 py-5">
            <h2 className="text-2xl font-black tracking-[-0.035em]">입력값 확인 가이드</h2>
            <div className="mt-4 grid grid-cols-4 gap-4">
              <Guide
                tone="green"
                icon={<UserRound />}
                title="GitHub ID 확인"
                points={[
                  "정확한 GitHub 사용자 ID를 입력했는지 확인하세요.",
                  "예: tekyung (O) / https://github.com/tekyung (X)",
                  "ID는 대소문자를 구분하지 않습니다.",
                ]}
              />
              <Guide
                tone="blue"
                icon={<LinkIcon />}
                title="레포지토리 URL 확인"
                points={[
                  "공개 상태의 레포지토리만 분석 가능합니다.",
                  "URL 형식: https://github.com/사용자명/레포명",
                  "최대 3개까지 입력할 수 있습니다.",
                ]}
              />
              <Guide
                tone="purple"
                icon={<UsersRound />}
                title="경력 선택"
                points={[
                  "현재 본인의 경력 구간을 선택해주세요.",
                  "신입(0년차) 또는 경력 연수에 따라 매칭 결과가 달라집니다.",
                ]}
              />
              <Guide
                tone="orange"
                icon={<Lock />}
                title="접근 권한 확인"
                points={[
                  "비공개 레포는 분석이 불가능합니다.",
                  "접근 권한이 있는 레포만 입력해주세요.",
                  "404 오류가 발생하면 권한을 확인하세요.",
                ]}
              />
            </div>
          </Card>

          <div className="mt-4 grid grid-cols-[1fr_560px] items-stretch gap-4">
            <Card className="px-6 py-5">
              <h2 className="text-2xl font-black tracking-[-0.035em]">자주 발생하는 문제와 해결 방법</h2>
              <table className="mt-3 w-full">
                <tbody>
                  {problems.map((problem) => (
                    <tr key={problem.title} className="border-b align-top last:border-b-0">
                      <td className="w-14 py-4">{problem.icon}</td>
                      <td className="w-[290px] py-4 pr-4 text-lg font-black tracking-[-0.025em] text-slate-950">
                        {problem.title}
                      </td>
                      <td className="pb-4 pt-5">
                        <ul className="list-disc space-y-1 pl-5 text-[15px] font-extrabold leading-6 text-slate-600">
                          {problem.items.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            <div className="flex h-full flex-col gap-4">
              <Setting
                icon={<KeyRound />}
                title="GitHub API 토큰 확인"
                desc=".env 파일에 GitHub Personal Access Token이 설정되어 있는지 확인하세요."
              />
              <Setting
                icon={<FolderOpen />}
                title="데이터 파일 확인"
                desc="vector/ 폴더와 연봉 데이터 파일이 정상적으로 위치해 있는지 확인하세요."
              />
              <Setting
                icon={<RotateCcw />}
                title="캐시 초기화"
                desc="오래된 캐시 파일 때문에 문제가 발생할 수 있습니다. experience_cache.json 파일을 삭제 후 다시 분석해보세요."
              />
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-orange-200 bg-orange-50 px-5 py-4">
            <h2 className="flex items-center gap-2 text-xl font-black tracking-[-0.035em] text-orange-800">
              <Image src="/images/light.png" alt="" width={28} height={26} />더 좋은 분석 결과를 위한 팁
            </h2>
            <ul className="mt-2 flex items-center justify-between gap-6 text-[14px] font-black leading-6 text-slate-700">
              <li className="whitespace-nowrap">✓ README에 목적, 기술 스택, 실행 방법, 스크린샷, 성과 등을 작성하세요.</li>
              <li className="whitespace-nowrap">✓ 커밋 메시지를 의미 있고 일관성 있게 작성하세요.</li>
              <li className="whitespace-nowrap">✓ 테스트, CI/CD, 배포 관리 등 협업 역량을 보여주는 요소를 추가하세요.</li>
            </ul>
          </div>
        </div>
      </main>
    </div>
  )
}

function Guide({
  icon,
  title,
  points,
  tone,
}: {
  icon: React.ReactNode
  title: string
  points: string[]
  tone: GuideTone
}) {
  const toneStyle = {
    green: "bg-emerald-50 text-emerald-600 border-emerald-100",
    blue: "bg-blue-50 text-blue-600 border-blue-100",
    purple: "bg-purple-50 text-purple-600 border-purple-100",
    orange: "bg-orange-50 text-orange-600 border-orange-100",
  }[tone]

  return (
    <div className="rounded-2xl border bg-white px-4 py-4">
      <div className="flex items-start gap-4">
        <div className={`grid h-14 w-14 min-w-14 place-items-center rounded-full border ${toneStyle}`}>
          <div className="[&>svg]:h-8 [&>svg]:w-8">{icon}</div>
        </div>
        <div className="min-w-0 pt-1">
          <h3 className="text-lg font-black tracking-[-0.025em] text-slate-950">{title}</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-[13.5px] font-extrabold leading-6 text-slate-600">
            {points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

function Setting({
  icon,
  title,
  desc,
}: {
  icon: React.ReactNode
  title: string
  desc: string
}) {
  return (
    <Card className="flex-1 border-blue-100 bg-blue-50/40 px-5 py-4">
      <div className="flex h-full items-center justify-center gap-4">
        <div className="grid h-[52px] w-[52px] min-w-[52px] place-items-center rounded-full bg-white text-blue-600 shadow-sm">
          <div className="[&>svg]:h-7 [&>svg]:w-7">{icon}</div>
        </div>
        <div className="min-w-0">
          <h3 className="text-xl font-black tracking-[-0.035em] text-blue-700">{title}</h3>
          <p className="mt-1 max-w-[410px] text-[15px] font-extrabold leading-6 text-slate-600">{desc}</p>
        </div>
      </div>
    </Card>
  )
}
