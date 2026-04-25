/** Resizable desktop layout — presets, pixel rails, localStorage persistence */

export type LayoutPresetId =
  | 'balanced'
  | 'copilot-focus'
  | 'threat-focus'
  | 'map-focus'
  | 'briefing';

export const LAYOUT_PRESETS: Record<
  LayoutPresetId,
  { label: string; leftPct: number; rightPct: number }
> = {
  balanced: { label: 'Balanced', leftPct: 22, rightPct: 32 },
  'copilot-focus': { label: 'Copilot Focus', leftPct: 20, rightPct: 42 },
  'threat-focus': { label: 'Threat Focus', leftPct: 30, rightPct: 28 },
  'map-focus': { label: 'Map Focus', leftPct: 18, rightPct: 26 },
  briefing: { label: 'Briefing Mode', leftPct: 24, rightPct: 42 },
};

const MIN_LEFT = 280;
const MIN_RIGHT = 360;
const MIN_CENTER = 420;
const RESIZER = 6;
const STORAGE_KEY = 'neon-command-layout-v1';

export type BottomBarMode = 'compact' | 'normal' | 'expanded';

const BOTTOM_HEIGHTS: Record<BottomBarMode, number> = {
  compact: 80,
  normal: 118,
  expanded: 168,
};

export function getBottomHeight(mode: BottomBarMode): number {
  return BOTTOM_HEIGHTS[mode];
}

export interface StoredLayout {
  preset: LayoutPresetId;
  leftPx: number;
  rightPx: number;
  /** Timeline row height (optional for older saved layouts) */
  bottomMode?: BottomBarMode;
}

/** Clamp rail widths so center stays usable */
export function clampRails(
  containerWidth: number,
  leftPx: number,
  rightPx: number,
): { leftPx: number; rightPx: number } {
  const maxTotal = Math.max(
    MIN_LEFT + MIN_RIGHT + MIN_CENTER + RESIZER * 2,
    containerWidth - RESIZER * 2,
  );
  let L = Math.max(MIN_LEFT, Math.min(leftPx, maxTotal - MIN_RIGHT - MIN_CENTER - RESIZER * 2));
  let R = Math.max(MIN_RIGHT, Math.min(rightPx, maxTotal - MIN_LEFT - MIN_CENTER - RESIZER * 2));
  const center = containerWidth - L - R - RESIZER * 2;
  if (center < MIN_CENTER) {
    const deficit = MIN_CENTER - center;
    const takeL = Math.min(deficit * 0.45, L - MIN_LEFT);
    const takeR = Math.min(deficit - takeL, R - MIN_RIGHT);
    L = Math.max(MIN_LEFT, L - takeL);
    R = Math.max(MIN_RIGHT, R - (deficit - takeL));
    if (containerWidth - L - R - RESIZER * 2 < MIN_CENTER) {
      R = Math.max(MIN_RIGHT, containerWidth - L - MIN_CENTER - RESIZER * 2);
    }
  }
  return { leftPx: Math.round(L), rightPx: Math.round(R) };
}

export function presetToPixels(
  preset: LayoutPresetId,
  containerWidth: number,
): { leftPx: number; rightPx: number } {
  const p = LAYOUT_PRESETS[preset];
  const leftPx = (containerWidth * p.leftPct) / 100;
  const rightPx = (containerWidth * p.rightPct) / 100;
  return clampRails(containerWidth, leftPx, rightPx);
}

export function loadLayout(): StoredLayout | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw) as StoredLayout;
    if (o && typeof o.leftPx === 'number' && typeof o.rightPx === 'number' && o.preset in LAYOUT_PRESETS) {
      if (!o.bottomMode || !(o.bottomMode in BOTTOM_HEIGHTS)) {
        (o as StoredLayout).bottomMode = 'normal';
      }
      return o;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function saveLayout(layout: StoredLayout): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  } catch {
    /* ignore */
  }
}

