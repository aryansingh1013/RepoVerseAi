import type { ObjectDetails, SpaceObject } from "@/types";

/**
 * Keyed lookup of detail payloads for each selectable space object.
 * In production this becomes GET /api/objects/{id} returning the same shape.
 */
export const mockObjectDetails: Record<string, ObjectDetails> = {
  "galaxy-nova": {
    id: "galaxy-nova",
    name: "nova-engine",
    type: "galaxy",
    description: "Core simulation engine for orbital mechanics and trajectory prediction.",
    language: "TypeScript / Python",
    dependencies: ["numpy", "fastapi", "three.js"],
    summary:
      "The primary repository powering real-time orbital simulations. Contains the physics core, API routes, and shared utilities.",
    stats: [
      { label: "Files", value: "142" },
      { label: "Contributors", value: "6" },
      { label: "Last commit", value: "3h ago" },
      { label: "Open issues", value: "9" },
    ],
    codePreview: [
      { line: 1, content: "# nova-engine" },
      { line: 2, content: "Orbital simulation core." },
    ],
  },
  "star-core": {
    id: "star-core",
    name: "core/",
    type: "star",
    description: "Folder containing the physics and math primitives for the simulation engine.",
    dependencies: ["numpy"],
    summary: "Houses orbit_solver.py and vector_math.py, the two hot-path modules in the engine.",
    stats: [
      { label: "Files", value: "8" },
      { label: "Size", value: "24 KB" },
    ],
    codePreview: [],
  },
  "planet-orbit-solver": {
    id: "planet-orbit-solver",
    name: "orbit_solver.py",
    type: "planet",
    description: "Computes trajectory solutions for orbiting bodies using numerical integration.",
    language: "Python",
    dependencies: ["numpy", "scipy"],
    summary:
      "Central solver module. Exposes solve_trajectory() and the OrbitBody class used throughout the simulation loop.",
    stats: [
      { label: "Lines", value: "312" },
      { label: "Functions", value: "7" },
      { label: "Test coverage", value: "88%" },
    ],
    codePreview: [
      { line: 1, content: "class OrbitBody:" },
      { line: 2, content: "    def __init__(self, mass, position, velocity):" },
      { line: 3, content: "        self.mass = mass" },
      { line: 4, content: "        self.position = position" },
      { line: 5, content: "" },
      { line: 6, content: "def solve_trajectory(body, steps):" },
      { line: 7, content: "    # numerical integration placeholder" },
      { line: 8, content: "    ..." },
    ],
  },
  "moon-solve-fn": {
    id: "moon-solve-fn",
    name: "solve_trajectory()",
    type: "moon",
    description: "Function that integrates position and velocity across simulation steps.",
    language: "Python",
    dependencies: ["scipy.integrate"],
    summary: "Called once per simulation tick; returns the updated OrbitBody state.",
    stats: [
      { label: "Calls / min", value: "1,204" },
      { label: "Avg runtime", value: "0.4ms" },
    ],
    codePreview: [
      { line: 6, content: "def solve_trajectory(body, steps):" },
      { line: 7, content: "    # numerical integration placeholder" },
      { line: 8, content: "    ..." },
    ],
  },
  "star-routes": {
    id: "star-routes",
    name: "routes/",
    type: "star",
    description: "Folder containing the FastAPI route handlers exposed by the indexing service.",
    dependencies: ["fastapi"],
    summary: "Houses index_router.py and auth_routes.py, the entry points for the public API surface.",
    stats: [
      { label: "Files", value: "6" },
      { label: "Size", value: "18 KB" },
    ],
    codePreview: [],
  },
  "star-utils": {
    id: "star-utils",
    name: "utils/",
    type: "star",
    description: "Shared helper functions used across the engine and API layers.",
    dependencies: [],
    summary: "Small, dependency-light folder of cross-cutting helpers.",
    stats: [{ label: "Files", value: "4" }],
    codePreview: [],
  },
  "planet-vector-math": {
    id: "planet-vector-math",
    name: "vector_math.py",
    type: "planet",
    description: "Vector and matrix operations used throughout the physics core.",
    language: "Python",
    dependencies: ["numpy"],
    summary: "Provides integrate_step() and other low-level vector utilities used by the solver.",
    stats: [
      { label: "Lines", value: "168" },
      { label: "Functions", value: "5" },
    ],
    codePreview: [
      { line: 1, content: "def integrate_step(state, dt):" },
      { line: 2, content: "    # semi-implicit Euler integration" },
      { line: 3, content: "    ..." },
    ],
  },
  "planet-collision": {
    id: "planet-collision",
    name: "collision.py",
    type: "planet",
    description: "Broad-phase and narrow-phase collision detection between orbiting bodies.",
    language: "Python",
    dependencies: ["numpy"],
    summary: "Runs each tick after integration to resolve overlapping bodies.",
    stats: [{ label: "Lines", value: "94" }],
    codePreview: [],
  },
  "planet-index-router": {
    id: "planet-index-router",
    name: "index_router.py",
    type: "planet",
    description: "Top-level FastAPI router wiring repository indexing endpoints.",
    language: "Python",
    dependencies: ["fastapi"],
    summary: "Registers the /index and /status routes consumed by the frontend's mock status bar.",
    stats: [{ label: "Lines", value: "76" }],
    codePreview: [],
  },
  "planet-auth-routes": {
    id: "planet-auth-routes",
    name: "auth_routes.py",
    type: "planet",
    description: "Authentication route stubs — not yet wired to a real identity provider.",
    language: "Python",
    dependencies: ["fastapi"],
    summary: "Exposes verify_token() for downstream route protection.",
    stats: [{ label: "Lines", value: "52" }],
    codePreview: [],
  },
  "moon-orbit-class": {
    id: "moon-orbit-class",
    name: "class OrbitBody",
    type: "moon",
    description: "Represents a single simulated body with mass, position, and velocity.",
    language: "Python",
    dependencies: [],
    summary: "The core data structure passed through solve_trajectory() each tick.",
    stats: [{ label: "Instances / sim", value: "~40" }],
    codePreview: [
      { line: 1, content: "class OrbitBody:" },
      { line: 2, content: "    def __init__(self, mass, position, velocity):" },
      { line: 3, content: "        self.mass = mass" },
    ],
  },
  "moon-integrate-fn": {
    id: "moon-integrate-fn",
    name: "integrate_step()",
    type: "moon",
    description: "Advances a body's position and velocity by one timestep.",
    language: "Python",
    dependencies: ["numpy"],
    summary: "Called once per body, per simulation tick.",
    stats: [{ label: "Avg runtime", value: "0.1ms" }],
    codePreview: [],
  },
  "moon-verify-token": {
    id: "moon-verify-token",
    name: "verify_token()",
    type: "moon",
    description: "Validates an incoming auth token before a request reaches its route handler.",
    language: "Python",
    dependencies: [],
    summary: "Currently a stub — real verification will be wired up once auth is implemented.",
    stats: [{ label: "Calls / min", value: "—" }],
    codePreview: [],
  },
};

export const defaultObjectDetails: ObjectDetails = {
  id: "none",
  name: "No object selected",
  type: "galaxy",
  description: "Select a star, planet, or moon in the space view to inspect it.",
  dependencies: [],
  summary: "Click any object in the 3D scene, or choose one from the sidebar, to load its details here.",
  stats: [],
  codePreview: [],
};

/**
 * Returns hand-authored details when available, otherwise synthesizes a
 * reasonable placeholder from the object's own graph data. This keeps the
 * panel meaningful for every node without requiring every mock object to
 * be manually authored — mirrors how a real API would always return
 * *something* for a valid id even before every field is fully populated.
 */
export function getObjectDetails(object: SpaceObject | undefined): ObjectDetails {
  if (!object) return defaultObjectDetails;
  const authored = mockObjectDetails[object.id];
  if (authored) return authored;

  return {
    id: object.id,
    name: object.name,
    type: object.kind,
    description: `No detailed description indexed yet for this ${object.kind}.`,
    dependencies: [],
    summary: "This object hasn't been fully indexed by the backend yet — details will populate once it is.",
    stats: [],
    codePreview: [],
  };
}
