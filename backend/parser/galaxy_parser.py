import os
import json
from typing import Dict, List, Any
from backend.parser.code_analyzer import CodeAnalyzer
from backend.core.config import settings

class GalaxyParser:
    EXCLUDE_DIRS = {
        ".git", "__pycache__", "node_modules", ".gemini", 
        "venv", ".venv", "db", "dist", "build", ".agents",
        ".vscode", ".idea"
    }
    
    EXCLUDE_FILES = {
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        ".gitignore", ".env", "tsconfig.tsbuildinfo"
    }

    def __init__(self, root_dir: str = None):
        self.root_dir = root_dir or settings.WORKSPACE_DIR

    def scan_directory(self) -> Dict[str, Any]:
        """
        Recursively scans the directory and returns a space-themed hierarchical mapping:
        Universe -> Galaxy -> Constellations -> Stars -> Planets -> Moons.
        """
        galaxy_name = os.path.basename(self.root_dir)
        
        # We define Constellations as high-level directories (e.g. backend, frontend, docs)
        constellations = {}
        
        # Traverse directory
        for root, dirs, files in os.walk(self.root_dir):
            # Prune directories in place
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            # Check relative depth
            rel_path = os.path.relpath(root, self.root_dir)
            if rel_path == ".":
                # Root level files go under "Core System" constellation
                constellation_name = "System Center"
            else:
                parts = rel_path.split(os.sep)
                # First subfolder name is the Constellation
                constellation_name = parts[0].capitalize()
                
            if constellation_name not in constellations:
                constellations[constellation_name] = {
                    "name": constellation_name,
                    "type": "constellation",
                    "stars": {} # Folders inside this constellation
                }
                
            # Star represents the current folder inside the constellation
            star_path = rel_path if rel_path != "." else ""
            star_name = os.path.basename(root) if rel_path != "." else "core"
            
            star_node = {
                "name": star_name,
                "path": star_path.replace("\\", "/"),
                "type": "star",
                "planets": [] # Files
            }
            
            for file in files:
                if file in self.EXCLUDE_FILES:
                    continue
                    
                _, ext = os.path.splitext(file)
                # Skip common binary/generated files during tree scan
                SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff",
                             ".woff2", ".ttf", ".eot", ".otf", ".map", ".lock", ".bin",
                             ".pyc", ".pyo", ".exe", ".dll", ".so", ".o"}
                if ext.lower() in SKIP_EXTS:
                    continue

                file_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(file_path, self.root_dir).replace("\\", "/")
                
                try:
                    file_size = os.path.getsize(file_path)
                except OSError:
                    file_size = 1000

                planet_node = {
                    "name": file,
                    "path": rel_file_path,
                    "type": "planet",
                    "language": ext.lstrip(".") or "text",
                    "size_bytes": file_size,
                    "imports": [],
                    "exports": [],
                    "moons": []
                }
                star_node["planets"].append(planet_node)
                
            # Save the star under the constellation
            if star_path == "":
                constellations[constellation_name]["stars"]["root"] = star_node
            else:
                constellations[constellation_name]["stars"][star_path.replace("\\", "/")] = star_node

        # Format output
        constellations_list = []
        for c_key, c_val in constellations.items():
            stars_list = list(c_val["stars"].values())
            # Only include constellations that contain files
            if any(len(s["planets"]) > 0 for s in stars_list):
                c_val["stars"] = stars_list
                constellations_list.append(c_val)

        return {
            "universe": "RepoVerse",
            "galaxy": galaxy_name,
            "constellations": constellations_list
        }

    def generate_heuristics_summary(self) -> Dict[str, Any]:
        """
        Gathers structural insights from files to compile an offline summary of the repository.
        """
        tech_stack = []
        entry_points = []
        dependencies = []
        
        file_types = {}
        file_count = 0
        
        # Analyze package.json or requirements.txt
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for file in files:
                if file in self.EXCLUDE_FILES:
                    continue
                    
                file_count += 1
                ext = file.split(".")[-1].lower() if "." in file else "unknown"
                file_types[ext] = file_types.get(ext, 0) + 1
                
                # Scan package.json for frontend dependencies
                if file == "package.json":
                    try:
                        with open(os.path.join(root, file), "r") as f:
                            pjs = json.load(f)
                            tech_stack.append("React" if "react" in pjs.get("dependencies", {}) else "Node.js")
                            if "vite" in pjs.get("devDependencies", {}):
                                tech_stack.append("Vite")
                            if "tailwindcss" in pjs.get("dependencies", {}) or "tailwindcss" in pjs.get("devDependencies", {}):
                                tech_stack.append("TailwindCSS")
                            
                            deps = list(pjs.get("dependencies", {}).keys()) + list(pjs.get("devDependencies", {}).keys())
                            dependencies.extend(deps[:15]) # cap to 15
                    except Exception:
                        pass
                
                # Scan requirements.txt for python dependencies
                if file == "requirements.txt":
                    try:
                        with open(os.path.join(root, file), "r") as f:
                            lines = f.readlines()
                            tech_stack.append("Python")
                            for line in lines:
                                dep = line.strip().split("=")[0].split(">")[0].split("<")[0].strip()
                                if dep and not dep.startswith("#"):
                                    dependencies.append(dep)
                    except Exception:
                        pass
                
                # Entry points heuristics
                if file in ("main.py", "app.py", "index.ts", "index.js", "main.tsx", "main.ts"):
                    rel_file = os.path.relpath(os.path.join(root, file), self.root_dir).replace("\\", "/")
                    entry_points.append(rel_file)

        # Build language summary
        if file_types.get("py", 0) > 0:
            tech_stack.append("Python")
        if file_types.get("ts", 0) > 0 or file_types.get("tsx", 0) > 0:
            tech_stack.append("TypeScript")
        if file_types.get("js", 0) > 0 or file_types.get("jsx", 0) > 0:
            tech_stack.append("JavaScript")
        if file_types.get("css", 0) > 0:
            tech_stack.append("CSS")
            
        tech_stack = list(set(tech_stack))
        dependencies = list(set(dependencies))
        
        # Overview template
        summary = {
            "title": f"Galaxy: {os.path.basename(self.root_dir)}",
            "tech_stack": tech_stack,
            "entry_points": entry_points,
            "dependencies": dependencies[:20],
            "file_metrics": {
                "total_files": file_count,
                "languages": file_types
            },
            "readme_summary": f"This repository contains {file_count} files spanning {', '.join(tech_stack)} components.",
            "architecture": "The repository is structured with high-level directories mapped as constellations representing different feature modules. It follows a multi-tier codebase architecture."
        }
        
        return summary
