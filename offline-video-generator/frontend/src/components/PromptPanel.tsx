import { Dices, Play } from "lucide-react";

import type { GenerationRequest, Preset } from "../api/types";

interface PromptPanelProps {
  request: GenerationRequest;
  presets: Preset[];
  disabled: boolean;
  onChange: (patch: Partial<GenerationRequest>) => void;
  onGenerate: () => void;
  onRandomSeed: () => void;
  onApplyPreset: (preset: Preset) => void;
}

export function PromptPanel({
  request,
  presets,
  disabled,
  onChange,
  onGenerate,
  onRandomSeed,
  onApplyPreset
}: PromptPanelProps) {
  return (
    <section className="panel promptPanel">
      <div className="panelHeader">
        <h2>Prompt</h2>
        <span className="runtimePill">{request.runtime === "mock" ? "Mock" : "Local"}</span>
      </div>

      <label className="field">
        <span>Prompt</span>
        <textarea
          value={request.prompt}
          onChange={(event) => onChange({ prompt: event.target.value })}
          rows={7}
        />
      </label>

      <label className="field">
        <span>Negative</span>
        <textarea
          value={request.negative_prompt}
          onChange={(event) => onChange({ negative_prompt: event.target.value })}
          rows={3}
        />
      </label>

      <div className="fieldGrid two">
        <label className="field">
          <span>Preset</span>
          <select
            value={request.preset}
            onChange={(event) => {
              const preset = presets.find((item) => item.name === event.target.value);
              if (preset) onApplyPreset(preset);
            }}
          >
            <option value={request.preset}>{request.preset}</option>
            {presets.map((preset) => (
              <option key={preset.id} value={preset.name}>
                {preset.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Runtime</span>
          <select
            value={request.runtime}
            onChange={(event) => onChange({ runtime: event.target.value as GenerationRequest["runtime"] })}
          >
            <option value="mock">mock</option>
            <option value="hunyuan_original">hunyuan original</option>
            <option value="hunyuan_15">hunyuan 1.5</option>
          </select>
        </label>
      </div>

      <div className="actionRow">
        <button className="primaryButton" onClick={onGenerate} disabled={disabled || request.prompt.trim().length === 0}>
          <Play size={17} />
          <span>Generate</span>
        </button>
        <button className="iconTextButton" onClick={onRandomSeed} title="Randomize seed">
          <Dices size={17} />
          <span>Seed</span>
        </button>
      </div>
    </section>
  );
}
