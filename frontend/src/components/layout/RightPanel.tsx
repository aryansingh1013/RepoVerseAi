import { AnimatePresence, motion } from "framer-motion";
import {
  Tag,
  Code2,
  Package,
  BarChart3,
  GitBranch,
  Orbit,
  ArrowLeft,
  Scissors,
  Undo2,
  Folder,
  FileCode,
  Layers,
} from "lucide-react";
import { useNavigation } from "@/hooks/useNavigation";
import { SPACE_OBJECT_LABELS, type ObjectDetails } from "@/types";

export function RightPanel() {
  const {
    displayedId,
    isTransitioning,
    spaceGraph,
    activeFileDetails,
    navigateTo,
    goBack,
    cutObject,
    restoreAll,
    cutIds,
  } = useNavigation();

  const object = spaceGraph.find((o) => o.id === displayedId);

  if (!object) {
    return (
      <aside className="w-full h-full panel-glass flex flex-col justify-center items-center p-6 text-center rounded-2xl shadow-2xl">
        <Orbit className="h-8 w-8 text-mist-600 animate-spin-slow mb-3" />
        <p className="text-xs text-mist-500 font-mono">No celestial object selected.</p>
      </aside>
    );
  }

  const isStar = object.kind === "star" || object.kind === "galaxy" || object.kind === "repository";
  const isFolder = object.kind === "folder" || object.kind === "planet";
  const isFile = object.kind === "file" || object.kind === "moon";

  const details: ObjectDetails =
    activeFileDetails && activeFileDetails.id === displayedId
      ? activeFileDetails
      : {
          id: object.id,
          name: object.name,
          type: object.kind,
          language: (object as any).language || undefined,
          description: isStar
            ? "Repository Central Star"
            : isFolder
            ? `${object.name}/`
            : (object as any).filePath || object.name,
          dependencies: [],
          summary: isStar
            ? "Central star representing the active repository."
            : isFolder
            ? `Folder planet containing ${object.fileCount || 0} files.`
            : "File moon orbiting repository system.",
          stats: object.fileCount ? [{ label: "Files", value: String(object.fileCount) }] : [],
          codePreview: [],
          symbols: [],
        };

  // Immediate child celestial bodies
  const childBodies = spaceGraph.filter((o) => o.parentId === displayedId);
  const isRootStar =
    displayedId === "repository-star" || displayedId === "galaxy-root" || !object.parentId;

  return (
    <aside className="w-full h-full panel-glass flex flex-col overflow-y-auto rounded-2xl shadow-2xl">
      <AnimatePresence mode="wait">
        <motion.div
          key={details.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: isTransitioning ? 0.4 : 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="flex flex-col gap-5 p-4"
        >
          {/* Header */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-signal-400 font-mono font-semibold">
                {SPACE_OBJECT_LABELS[details.type] || details.type}
              </span>
              {!isRootStar && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => cutObject(displayedId)}
                    aria-label={`Cut ${details.name} from the view`}
                    title="Cut — hide this object from the solar system view"
                    className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-mist-500 hover:text-ember-400 transition-colors font-mono cursor-pointer"
                  >
                    <Scissors className="h-3 w-3" /> Cut
                  </button>
                  <button
                    onClick={goBack}
                    className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-mist-500 hover:text-mist-300 transition-colors font-mono cursor-pointer"
                  >
                    <ArrowLeft className="h-3 w-3" /> Back
                  </button>
                </div>
              )}
            </div>
            <h2 className="font-display text-base font-semibold text-mist-100 leading-snug break-words">
              {details.name}
            </h2>
            <p className="text-xs text-mist-500 leading-relaxed font-mono break-all">
              {details.description}
            </p>
          </div>

          {/* Parent Folder Navigation (for File Moons) */}
          {details.parentFolderId && (
            <button
              onClick={() => navigateTo(details.parentFolderId!)}
              className="flex items-center gap-2 text-xs font-mono text-signal-400 bg-signal-500/10 border border-signal-500/20 py-1.5 px-2.5 rounded-lg hover:bg-signal-500/20 transition-colors self-start cursor-pointer"
            >
              <Folder className="h-3.5 w-3.5" />
              <span>Parent Folder: {details.parentFolderName || "Folder"}</span>
            </button>
          )}

          {/* Language Badge */}
          {details.language && (
            <div className="flex items-center gap-1.5 text-xs text-mist-300 font-mono bg-white/5 border border-white/5 py-1 px-2.5 rounded-md self-start">
              <Tag className="h-3.5 w-3.5 text-signal-400" />
              {details.language}
            </div>
          )}

          {/* Metrics Grid */}
          {details.stats.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist-500 mb-2 font-display">
                <BarChart3 className="h-3.5 w-3.5 text-signal-400" />
                Metrics
              </div>
              <div className="grid grid-cols-2 gap-2">
                {details.stats.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-lg border border-white/5 bg-void-950/50 p-2 text-center"
                  >
                    <div className="text-sm font-semibold text-mist-100 font-display">
                      {stat.value}
                    </div>
                    <div className="text-[9px] text-mist-500 uppercase tracking-wide">
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Folder: Languages Breakdown (Section 18) */}
          {details.languagesBreakdown && details.languagesBreakdown.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist-500 mb-2 font-display">
                <Layers className="h-3.5 w-3.5 text-signal-400" />
                Languages
              </div>
              <div className="flex flex-col gap-1.5">
                {details.languagesBreakdown.map((item) => (
                  <div key={item.language} className="flex flex-col gap-1">
                    <div className="flex justify-between text-xs font-mono text-mist-300">
                      <span>{item.language}</span>
                      <span className="text-signal-400">{item.percentage}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-void-950 border border-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-signal-400"
                        style={{ width: `${item.percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Folder: Top Files */}
          {details.topFiles && details.topFiles.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist-500 mb-2 font-display">
                <FileCode className="h-3.5 w-3.5 text-signal-400" />
                Top Files
              </div>
              <div className="flex flex-col gap-1 max-h-36 overflow-y-auto pr-1">
                {details.topFiles.map((fileName) => {
                  const matchingMoon = spaceGraph.find(
                    (o) => o.parentId === details.id && o.name === fileName
                  );
                  return (
                    <button
                      key={fileName}
                      onClick={() => matchingMoon && navigateTo(matchingMoon.id)}
                      className="w-full flex items-center justify-between text-left text-xs font-mono text-mist-300 hover:text-signal-400 py-1 px-1.5 rounded hover:bg-white/5 border border-transparent hover:border-white/5 transition-all cursor-pointer"
                    >
                      <span className="truncate pr-2">🌙 {fileName}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* File: Functions / Classes Metadata (Section 14 & 19) */}
          {details.symbols && details.symbols.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist-500 mb-2 font-display">
                <Code2 className="h-3.5 w-3.5 text-signal-400" />
                Symbols ({details.symbols.length})
              </div>
              <div className="flex flex-col gap-1 max-h-40 overflow-y-auto pr-1">
                {details.symbols.map((sym, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-xs font-mono text-mist-300 py-1 px-1.5 rounded bg-white/5 border border-white/5"
                  >
                    <span className="truncate pr-2">
                      <span className={sym.type === "class" ? "text-purple-400 font-semibold" : "text-amber-400"}>
                        {sym.type === "class" ? "class" : "def"}
                      </span>{" "}
                      {sym.name}
                    </span>
                    <span className="text-[9px] text-mist-500 shrink-0">L{sym.start_line}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dependencies / Imports */}
          {details.dependencies.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist-500 mb-2 font-display">
                <Package className="h-3.5 w-3.5 text-signal-400" />
                Imports ({details.dependencies.length})
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto pr-1">
                {details.dependencies.map((dep) => (
                  <span
                    key={dep}
                    className="text-[10px] font-mono rounded border border-white/10 bg-void-800/70 px-1.5 py-0.5 text-mist-300 truncate max-w-[160px]"
                    title={dep}
                  >
                    {dep.split(".").pop()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Overview Summary */}
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider text-mist-500 mb-1 font-display">
              Overview Summary
            </div>
            <p className="text-xs text-mist-300 leading-relaxed font-body">
              {details.summary}
            </p>
          </div>

          {/* Source Code Preview */}
          {details.codePreview && details.codePreview.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist-500 mb-2 font-display">
                <Code2 className="h-3.5 w-3.5 text-signal-400" />
                Source Preview
              </div>
              <div className="rounded-lg border border-white/5 bg-void-950/70 p-2.5 font-mono text-[11px] leading-relaxed max-h-48 overflow-y-auto text-mist-300">
                {details.codePreview.map((line) => (
                  <div key={line.line} className="flex gap-2">
                    <span className="text-mist-600 select-none w-6 text-right shrink-0">
                      {line.line}
                    </span>
                    <span className="whitespace-pre overflow-x-auto">{line.content}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Orbiting Children (Folder Planets around Star, or File Moons around Folder) */}
          {isStar && childBodies.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist-500 mb-2 font-display">
                <GitBranch className="h-3.5 w-3.5 text-signal-400" />
                Folder Planets ({childBodies.filter((o) => o.kind === "folder" || o.kind === "planet").length})
              </div>
              <div className="flex flex-col gap-1 max-h-48 overflow-y-auto pr-1">
                {childBodies
                  .filter((child) => child.kind === "folder" || child.kind === "planet")
                  .map((child) => (
                    <button
                      key={child.id}
                      onClick={() => navigateTo(child.id)}
                      className="w-full flex items-center justify-between text-left text-xs font-mono text-mist-300 hover:text-signal-400 py-1.5 px-2 rounded hover:bg-white/5 border border-transparent hover:border-white/5 transition-all cursor-pointer"
                    >
                      <span className="truncate flex-1 pr-2">🪐 {child.name}/</span>
                      <span className="text-[9px] uppercase tracking-wide text-mist-500 bg-void-950/50 px-1 py-0.5 rounded">
                        {child.fileCount ?? 0} files
                      </span>
                    </button>
                  ))}
              </div>
            </div>
          )}

          {/* Restore cut objects */}
          {cutIds.size > 0 && (
            <button
              onClick={restoreAll}
              aria-label="Restore all cut objects"
              className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-mist-500 hover:text-signal-400 border border-white/10 rounded-md px-2 py-1.5 hover:border-signal-400/40 transition-colors self-start cursor-pointer"
            >
              <Undo2 className="h-3 w-3" /> Restore {cutIds.size} cut
            </button>
          )}
        </motion.div>
      </AnimatePresence>
    </aside>
  );
}
