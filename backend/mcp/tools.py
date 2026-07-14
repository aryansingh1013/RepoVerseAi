import os
import subprocess
import urllib.parse
import urllib.request
import re
from typing import Dict, Any, List

class MCPTools:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = os.path.abspath(workspace_dir)

    def _resolve_path(self, path: str) -> str:
        """Helper to ensure paths stay within the workspace for safety."""
        resolved = os.path.abspath(os.path.join(self.workspace_dir, path))
        if not resolved.startswith(self.workspace_dir):
            raise PermissionError("Access outside workspace is restricted.")
        return resolved

    # 1. Filesystem Tools
    def filesystem_list(self, relative_path: str = ".") -> str:
        try:
            full_path = self._resolve_path(relative_path)
            items = os.listdir(full_path)
            result = []
            for item in items:
                item_path = os.path.join(full_path, item)
                is_dir = os.path.isdir(item_path)
                result.append(f"{'[DIR]' if is_dir else '[FILE]'} {item}")
            return "\n".join(result) if result else "Directory is empty."
        except Exception as e:
            return f"Error listing directory: {e}"

    def filesystem_read(self, relative_path: str = "", start_line: int = 1, end_line: int = 100) -> str:
        if not relative_path:
            return "No relative_path provided. Skipped file read."
        try:
            full_path = self._resolve_path(relative_path)
            if os.path.isdir(full_path):
                return f"Path '{relative_path}' is a directory. Use filesystem_list instead."
                
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            # 1-indexed line numbers
            start = max(0, start_line - 1)
            end = min(len(lines), end_line)
            
            output = []
            for idx in range(start, end):
                output.append(f"{idx+1}: {lines[idx].rstrip()}")
            return "\n".join(output) if output else "No content in specified line range."
        except Exception as e:
            return f"Error reading file: {e}"

    # 2. Git Tools
    def git_log(self, limit: int = 5) -> str:
        try:
            res = subprocess.run(
                ["git", "log", f"-n {limit}", "--oneline"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                shell=True
            )
            return res.stdout if res.returncode == 0 else f"Git log error: {res.stderr}"
        except Exception as e:
            return f"Error executing git log: {e}"

    def git_diff(self, file_path: str = "") -> str:
        try:
            args = ["git", "diff"]
            if file_path:
                args.append(self._resolve_path(file_path))
            res = subprocess.run(
                args,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                shell=True
            )
            return res.stdout if res.returncode == 0 else f"Git diff error: {res.stderr}"
        except Exception as e:
            return f"Error executing git diff: {e}"

    # 3. Terminal Executions
    def terminal_run(self, command: str) -> str:
        """
        Runs specific allowed terminal commands (like pytest or npm build).
        """
        # Security: restrict commands
        allowed_prefixes = ["pytest", "npm run build", "python -m pytest", "npm test"]
        is_allowed = any(command.strip().startswith(pref) for pref in allowed_prefixes)
        
        if not is_allowed:
            return f"Security Error: Command '{command}' is not in the whitelist of execution commands (pytest, npm run build)."
            
        try:
            res = subprocess.run(
                command,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                shell=True,
                timeout=30 # 30s timeout
            )
            stdout = res.stdout or ""
            stderr = res.stderr or ""
            return f"Exit Code: {res.returncode}\nStdout:\n{stdout}\nStderr:\n{stderr}"
        except subprocess.TimeoutExpired:
            return "Command execution timed out after 30 seconds."
        except Exception as e:
            return f"Error running terminal command: {e}"

    # 4. Python Sandbox Execution
    def python_execute(self, code: str) -> str:
        try:
            # Writes to a temp script and runs it in a subprocess
            temp_file = os.path.join(self.workspace_dir, "db", "_temp_exec.py")
            os.makedirs(os.path.dirname(temp_file), exist_ok=True)
            
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(code)
                
            res = subprocess.run(
                ["python", temp_file],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
            stdout = res.stdout or ""
            stderr = res.stderr or ""
            return f"Exit Code: {res.returncode}\nStdout:\n{stdout}\nStderr:\n{stderr}"
        except subprocess.TimeoutExpired:
            return "Python execution timed out after 10 seconds."
        except Exception as e:
            return f"Error running Python code: {e}"

    # 5. Browser Tool (Mock Search / API Docs Fetcher)
    def browser_search(self, query: str) -> str:
        """
        Fetches web page or searches online. Falls back to a simulated doc search
        if API is offline.
        """
        try:
            # Direct search queries can fetch duckduckgo html or return simulated response
            url_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={url_query}"
            
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
            # Extract basic text links/titles
            links = re.findall(r'<a class="result__snippet" href="[^"]*">(.*?)</a>', html, re.DOTALL)
            text_snippets = []
            for link in links[:3]: # top 3
                # remove html tags
                clean = re.sub(r'<[^>]*>', '', link).strip()
                text_snippets.append(clean)
                
            if text_snippets:
                return "\n\n".join(text_snippets)
            return "No web results found."
        except Exception:
            # Offline / Fallback
            return f"Browser Offline: Could not complete search for '{query}'. Please check network connections."

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        if tool_name == "filesystem_list":
            return self.filesystem_list(args.get("relative_path", "."))
        elif tool_name == "filesystem_read":
            return self.filesystem_read(
                args.get("relative_path"), 
                args.get("start_line", 1), 
                args.get("end_line", 100)
            )
        elif tool_name == "git_log":
            return self.git_log(args.get("limit", 5))
        elif tool_name == "git_diff":
            return self.git_diff(args.get("file_path", ""))
        elif tool_name == "terminal_run":
            return self.terminal_run(args.get("command"))
        elif tool_name == "python_execute":
            return self.python_execute(args.get("code"))
        elif tool_name == "browser_search":
            return self.browser_search(args.get("query"))
        else:
            return f"Unknown tool: {tool_name}"
