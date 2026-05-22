import type { GenerationRequest } from "../api/types";

interface SettingsPanelProps {
  request: GenerationRequest;
  onChange: (patch: Partial<GenerationRequest>) => void;
}

const aspectSizes: Record<string, { width: number; height: number }> = {
  "16:9": { width: 1280, height: 720 },
  "9:16": { width: 720, height: 1280 },
  "1:1": { width: 768, height: 768 },
  "4:3": { width: 1024, height: 768 },
  "3:4": { width: 768, height: 1024 },
  "21:9": { width: 1344, height: 576 }
};

export function SettingsPanel({ request, onChange }: SettingsPanelProps) {
  return (
    <section className="panel settingsPanel">
      <div className="panelHeader">
        <h2>Settings</h2>
      </div>

      <div className="segmented">
        {Object.keys(aspectSizes).map((ratio) => (
          <button
            key={ratio}
            className={request.aspect_ratio === ratio ? "active" : ""}
            onClick={() => onChange({ aspect_ratio: ratio, ...aspectSizes[ratio] })}
          >
            {ratio}
          </button>
        ))}
      </div>

      <div className="fieldGrid two">
        <label className="field">
          <span>Width</span>
          <input
            type="number"
            value={request.width}
            min={64}
            max={4096}
            onChange={(event) => onChange({ width: Number(event.target.value) })}
          />
        </label>
        <label className="field">
          <span>Height</span>
          <input
            type="number"
            value={request.height}
            min={64}
            max={4096}
            onChange={(event) => onChange({ height: Number(event.target.value) })}
          />
        </label>
      </div>

      <div className="fieldGrid two">
        <label className="field">
          <span>Frames</span>
          <input
            type="number"
            value={request.video_length}
            min={1}
            max={257}
            onChange={(event) => onChange({ video_length: Number(event.target.value) })}
          />
        </label>
        <label className="field">
          <span>FPS</span>
          <input
            type="number"
            value={request.fps}
            min={1}
            max={60}
            onChange={(event) => onChange({ fps: Number(event.target.value) })}
          />
        </label>
      </div>

      <label className="field">
        <span>Steps {request.steps}</span>
        <input
          type="range"
          value={request.steps}
          min={1}
          max={120}
          onChange={(event) => onChange({ steps: Number(event.target.value) })}
        />
      </label>

      <div className="fieldGrid two">
        <label className="field">
          <span>CFG</span>
          <input
            type="number"
            step={0.5}
            value={request.cfg_scale}
            onChange={(event) => onChange({ cfg_scale: Number(event.target.value) })}
          />
        </label>
        <label className="field">
          <span>Flow</span>
          <input
            type="number"
            step={0.5}
            value={request.flow_shift}
            onChange={(event) => onChange({ flow_shift: Number(event.target.value) })}
          />
        </label>
      </div>

      <label className="field">
        <span>Seed</span>
        <input
          type="number"
          value={request.seed ?? ""}
          placeholder="random"
          onChange={(event) => onChange({ seed: event.target.value ? Number(event.target.value) : null })}
        />
      </label>

      <div className="toggleGrid">
        <label>
          <input
            type="checkbox"
            checked={request.use_cpu_offload}
            onChange={(event) => onChange({ use_cpu_offload: event.target.checked })}
          />
          <span>CPU offload</span>
        </label>
        <label>
          <input
            type="checkbox"
            checked={request.use_fp8}
            onChange={(event) => onChange({ use_fp8: event.target.checked })}
          />
          <span>FP8</span>
        </label>
        <label title="Prompt rewriting is not yet implemented" style={{ opacity: 0.4, cursor: "not-allowed" }}>
          <input
            type="checkbox"
            checked={false}
            disabled
            onChange={() => undefined}
          />
          <span>Rewrite</span>
        </label>
      </div>
    </section>
  );
}
