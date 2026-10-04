export function toISODate(date) {
  const value = new Date(date);
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

export function rangeFromPreset(preset) {
  const today = new Date();
  const end = toISODate(today);
  const startDate = new Date(today);
  const year = today.getFullYear();
  const month = today.getMonth();

  switch (preset) {
    case "today":
      return { start: end, end };
    case "yesterday": {
      startDate.setDate(today.getDate() - 1);
      const day = toISODate(startDate);
      return { start: day, end: day };
    }
    case "last7":
      startDate.setDate(today.getDate() - 6);
      return { start: toISODate(startDate), end };
    case "last30":
      startDate.setDate(today.getDate() - 29);
      return { start: toISODate(startDate), end };
    case "lastMonth": {
      const first = new Date(year, month - 1, 1);
      const last = new Date(year, month, 0);
      return { start: toISODate(first), end: toISODate(last) };
    }
    case "currentMonth":
      return { start: toISODate(new Date(year, month, 1)), end };
    case "previousMonth": {
      const first = new Date(year, month - 1, 1);
      const last = new Date(year, month, 0);
      return { start: toISODate(first), end: toISODate(last) };
    }
    case "ytd":
      return { start: toISODate(new Date(year, 0, 1)), end };
    default:
      return { start: toISODate(new Date(year, month, 1)), end };
  }
}

export function money(value = 0) {
  return `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export function formatDateTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
