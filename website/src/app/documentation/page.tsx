import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  Code2,
  Cpu,
  Network,
  Package,
  Rocket,
  Server,
  Terminal,
} from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

const githubUrl = "https://github.com/PinewoodRobotics/B.L.I.T.Z";
const installer =
  '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/install_on_system.sh)"';
const wpilibInstaller =
  '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/install_on_wpilib.sh)"';

const navigation = [
  { label: "Overview", href: "#overview" },
  { label: "Quickstart", href: "#quickstart" },
  { label: "How BLITZ works", href: "#how-it-works" },
  { label: "Process plans", href: "#process-plans" },
  { label: "Modules", href: "#modules" },
  { label: "Deploy", href: "#deploy" },
] as const;

export const metadata: Metadata = {
  title: "Documentation · BLITZ",
  description:
    "Install BLITZ, define typed process plans, and deploy robotics software across your fleet.",
};

function CodeBlock({
  children,
  label,
}: Readonly<{
  children: string;
  label?: string;
}>) {
  return (
    <div className="overflow-hidden rounded-lg border border-[#292929] bg-[#0a0a0a] shadow-[0_18px_60px_rgba(0,0,0,0.24)]">
      {label && (
        <div className="flex h-10 items-center border-b border-[#292929] px-4">
          <span className="font-mono text-[11px] tracking-[0.08em] text-[#777] uppercase">
            {label}
          </span>
          <span className="ml-auto flex gap-1.5" aria-hidden="true">
            <span className="size-1.5 rounded-full bg-[#3b3b3b]" />
            <span className="size-1.5 rounded-full bg-[#3b3b3b]" />
            <span className="size-1.5 rounded-full bg-[#3b3b3b]" />
          </span>
        </div>
      )}
      <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-6 text-[#d8d8d8]">
        <code>{children}</code>
      </pre>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  children,
}: Readonly<{
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}>) {
  return (
    <div className="mb-8">
      <p className="mb-3 font-mono text-[11px] font-medium tracking-[0.12em] text-[#6c8cff] uppercase">
        {eyebrow}
      </p>
      <h2 className="text-[34px] leading-tight font-semibold tracking-[-0.045em] text-white max-sm:text-[29px]">
        {title}
      </h2>
      <p className="mt-3 max-w-2xl text-[16px] leading-7 text-[#969696]">
        {children}
      </p>
    </div>
  );
}

function NumberedStep({
  number,
  title,
  children,
}: Readonly<{
  number: string;
  title: string;
  children: React.ReactNode;
}>) {
  return (
    <div className="grid grid-cols-[36px_1fr] gap-4 border-t border-[#252525] py-5 first:border-t-0 first:pt-0 last:pb-0">
      <span className="flex size-8 items-center justify-center rounded-full border border-[#353535] bg-[#121212] font-mono text-xs text-[#7c98ff]">
        {number}
      </span>
      <div>
        <h3 className="font-medium text-[#ededed]">{title}</h3>
        <div className="mt-1 text-sm leading-6 text-[#888]">{children}</div>
      </div>
    </div>
  );
}

export default function DocumentationPage() {
  return (
    <div className="min-h-screen bg-black text-white">
      <header className="sticky top-0 z-50 border-b border-[#262626] bg-black/88 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center px-6 max-sm:px-4">
          <Link
            href="/"
            className="font-mono text-xl font-bold tracking-[0.085em]"
          >
            BLITZ
          </Link>
          <div className="mx-4 h-5 w-px bg-[#343434]" />
          <span className="text-sm font-medium text-[#a6a6a6]">
            Documentation
          </span>

          <nav
            aria-label="Documentation header navigation"
            className="ml-auto flex items-center gap-5 text-sm"
          >
            <a
              href={githubUrl}
              target="_blank"
              rel="noreferrer"
              className="text-[#9b9b9b] transition-colors hover:text-white max-sm:hidden"
            >
              GitHub
            </a>
            <Link
              href="/#platform"
              className="flex h-9 items-center gap-2 rounded-md bg-white px-4 font-medium text-black transition-colors hover:bg-[#e7e7e7]"
            >
              Get started
              <ArrowRight className="size-3.5" />
            </Link>
          </nav>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] grid-cols-[220px_minmax(0,760px)_190px] justify-center gap-12 px-6 max-xl:grid-cols-[200px_minmax(0,760px)] max-xl:gap-8 max-lg:block max-sm:px-4">
        <aside className="border-r border-[#202020] pt-12 pr-7 max-lg:hidden">
          <div className="sticky top-28">
            <Link
              href="/"
              className="mb-9 flex items-center gap-2 text-sm text-[#777] transition-colors hover:text-white"
            >
              <ArrowLeft className="size-3.5" />
              Back to BLITZ
            </Link>
            <nav aria-label="Documentation sections">
              <p className="mb-3 font-mono text-[10px] tracking-[0.14em] text-[#5e5e5e] uppercase">
                Start here
              </p>
              <div className="space-y-0.5">
                {navigation.map((item, index) => (
                  <a
                    key={item.href}
                    href={item.href}
                    className={`block rounded-md px-3 py-2 text-sm transition-colors ${
                      index === 0
                        ? "bg-[#171717] text-white"
                        : "text-[#808080] hover:bg-[#101010] hover:text-[#d4d4d4]"
                    }`}
                  >
                    {item.label}
                  </a>
                ))}
              </div>
            </nav>

            <div className="mt-9 rounded-lg border border-[#252525] bg-[#0b0b0b] p-4">
              <p className="text-sm font-medium text-[#d8d8d8]">
                View the source
              </p>
              <p className="mt-1.5 text-xs leading-5 text-[#717171]">
                BLITZ is open source and built by Pinewood Robotics.
              </p>
              <a
                href={githubUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-3 flex items-center gap-1.5 text-xs font-medium text-[#91a6ff] hover:text-[#bdc8ff]"
              >
                Open GitHub
                <ChevronRight className="size-3" />
              </a>
            </div>
          </div>
        </aside>

        <main className="min-w-0 pb-28">
          <section
            id="overview"
            className="scroll-mt-24 border-b border-[#222] pt-20 pb-20 max-sm:pt-14 max-sm:pb-14"
          >
            <div className="mb-7 flex size-11 items-center justify-center rounded-lg border border-[#2d3658] bg-[#111526] text-[#8299ff]">
              <Terminal className="size-5" />
            </div>
            <p className="mb-4 font-mono text-[12px] font-medium tracking-[0.12em] text-[#728cff] uppercase">
              BLITZ Documentation
            </p>
            <h1 className="max-w-[700px] text-[56px] leading-[1.02] font-semibold tracking-[-0.058em] text-[#f5f5f5] max-sm:text-[42px]">
              Your robotics stack, deployed as code.
            </h1>
            <p className="mt-6 max-w-[650px] text-[19px] leading-8 text-[#969696]">
              BLITZ discovers target computers, builds the right bundle for each
              architecture, syncs your code, and assigns every process from one
              typed Python plan.
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              <a
                href="#quickstart"
                className="flex h-11 items-center gap-2 rounded-md bg-white px-5 text-sm font-medium text-black transition-colors hover:bg-[#e8e8e8]"
              >
                Install BLITZ
                <ArrowRight className="size-4" />
              </a>
              <a
                href="#process-plans"
                className="flex h-11 items-center rounded-md border border-[#383838] px-5 text-sm font-medium text-[#d2d2d2] transition-colors hover:border-[#5b5b5b] hover:bg-[#101010]"
              >
                Define a process plan
              </a>
            </div>

            <div className="mt-12 grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-[#292929] bg-[#292929] max-sm:grid-cols-1">
              {[
                ["Typed plans", "No YAML control plane"],
                ["Mixed targets", "Build per architecture"],
                ["Local network", "Discover and sync"],
              ].map(([title, detail]) => (
                <div key={title} className="bg-[#0b0b0b] p-5">
                  <div className="mb-3 flex size-6 items-center justify-center rounded-full bg-[#142019] text-[#60d57a]">
                    <Check className="size-3.5" strokeWidth={2.5} />
                  </div>
                  <p className="text-sm font-medium text-[#dedede]">{title}</p>
                  <p className="mt-1 text-xs text-[#6e6e6e]">{detail}</p>
                </div>
              ))}
            </div>
          </section>

          <section
            id="quickstart"
            className="scroll-mt-24 border-b border-[#222] py-20 max-sm:py-14"
          >
            <SectionHeading eyebrow="01 · Quickstart" title="Install a target">
              Run the installer on each native Linux computer that should join
              your fleet. It names the target, installs dependencies, and
              registers the watchdog as a system service.
            </SectionHeading>

            <CodeBlock label="Linux target">{installer}</CodeBlock>

            <div className="mt-8 rounded-lg border border-[#252525] bg-[#0b0b0b] p-6">
              <h3 className="flex items-center gap-2.5 font-medium text-[#e7e7e7]">
                <Cpu className="size-4 text-[#8299ff]" />
                Using WPILib?
              </h3>
              <p className="mt-2 text-sm leading-6 text-[#868686]">
                Run the project installer from your Java WPILib project. It adds
                the Python deployment layer and a Gradle{" "}
                <code className="font-mono text-[#c9c9c9]">deployBlitz</code>{" "}
                task while preserving your customized deployment file.
              </p>
              <div className="mt-5">
                <CodeBlock label="WPILib project">{wpilibInstaller}</CodeBlock>
              </div>
            </div>

            <div className="mt-9">
              <NumberedStep number="1" title="Name the target">
                Choose a stable name such as{" "}
                <code className="font-mono text-[#c7c7c7]">vision-left</code> or{" "}
                <code className="font-mono text-[#c7c7c7]">coprocessor-1</code>.
              </NumberedStep>
              <NumberedStep number="2" title="Start the watchdog">
                Setup installs and starts the systemd service, which advertises
                the target and runs the processes BLITZ assigns.
              </NumberedStep>
              <NumberedStep number="3" title="Deploy from your project">
                Keep deployment logic in{" "}
                <code className="font-mono text-[#c7c7c7]">
                  backend/deploy.py
                </code>
                , then run your project&apos;s deploy command.
              </NumberedStep>
            </div>
          </section>

          <section
            id="how-it-works"
            className="scroll-mt-24 border-b border-[#222] py-20 max-sm:py-14"
          >
            <SectionHeading eyebrow="02 · Architecture" title="How BLITZ works">
              A deployment follows a predictable pipeline. The host does the
              expensive work; each target receives only the bundle and process
              configuration it needs.
            </SectionHeading>

            <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
              {[
                {
                  icon: Network,
                  step: "01",
                  title: "Discover",
                  copy: "Find watchdogs advertising themselves on the local network.",
                },
                {
                  icon: Package,
                  step: "02",
                  title: "Build",
                  copy: "Create one bundle for each unique target architecture.",
                },
                {
                  icon: Server,
                  step: "03",
                  title: "Sync",
                  copy: "Transfer the appropriate bundle and optional dependencies.",
                },
                {
                  icon: Rocket,
                  step: "04",
                  title: "Assign",
                  copy: "Apply config and a balanced, typed process plan to the fleet.",
                },
              ].map((item) => (
                <article
                  key={item.step}
                  className="group rounded-lg border border-[#282828] bg-[#0a0a0a] p-6 transition-colors hover:border-[#3b3b3b]"
                >
                  <div className="flex items-start justify-between">
                    <item.icon className="size-5 text-[#8097fa]" />
                    <span className="font-mono text-[11px] text-[#515151]">
                      {item.step}
                    </span>
                  </div>
                  <h3 className="mt-8 font-medium text-[#ebebeb]">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-[#7d7d7d]">
                    {item.copy}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <section
            id="process-plans"
            className="scroll-mt-24 border-b border-[#222] py-20 max-sm:py-14"
          >
            <SectionHeading
              eyebrow="03 · Process plans"
              title="Describe the work, not the machines"
            >
              Give each process a relative weight, add the instances you need,
              and let BLITZ balance them. Pin only the work that must run on a
              specific target.
            </SectionHeading>

            <CodeBlock label="backend/deploy.py">{`from backend.deployment.processes import ProcessPlan, WeightedProcess

class ProcessType(WeightedProcess):
    VISION = "vision", 1.0
    MOTION = "motion", 0.6

def pi_name_to_process_types(
    pi_names: list[str],
) -> dict[str, list[ProcessType]]:
    return (
        ProcessPlan[ProcessType]()
        .add(ProcessType.VISION, count=2)
        .add(ProcessType.MOTION)
        .pin(ProcessType.VISION, "vision-left")
        .assign(pi_names)
    )`}</CodeBlock>

            <div className="mt-7 grid grid-cols-3 gap-3 max-sm:grid-cols-1">
              {[
                [".add(process)", "Add one or more desired process instances."],
                [
                  ".pin(process, name)",
                  "Create work that must run on a named target.",
                ],
                [
                  ".assign(pi_names)",
                  "Return the final host-to-process mapping.",
                ],
              ].map(([title, copy]) => (
                <div
                  key={title}
                  className="rounded-lg border border-[#252525] bg-[#090909] p-4"
                >
                  <code className="font-mono text-xs text-[#9badff]">
                    {title}
                  </code>
                  <p className="mt-2 text-xs leading-5 text-[#777]">{copy}</p>
                </div>
              ))}
            </div>
          </section>

          <section
            id="modules"
            className="scroll-mt-24 border-b border-[#222] py-20 max-sm:py-14"
          >
            <SectionHeading
              eyebrow="04 · Modules"
              title="Register runnable code"
            >
              Modules tell BLITZ what to package and how a runnable maps back to
              your process plan. Python, C++, Rust, generated code, and C++
              libraries use the same deployment pipeline.
            </SectionHeading>

            <CodeBlock label="backend/deploy.py">{`from backend.deployment.module.supported import SupportedModules
from backend.deployment.network_api.utils import FolderPath

def get_modules() -> list[SupportedModules._Generic]:
    return [
        SupportedModules.PythonModule(
            name="vision",
            extra_run_args=[],
            equivalent_run_definition=ProcessType.VISION,
            module_folder_path=FolderPath("backend/python/vision"),
        ),
    ]`}</CodeBlock>

            <div className="mt-7 overflow-hidden rounded-lg border border-[#282828]">
              {[
                ["PythonModule", "Copy and run a Python module"],
                ["CPPRunnableModule", "Compile and run a C++ executable"],
                ["RustModule", "Compile and run a Rust executable"],
                ["GeneratedModule", "Ship generated artifacts"],
                ["CPPLibraryModule", "Compile and link a C++ library"],
              ].map(([name, detail]) => (
                <div
                  key={name}
                  className="flex items-center gap-4 border-b border-[#252525] bg-[#090909] px-5 py-3.5 last:border-b-0 max-sm:flex-col max-sm:items-start max-sm:gap-1"
                >
                  <code className="w-44 shrink-0 font-mono text-xs text-[#b8c3f5]">
                    {name}
                  </code>
                  <span className="text-sm text-[#767676]">{detail}</span>
                </div>
              ))}
            </div>
          </section>

          <section id="deploy" className="scroll-mt-24 pt-20 max-sm:pt-14">
            <SectionHeading eyebrow="05 · Deploy" title="Ship to the fleet">
              Choose the command that matches your setup. BLITZ discovers the
              available targets at deploy time and applies the plan returned by
              your two public deployment hooks.
            </SectionHeading>

            <div className="space-y-4">
              <div>
                <p className="mb-2 text-sm font-medium text-[#bdbdbd]">
                  Standard project
                </p>
                <CodeBlock>make deploy</CodeBlock>
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-[#bdbdbd]">
                  WPILib project
                </p>
                <CodeBlock>
                  ./gradlew --console=plain --quiet deployBlitz
                </CodeBlock>
              </div>
            </div>

            <div className="mt-8 rounded-lg border border-[#293252] bg-[#0e1220] p-6">
              <h3 className="flex items-center gap-2.5 font-medium text-[#e5e9ff]">
                <Code2 className="size-4 text-[#8299ff]" />
                Keep these hooks public
              </h3>
              <p className="mt-2 text-sm leading-6 text-[#8d94ac]">
                BLITZ expects{" "}
                <code className="font-mono text-[#c8d0f1]">get_modules()</code>{" "}
                and{" "}
                <code className="font-mono text-[#c8d0f1]">
                  pi_name_to_process_types()
                </code>{" "}
                in{" "}
                <code className="font-mono text-[#c8d0f1]">
                  backend/deploy.py
                </code>
                . They are the stable boundary between your project and the
                deployment engine.
              </p>
            </div>

            <div className="mt-16 flex items-center justify-between border-t border-[#242424] pt-8">
              <Link
                href="/"
                className="text-sm text-[#828282] transition-colors hover:text-white"
              >
                ← Back to home
              </Link>
              <a
                href={githubUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 text-sm font-medium text-[#aab8f5] transition-colors hover:text-white"
              >
                Explore the repository
                <ArrowRight className="size-3.5" />
              </a>
            </div>
          </section>
        </main>

        <aside className="pt-20 max-xl:hidden">
          <div className="sticky top-28 border-l border-[#262626] pl-5">
            <p className="mb-4 text-xs font-medium text-[#b3b3b3]">
              On this page
            </p>
            <nav aria-label="On this page" className="space-y-3">
              {navigation.slice(1).map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="block text-xs text-[#666] transition-colors hover:text-[#c9c9c9]"
                >
                  {item.label}
                </a>
              ))}
            </nav>
          </div>
        </aside>
      </div>
    </div>
  );
}
