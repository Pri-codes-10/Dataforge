import { createFileRoute } from "@tanstack/react-router";
import { Dashboard } from "@/components/sutra/dashboard";

// No head() here: the home route inherits title/description/og/twitter from
// __root.tsx, and ships no og:image so serve-time hosting can inject the
// project's social preview (explicit og:image or latest screenshot).
export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "Dashboard — SUTRA" }, { name: "description", content: "Speak naturally while SUTRA manages multilingual tasks and changing constraints." }, { property: "og:title", content: "SUTRA Voice Dashboard" }, { property: "og:description", content: "Real-time multilingual voice task execution." }, { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" }] }),
  component: Index,
});

// IMPORTANT: Replace this placeholder. See ./README.md for routing conventions.
function Index() { return <Dashboard />; }
