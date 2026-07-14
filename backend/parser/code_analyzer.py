import ast
import re
from typing import List, Dict, Any, Tuple

class CodeAnalyzer:
    @staticmethod
    def analyze_python(code: str, file_path: str) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
        """
        Parses python code using AST to find classes, functions, imports, and exports.
        Returns:
            symbols: List of dicts representing classes/functions (Moons)
            imports: List of imported modules
            exports: List of exported names
        """
        symbols = []
        imports = []
        exports = []
        
        try:
            tree = ast.parse(code)
        except Exception:
            # Fallback if AST parsing fails due to syntax error
            return symbols, imports, exports
            
        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
            
            # Classes
            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                symbols.append({
                    "name": node.name,
                    "type": "class",
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "summary": docstring.strip().split("\n")[0] if docstring else f"Class {node.name}",
                    "details": docstring
                })
                # Check for __all__ exports
                if node.name == "__all__":
                    pass # Handled differently if needed
            
            # Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Ignore nested functions for clean mapping
                parent = getattr(node, "parent", None)
                if parent is None:
                    # Let's verify parent scope. ast.walk doesn't have parent links.
                    # We can identify functions by checking if they are top-level or method-level.
                    pass
                docstring = ast.get_docstring(node) or ""
                symbols.append({
                    "name": node.name,
                    "type": "function",
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "summary": docstring.strip().split("\n")[0] if docstring else f"Function {node.name}",
                    "details": docstring
                })
        
        # Determine Python exports (usually symbols defined or listed in __all__)
        # To be simple, we can consider class and function names as exports
        exports = [s["name"] for s in symbols if s["type"] in ("class", "function")]
        
        return symbols, list(set(imports)), list(set(exports))

    @staticmethod
    def analyze_javascript(code: str, file_path: str) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
        """
        Regex-based symbol extractor for Javascript/TypeScript files.
        """
        symbols = []
        imports = []
        exports = []
        
        lines = code.split("\n")
        
        # Imports
        # import { x } from 'y'; import x from 'y'; require('y')
        import_patterns = [
            r"import\s+.*\s+from\s+['\"](.*)['\"]",
            r"require\(['\"](.*)['\"]\)"
        ]
        for line in lines:
            for pattern in import_patterns:
                match = re.search(pattern, line)
                if match:
                    imports.append(match.group(1))

        # Exports
        # export const x = ...; export default class Y ...
        export_patterns = [
            r"export\s+(?:default\s+)?(?:class|const|let|var|function)\s+(\w+)",
            r"module\.exports\s*=\s*(\w+)"
        ]
        for line in lines:
            for pattern in export_patterns:
                match = re.search(pattern, line)
                if match:
                    exports.append(match.group(1))

        # Class definitions
        class_pattern = re.compile(r"(?:export\s+)?class\s+(\w+)")
        # Function definitions
        func_patterns = [
            re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("),
            re.compile(r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>")
        ]
        
        for idx, line in enumerate(lines, start=1):
            # Class
            match = class_pattern.search(line)
            if match:
                symbols.append({
                    "name": match.group(1),
                    "type": "class",
                    "start_line": idx,
                    "end_line": idx, # Simple estimation for JS
                    "summary": f"Class {match.group(1)}",
                    "details": ""
                })
                continue
                
            # Function
            for pattern in func_patterns:
                match = pattern.search(line)
                if match:
                    symbols.append({
                        "name": match.group(1),
                        "type": "function",
                        "start_line": idx,
                        "end_line": idx, # Simple estimation for JS
                        "summary": f"Function {match.group(1)}",
                        "details": ""
                    })
                    break

        return symbols, list(set(imports)), list(set(exports))

    @classmethod
    def analyze(cls, code: str, file_path: str) -> Dict[str, Any]:
        """
        Analyze code and return symbols, imports, and exports depending on language.
        """
        ext = file_path.split(".")[-1].lower() if "." in file_path else ""
        
        if ext in ("py", "pyw"):
            symbols, imports, exports = cls.analyze_python(code, file_path)
            lang = "python"
        elif ext in ("js", "jsx", "ts", "tsx"):
            symbols, imports, exports = cls.analyze_javascript(code, file_path)
            lang = "javascript"
        else:
            symbols, imports, exports = [], [], []
            lang = ext if ext else "text"
            
        return {
            "language": lang,
            "symbols": symbols,
            "imports": imports,
            "exports": exports
        }
