import DashboardLayout from "./dashboard-layout";
import { stackServerApp } from "../../stack";

export default async function MainLayout({ children }: { children: React.ReactNode }) {
  // Server-side auth gate: redirect unauthenticated users to Stack handler sign-in
  await stackServerApp.getUser({ or: "redirect", tokenStore: "nextjs-cookie" });
  return <DashboardLayout>{children}</DashboardLayout>;
}

