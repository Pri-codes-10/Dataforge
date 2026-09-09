import { Link, useRouterState } from "@tanstack/react-router";
import {
  Bell,
  CheckCircle2,
  History,
  LayoutDashboard,
  Menu,
  MessageSquare,
  MessageSquareText,
  Mic2,
  Moon,
  Settings,
  Sun,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useRecentConversations } from "@/hooks/useConversations";
import logo from "@/assets/logo.ico";

const nav = [
  { label: "Dashboard", to: "/" as const, icon: LayoutDashboard },
  { label: "Conversations", to: "/conversations" as const, icon: MessageSquareText },
  { label: "Task History", to: "/tasks" as const, icon: History },
  { label: "Settings", to: "/settings" as const, icon: Settings },
];

// ---------------------------------------------------------------------------
// Theme Toggle
// ---------------------------------------------------------------------------

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const saved = window.localStorage.getItem("sutra-theme");
    const next = saved === "dark";
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
  }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    window.localStorage.setItem("sutra-theme", next ? "dark" : "light");
  };
  return (
    <Button
      variant="soft"
      size={compact ? "icon" : "sm"}
      onClick={toggle}
      aria-label="Toggle theme"
      title="Toggle theme"
    >
      {dark ? <Sun /> : <Moon />}
      {!compact && <span>{dark ? "Light" : "Dark"}</span>}
    </Button>
  );
}

// ---------------------------------------------------------------------------
// Brand
// ---------------------------------------------------------------------------

function Brand() {
  return (
    <Link to="/" className="group block px-4 pt-5">
      <div className="relative grid size-20 place-items-center overflow-hidden rounded-3xl border border-cyan/40">
        <img src={logo} alt="SUTRA Logo" width={100} height={100} className="object-contain" /> 
      </div>
      <div className="mt-3 text-xl font-extrabold tracking-tight">SUTRA</div>
      <p className="max-w-44 text-xs leading-snug text-muted-foreground">
        The conversation never loses the thread.
      </p>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Sidebar Content
// ---------------------------------------------------------------------------

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const { recentGroups } = useRecentConversations();
  return (
    <>
      <Brand />
      <nav className="mt-7 px-3" aria-label="Primary navigation">
        {nav.map((item) => {
          const active =
            item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={cn(
                "mb-1 flex items-center gap-3 border-b border-cyan/25 px-3 py-3 text-sm font-bold uppercase text-cyan transition-colors",
                active && "rounded-lg border-transparent bg-cyan-soft text-foreground ring-1 ring-cyan/30",
              )}
            >
              <item.icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Recent conversation history */}
      <div className="mt-6 flex flex-1 flex-col overflow-y-auto px-3">
        <div className="flex items-center justify-between px-2 pb-2 text-[10px] font-extrabold uppercase tracking-wider text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <History className="size-3.5 text-cyan" />
            History
          </span>
          <Link
            to="/conversations"
            onClick={onNavigate}
            className="text-[10px] font-semibold text-cyan hover:underline"
          >
            All
          </Link>
        </div>

        <div className="space-y-4">
          {recentGroups.map(({ group, items }) => (
            <div key={group} className="space-y-1">
              <div className="flex items-center gap-2 px-2 py-1">
                <span className="size-1 rounded-full bg-cyan/70" />
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-muted-foreground/80">
                  {group}
                </span>
                <div className="h-px flex-1 bg-border/40" />
              </div>

              <div className="space-y-0.5">
                {items.map((item) => {
                  const isActive = pathname === `/conversations/${item.id}`;
                  return (
                    <Link
                      key={item.id}
                      to="/conversations/$conversationId"
                      params={{ conversationId: item.id }}
                      onClick={onNavigate}
                      title={item.title}
                      className={cn(
                        "group flex items-center justify-between gap-2 rounded-xl px-2.5 py-2 text-xs transition-all duration-150",
                        isActive
                          ? "bg-cyan-soft font-bold text-cyan ring-1 ring-cyan/30"
                          : "text-muted-foreground hover:bg-cyan-soft/40 hover:text-foreground",
                      )}
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <MessageSquare className="size-3.5 shrink-0 text-cyan/70 transition-colors group-hover:text-cyan" />
                        <span className="truncate text-[12px]">{item.title}</span>
                      </div>
                      <span className="shrink-0 text-[10px] text-muted-foreground/60 transition-colors group-hover:text-muted-foreground">
                        {item.time}
                      </span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-auto space-y-3 border-t border-cyan/20 p-4">
        <ThemeToggle />
        <div className="flex items-center gap-2">
          <div className="grid size-8 place-items-center rounded-full bg-cyan text-xs font-extrabold text-primary-foreground">
            A
          </div>
          <div>
            <p className="text-xs font-bold">Aarav</p>
            <p className="flex items-center gap-1 text-[10px] text-success">
              <span className="size-1.5 rounded-full bg-success" />
              Connected
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Top Header
// ---------------------------------------------------------------------------

export function TopHeader({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="flex h-14 items-center justify-between rounded-2xl border border-cyan/45 bg-card/80 px-3 backdrop-blur-md sm:px-5">
      <div className="flex items-center gap-2.5">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={onMenu}
          aria-label="Open navigation"
        >
          <Menu />
        </Button>
        <Link to="/" className="text-sm font-extrabold lg:hidden">
          SUTRA
        </Link>
        <span className="hidden text-sm font-extrabold sm:inline">Interpreter Console</span>
        <span className="flex items-center gap-1.5 rounded-full bg-cyan-soft px-2.5 py-1 text-[11px] font-bold text-cyan">
          <span className="live-pulse size-1.5 rounded-full bg-cyan" />
          Rime is ready
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Notifications"
          title="Notifications"
          className="relative text-primary"
        >
          <Bell />
          <span className="absolute right-2 top-1.5 size-2 rounded-full bg-orange" />
        </Button>
        <ThemeToggle compact />
        <div className="grid size-9 place-items-center rounded-full bg-cyan text-sm font-extrabold text-primary-foreground">
          A
        </div>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// App Shell
// ---------------------------------------------------------------------------

export function AppShell({ children }: { children: ReactNode }) {
  const [drawer, setDrawer] = useState(false);
  return (
    <div className="min-h-dvh bg-background text-foreground">
      {/* Background gradient */}
      <div className="fixed inset-0 -z-0 bg-[radial-gradient(circle_at_30%_0%,var(--cyan-soft),transparent_34%),radial-gradient(circle_at_90%_95%,var(--purple-soft),transparent_25%)] opacity-55" />

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col rounded-r-3xl border-r border-cyan bg-card/90 backdrop-blur-md lg:flex">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            className="absolute inset-0 bg-foreground/20"
            onClick={() => setDrawer(false)}
            aria-label="Close navigation backdrop"
          />
          <aside className="relative flex h-full w-72 flex-col rounded-r-3xl border-r border-cyan bg-card shadow-xl">
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-3 top-3"
              onClick={() => setDrawer(false)}
              aria-label="Close navigation"
            >
              <X />
            </Button>
            <SidebarContent onNavigate={() => setDrawer(false)} />
          </aside>
        </div>
      )}

      {/* Main content */}
      <main className="relative z-10 min-w-0 p-3 lg:ml-60 lg:p-5">
        <TopHeader onMenu={() => setDrawer(true)} />
        <div className="mx-auto max-w-[1500px] py-4">{children}</div>
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared Components
// ---------------------------------------------------------------------------

export function PageHeading({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl font-extrabold">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "Completed"
      ? "text-success bg-success/10"
      : status === "Running"
        ? "text-orange bg-orange/10"
        : status === "Failed" || status === "Stale"
          ? "text-destructive bg-destructive/10"
          : "text-muted-foreground bg-muted";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold",
        tone,
      )}
    >
      {status === "Completed" ? (
        <CheckCircle2 className="size-3" />
      ) : (
        <span className={cn("size-1.5 rounded-full bg-current", status === "Running" && "live-pulse")} />
      )}
      {status}
    </span>
  );
}