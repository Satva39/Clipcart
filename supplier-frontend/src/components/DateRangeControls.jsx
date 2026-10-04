import { useEffect, useState } from "react";
import { rangeFromPreset } from "../utils/dateRange";

const PRESETS = [
  ["today", "Today"],
  ["yesterday", "Yesterday"],
  ["last7", "Last 7 days"],
  ["last30", "Last 30 days"],
  ["lastMonth", "Last month"],
  ["currentMonth", "Current month"],
  ["previousMonth", "Previous month"],
  ["ytd", "Year to date"],
  ["custom", "Custom range"],
];

export default function DateRangeControls({ onChange, compact = false }) {
  const initial = rangeFromPreset("last30");
  const [preset, setPreset] = useState("last30");
  const [start, setStart] = useState(initial.start);
  const [end, setEnd] = useState(initial.end);

  useEffect(() => {
    if (preset !== "custom") onChange?.(rangeFromPreset(preset));
  }, [preset, onChange]);

  useEffect(() => {
    if (preset === "custom" && start && end) onChange?.({ start, end });
  }, [preset, start, end, onChange]);

  function changePreset(value) {
    setPreset(value);
    if (value !== "custom") {
      const range = rangeFromPreset(value);
      setStart(range.start);
      setEnd(range.end);
    }
  }

  return (
    <div className={`date-range-controls ${compact ? "compact" : ""}`}>
      <select
        value={preset}
        onChange={(e) => changePreset(e.target.value)}
        aria-label="Date range preset"
      >
        {PRESETS.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      {preset === "custom" && (
        <>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            aria-label="Start date"
          />
          <span>to</span>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            aria-label="End date"
          />
        </>
      )}
    </div>
  );
}
