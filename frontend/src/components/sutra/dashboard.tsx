import { Check, Circle, Globe, Mic2, Pause, Square, X, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { VoiceState } from "@/types";
import { useVoiceSession, demoVoiceStates } from "@/hooks/useVoiceSession";
import { useLanguageDetection } from "@/hooks/useLanguageDetection";
import { useTaskPipeline } from "@/hooks/useTaskPipeline";

// ---------------------------------------------------------------------------
// Voice Orb
// ---------------------------------------------------------------------------

export function VoiceOrb({ state }: { state: VoiceState }) {
  const { isActive } = useVoiceSession(state);
  return (
    <div
      className={cn("relative grid size-60 place-items-center sm:size-72", isActive && "orb-breathe")}
      aria-label={`Voice state: ${state}`}
    >
      <div className="orbit-spin absolute inset-0 rounded-full border border-dashed border-cyan/70" />
      <div className="ring-pulse absolute inset-5 rounded-full border border-primary/50" />
      <div className="ring-pulse absolute inset-10 rounded-full border border-orange/45 [animation-delay:1.1s]" />
      <div className="absolute inset-12 rounded-full bg-[conic-gradient(from_20deg,var(--cyan),var(--primary),var(--orange),oklch(0.88_0.18_95),var(--cyan))] blur-sm" />
      <div className="absolute inset-[4.25rem] rounded-full bg-card/30 backdrop-blur-sm" />
      <div className="relative flex h-16 items-end gap-1" aria-hidden="true">
        {[0.45, 0.8, 1, 0.65, 0.92, 0.5, 0.72].map((scale, i) => (
          <span
            key={i}
            className="w-1.5 origin-bottom rounded-full bg-primary-foreground"
            style={{
              height: `${scale * 48}px`,
              animation: isActive
                ? `sutra-wave ${0.65 + i * 0.08}s ease-in-out infinite`
                : undefined,
            }}
          />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Audio Waveform (Rime indicator)
// ---------------------------------------------------------------------------

function AudioWaveform() {
  return (
    <div className="flex h-5 items-center gap-1">
      {[8, 16, 11, 19, 13, 7].map((h, i) => (
        <span
          key={i}
          className="w-1 origin-center rounded-full bg-cyan"
          style={{ height: h, animation: `sutra-wave ${0.55 + i * 0.08}s ease-in-out infinite` }}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Language Detection Panel
// ---------------------------------------------------------------------------

export function LanguagePanel() {
  const { activeLanguages, codeSwitched } = useLanguageDetection();

  return (
    <section className="rounded-2xl border border-cyan/25 bg-card/80 p-4 backdrop-blur-md">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="size-4 text-cyan" />
          <h2 className="font-extrabold">Language Detection</h2>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-bold text-cyan">
          <span className="live-pulse size-2 rounded-full bg-cyan" />
          {codeSwitched ? "Code-Switching" : "Single Language"}
        </span>
      </div>

      {/* Active Languages */}
      <div className="mt-3">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Active Languages
        </p>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {activeLanguages.map((l) => (
            <span
              key={l}
              className="rounded-lg bg-cyan-soft px-2.5 py-1 text-xs font-bold text-cyan"
            >
              {l === "Hindi" ? "हिन्दी (Hindi)" : l}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Task Pipeline Panel
// ---------------------------------------------------------------------------

export function TaskPipeline() {
  const { steps, activeTool, staleExecution, rimeState, isRunning, cancelTask, interruptTask } = useTaskPipeline();
  const rimeStatus = rimeState?.status ?? "idle";

  return (
    <section className="rounded-2xl border border-cyan/25 bg-card/80 p-4 backdrop-blur-md">
      <div className="flex items-center justify-between">
        <h2 className="font-extrabold">Task Pipeline</h2>
        <span className="flex items-center gap-1.5 text-xs font-bold text-orange">
          <span className="live-pulse size-2 rounded-full bg-orange" />
          {isRunning ? "Task Running" : "Cancelled"}
        </span>
      </div>

      {/* Pipeline steps */}
      <div className="mt-4 space-y-2">
        {steps.map((step) => (
          <div key={step.id} className="flex items-center gap-2 text-xs">
            <span
              className={cn(
                "grid size-5 place-items-center rounded-full",
                step.status === "completed"
                  ? "bg-success/15 text-success"
                  : step.status === "running" && isRunning
                    ? "bg-orange/15 text-orange"
                    : "bg-muted text-muted-foreground",
              )}
            >
              {step.status === "completed" ? (
                <Check className="size-3" />
              ) : step.status === "running" ? (
                <span className="live-pulse size-1.5 rounded-full bg-current" />
              ) : (
                <Circle className="size-2" />
              )}
            </span>
            <span className={cn(step.status === "running" && isRunning && "font-extrabold text-orange")}>
              {step.label}
            </span>
          </div>
        ))}
      </div>

      {/* Active tool execution */}
      <div className="mt-4 rounded-xl border border-orange/35 bg-orange/5 p-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-extrabold uppercase text-orange">
              {activeTool?.requestId ? `Request #${activeTool.requestId}` : "Request #0284"} · {activeTool?.isCurrent ? "Current" : "Current"}
            </p>
            <p className="mt-1 text-xs font-bold">
              {activeTool?.toolName || "Flight Search API"}{" "}
              <span className="font-normal text-muted-foreground">· 2.8s</span>
            </p>
          </div>
          <Zap className="size-4 text-orange" />
        </div>
        <div className="mt-2 flex gap-2">
          <Button variant="soft" size="sm" onClick={() => interruptTask()}>
            <Pause />
            Interrupt
          </Button>
          <Button
            variant="soft"
            size="sm"
            className="text-destructive"
            onClick={() => cancelTask()}
          >
            <Square />
            Cancel task
          </Button>
        </div>
      </div>

      {/* Stale request */}
      <div className="mt-2 rounded-xl border border-border bg-muted/45 p-3">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-extrabold uppercase text-muted-foreground">
            {staleExecution?.requestId ? `Request #${staleExecution.requestId}` : "Request #0283"} · Stale
          </span>
          <X className="size-4 text-destructive" />
        </div>
        <p className="mt-1 text-xs font-bold text-destructive">Stale result rejected</p>
      </div>

      {/* Rime status */}
      <div className="mt-4 flex items-center justify-between rounded-xl bg-cyan-soft p-3">
        <div>
          <p className="text-[10px] font-extrabold uppercase text-muted-foreground">Rime</p>
          <p className="text-xs font-bold text-cyan">
            {rimeStatus === "speaking" ? "Speaking" : rimeStatus === "completed" ? "Complete" : "Ready"}
          </p>
        </div>
        {rimeStatus === "speaking" && <AudioWaveform />}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export function Dashboard() {
  const {
    voiceState,
    label,
    isRecording,
    permissionDenied,
    errorMessage,
    lastTranscript,
    lastResponse,
    cycleNextState,
    setState,
    toggleRecording,
    stop,
  } = useVoiceSession();

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_330px]">
      {/* Main voice session panel */}
      <section className="min-h-[660px] rounded-3xl border border-border bg-card/65 p-5 backdrop-blur-md sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-extrabold">Live session</h1>
            <div className="mt-1.5 flex items-center gap-1.5">
              <div className="rounded-lg border border-cyan/30 bg-cyan-soft px-2.5 py-0.5 text-xs font-bold text-cyan">
                English
              </div>
              <span className="text-xs font-bold text-muted-foreground">+</span>
              <div className="rounded-lg border border-cyan/30 bg-cyan-soft px-2.5 py-0.5 text-xs font-bold text-cyan">
                Hindi
              </div>
            </div>
          </div>
        </div>

        <div className="flex min-h-[520px] flex-col items-center justify-center">
          <VoiceOrb state={voiceState} />
          <h2 className="mt-8 text-center text-3xl font-extrabold">How can I Help You?</h2>
          <p className="mt-2 text-sm font-bold text-primary">{label}</p>

          {/* Real Speech Transcription Display */}
          {lastTranscript && (
            <div className="mt-3 max-w-md rounded-xl bg-cyan-soft px-4 py-2 text-center text-xs font-semibold text-cyan">
              "{lastTranscript}"
            </div>
          )}
          {lastResponse && (
            <div className="mt-2 max-w-md rounded-xl bg-card border border-border px-4 py-2 text-center text-xs text-foreground">
              {lastResponse}
            </div>
          )}

          {/* Permission warning */}
          {permissionDenied && (
            <div className="mt-3 max-w-md rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-2.5 text-center text-xs font-semibold text-destructive">
              Microphone access is required. Please allow microphone access in your browser settings.
            </div>
          )}
          {errorMessage && !permissionDenied && (
            <div className="mt-3 max-w-md rounded-xl border border-orange/40 bg-orange/10 px-4 py-2 text-center text-xs font-semibold text-orange">
              {errorMessage}
            </div>
          )}

          {/* Microphone controls */}
          <div className="mt-5 flex items-center gap-3 rounded-full border border-border bg-card/80 p-2">
            <Button
              variant="purple"
              size="round"
              onClick={toggleRecording}
              aria-label={isRecording ? "Stop recording and send" : "Start recording"}
              className={cn(isRecording && "ring-4 ring-primary/40")}
            >
              <Mic2 className={cn("size-5", isRecording && "animate-pulse text-destructive")} />
            </Button>
            <Button
              variant="soft"
              size="round"
              onClick={stop}
              aria-label="Stop voice session"
            >
              <Square />
            </Button>
          </div>

          {/* Demo state selector */}
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {demoVoiceStates.map((s) => (
              <button
                key={s}
                onClick={() => setState(s)}
                className={cn(
                  "rounded-full px-2.5 py-1 text-[10px] font-bold uppercase transition-colors",
                  voiceState === s
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Right-side panels */}
      <aside className="flex flex-col gap-4">
        <LanguagePanel />
        <TaskPipeline />
      </aside>
    </div>
  );
}