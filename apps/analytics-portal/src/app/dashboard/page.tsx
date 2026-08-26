import { redirect } from "next/navigation";

// The Executive Overview lives at "/" — this page and Home rendered the same
// executive KPIs and search panel twice under two nav items, so the duplicate
// route now just preserves old bookmarks.
export default function DashboardPage() {
  redirect("/");
}
