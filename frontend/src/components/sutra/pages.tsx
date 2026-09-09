import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Filter,
  Mic2,
  Plus,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { PageHeading, StatusBadge, ThemeToggle } from "./app-shell";
import { useConversations, useConversation } from "@/hooks/useConversations";
import { useTasks, useTaskDetail, taskPipelineEventLabels } from "@/hooks/useTasks";
import { useSettings } from "@/hooks/useSettings";
import { useState } from "react";

// ---------------------------------------------------------------------------
// Conversations Page
// ---------------------------------------------------------------------------

export function ConversationsPage() {
  const { conversations, createConversation } = useConversations();

  return (
    <>
      <PageHeading
        title="Conversations"
        subtitle="Continue where you left off."
        action={
          <Button variant="purple" onClick={() => createConversation()}>
            <Plus />
            New conversation
          </Button>
        }
      />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="Search conversations" />
        </div>
        <Button variant="soft">
          <Filter />
          Filter
        </Button>
        <Button variant="soft">
          <SlidersHorizontal />
          Sort
        </Button>
      </div>
      <div className="overflow-hidden rounded-2xl border border-border bg-card/75 backdrop-blur-md">
        {conversations.map((conversation) => (
          <Link
            key={conversation.id}
            to="/conversations/$conversationId"
            params={{ conversationId: conversation.id }}
            className="grid gap-3 border-b border-border p-5 transition-colors last:border-0 hover:bg-cyan-soft/55 sm:grid-cols-[1fr_auto] sm:items-center"
          >
            <div>
              <h2 className="font-extrabold">{conversation.title}</h2>
              <p className="mt-1 text-sm text-muted-foreground">"{conversation.lastMessage}"</p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs font-bold text-cyan">
                <span>{conversation.languages}</span>
                <span className="text-muted-foreground">·</span>
                <span className="text-muted-foreground">{conversation.time}</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={conversation.status} />
              <ArrowRight className="size-4 text-muted-foreground" />
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Conversation Detail Page
// ---------------------------------------------------------------------------

export function ConversationDetailPage({ conversationId }: { conversationId: string }) {
  const { conversation, messages, sendMessage } = useConversation(conversationId);
  const [inputText, setInputText] = useState("");

  const handleSend = () => {
    if (!inputText.trim()) return;
    sendMessage(inputText.trim());
    setInputText("");
  };

  return (
    <>
      <Link
        to="/conversations"
        className="mb-5 inline-flex items-center gap-2 text-sm font-bold text-muted-foreground"
      >
        <ArrowLeft className="size-4" />
        Conversations
      </Link>
      <PageHeading
        title={conversation?.title ?? "Conversation"}
        subtitle={conversation?.languages ?? "Voice session"}
      />
      <div className="max-w-4xl">
        <section className="rounded-2xl border border-border bg-card/75 p-5">
          <div className="space-y-5">
            {messages.map((msg) => {
              const isUser = msg.role === "user";
              const isInterruption = msg.wasInterruption === true;
              return (
                <div
                  key={msg.id}
                  className={
                    isInterruption
                      ? "max-w-[82%] rounded-2xl rounded-bl-sm border border-orange/35 bg-orange/5 p-4"
                      : isUser
                        ? "max-w-[82%] rounded-2xl rounded-bl-sm bg-cyan-soft p-4"
                        : "ml-auto max-w-[82%] rounded-2xl rounded-br-sm bg-purple-soft p-4"
                  }
                >
                  <p
                    className={`text-xs font-bold ${isInterruption ? "text-orange" : isUser ? "text-cyan" : "text-primary"}`}
                  >
                    {isInterruption
                      ? "You interrupted"
                      : isUser
                        ? `You · ${msg.language ?? conversation?.languages ?? "English"}`
                        : "SUTRA"}
                  </p>
                  <p className="mt-1 text-sm">{msg.content}</p>
                </div>
              );
            })}
          </div>
          <div className="mt-8 flex items-center gap-2 rounded-xl border border-border bg-background p-2">
            <Button variant="purple" size="icon" aria-label="Speak">
              <Mic2 />
            </Button>
            <Input
              className="border-0 shadow-none"
              placeholder="Continue the conversation…"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
            />
          </div>
        </section>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Tasks Page
// ---------------------------------------------------------------------------

export function TasksPage() {
  const { tasks } = useTasks();

  return (
    <>
      <PageHeading title="Task History" subtitle="Track everything SUTRA has executed." />
      <div className="overflow-x-auto rounded-2xl border border-border bg-card/75 backdrop-blur-md">
        <table className="w-full min-w-[760px] text-left">
          <thead className="border-b border-border bg-cyan-soft/45 text-xs uppercase text-muted-foreground">
            <tr>
              {["Task", "Type", "Status", "Language", "Started", "Duration", ""].map((h) => (
                <th key={h} className="px-5 py-4 font-extrabold">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr
                key={task.id}
                className="border-b border-border last:border-0 hover:bg-cyan-soft/35"
              >
                <td className="px-5 py-4 font-extrabold">{task.task}</td>
                <td className="px-5 py-4 text-sm text-muted-foreground">{task.type}</td>
                <td className="px-5 py-4">
                  <StatusBadge status={task.status} />
                </td>
                <td className="px-5 py-4 text-sm">{task.language}</td>
                <td className="px-5 py-4 text-sm text-muted-foreground">{task.started}</td>
                <td className="px-5 py-4 text-sm font-bold">{task.duration}</td>
                <td className="px-5 py-4">
                  <Button variant="ghost" size="icon" asChild>
                    <Link
                      to="/tasks/$taskId"
                      params={{ taskId: task.id }}
                      aria-label={`Open ${task.task}`}
                    >
                      <ArrowRight />
                    </Link>
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Task Detail Page
// ---------------------------------------------------------------------------

export function TaskDetailPage({ taskId }: { taskId: string }) {
  const { tasks } = useTasks();
  const { taskDetail } = useTaskDetail(taskId);

  const item = tasks.find((t) => t.id === taskId) ?? taskDetail;
  const detail = taskDetail;

  const executionRows: [string, string][] = [
    ["Conversation", item?.language ?? "—"],
    ["Tool", detail?.tool ?? "—"],
    ...(Object.entries(detail?.entities ?? {}).map(([k, v]) => [
      k.charAt(0).toUpperCase() + k.slice(1),
      v,
    ]) as [string, string][]),
    ...(Object.entries(detail?.constraints ?? {}).map(([k, v]) => [
      k.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
      String(v),
    ]) as [string, string][]),
    ["Request ID", detail?.requestId ?? "—"],
    ["State version", `v${detail?.stateVersion ?? 1}`],
    ["Execution duration", item?.duration ?? "—"],
    ...(detail?.firstAudioLatencyMs != null
      ? [["First audio latency", `${detail.firstAudioLatencyMs}ms`] as [string, string]]
      : []),
  ];

  return (
    <>
      <Link
        to="/tasks"
        className="mb-5 inline-flex items-center gap-2 text-sm font-bold text-muted-foreground"
      >
        <ArrowLeft className="size-4" />
        Task History
      </Link>
      <PageHeading
        title={`TASK #${item?.id ?? taskId}`}
        subtitle={item?.task ?? "Task"}
        action={<StatusBadge status={item?.status ?? "Completed"} />}
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-border bg-card/75 p-5">
          <h2 className="font-extrabold">Execution details</h2>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            {executionRows.map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs text-muted-foreground">{k}</dt>
                <dd className="mt-1 font-bold">{v}</dd>
              </div>
            ))}
          </dl>
        </section>
        <section className="rounded-2xl border border-border bg-card/75 p-5">
          <h2 className="font-extrabold">Execution timeline</h2>
          <ol className="mt-5 space-y-0">
            {(detail?.timeline ?? []).map((event, i) => (
              <li key={event} className="relative flex gap-3 pb-4 text-sm last:pb-0">
                <span className="z-10 grid size-5 shrink-0 place-items-center rounded-full bg-success/15 text-success">
                  <Check className="size-3" />
                </span>
                {i < (detail?.timeline.length ?? 0) - 1 && (
                  <span className="absolute left-2.5 top-5 h-full w-px bg-border" />
                )}
                <span className="font-bold">
                  {taskPipelineEventLabels[event] ?? event}
                </span>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Settings Page
// ---------------------------------------------------------------------------

function SettingRow({
  label,
  description,
  checked = true,
  onChange,
}: {
  label: string;
  description?: string;
  checked?: boolean;
  onChange?: (val: boolean) => void;
}) {
  const [enabled, setEnabled] = useState(checked);
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-4 last:border-0">
      <div>
        <p className="text-sm font-bold">{label}</p>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      <Switch
        checked={enabled}
        onCheckedChange={(val) => {
          setEnabled(val);
          onChange?.(val);
        }}
      />
    </div>
  );
}

function SettingsSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-border bg-card/75 p-5">
      <h2 className="text-xs font-extrabold uppercase text-cyan">{title}</h2>
      <div className="mt-2">{children}</div>
    </section>
  );
}

export function SettingsPage() {
  const { settings, updateSettings } = useSettings();

  return (
    <>
      <PageHeading
        title="Settings"
        subtitle="Configure how SUTRA understands and responds."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <SettingsSection title="Voice">
          <div className="flex items-center justify-between border-b border-border py-4">
            <div>
              <p className="text-sm font-bold">Voice Engine</p>
              <p className="text-xs text-muted-foreground capitalize">{settings.voice.engine}</p>
            </div>
            <span className="flex items-center gap-1.5 text-xs font-bold text-success">
              <span className="size-2 rounded-full bg-success" />
              Connected
            </span>
          </div>
          <div className="grid gap-3 py-4 sm:grid-cols-2">
            <Select
              defaultValue={settings.voice.accent}
              onValueChange={(val) => updateSettings({ voice: { ...settings.voice, accent: val } })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Voice" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="aria">Aria</SelectItem>
                <SelectItem value="maya">Maya</SelectItem>
              </SelectContent>
            </Select>
            <Select defaultValue="auto">
              <SelectTrigger>
                <SelectValue placeholder="Language" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Auto Detect</SelectItem>
                <SelectItem value="hindi">Hindi</SelectItem>
                <SelectItem value="english">English</SelectItem>
                <SelectItem value="bengali">Bengali</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="pb-3">
            <div className="mb-3 flex justify-between text-sm font-bold">
              <span>Speaking speed</span>
              <span className="text-cyan">{settings.voice.speed.toFixed(1)}×</span>
            </div>
            <Slider
              defaultValue={[settings.voice.speed * 50]}
              max={100}
              step={10}
              onValueChange={(val) => {
                const speed = (val[0] ?? 50) / 50;
                updateSettings({ voice: { ...settings.voice, speed } });
              }}
            />
          </div>
        </SettingsSection>
        <SettingsSection title="Language">
          <div className="py-3">
            <p className="mb-3 text-sm font-bold">Preferred languages</p>
            <div className="flex flex-wrap gap-2">
              {["English", "Hindi", "Bengali", "Sanskrit"].map((l) => (
                <span
                  key={l}
                  className="rounded-lg border border-primary bg-purple-soft px-3 py-1.5 text-xs font-bold"
                >
                  {l}
                </span>
              ))}
            </div>
          </div>
          <SettingRow
            label="Allow code-switching"
            checked={settings.language.autoDetectCodeSwitching}
            onChange={(val) =>
              updateSettings({ language: { ...settings.language, autoDetectCodeSwitching: val } })
            }
          />
          <SettingRow label="Automatic language detection" />
        </SettingsSection>
        <SettingsSection title="Conversation">
          <SettingRow label="Conversation memory" />
          <SettingRow label="Context retention" />
          <SettingRow
            label="Allow interruptions"
            checked={settings.conversation.interruptible}
            onChange={(val) =>
              updateSettings({
                conversation: { ...settings.conversation, interruptible: val },
              })
            }
          />
          <SettingRow label="Automatic task updates" />
        </SettingsSection>
        <SettingsSection title="Task Execution">
          <SettingRow label="Allow tool execution" />
          <SettingRow
            label="Stale result protection"
            description="Reject results from superseded requests"
            checked={settings.conversation.staleResultProtection}
            onChange={(val) =>
              updateSettings({
                conversation: { ...settings.conversation, staleResultProtection: val },
              })
            }
          />
          <SettingRow label="Confirm before destructive actions" />
        </SettingsSection>
        <SettingsSection title="Appearance">
          <div className="flex items-center justify-between py-4">
            <div>
              <p className="text-sm font-bold">Theme</p>
              <p className="text-xs text-muted-foreground">Light is the default</p>
            </div>
            <ThemeToggle />
          </div>
        </SettingsSection>
      </div>
    </>
  );
}