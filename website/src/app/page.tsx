import { FileText, Folder } from "lucide-react";
import Link from "next/link";

const githubUrl = "https://github.com/PinewoodRobotics/B.L.I.T.Z";

function ProjectTree() {
  return (
    <div
      aria-label="Project structure"
      className="relative font-mono text-[16px] leading-[20px] text-[#c1c1c1]"
    >
      <div
        aria-hidden="true"
        className="absolute top-[29px] left-[9px] h-[67px] w-px bg-[#333]"
      />
      <div
        aria-hidden="true"
        className="absolute top-[104px] left-[39px] h-[140px] w-px bg-[#333]"
      />

      <div className="flex h-5 items-center gap-[15px]">
        <span className="h-0 w-0 shrink-0 border-x-[7px] border-t-[10px] border-x-transparent border-t-[#d4d4d4]" />
        <span className="font-semibold text-[#38a6ff]">src/</span>
      </div>

      <div className="mt-[5px] space-y-[5px]">
        <div className="flex h-5 items-center gap-[13px] pl-[29px]">
          <Folder
            className="size-[18px] shrink-0 text-[#c8c8c8]"
            fill="currentColor"
            strokeWidth={0}
          />
          <span>simulation/</span>
        </div>

        <div className="flex h-5 items-center gap-[13px] pl-[29px]">
          <Folder
            className="size-[18px] shrink-0 text-[#c8c8c8]"
            fill="currentColor"
            strokeWidth={0}
          />
          <span>frontend/</span>
        </div>

        <div className="flex h-5 items-center gap-[10px] pl-[29px] font-semibold text-[#38a6ff]">
          <span className="h-0 w-0 shrink-0 border-x-[6px] border-t-[8px] border-x-transparent border-t-[#9a9a9a]" />
          <span>backend/</span>
        </div>

        <div className="flex h-5 items-center gap-[13px] pl-[59px]">
          <Folder
            className="size-[18px] shrink-0 text-[#c8c8c8]"
            fill="currentColor"
            strokeWidth={0}
          />
          <span>cpp/</span>
        </div>

        <div className="flex h-5 items-center gap-[13px] pl-[59px]">
          <Folder
            className="size-[18px] shrink-0 text-[#c8c8c8]"
            fill="currentColor"
            strokeWidth={0}
          />
          <span>deployment/</span>
        </div>

        <div className="flex h-5 items-center gap-[13px] pl-[59px]">
          <Folder
            className="size-[18px] shrink-0 text-[#c8c8c8]"
            fill="currentColor"
            strokeWidth={0}
          />
          <span>generated/</span>
        </div>

        <div className="flex h-5 items-center gap-[13px] pl-[59px]">
          <Folder
            className="size-[18px] shrink-0 text-[#c8c8c8]"
            fill="currentColor"
            strokeWidth={0}
          />
          <span>python/</span>
        </div>

        <div className="flex h-5 items-center gap-[13px] pl-[59px]">
          <Folder
            className="size-[18px] shrink-0 text-[#c8c8c8]"
            fill="currentColor"
            strokeWidth={0}
          />
          <span>rust/</span>
        </div>

        <div className="flex h-5 items-center gap-[13px] pl-[59px]">
          <FileText
            className="size-[19px] shrink-0 text-[#c8c8c8]"
            strokeWidth={1.65}
          />
          <span>deploy.py</span>
        </div>

        <div className="flex h-5 items-center gap-[13px]">
          <Folder
            className="size-[18px] shrink-0 text-[#c8c8c8]"
            fill="currentColor"
            strokeWidth={0}
          />
          <span>tests/</span>
        </div>

        <div className="flex h-5 items-center gap-[13px]">
          <FileText
            className="size-[19px] shrink-0 text-[#c8c8c8]"
            strokeWidth={1.65}
          />
          <span>AGENTS.md</span>
        </div>

        <div className="flex h-5 items-center gap-[13px]">
          <FileText
            className="size-[19px] shrink-0 text-[#c8c8c8]"
            strokeWidth={1.65}
          />
          <span>Makefile</span>
        </div>

        <div className="flex h-5 items-center gap-[13px]">
          <FileText
            className="size-[19px] shrink-0 text-[#c8c8c8]"
            strokeWidth={1.65}
          />
          <span>pyproject.toml</span>
        </div>

        <div className="flex h-5 items-center gap-[13px]">
          <FileText
            className="size-[19px] shrink-0 text-[#c8c8c8]"
            strokeWidth={1.65}
          />
          <span>README.md</span>
        </div>
      </div>
    </div>
  );
}

function CodeLine({
  number,
  children,
}: Readonly<{
  number: number;
  children?: React.ReactNode;
}>) {
  return (
    <div className="grid h-[19px] grid-cols-[45px_1fr]">
      <span className="text-[#757575] select-none">{number}</span>
      <span>{children}</span>
    </div>
  );
}

function CodePreview() {
  return (
    <div className="font-mono text-[17px] leading-[19px] text-[#ececec]">
      <CodeLine number={1}>
        <span className="text-[#c7b7ff]">from</span>{" "}
        <span>backend.deployment</span>{" "}
        <span className="text-[#c7b7ff]">import</span> <span>processes</span>
      </CodeLine>
      <CodeLine number={2}>
        <span className="text-[#c7b7ff]">class</span>{" "}
        <span className="text-[#6ee7f2]">ProcessType</span>
        <span>(processes.WeightedProcess):</span>
      </CodeLine>
      <CodeLine number={3}>
        <span>&nbsp;&nbsp;&nbsp;&nbsp;VISION = </span>
        <span className="text-[#f6e8a9]">&quot;vision&quot;</span>
        <span>, 1.0</span>
      </CodeLine>
      <CodeLine number={4}>
        <span>&nbsp;&nbsp;&nbsp;&nbsp;MOTION = </span>
        <span className="text-[#f6e8a9]">&quot;motion&quot;</span>
        <span>, 0.6</span>
      </CodeLine>
      <CodeLine number={5} />
      <CodeLine number={6}>
        <span className="text-[#c7b7ff]">def</span>{" "}
        <span className="text-[#6ee7f2]">pi_name_to_process_types</span>
        <span>(pi_names: list[str]):</span>
      </CodeLine>
      <CodeLine number={7}>
        <span>&nbsp;&nbsp;&nbsp;&nbsp;</span>
        <span className="text-[#c7b7ff]">return</span>
        <span> (</span>
      </CodeLine>
      <CodeLine number={8}>
        <span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>
        <span>processes.</span>
        <span className="text-[#6ee7f2]">ProcessPlan</span>
        <span>[ProcessType]()</span>
      </CodeLine>
      <CodeLine number={9}>
        <span>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;.add(ProcessType.VISION)
        </span>
      </CodeLine>
      <CodeLine number={10}>
        <span>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;.add(ProcessType.MOTION)
        </span>
      </CodeLine>
      <CodeLine number={11}>
        <span>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;.assign(pi_names)
        </span>
      </CodeLine>
      <CodeLine number={12}>
        <span>&nbsp;&nbsp;&nbsp;&nbsp;)</span>
      </CodeLine>
    </div>
  );
}

function DeploymentOutput() {
  const steps = [
    "Discovered 3 systems",
    "Built 2 target bundles",
    "Synced backend to fleet",
    "Applied process plan in 3.2s",
  ];

  return (
    <div className="font-mono text-[19px] leading-[28.25px] tracking-[0.01em]">
      <div className="text-[#e8e8e8]">$ uv run src/backend/deploy.py</div>
      {steps.map((step) => (
        <div key={step} className="flex items-center gap-[12px]">
          <span className="font-bold text-[#00e83b]">✓</span>
          <span className="text-[#2788ff]">{step}</span>
        </div>
      ))}
    </div>
  );
}

function WorkspacePreview() {
  return (
    <div className="relative mx-auto mt-[22px] grid h-[427px] w-full max-w-[1140px] translate-y-px grid-cols-[281px_1fr] overflow-hidden rounded-[6px] border border-[#4a4a4a] bg-black text-left shadow-[0_24px_90px_rgba(0,0,0,0.72)] max-md:h-auto max-md:grid-cols-1">
      <aside className="border-r border-[#464646] px-[31px] pt-[41px] max-md:border-r-0 max-md:border-b max-md:pb-10">
        <ProjectTree />
      </aside>

      <div className="grid grid-rows-[258px_1fr] overflow-hidden">
        <div className="overflow-x-auto px-[31px] pt-[27px]">
          <CodePreview />
        </div>

        <div className="border-t border-[#454545] px-[31px] pt-[11px]">
          <DeploymentOutput />
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-white">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(255,255,255,0.026),transparent_43%)]"
      />

      <header className="relative z-20 flex h-[66px] items-start justify-between px-[28px] pt-[13px] max-sm:px-5">
        <Link
          href="/"
          className="font-mono text-[28px] leading-[38px] font-bold tracking-[0.085em]"
        >
          BLITZ
        </Link>

        <nav
          aria-label="Primary navigation"
          className="absolute top-[25px] left-1/2 flex -translate-x-1/2 gap-[42px] text-[17px] leading-none text-[#b1b1b1] max-sm:hidden"
        >
          <a className="transition-colors hover:text-white" href="#docs">
            Docs
          </a>
          <a
            className="transition-colors hover:text-white"
            href={githubUrl}
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </nav>

        <Link
          href="/application"
          className="mr-[11px] flex h-[40px] w-[139px] items-center justify-center rounded-[4px] bg-white text-[16px] font-medium text-black shadow-[0_0_18px_rgba(255,255,255,0.08)] transition-colors hover:bg-[#e8e8e8]"
        >
          Get started
        </Link>
      </header>

      <main id="top" className="relative z-10">
        <section className="px-6 pt-[58px] text-center">
          <h1 className="mx-auto max-w-[1080px] translate-x-[13px] -translate-y-px text-[88px] leading-[0.95] font-semibold tracking-[-0.075em] text-[#f7f7f7] max-lg:translate-x-0 max-lg:text-[66px] max-md:text-[52px] max-sm:text-[42px]">
            Ship robotics like software.
          </h1>

          <p className="mx-auto mt-[15px] max-w-[760px] translate-y-px text-[25px] leading-[32px] text-[#a9a9a9] max-sm:text-lg max-sm:leading-7">
            <span className="block translate-x-[8px] tracking-[-0.026em] max-sm:translate-x-0">
              Your app, processors, simulation, and deployment—together,
            </span>
            <span className="block translate-y-px tracking-[-0.02em]">
              where your agents can see all of it.
            </span>
          </p>

          <div className="mt-[28px] flex -translate-x-[2px] translate-y-px justify-center gap-[23px] max-sm:translate-x-0 max-sm:flex-col max-sm:items-center">
            <Link
              href="/application"
              className="flex h-[42px] w-[153px] items-center justify-center rounded-[4px] bg-white text-[16px] font-medium text-black transition-colors hover:bg-[#e8e8e8]"
            >
              Start building
            </Link>
            <a
              href={githubUrl}
              target="_blank"
              rel="noreferrer"
              className="flex h-[42px] w-[170px] items-center justify-center rounded-[4px] border border-[#565656] bg-black text-[16px] font-medium text-white transition-colors hover:border-[#888] hover:bg-[#101010]"
            >
              Read the docs
            </a>
          </div>

          <WorkspacePreview />

          <section id="docs" className="pt-[41px]">
            <h2 className="-translate-x-[5px] text-[40px] leading-[44px] font-semibold tracking-[-0.03em] text-[#f2f2f2] max-sm:translate-x-0 max-sm:text-[30px]">
              Dashboards are overrated.
            </h2>
            <p className="mt-0 -translate-x-[4px] translate-y-px text-[27px] leading-[37px] tracking-[-0.007em] text-[#aaa] max-sm:translate-x-0">
              Your code is the control plane.
            </p>
            <p className="mt-[8px] -translate-x-[5px] text-[20px] leading-[30px] tracking-normal text-[#747474] max-sm:translate-x-0">
              Vanilla code. Vanilla hardware. Zero context switching.
            </p>

            <div
              aria-hidden="true"
              className="relative mx-auto mt-[36px] h-[23px] w-full max-w-[1020px]"
            >
              <div className="absolute top-0 right-[calc(50%+14px)] left-0 h-px bg-[#343434]" />
              <div className="absolute top-0 right-0 left-[calc(50%+14px)] h-px bg-[#343434]" />
              <div className="absolute top-[-10px] left-1/2 size-[20px] -translate-x-1/2 rotate-45 border-r border-b border-[#343434] bg-black" />
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}
