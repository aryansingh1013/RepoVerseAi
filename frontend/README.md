# RepoVerse AI — Frontend Foundation

A NASA-inspired mission-control interface for exploring repository structure in 3D.
This is a **frontend-only** scaffold — no backend, auth, or API calls are implemented.
Every value on screen comes from the mock data layer in `src/data/`.

## Run it

```bash
npm install
npm run dev
```

Opens at `http://localhost:5173`.

## Structure

```
src/
  components/layout/   TopNavbar, LeftSidebar, RightPanel, BottomStatusBar, AppShell, NavigationHud
  three/                SpaceScene, StarField, FocusBody, OrbitingBody, CameraRig, positionsRegistry
  hooks/                useNavigation — focus stack, breadcrumbs, arrival-gated panel state (Context)
  data/                 mockRepository.ts, mockPanel.ts, mockStatus.ts — the entire mock API
  types/                Shared TS contracts every mock file (and future API response) must satisfy
  pages/                Workspace.tsx — hosts the 3D canvas + navigation HUD
  utils/                clsx.ts — tiny classnames helper (no extra dependency)
```

## Space object mapping

| 3D object | Represents      |
|-----------|------------------|
| Galaxy    | Repository       |
| Star      | Folder           |
| Planet    | File             |
| Moon      | Class / Function |

## Navigation model — this is the important part

The scene renders **one hierarchy level at a time**, recentered at the origin, rather
than the whole tree at once. This is what makes it feel like flying through a
universe instead of looking at a static node graph:

- `useNavigation` tracks `focusId` (changes the instant you click something) and
  `displayedId` (what's actually rendered — only updates once the camera arrives).
- Clicking an orbiting star/planet/moon calls `navigateTo(id)`. The camera (`CameraRig`)
  eases toward that object's *live orbiting position*, read each frame from
  `positionsRegistry` (a plain mutable map, deliberately outside React state — you do
  not want 60fps position updates going through React's render cycle).
- Only once `CameraRig` detects arrival does `displayedId` flip to the new focus,
  swapping which objects are rendered as the center + its children. This ordering is
  what prevents the tree from snapping to the new level before the camera gets there.
- Clicking the centered object itself, or the back button / breadcrumb trail in
  `NavigationHud`, calls `goBack()` / `jumpTo()` to ascend.
- `RightPanel` reads `displayedId`, not `focusId` — so details update after the
  camera settles, per spec, and dim slightly during `isTransitioning`.

### Known simplification

Ascending (`goBack`) is snappier than descending, because the parent's registry
position is always `(0,0,0)` from the last time it was centered, so the camera has
little distance left to cover. Descending into a *moving* child produces the full
cinematic ease-in described above. If you want symmetric "zoom out" choreography on
the way back up, that's the next thing to build — a good candidate for a small,
focused follow-up rather than bundling it in here.

## Wiring up the real backend later

1. Replace the exported arrays in `src/data/mockRepository.ts`, `mockPanel.ts`, and
   `mockStatus.ts` with `fetch()` calls (or React Query) that hit your FastAPI routes.
   The **types stay the same** — `SpaceObject`, `ObjectDetails`, `SystemStatus` in
   `src/types/index.ts` are the contract both mock data and real responses must match.
2. No component in `three/`, `layout/`, or `pages/` needs to change — they only
   ever read from the typed data layer, never hardcoded values.
3. `getObjectDetails()` in `mockPanel.ts` is the single seam to swap for a real
   `GET /api/objects/{id}` call — it already falls back gracefully for any id
   that doesn't have hand-authored mock details yet.

## Notes on scope

- Camera flight, hover highlighting, click-to-descend, and breadcrumb-based
  ascend are implemented.
- Orbit motion (with per-object inclination + direction) is a lightweight
  `useFrame` sine/cosine offset — no physics engine, kept cheap on purpose for
  mid-range laptop performance.
- Star "glow" and planet atmosphere are cheap additive-blended shells, not a
  real bloom post-process pass — matches the "no excessive bloom" direction
  and avoids the GPU cost of a full post-processing pipeline.
- Framer Motion is used only for DOM/UI transitions (panel fade-ins, sidebar entrance,
  HUD);  Three.js objects animate via `useFrame` so the two systems don't conflict.
