"use client";

import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  FileUp,
  LogOut,
  Plus,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const sections = [
  "Founders",
  "Founder Video",
  "Company",
  "Progress",
  "Idea",
  "Equity",
  "Curious",
  "Batch Preference",
] as const;

function Field({
  label,
  hint,
  required = false,
  children,
}: Readonly<{
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}>) {
  return (
    <div className="space-y-2.5">
      <label className="block text-[15px] leading-6 font-medium text-[#292929]">
        {label}
        {required && <span className="ml-0.5 text-[#e34f2f]">*</span>}
      </label>
      {hint && <p className="-mt-1 text-sm leading-5 text-[#74746d]">{hint}</p>}
      {children}
    </div>
  );
}

function TextInput({
  defaultValue,
  placeholder,
  type = "text",
}: Readonly<{
  defaultValue?: string;
  placeholder?: string;
  type?: string;
}>) {
  return (
    <input
      type={type}
      defaultValue={defaultValue}
      placeholder={placeholder}
      className="h-11 w-full rounded-lg border border-[#d6d6cf] bg-white px-3.5 text-[15px] text-[#242424] shadow-[0_1px_1px_rgba(0,0,0,0.02)] transition outline-none placeholder:text-[#aaa9a1] focus:border-[#ff6a3d] focus:ring-3 focus:ring-[#ff6a3d]/10"
    />
  );
}

function TextArea({
  defaultValue,
  placeholder,
  rows = 4,
}: Readonly<{
  defaultValue?: string;
  placeholder?: string;
  rows?: number;
}>) {
  return (
    <textarea
      defaultValue={defaultValue}
      placeholder={placeholder}
      rows={rows}
      className="w-full resize-y rounded-lg border border-[#d6d6cf] bg-white px-3.5 py-3 text-[15px] leading-6 text-[#242424] shadow-[0_1px_1px_rgba(0,0,0,0.02)] transition outline-none placeholder:text-[#aaa9a1] focus:border-[#ff6a3d] focus:ring-3 focus:ring-[#ff6a3d]/10"
    />
  );
}

function Choice({
  name,
  first = "Yes",
  second = "No",
  selected = second,
}: Readonly<{
  name: string;
  first?: string;
  second?: string;
  selected?: string;
}>) {
  return (
    <div className="flex flex-wrap gap-3">
      {[first, second].map((option) => (
        <label
          key={option}
          className="flex min-w-[100px] cursor-pointer items-center gap-2.5 rounded-lg border border-[#d6d6cf] bg-white px-3.5 py-2.5 text-sm font-medium transition hover:border-[#a9a99f] has-checked:border-[#ff6a3d] has-checked:bg-[#fff7f3]"
        >
          <input
            type="radio"
            name={name}
            value={option}
            defaultChecked={option === selected}
            className="size-4 accent-[#f2653d]"
          />
          {option}
        </label>
      ))}
    </div>
  );
}

function UploadArea({ label }: Readonly<{ label: string }>) {
  const [fileName, setFileName] = useState("");

  return (
    <label className="group flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-[#c9c9c1] bg-[#fafaf7] px-6 text-center transition hover:border-[#ff6a3d] hover:bg-[#fff8f5]">
      <input
        type="file"
        className="sr-only"
        onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")}
      />
      <span className="mb-2 flex size-9 items-center justify-center rounded-full bg-white text-[#6f6f68] shadow-sm ring-1 ring-[#deded7] transition group-hover:text-[#f2653d]">
        <FileUp className="size-4" />
      </span>
      <span className="text-sm font-medium text-[#33332f]">
        {fileName || label}
      </span>
      <span className="mt-1 text-xs text-[#85857e]">
        {fileName ? "Click to replace" : "Drop here or browse"}
      </span>
    </label>
  );
}

function FormSection({
  id,
  title,
  description,
  children,
}: Readonly<{
  id: string;
  title: string;
  description?: string;
  children: React.ReactNode;
}>) {
  return (
    <section
      id={id}
      className="scroll-mt-24 rounded-2xl border border-[#deded7] bg-[#fbfbf8] px-7 py-7 shadow-[0_1px_2px_rgba(0,0,0,0.03)] max-sm:px-5"
    >
      <div className="mb-7 border-b border-[#e4e4dd] pb-5">
        <h2 className="text-[23px] leading-7 font-semibold tracking-[-0.025em] text-[#20201e]">
          {title}
        </h2>
        {description && (
          <p className="mt-1.5 max-w-2xl text-sm leading-6 text-[#77776f]">
            {description}
          </p>
        )}
      </div>
      <div className="space-y-7">{children}</div>
    </section>
  );
}

function FounderCard({
  name,
  removable = false,
}: Readonly<{
  name: string;
  removable?: boolean;
}>) {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .join("");

  return (
    <div className="flex items-center gap-4 rounded-xl border border-[#dcdcd5] bg-white p-4">
      <div className="flex size-11 shrink-0 items-center justify-center rounded-full bg-[#1f1f1d] text-sm font-semibold text-white">
        {initials}
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-[#292927]">{name}</p>
        <p className="mt-0.5 flex items-center gap-1.5 text-sm text-[#5f765a]">
          <CheckCircle2 className="size-3.5" />
          Profile complete
        </p>
      </div>
      <button
        type="button"
        className="flex items-center gap-1.5 text-sm font-medium text-[#5d5d57] transition hover:text-black"
      >
        {removable ? "Remove" : "Edit profile"}
        {!removable && <ArrowRight className="size-3.5" />}
      </button>
    </div>
  );
}

export default function ApplicationPage() {
  const [saveState, setSaveState] = useState<"idle" | "saved">("idle");

  function saveApplication() {
    setSaveState("saved");
    window.setTimeout(() => setSaveState("idle"), 2200);
  }

  return (
    <div className="min-h-screen bg-[#f2f2ed] text-[#252522]">
      <header className="sticky top-0 z-50 border-b border-[#deded7] bg-[#fbfbf8]/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1240px] items-center px-6 max-sm:px-4">
          <Link
            href="/"
            className="flex items-center gap-2.5 font-semibold tracking-[-0.02em]"
          >
            <span className="flex size-7 items-center justify-center rounded-sm bg-[#ff5a1f] text-sm font-bold text-white">
              Y
            </span>
            <span className="max-sm:hidden">Y Combinator</span>
          </Link>

          <div className="ml-auto flex items-center gap-5 text-sm text-[#5d5d57]">
            <span className="font-medium text-[#292927] max-sm:hidden">
              Adam Xu
            </span>
            <button
              type="button"
              aria-label="Settings"
              className="transition hover:text-black"
            >
              <Settings className="size-[18px]" />
            </button>
            <button
              type="button"
              className="flex items-center gap-1.5 transition hover:text-black"
            >
              <LogOut className="size-[17px]" />
              <span className="max-sm:hidden">Log out</span>
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1180px] grid-cols-[220px_minmax(0,1fr)] gap-10 px-6 py-9 max-lg:grid-cols-1 max-lg:gap-6 max-sm:px-4 max-sm:py-6">
        <aside className="max-lg:hidden">
          <div className="sticky top-24">
            <Link
              href="/"
              className="mb-7 flex items-center gap-1.5 text-sm font-medium text-[#6f6f68] transition hover:text-black"
            >
              <ChevronLeft className="size-4" />
              Back
            </Link>

            <nav aria-label="Application sections">
              <p className="mb-3 px-3 text-[11px] font-semibold tracking-[0.12em] text-[#92928a] uppercase">
                Application
              </p>
              <div className="space-y-1">
                {sections.map((section, index) => {
                  const slug = section.toLowerCase().replaceAll(" ", "-");
                  const isCurrent = index === 0;
                  const needsAttention = section === "Founder Video";

                  return (
                    <a
                      key={section}
                      href={`#${slug}`}
                      className={`flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                        isCurrent
                          ? "bg-white text-[#252522] shadow-sm ring-1 ring-[#dfdfd8]"
                          : "text-[#6d6d66] hover:bg-white/70 hover:text-[#292927]"
                      }`}
                    >
                      {section}
                      {needsAttention ? (
                        <AlertCircle className="size-3.5 text-[#e25b3a]" />
                      ) : index < 1 ? (
                        <CheckCircle2 className="size-3.5 text-[#6e8a68]" />
                      ) : null}
                    </a>
                  );
                })}
              </div>
            </nav>
          </div>
        </aside>

        <main className="min-w-0">
          <div className="mb-8 flex items-end justify-between gap-5">
            <div>
              <Link
                href="/"
                className="mb-5 hidden items-center gap-1 text-sm font-medium text-[#6f6f68] max-lg:flex"
              >
                <ChevronLeft className="size-4" />
                Back
              </Link>
              <p className="mb-2 text-xs font-semibold tracking-[0.12em] text-[#85857e] uppercase">
                Fall 2026
              </p>
              <h1 className="text-[38px] leading-tight font-semibold tracking-[-0.04em] text-[#1d1d1b] max-sm:text-[32px]">
                YC Application
              </h1>
              <p className="mt-2 text-[15px] text-[#707069]">
                Robotify · Last saved just now
              </p>
            </div>
            <div className="rounded-full border border-[#dbdbd3] bg-white px-3 py-1.5 text-xs font-medium text-[#66665f] max-sm:hidden">
              Draft
            </div>
          </div>

          <form
            className="space-y-7"
            onSubmit={(event) => {
              event.preventDefault();
              saveApplication();
            }}
          >
            <FormSection id="founders" title="Founders">
              <div className="grid grid-cols-2 gap-3 max-md:grid-cols-1">
                <FounderCard name="Adam Xu" />
                <FounderCard name="Denis Koterov" removable />
              </div>

              <button
                type="button"
                className="flex items-center gap-2 text-sm font-semibold text-[#e4572e] transition hover:text-[#bd3f1c]"
              >
                <Plus className="size-4" />
                Add a co-founder
              </button>

              <Field label="How long have the founders known one another and how did you meet? Have any of the founders not met in person?">
                <TextArea
                  rows={4}
                  defaultValue="We met at our high school and happened to be the only two people seriously building technical projects there. We have known each other for more than three years and have attended events, built projects, and won hackathons together."
                />
              </Field>

              <Field label="Who writes code, or does other technical work on your product? Was any of it done by a non-founder?">
                <TextArea
                  rows={5}
                  defaultValue="We both write the product. Adam focuses on the web application and developer experience, while Denis focuses on embedded systems, deployment, and process orchestration. BLITZ brings those two domains into one codebase. No non-founder has written the core product."
                />
              </Field>

              <Field label="Are you looking for a cofounder?">
                <Choice name="looking-for-cofounder" selected="No" />
              </Field>
            </FormSection>

            <FormSection
              id="founder-video"
              title="Founder Video"
              description="Record a one-minute video introducing the founders. The file must not exceed 100 MB."
            >
              <UploadArea label="Upload founder video" />
              <div className="flex items-center gap-2 rounded-lg bg-[#fff0eb] px-3.5 py-3 text-sm font-medium text-[#b64120]">
                <AlertCircle className="size-4 shrink-0" />
                Founder video is required before submitting.
              </div>
            </FormSection>

            <FormSection id="company" title="Company">
              <div className="grid grid-cols-2 gap-5 max-md:grid-cols-1">
                <Field label="Company name" required>
                  <TextInput defaultValue="Robotify" />
                </Field>
                <Field
                  label="Describe what your company does"
                  hint="50 characters or fewer"
                  required
                >
                  <TextInput defaultValue="Web framework for consumer robotics code" />
                </Field>
              </div>

              <Field label="Company URL, if any">
                <TextInput placeholder="https://" type="url" />
              </Field>

              <Field
                label="If you have a demo, attach it below."
                hint="Anything that shows how the product works. Limit: 3 minutes / 100 MB."
              >
                <UploadArea label="Upload product demo" />
              </Field>

              <Field label="Please provide a link to the product, if any.">
                <TextInput placeholder="https://" type="url" />
              </Field>

              <Field label="If login credentials are required, enter them here.">
                <TextInput placeholder="username / password" />
              </Field>

              <Field label="What is your company going to make? Please describe your product and what it does or will do.">
                <TextArea
                  rows={12}
                  defaultValue={`We are developers, and we hate dashboards. BLITZ gives robotics teams one AI-native codebase for their application, processors, simulation, and deployment.

Instead of context switching between projects and infrastructure, developers define how their systems run with typed code, then deploy to a robotics computer cluster in one command. There is no manual SSH workflow, no fragile config file, and no separate dashboard that an agent cannot inspect or debug.

Paired with a node-like module system, BLITZ lets developers and coding agents work on the entire robot in one repository, keep full project context, and run natively across different devices.`}
                />
              </Field>

              <Field
                label="Where do you live now, and where would the company be based after YC?"
                hint="Use the format City A, Country A / City B, Country B"
              >
                <TextInput defaultValue="San Francisco Bay Area, USA / San Francisco, USA" />
              </Field>

              <Field label="Explain your decision regarding location.">
                <TextArea
                  rows={4}
                  defaultValue="San Francisco is the center of the startup ecosystem and one of the strongest robotics communities in the world. Both founders already live in the Bay Area, so building the company there is the natural choice."
                />
              </Field>
            </FormSection>

            <FormSection id="progress" title="Progress">
              <Field label="How far along are you?">
                <TextArea
                  rows={6}
                  defaultValue="We have a closed-testing version running the complete deployment pipeline and being used in production by robotics teams. The consumer-facing command interface and plugin system are still in progress. We are also expanding hardware coverage and optimizing the edge runtime."
                />
              </Field>

              <Field label="How long have each of you been working on this? How much of that has been full-time?">
                <TextArea
                  rows={4}
                  defaultValue="Denis began building the original system roughly a year ago and brought Adam into the project about six months ago. Since then, both founders have been working on BLITZ full-time."
                />
              </Field>

              <Field label="What tech stack are you using or planning to use? Include AI models and coding tools.">
                <TextArea
                  rows={5}
                  defaultValue="The deployment and edge runtime are built in typed Python, with native C++ and Rust module support. The product frontend uses Next.js and TypeScript. We use both Claude Code and Codex extensively for codebase-aware engineering."
                />
              </Field>

              <Field label="Are people using your product?">
                <Choice name="people-using-product" selected="Yes" />
              </Field>

              <Field label="How many active users or customers do you have? How many are paying?">
                <TextArea
                  rows={5}
                  defaultValue="Current users are robotics teams self-hosting the open-source project, primarily in the FRC ecosystem. Several teams actively rely on it for their development pipelines. All current users are free."
                />
              </Field>

              <Field label="Do you have revenue?">
                <Choice name="revenue" selected="No" />
              </Field>
            </FormSection>

            <FormSection id="idea" title="Idea">
              <Field label="Why did you pick this idea? How do you know people need it?">
                <TextArea
                  rows={6}
                  defaultValue="We ran into the problem ourselves while building robotics systems. The code was split across web apps, embedded devices, simulation projects, and deployment scripts. Every robotics team we spoke with had a version of the same problem: too much infrastructure work and too little time spent building the robot."
                />
              </Field>
              <Field label="Who are your competitors? What do you understand that they don’t?">
                <TextArea
                  rows={4}
                  placeholder="Describe the alternatives and your insight."
                />
              </Field>
              <Field label="How do or will you make money? How much could you make?">
                <TextArea
                  rows={4}
                  placeholder="Describe your business model."
                />
              </Field>
              <Field label="If you had any other ideas you considered applying with, please list them.">
                <TextArea rows={3} />
              </Field>
            </FormSection>

            <FormSection id="equity" title="Equity">
              <Field label="Have you formed any legal entity yet?">
                <Choice name="legal-entity" selected="No" />
              </Field>
              <Field label="Describe the planned equity ownership breakdown.">
                <TextArea
                  rows={3}
                  defaultValue="Each founder will own 50% of the company."
                />
              </Field>
              <Field label="Have you taken any investment yet?">
                <Choice name="investment" selected="No" />
              </Field>
              <Field label="Are you currently fundraising?">
                <Choice name="fundraising" selected="No" />
              </Field>
            </FormSection>

            <FormSection id="curious" title="Curious">
              <Field label="What convinced you to apply to Y Combinator? Did someone encourage you to apply?">
                <TextArea
                  rows={6}
                  defaultValue="We attended YC Startup School, which made YC feel less like a distant institution and more like a community of builders trying to change the world. We have also attended YC hackathons and met many exceptional founders there."
                />
              </Field>
              <Field label="How did you hear about Y Combinator?">
                <TextArea
                  rows={3}
                  defaultValue="YC is central to the builder community, and Denis grew up around it because his father was part of the W20 batch."
                />
              </Field>
            </FormSection>

            <FormSection id="batch-preference" title="Batch Preference">
              <Field label="What batch do you want to apply for?">
                <Choice
                  name="batch"
                  first="Fall 2026"
                  second="A later batch"
                  selected="Fall 2026"
                />
              </Field>
            </FormSection>

            <div className="sticky bottom-4 z-30 flex items-center gap-3 rounded-2xl border border-[#d6d6cf] bg-[#fbfbf8]/95 p-3 shadow-[0_12px_45px_rgba(30,30,25,0.14)] backdrop-blur max-sm:flex-wrap">
              <Link
                href="/"
                className="flex h-10 items-center gap-1.5 px-3 text-sm font-semibold text-[#5c5c56] transition hover:text-black"
              >
                <ChevronLeft className="size-4" />
                Back
              </Link>
              <span
                className={`ml-auto text-sm font-medium text-[#61725e] transition-opacity ${
                  saveState === "saved" ? "opacity-100" : "opacity-0"
                }`}
                aria-live="polite"
              >
                Changes saved
              </span>
              <button
                type="submit"
                className="h-10 rounded-lg border border-[#d2d2cb] bg-white px-4 text-sm font-semibold transition hover:bg-[#f5f5f0]"
              >
                Save changes
              </button>
              <button
                type="button"
                className="h-10 rounded-lg bg-[#ff5a1f] px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-[#e94d16]"
              >
                Submit application
              </button>
            </div>
          </form>
        </main>
      </div>

      <footer className="mt-14 border-t border-[#deded7] bg-[#fbfbf8]">
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center gap-x-6 gap-y-3 px-6 py-8 text-sm text-[#77776f] max-sm:px-4">
          {["About", "People", "Blog", "Resources", "Legal", "Contact"].map(
            (item) => (
              <a key={item} href="#" className="transition hover:text-black">
                {item}
              </a>
            ),
          )}
          <span className="ml-auto max-sm:w-full">
            Application draft · Fall 2026
          </span>
        </div>
      </footer>
    </div>
  );
}
