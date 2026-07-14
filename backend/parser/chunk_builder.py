import os
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.parser.code_analyzer import CodeAnalyzer

class ChunkBuilder:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.code_splitter = RecursiveCharacterTextSplitter.from_language(
            language="python", # default language, will adjust dynamically if possible
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def build_chunks(self, file_path: str, root_dir: str) -> List[Dict[str, Any]]:
        """
        Reads a file, analyzes its code structure, and returns a list of chunks
        with enriched metadata.
        """
        relative_path = os.path.relpath(file_path, root_dir).replace("\\", "/")
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        if not content.strip():
            return []

        # Analyze structure (symbols, imports, exports)
        analysis = CodeAnalyzer.analyze(content, file_path)
        language = analysis["language"]
        symbols = analysis["symbols"]
        imports = analysis["imports"]
        exports = analysis["exports"]

        chunks = []
        lines = content.split("\n")

        # 1. AST-based Chunks for Python and JS/TS
        if language in ("python", "javascript") and symbols:
            # Create a map to track which parts of the code have been chunked
            covered_ranges = []
            
            for sym in symbols:
                start = max(1, sym["start_line"] - 1)
                end = min(len(lines), sym["end_line"])
                
                # Extract code block for this function or class (Moon)
                symbol_code = "\n".join(lines[start:end])
                if not symbol_code.strip():
                    continue
                    
                covered_ranges.append((start, end))
                
                # Check if it fits or needs further splitting
                if len(symbol_code) <= self.chunk_size:
                    chunks.append({
                        "content": symbol_code,
                        "metadata": {
                            "path": relative_path,
                            "language": language,
                            "class": sym["name"] if sym["type"] == "class" else "",
                            "function": sym["name"] if sym["type"] == "function" else "",
                            "imports": imports,
                            "exports": exports,
                            "summary": sym["summary"],
                            "chunk_type": sym["type"],
                            "start_line": start + 1,
                            "end_line": end
                        }
                    })
                else:
                    # Sub-chunk the large class/function
                    sub_chunks = self.code_splitter.split_text(symbol_code)
                    for idx, sub_content in enumerate(sub_chunks):
                        chunks.append({
                            "content": sub_content,
                            "metadata": {
                                "path": relative_path,
                                "language": language,
                                "class": sym["name"] if sym["type"] == "class" else "",
                                "function": sym["name"] if sym["type"] == "function" else "",
                                "imports": imports,
                                "exports": exports,
                                "summary": f"{sym['summary']} (Part {idx+1})",
                                "chunk_type": sym["type"],
                                "start_line": start + 1,
                                "end_line": end
                            }
                        })
            
            # Identify "orphan" ranges (comments, global statements, config, setup code)
            # and chunk them as generic modules
            covered_ranges.sort()
            current_idx = 0
            orphan_blocks = []
            
            for start, end in covered_ranges:
                if start > current_idx:
                    orphan_blocks.append((current_idx, start))
                current_idx = end
            if current_idx < len(lines):
                orphan_blocks.append((current_idx, len(lines)))
                
            for start, end in orphan_blocks:
                orphan_code = "\n".join(lines[start:end]).strip()
                if not orphan_code:
                    continue
                sub_chunks = self.code_splitter.split_text(orphan_code)
                for sub_content in sub_chunks:
                    chunks.append({
                        "content": sub_content,
                        "metadata": {
                            "path": relative_path,
                            "language": language,
                            "class": "",
                            "function": "",
                            "imports": imports,
                            "exports": exports,
                            "summary": f"Orphan script block in {os.path.basename(file_path)}",
                            "chunk_type": "global_block",
                            "start_line": start + 1,
                            "end_line": end
                        }
                    })
        
        # 2. General files (Markdown, JSON, Text, or code without symbols)
        else:
            # Use general text splitter
            sub_chunks = self.text_splitter.split_text(content)
            for idx, sub_content in enumerate(sub_chunks):
                chunks.append({
                    "content": sub_content,
                    "metadata": {
                        "path": relative_path,
                        "language": language,
                        "class": "",
                        "function": "",
                        "imports": [],
                        "exports": [],
                        "summary": f"Text chunk {idx+1} of {os.path.basename(file_path)}",
                        "chunk_type": "text_block",
                        "start_line": 1,
                        "end_line": len(lines)
                    }
                })

        # 3. Add a file-level summary chunk to act as the "Planet" entry point
        # This is great for document retrieval and high level summaries
        file_summary = f"File: {relative_path}\nLanguage: {language}\nImports: {', '.join(imports)}\nExports: {', '.join(exports)}\n"
        if symbols:
            file_summary += f"Contains symbols: {', '.join([s['name'] for s in symbols])}\n"
        chunks.append({
            "content": file_summary,
            "metadata": {
                "path": relative_path,
                "language": language,
                "class": "",
                "function": "",
                "imports": imports,
                "exports": exports,
                "summary": f"System profile of file {relative_path}",
                "chunk_type": "file_summary",
                "start_line": 1,
                "end_line": len(lines)
            }
        })

        return chunks
