"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Icon } from "./icons";

const ITEMS = [
  ["dashboard", "Dashboard", "/dashboard"],
  ["documents", "Documents", "/documents"],
  ["templates", "Templates", "/templates"],
  ["handwriting", "Handwriting", "/handwriting"],
  ["batch", "Batch Generator", "/batch"],
  ["exports", "Exports", "/exports"],
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("hs-collapsed") === "1";
    const theme = localStorage.getItem("hs-theme");
    setCollapsed(stored);
    setDark(theme === "dark");
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey)) return;
      const index = Number(event.key) - 1;
      if (index >= 0 && index < ITEMS.length) {
        event.preventDefault();
        router.push(ITEMS[index][2]);
      }
      if (event.key.toLowerCase() === "b") {
        event.preventDefault();
        setCollapsed((value) => {
          localStorage.setItem("hs-collapsed", value ? "0" : "1");
          return !value;
        });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  function toggleTheme() {
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("hs-theme", next);
    setDark(!dark);
  }

  const section = "/" + (pathname.split("/")[1] || "dashboard");

  return (
    <div className="shell">
      <aside className={collapsed ? "sidebar collapsed" : "sidebar"}>
        <div className="brand">
          <div className="brand-mark"><Icon name="handwriting" size={16} /></div>
          <div className="brand-copy">
            <strong>HandScript</strong>
            <span>Studio</span>
          </div>
        </div>
        <nav className="nav-group">
          {ITEMS.map(([icon, label, href]) => (
            <Link key={href} href={href} className={section === href ? "nav-item active" : "nav-item"}>
              <Icon name={icon} />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
        <div className="spacer" />
        <Link href="/settings" className={section === "/settings" ? "nav-item active" : "nav-item"}>
          <Icon name="settings" />
          <span>Settings</span>
        </Link>
      </aside>
      <div className="main">
        <div className="topbar">
          <button className="icon-btn" onClick={() => {
            setCollapsed((value) => {
              localStorage.setItem("hs-collapsed", value ? "0" : "1");
              return !value;
            });
          }} aria-label="Collapse sidebar"><Icon name="sidebar" /></button>
          <div className="grow" />
          <button className="icon-btn" onClick={toggleTheme} aria-label="Toggle theme">
            <Icon name={dark ? "sun" : "moon"} />
          </button>
        </div>
        <div className={pathname.includes("/documents/") || pathname.includes("/templates/") ? "content wide" : "content"}>
          {children}
        </div>
      </div>
    </div>
  );
}
