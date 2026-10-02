import type { Source, StudentProfile } from "./types";

export const CATALOG_LABEL = "2025–26 Catalog";
export const CATALOG_SOURCE_LABEL = "Lafayette College Catalog · 2025–26";

/** "Mohammad Rasim Omer" -> "MO". Returns "" when there is nothing usable. */
export function initialsFrom(name: string | undefined | null): string {
  if (!name) return "";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function firstNameFrom(name: string | undefined | null): string {
  if (!name) return "";
  return name.trim().split(/\s+/)[0] ?? "";
}

/** Last segment of a `A > B > C` heading path, trimmed. */
export function cleanTitle(source: Source): string {
  const raw = source.heading_path || source.section || "";
  const last = raw.split(">").pop()?.trim();
  if (last) return last;
  return humanizeSection(source.section) || "Lafayette College Catalog";
}

/** "course_description" -> "Course Description" */
export function humanizeSection(section: string | undefined | null): string {
  if (!section) return "";
  return section
    .replace(/[_-]+/g, " ")
    .trim()
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

/** `12` or `12–14` */
export function pageLabel(source: Source): string {
  const { start_page, end_page } = source;
  if (!start_page) return "";
  if (end_page && end_page !== start_page) return `${start_page}–${end_page}`;
  return String(start_page);
}

/** `Lafayette College Catalog · 2025–26 · p.42` */
export function sourceSubtitle(source: Source): string {
  const page = pageLabel(source);
  return page ? `${CATALOG_SOURCE_LABEL} · p.${page}` : CATALOG_SOURCE_LABEL;
}

/** 1699999999999 -> "3:04 PM" */
export function formatTime(ts: number): string {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return "";
  }
}

/** Degree progress percentage, guarded against divide-by-zero. */
export function progressPct(profile: StudentProfile): number {
  const required = profile.credits?.required ?? 0;
  const applied = profile.credits?.applied ?? 0;
  if (!required || required <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((applied / required) * 100)));
}
