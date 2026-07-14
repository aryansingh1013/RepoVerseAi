import json
from typing import List, Dict, Any

class ResultFusion:
    @staticmethod
    def fuse_contexts(tasks: List[Any], rag_contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Gathers tool results and RAG vector store chunks, removes duplicates,
        ranks relevance, and structures unified context.
        """
        fused_snippets = []
        seen_identifiers = set()
        provenance_log = []

        # 1. Parse and extract results from executed tasks
        for task in tasks:
            if not task.output_payload or "results" not in task.output_payload:
                continue
            
            for res in task.output_payload["results"]:
                # Check status
                if res.get("status") != "success":
                    continue
                
                tool_name = res.get("tool_name")
                capability = res.get("capability")
                payload = res.get("result")
                
                # Check formatting
                # Subprocess tool results or mock outputs
                content_str = str(payload)
                
                # Generate unique key to avoid duplicate tool dumps
                key = f"tool#{tool_name}#{hash(content_str)}"
                if key not in seen_identifiers:
                    seen_identifiers.add(key)
                    fused_snippets.append({
                        "source": f"Tool: {tool_name} ({capability})",
                        "content": content_str,
                        "score": 1.0, # High relevance by default for targeted tool actions
                        "metadata": {"tool": tool_name, "capability": capability}
                    })
                    provenance_log.append(f"Loaded details via {tool_name} ({capability})")

        # 2. Parse and merge vector RAG contexts
        for chunk in rag_contexts:
            meta = chunk.get("metadata", {})
            path = meta.get("path", "source_file")
            start = meta.get("start_line", 1)
            end = meta.get("end_line", 100)
            
            # Generate unique key
            key = f"rag#{path}#{start}#{end}"
            if key not in seen_identifiers:
                seen_identifiers.add(key)
                fused_snippets.append({
                    "source": f"Codebase: {path} (Lines {start}-{end})",
                    "content": chunk.get("content", ""),
                    "score": chunk.get("score", 0.8), # Vector score or default
                    "metadata": meta
                })
                provenance_log.append(f"Retrieved codebase context from {path}")

        # 3. Sort merged snippets by relevance score descending
        fused_snippets.sort(key=lambda x: x["score"], reverse=True)

        return {
            "contexts": fused_snippets,
            "provenance": list(set(provenance_log)),
            "summary": f"Fused {len(fused_snippets)} snippets with active provenance logs."
        }
