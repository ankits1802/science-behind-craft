"use client";

import { useState } from "react";

import { Demo, Grid, Section } from "@/app/design/DesignParts";
import { Field, Select, TextArea, TextInput } from "@/components/FormControls";
import { SearchInput } from "@/components/SearchInput";
import { OtpCodeInput } from "@/components/ui/OtpCodeInput";
import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { Toggle } from "@/components/ui/Toggle";

const LANGUAGES = [
  ["en", "English"],
  ["hi", "हिन्दी · Hindi"],
  ["bn", "বাংলা · Bengali"],
  ["gu", "ગુજરાતી · Gujarati"],
  ["ta", "தமிழ் · Tamil"],
  ["kn", "ಕನ್ನಡ · Kannada"],
  ["ml", "മലയാളം · Malayalam"],
  ["te", "తెలుగు · Telugu"],
  ["mr", "मराठी · Marathi"],
  ["ur", "اردو · Urdu"]
];

export function FormsSection() {
  const [query, setQuery] = useState("lost wax");
  const [code, setCode] = useState("482");
  const [depth, setDepth] = useState("standard");
  const [arrange, setArrange] = useState("family");
  const [motion, setMotion] = useState(false);
  const [larger, setLarger] = useState(true);
  const [language, setLanguage] = useState("hi");
  return (
    <Section id="fields" title="Fields and choices" lede="Label above in sentence case, 16px text so phones do not zoom, focus as a ring and an indigo edge, errors in words with an icon.">
      <Demo caption="Inputs" raised>
        <div className="grid gap-5 md:grid-cols-3">
          <Field label="Name" hint="As it should appear on your account.">
            <TextInput placeholder="Your full name" />
          </Field>
          <Field label="Institution" hint="Focused.">
            <TextInput defaultValue="IIT Kharagpur" data-focus="" />
          </Field>
          <Field label="Email" error="Enter an email address with a domain, like name@iitkgp.ac.in." required>
            <TextInput defaultValue="ananya@" />
          </Field>
          <Field label="Role" hint="Set by your administrator.">
            <TextInput defaultValue="Researcher" disabled />
          </Field>
          <div className="md:col-span-2">
            <Field label="Question">
              <TextArea defaultValue="How does indigo turn blue on Kutch Ajrakh cloth?" />
            </Field>
          </div>
        </div>
      </Demo>
      <Demo caption="Search">
        <div className="max-w-[40rem]">
          <SearchInput value={query} onChange={setQuery} placeholder="Search crafts, places and the science behind them" ariaLabel="Search crafts, places and the science behind them" shortcut />
        </div>
      </Demo>
      <Grid>
        <Demo caption="The six-box code" raised>
          <OtpCodeInput label="Sign-in code" value={code} onChange={setCode} hint="Six digits from your authenticator app." />
          <div className="mt-6">
            <OtpCodeInput label="Disabled" value="" onChange={() => undefined} disabled />
          </div>
        </Demo>
        <Demo caption="Code with an error" raised>
          <OtpCodeInput label="Sign-in code" value="482917" onChange={() => undefined} error hint="That code did not match. Codes change every 30 seconds." />
        </Demo>
      </Grid>
      <Grid>
        <Demo caption="Switches" raised>
          <Toggle label="Reduce motion" description="Animations jump to their end state." checked={motion} onChange={setMotion} />
          <Toggle label="Larger text" description="Everything grows by an eighth." checked={larger} onChange={setLarger} />
          <Toggle label="Weekly digest" checked busy busyLabel="Saving" />
          <Toggle label="Voice answers" description="Turned on by your administrator." disabled />
        </Demo>
        <Demo caption="Segmented choice and select" raised>
          <SegmentedChoice label="Answer depth" value={depth} onChange={setDepth} options={[{ value: "short", label: "Short" }, { value: "standard", label: "Standard" }, { value: "expert", label: "Expert" }]} />
          <div className="mt-4">
            <SegmentedChoice label="Arrange by" value={arrange} onChange={setArrange} options={[{ value: "family", label: "Family" }, { value: "place", label: "Place" }, { value: "science", label: "Science", disabled: true, reason: "Choose a family first" }]} />
          </div>
          <div className="mt-6 max-w-xs">
            <Field label="Answer language">
              <Select value={language} onChange={(event) => setLanguage(event.target.value)} searchable>
                {LANGUAGES.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
        </Demo>
      </Grid>
    </Section>
  );
}
