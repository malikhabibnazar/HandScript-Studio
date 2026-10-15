"use client";

import type { ReactNode } from "react";
import { Shell } from "@/components/shell";

export default function StudioLayout({ children }: { children: ReactNode }) {
  return <Shell>{children}</Shell>;
}
