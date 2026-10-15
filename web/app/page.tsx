"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  useEffect(() => {
    api.settings()
      .then((settings) => router.replace(settings.onboarding_complete ? "/dashboard" : "/onboarding"))
      .catch(() => router.replace("/dashboard"));
  }, [router]);
  return <div className="content"><div className="loading">Opening HandScript Studio…</div></div>;
}
