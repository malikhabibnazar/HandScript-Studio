"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Icon } from "@/components/icons";

const STEPS = [
  ["Welcome to HandScript Studio", "Generate printable cards and envelopes from handwriting styles. This setup takes a minute."],
  ["Name your workspace", "Profiles, templates and generated files are stored with this studio."],
  ["Choose a starting profile", "You can import handwriting samples after setup. A sample profile is already ready to use."],
  ["Choose a starting template", "Begin with a 4×6 card or a #10 envelope. Layouts stay editable."],
  ["You're ready", "Open the dashboard to edit a document or generate a batch from a CSV."],
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [workspace, setWorkspace] = useState("HandScript");
  const [kind, setKind] = useState("4×6 Card");

  useEffect(() => {
    api.settings().then((settings) => {
      if (settings.onboarding_complete) router.replace("/dashboard");
      setWorkspace(settings.workspace);
    }).catch(() => undefined);
  }, [router]);

  async function finish() {
    await api.saveSettings({ workspace, onboarding_complete: true });
    router.replace("/dashboard");
  }

  return (
    <div className="onboarding-wrap">
      <div className="onboard-card">
        <div className="dots">{STEPS.map((_, index) => <i key={index} className={index === step ? "on" : ""} />)}</div>
        <div className="icon-bubble" style={{ marginBottom: 14 }}><Icon name="handwriting" /></div>
        <h1 style={{ fontSize: 22, marginBottom: 8 }}>{STEPS[step][0]}</h1>
        <p className="secondary" style={{ lineHeight: 1.5, marginBottom: 18 }}>{STEPS[step][1]}</p>
        {step === 1 ? (
          <div className="field"><label>Workspace name</label><input value={workspace} onChange={(event) => setWorkspace(event.target.value)} /></div>
        ) : null}
        {step === 3 ? (
          <div className="row">
            {["4×6 Card", "#10 Envelope"].map((item) => (
              <button key={item} className={kind === item ? "option on" : "option"} onClick={() => setKind(item)}>{item}</button>
            ))}
          </div>
        ) : null}
        <div className="row" style={{ marginTop: 22, justifyContent: "space-between" }}>
          <button className="btn ghost" onClick={finish}>Skip</button>
          <div className="row">
            {step > 0 ? <button className="btn secondary" onClick={() => setStep((value) => value - 1)}>Back</button> : null}
            {step < STEPS.length - 1
              ? <button className="btn primary" onClick={() => setStep((value) => value + 1)}>Continue</button>
              : <button className="btn primary" onClick={finish}>Go to dashboard</button>}
          </div>
        </div>
      </div>
    </div>
  );
}
