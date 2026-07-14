export type ClassValue = string | number | boolean | null | undefined;

/** Minimal classnames joiner — filters falsy values, joins the rest. */
export function clsx(...values: ClassValue[]): string {
  return values.filter(Boolean).join(" ");
}
