import { FolderGit2, Clock, Bookmark as BookmarkIcon, Layers, ShieldAlert } from "lucide-react";
import { motion } from "framer-motion";
import { useNavigation } from "@/hooks/useNavigation";
import { clsx } from "@/utils/clsx";

export function LeftSidebar() {
  const { 
    jumpTo, 
    spaceGraph, 
    repositories, 
    recentFiles, 
    bookmarks,
    isMissionControlOpen,
    messages,
    selectedMessageId,
    activeFileContent,
    activeFileDetails
  } = useNavigation();

  // PRIORITIZED VIEW: Full Code Viewer when file content is loaded
  if (activeFileContent !== null && activeFileDetails) {
    const symbolLineNum = activeFileDetails.stats?.find(s => s.label === "Start Line")?.value;
    const targetLine = symbolLineNum ? parseInt(symbolLineNum, 10) : null;
    const lines = activeFileContent.split("\n");

    return (
      <motion.aside
        initial={{ opacity: 0, x: -12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full shrink-0 flex flex-col h-full overflow-hidden bg-void-900/60 rounded-2xl border border-white/5 shadow-2xl"
      >
        {/* File Path Header */}
        <div className="p-3 border-b border-white/5 bg-void-950/40 select-none shrink-0 flex items-center justify-between">
          <div className="flex flex-col min-w-0 pr-2">
            <span className="text-[10px] font-mono text-signal-400 uppercase tracking-wider">
              Code Vault
            </span>
            <h2 className="text-xs font-mono text-mist-100 truncate" title={activeFileDetails.description}>
              {activeFileDetails.name}
            </h2>
          </div>
          {activeFileDetails.language && (
            <span className="text-[9px] font-mono bg-white/5 border border-white/10 px-1.5 py-0.5 rounded text-mist-400 uppercase">
              {activeFileDetails.language}
            </span>
          )}
        </div>

        {/* Scrollable Code Viewer */}
        <div className="flex-1 overflow-auto p-3 font-mono text-[10px] leading-relaxed select-text scrollbar-thin select-all">
          {lines.map((lineText, idx) => {
            const lineNum = idx + 1;
            const isHighlighted = lineNum === targetLine;
            return (
              <div
                key={idx}
                className={clsx(
                  "flex gap-3 px-1 py-0.5 rounded transition-colors",
                  isHighlighted ? "bg-signal-500/20 border-l-2 border-signal-400 font-bold shadow-md shadow-signal-500/5 text-mist-100" : "hover:bg-white/5 text-mist-300"
                )}
              >
                <span className={clsx(
                  "select-none w-6 text-right shrink-0",
                  isHighlighted ? "text-signal-400" : "text-mist-700"
                )}>
                  {lineNum}
                </span>
                <span className="whitespace-pre">{lineText || " "}</span>
              </div>
            );
          })}
        </div>
      </motion.aside>
    );
  }

  // SECONDARY VIEW: Grounding citations when AI chat is active
  if (isMissionControlOpen) {
    const activeMsg = messages.find(m => m.id === selectedMessageId);
    const citations = activeMsg?.citations || [];
    const trace = activeMsg?.trace;

    return (
      <motion.aside
        initial={{ opacity: 0, x: -12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full shrink-0 panel-glass flex flex-col overflow-y-auto h-full rounded-2xl shadow-2xl"
      >
        <div className="p-4 border-b border-white/5 shrink-0">
          <h2 className="font-display font-semibold text-sm text-mist-100 uppercase tracking-wider flex items-center gap-1.5">
            <ShieldAlert className="h-4 w-4 text-signal-400" />
            Grounding Sources
          </h2>
          <p className="text-[11px] text-mist-500 mt-1">Citations verified against codebase facts</p>
        </div>

        <div className="flex-1 p-4 space-y-4">
          {citations.length === 0 ? (
            <div className="text-xs text-mist-500 italic p-3 text-center">
              No codebase citations retrieved for this message yet.
            </div>
          ) : (
            <div className="space-y-3">
              {citations.map((cit, idx) => {
                const planetId = `planet-${cit.file}`;
                const fileExists = spaceGraph.some(o => o.id === planetId);
                return (
                  <div 
                    key={idx}
                    className="p-3 rounded-lg border border-white/5 bg-void-800/40 hover:border-signal-500/30 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-mono text-mist-100 truncate flex-1">{cit.file}</span>
                      {fileExists && (
                        <button 
                          onClick={() => jumpTo(planetId)}
                          className="text-[10px] text-signal-400 hover:text-signal-300 font-medium whitespace-nowrap"
                        >
                          Locate Orbit 🛸
                        </button>
                      )}
                    </div>
                    {cit.lines && (
                      <div className="text-[10px] text-ember-400 font-mono mt-1">
                        Lines {cit.lines[0]} - {cit.lines[1]}
                      </div>
                    )}
                    {cit.content && (
                      <pre className="text-[10px] text-mist-400 bg-void-950/60 p-2 rounded border border-white/5 font-mono overflow-x-auto mt-2 leading-normal whitespace-pre-wrap max-h-24">
                        {cit.content}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {trace && (
            <div className="border-t border-white/5 pt-4">
              <h3 className="text-xs font-medium text-mist-500 uppercase tracking-wider mb-2">Reasoning Chain</h3>
              <pre className="text-[10px] text-mist-500 font-mono whitespace-pre-wrap leading-normal max-h-40 overflow-y-auto bg-void-950/40 p-2.5 rounded border border-white/5">
                {trace}
              </pre>
            </div>
          )}
        </div>
      </motion.aside>
    );
  }

  // DEFAULT VIEW: Repositories explorer tree
  const findGalaxyIdForRepo = (repoName: string): string | undefined => {
    return spaceGraph.find((o) => o.kind === "galaxy" && o.name === repoName)?.id;
  };

  function SectionHeader({ icon: Icon, label }: { icon: typeof FolderGit2; label: string }) {
    return (
      <div className="flex items-center gap-2 px-3 pt-4 pb-2 text-xs font-medium uppercase tracking-wider text-mist-500">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
    );
  }

  const activeRepos = repositories.length > 0 ? repositories : [
    {
      id: "repo-active-fallback",
      name: spaceGraph.find(o => o.kind === "galaxy")?.name || "Repository",
      description: "Active local workspace folder",
      language: "Source Code",
      updatedAt: "Active Now",
      starCount: 100,
    }
  ];

  return (
    <motion.aside
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="w-full shrink-0 panel-glass flex flex-col overflow-y-auto h-full rounded-2xl"
    >
      <SectionHeader icon={FolderGit2} label="Repositories" />
      <div className="px-2 space-y-1">
        {activeRepos.map((repo) => {
          const galaxyId = findGalaxyIdForRepo(repo.name) || spaceGraph.find(o => o.kind === "galaxy")?.id;
          return (
            <button
              key={repo.id}
              disabled={!galaxyId}
              onClick={() => galaxyId && jumpTo(galaxyId)}
              className="w-full text-left rounded-md px-2.5 py-2 hover:bg-void-700/60 transition-colors group disabled:opacity-50 disabled:hover:bg-transparent"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm text-mist-100 group-hover:text-signal-400 transition-colors">
                  {repo.name}
                </span>
                <span className="text-[10px] font-mono text-mist-500">{repo.language}</span>
              </div>
              <p className="text-xs text-mist-500 truncate mt-0.5">{repo.description}</p>
            </button>
          );
        })}
      </div>

      <SectionHeader icon={Clock} label="Recent Files" />
      <div className="px-2 space-y-0.5">
        {recentFiles.map((file) => {
          const planetId = `planet-${file.path}`;
          const exists = spaceGraph.some(o => o.id === planetId);
          return (
            <button
              key={file.id}
              disabled={!exists}
              onClick={() => exists && jumpTo(planetId)}
              className="w-full text-left rounded-md px-2.5 py-1.5 hover:bg-void-700/60 transition-colors disabled:opacity-50"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-mist-300 font-mono">{file.name}</span>
                <span className="text-[10px] text-mist-500">{file.openedAt}</span>
              </div>
            </button>
          );
        })}
      </div>

      <SectionHeader icon={BookmarkIcon} label="Bookmarks" />
      <div className="px-2 space-y-0.5 pb-4">
        {bookmarks.length === 0 ? (
          <div className="text-xs text-mist-500 italic px-3 py-1">No bookmarks yet</div>
        ) : (
          bookmarks.map((bm) => {
            const planetId = `planet-${bm.path}`;
            const exists = spaceGraph.some(o => o.id === planetId);
            return (
              <button
                key={bm.id}
                disabled={!exists}
                onClick={() => exists && jumpTo(planetId)}
                className="w-full text-left rounded-md px-2.5 py-1.5 hover:bg-void-700/60 transition-colors text-xs text-mist-300 font-mono disabled:opacity-50"
              >
                {bm.name}
              </button>
            );
          })
        )}
      </div>

      <div className="mt-auto px-3 py-3 border-t border-white/5 flex items-center gap-2 text-[11px] text-mist-500">
        <Layers className="h-3.5 w-3.5" />
        Layout · Universe → Galaxy → Star → Planet → Moon
      </div>
    </motion.aside>
  );
}
