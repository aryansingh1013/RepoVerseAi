import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_heading_styled(doc, text, level):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.bold = True
    
    if level == 1:
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0, 0, 0)
    elif level == 2:
        run.font.size = Pt(12.5)
        run.font.color.rgb = RGBColor(0, 0, 0)
    else:
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0, 0, 0)
    return p

def add_body_paragraph(doc, text, bold_prefix="", indent=0):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent > 0:
        p.paragraph_format.left_indent = Inches(indent)
        
    if bold_prefix:
        r_bold = p.add_run(bold_prefix)
        r_bold.font.name = 'Times New Roman'
        r_bold.font.size = Pt(11)
        r_bold.font.bold = True
        
    r_body = p.add_run(text)
    r_body.font.name = 'Times New Roman'
    r_body.font.size = Pt(11)
    return p

def create_report(output_path, name, reg_no):
    doc = Document()
    
    # Page setup - Margins (1 inch)
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # ─────────────────────────────────────────────────────────────────────────
    # COVER PAGE
    # ─────────────────────────────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("SUMMER TRAINING/INTERNSHIP REPORT\n(Term Aug-Dec 2026)\n\n")
    run.font.name = 'Times New Roman'
    run.font.size = Pt(14)
    run.font.bold = True

    # Live Deployment Section
    p_live = doc.add_paragraph()
    p_live.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_live.paragraph_format.space_after = Pt(2)
    run_live = p_live.add_run("Live Deployment\n")
    run_live.font.name = 'Times New Roman'
    run_live.font.size = Pt(11)
    run_live.font.bold = True
    run_live.font.underline = True

    add_body_paragraph(doc, "https://github.com/aryansingh1013/RepoVerseAi", "Github: ")
    add_body_paragraph(doc, "https://aryansingh1013-repoverseai.static.hf.space", "Frontend (Live Demo): ")
    add_body_paragraph(doc, "https://repoverseai.onrender.com (Note: Cold start of ~40s when idle)", "Backend (API Service): ")

    doc.add_paragraph("\n")

    # Report Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run(
        "A REPORT ON\n\n"
        "REPOVERSE AI: AN INTERACTIVE 3D GALAXY EXPLORER AND SEMANTIC RAG SEARCH PLATFORM FOR MODERN CODEBASES\n\n"
    )
    run_title.font.name = 'Times New Roman'
    run_title.font.size = Pt(15)
    run_title.font.bold = True

    # Submitted By
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run(
        "SUBMITTED BY:\n\n"
        f"{name}\n"
        f"Registration Number: {reg_no}\n\n\n"
    )
    run_sub.font.name = 'Times New Roman'
    run_sub.font.size = Pt(12)
    run_sub.font.bold = True

    # University Footer
    p_univ = doc.add_paragraph()
    p_univ.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_univ = p_univ.add_run(
        "School of Computer Science and Engineering\n"
        "Lovely Professional University, Phagwara, Punjab"
    )
    run_univ.font.name = 'Times New Roman'
    run_univ.font.size = Pt(12)
    run_univ.font.bold = True
    
    doc.add_page_break()

    # ─────────────────────────────────────────────────────────────────────────
    # DECLARATION
    # ─────────────────────────────────────────────────────────────────────────
    add_heading_styled(doc, "DECLARATION", 1)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    decl_text = (
        f"I, {name}, hereby declare that the summer training/internship report entitled "
        "\"RepoVerse AI: An Interactive 3D Galaxy Explorer and Semantic RAG Search Platform for Modern Codebases\" "
        "submitted by me to the Department of Computer Science & Engineering, Lovely Professional University in "
        "partial fulfillment of the requirements for the award of the degree of Bachelor of Technology in "
        "Computer Science and Engineering is an authentic record of my training carried out during the period "
        "from June 2026 to July 2026 under the supervision of , Assistant Professor.\n\n"
        "The matter embodied in this training report has not been submitted by me for the award of any "
        "other degree or diploma of this or any other University."
    )
    add_body_paragraph(doc, decl_text)
    
    doc.add_paragraph("\n\n")
    p_sig = doc.add_paragraph()
    p_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sig.paragraph_format.line_spacing = 1.15
    r_sig = p_sig.add_run(f"Date: 15 Jul '26\nPlace: Phagwara\n\n\n{name}\nRegistration Number: {reg_no}")
    r_sig.font.name = 'Times New Roman'
    r_sig.font.size = Pt(11)
    r_sig.font.bold = True
    
    doc.add_page_break()

    # ─────────────────────────────────────────────────────────────────────────
    # CERTIFICATE
    # ─────────────────────────────────────────────────────────────────────────
    add_heading_styled(doc, "CERTIFICATE", 1)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    cert_text = (
        f"This is to certify that the Summer Training/Internship report entitled \"RepoVerse AI: An Interactive "
        "3D Galaxy Explorer and Semantic RAG Search Platform for Modern Codebases\" submitted by "
        f"{name} (Registration Number: {reg_no}) in partial fulfillment of the requirements for the award "
        "of the degree of Bachelor of Technology in Computer Science and Engineering, Lovely Professional "
        "University is a record of student's training work carried out under my supervision.\n\n"
        "To the best of my knowledge, the work presented here has reached the requisite standard for the "
        "submission of B.Tech summer training report."
    )
    add_body_paragraph(doc, cert_text)
    
    doc.add_paragraph("\n\n\n\n")
    p_cert_sig = doc.add_paragraph()
    p_cert_sig.paragraph_format.line_spacing = 1.2
    r_cert_sig = p_cert_sig.add_run(
        "___________________________\n"
        "[Rohit Bharti and Dipen Saini]\n"
        "Assistant Professor\n"
        "Department of Computer Science & Engineering\n\n\n\n\n\n"
        "___________________________\n"
        "Head of Department\n"
        "Department of Computer Science & Engineering"
    )
    r_cert_sig.font.name = 'Times New Roman'
    r_cert_sig.font.size = Pt(11)
    r_cert_sig.font.bold = True
    
    doc.add_page_break()

    # ─────────────────────────────────────────────────────────────────────────
    # ACKNOWLEDGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    add_heading_styled(doc, "ACKNOWLEDGEMENT", 1)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    ack_text = (
        "I would like to express my sincere gratitude and deep appreciation to my training supervisors, "
        "Rohit Bharti and Dipen Saini, Assistant Professor, Department of Computer Science & Engineering, for providing "
        "support, constructive advice, and guidance throughout my summer training curriculum and project execution. "
        "Their technical expertise and encouragement have been instrumental in the completion of this project.\n\n"
        "I also extend my heartfelt thanks to the Head of the Department and the administration of Lovely Professional "
        "University for providing the academic infrastructure and laboratories that facilitated this work. I am grateful "
        "to the open-source community behind FastAPI, LangChain, LangGraph, and React, whose libraries made this project "
        "modular, performant, and scalable.\n\n"
        "Finally, I would like to thank my parents, family, and peers for their continuous support, patience, and "
        "encouragement throughout this academic term."
    )
    add_body_paragraph(doc, ack_text)
    
    doc.add_paragraph("\n\n")
    p_ack_sub = doc.add_paragraph()
    p_ack_sub.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_ack_sub = p_ack_sub.add_run(f"{name}\nRegistration Number: {reg_no}")
    r_ack_sub.font.name = 'Times New Roman'
    r_ack_sub.font.size = Pt(11)
    r_ack_sub.font.bold = True
    
    doc.add_page_break()

    # ─────────────────────────────────────────────────────────────────────────
    # TABLE OF CONTENTS
    # ─────────────────────────────────────────────────────────────────────────
    add_heading_styled(doc, "TABLE OF CONTENTS", 1)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    toc_p = doc.add_paragraph()
    toc_p.paragraph_format.line_spacing = 1.3
    r_toc = toc_p.add_run(
        "Declaration\t\t\ti\n"
        "Certificate\t\t\tii\n"
        "Acknowledgement\t\t\tiii\n"
        "Table of Contents\t\t\tiv\n"
        "1. INTRODUCTION OF ORGANIZATION\t\t\t1\n"
        "   1.1 Overview of 3D Galaxy Visualization & RAG\t\t\t1\n"
        "   1.2 Open-Source Ecosystem and Collaborative Development\t\t\t1\n"
        "   1.3 Project Motivation: Visualizing Complex Codebases\t\t\t2\n"
        "2. SUMMER TRAINING COURSE/INTERNSHIP CONTENT DETAIL\t\t\t3\n"
        "   2.1 Training Curriculum Overview\t\t\t3\n"
        "   2.2 Week-by-Week Learning and Execution Path\t\t\t3\n"
        "3. SUMMER TRAINING/INTERNSHIP PROJECT DETAIL\t\t\t6\n"
        "   3.1 Problem Statement\t\t\t6\n"
        "   3.2 Project Outcomes\t\t\t6\n"
        "   3.3 System Architecture\t\t\t7\n"
        "   3.4 Technologies Used\t\t\t8\n"
        "4. SOURCE CODE OR SYSTEM SNAPSHOTS\t\t\t10\n"
        "   4.1 Key Implementation Snippets\t\t\t10\n"
        "   4.2 System Interface Snapshots\t\t\t13\n"
        "12. BIBLIOGRAPHY\t\t\t15\n"
    )
    r_toc.font.name = 'Times New Roman'
    r_toc.font.size = Pt(11)
    
    doc.add_page_break()

    # ─────────────────────────────────────────────────────────────────────────
    # CHAPTER 1
    # ─────────────────────────────────────────────────────────────────────────
    add_heading_styled(doc, "1. INTRODUCTION OF ORGANIZATION", 1)
    
    add_heading_styled(doc, "1.1 OVERVIEW OF 3D GALAXY VISUALIZATION & RAG", 2)
    p1 = (
        "RepoVerse AI represents a foundational shift in how developers explore, understand, and interact "
        "with large, complex codebases. While traditional IDEs provide text-based directories and search utilities, "
        "they fail to show the high-level structural patterns, coupling, and nested hierarchies of a system. "
        "RepoVerse AI resolves this constraint by mapping code structures into an interactive 3D space-themed galaxy. "
        "Files and folders are translated to stars, planets, and moons, while semantic code symbols are indexed using a "
        "Retrieval-Augmented Generation (RAG) pipeline. This combines visual representation and language model "
        "intelligence, enabling developers to chat directly with their repository."
    )
    add_body_paragraph(doc, p1)
    
    add_heading_styled(doc, "1.2 OPEN-SOURCE ECOSYSTEM AND COLLABORATIVE DEVELOPMENT", 2)
    p2 = (
        "This internship and research work was conducted within the framework of an Open-Source Software "
        "Development Lab environment, focusing on modern collaborative practices. The development pipeline simulated "
        "an industry-grade agile environment, involving git version control, detailed code documentation, and incremental "
        "integration. The research objectives centered on creating local, low-footprint, private pipelines to crawl, parse, "
        "index, and visualize code repositories. Through this model, students get hands-on experience in full-stack "
        "development, ranging from AST parsing algorithms and vector embeddings in Python, to 3D rendering with React Three Fiber."
    )
    add_body_paragraph(doc, p2)
    
    add_heading_styled(doc, "1.3 PROJECT MOTIVATION: VISUALIZING COMPLEX CODEBASES", 2)
    p3 = (
        "Developers onboarding onto large legacy projects face a massive cognitive load trying to map out file dependencies "
        "and folder structures. Visualizing these relationships makes system boundaries and modularity immediately clear. "
        "By hosting the backend-only FastAPI engine on Render (optimized to run within 512MB RAM using lazy-loaded embeddings) "
        "and serving the React client statically on Hugging Face Spaces, RepoVerse AI offers a free, lightweight, and secure "
        "hosting model. Security concerns are addressed since the LLM requests are run via secure, rate-optimized API "
        "keys (Groq/Gemini) instead of sending raw proprietary files directly to unverified servers, keeping the footprint local."
    )
    add_body_paragraph(doc, p3)
    
    doc.add_page_break()

    # ─────────────────────────────────────────────────────────────────────────
    # CHAPTER 2
    # ─────────────────────────────────────────────────────────────────────────
    add_heading_styled(doc, "2. SUMMER TRAINING COURSE/INTERNSHIP CONTENT DETAIL", 1)
    
    add_heading_styled(doc, "2.1 TRAINING CURRICULUM OVERVIEW", 2)
    p4 = (
        "The six-week training curriculum was structured to cover the entire lifecycle of a modern AI-powered web application. "
        "The syllabus advanced from Python asynchronous coding and folder structural AST parsing to natural language "
        "processing (NLP), semantic search indexing, relational database schema designing, RESTful API routing, real-time "
        "communication protocols, frontend 3D rendering, and DevOps deployment. Each week, specific technical milestones "
        "were defined and verified against the RepoVerse AI project codebase."
    )
    add_body_paragraph(doc, p4)
    
    add_heading_styled(doc, "2.2 WEEK-BY-WEEK LEARNING AND EXECUTION PATH", 2)
    add_body_paragraph(doc, 
        "Acquired deep proficiency in Python's asynchronous programming framework (asyncio). "
        "Studied the mechanics of code parsing and AST (Abstract Syntax Tree) traversal. Designed a directory walking "
        "utility that maps code layouts and identifies entry points (e.g. app.py, index.ts) recursively while ignoring "
        "dependencies like node_modules.", 
        "• Week 1: Foundations of Asynchronous Code Parsing. "
    )
    add_body_paragraph(doc, 
        "Focused on syntax tree dissection and code tokenization. Used Python's ast module to extract "
        "class structures, method signatures, imports, and docstrings from python files. Designed overlapping character-based "
        "chunking algorithms to partition codebase files into semantically clean parts for embedding (typically 1000 characters "
        "with 10% overlap).", 
        "• Week 2: AST Node Analysis, Tokenization, and Code Chunking. "
    )
    add_body_paragraph(doc, 
        "Explored vector space models and token embeddings. Integrated local embedding models "
        "(such as BAAI/bge-small-en-v1.5) and cloud APIs. Learned how to configure and interact with ChromaDB, a lightweight "
        "vector database. Programmed vector collection creation, document insertion with metadata filtering, and L2 distance similarity searching.", 
        "• Week 3: Vector Embeddings and Indexing with Vector Databases. "
    )
    add_body_paragraph(doc, 
        "Designed REST APIs using FastAPI to run AST scans and trigger indexing. Integrated "
        "real-time WebSocket connection managers to stream agent reasoning steps directly to clients. Configured CORS, "
        "request validation schemas, and database persistence layers to handle asynchronous indexing queues.", 
        "• Week 4: API Development, Asynchronous Tasks, and WebSockets. "
    )
    add_body_paragraph(doc, 
        "Built the LangChain and LangGraph orchestration layer. Configured conversational memory "
        "that appends multi-turn history. Programmed a dynamic Skills Engine (Overview, Architecture, Health, Security, "
        "Performance) using a hybrid approach—combining Python static code analysis (0 tokens) and cached LLM prompts (under 1000 tokens) "
        "to prevent credit exhaustion.", 
        "• Week 5: LangGraph Agentic Chains and AI Skills Engine. "
    )
    add_body_paragraph(doc, 
        "Created an interactive frontend using React, Vite, and React Three Fiber (Three.js) to render "
        "the 3D galaxy scene. Integrated OrbitControls and animated transition hooks. Built the production Dockerfile and successfully "
        "deployed the backend to Render (optimized under 512MB RAM) and the static client to Hugging Face Spaces using HashRouter.", 
        "• Week 6: Frontend 3D Galaxy Rendering and DevOps Deployment. "
    )

    doc.add_page_break()

    # ─────────────────────────────────────────────────────────────────────────
    # CHAPTER 3
    # ─────────────────────────────────────────────────────────────────────────
    add_heading_styled(doc, "3. SUMMER TRAINING/INTERNSHIP PROJECT DETAIL", 1)
    
    add_heading_styled(doc, "3.1 PROBLEM STATEMENT", 2)
    p5 = (
        "Modern code repositories contain hundreds of files and dynamic configurations. Software developers onboarding onto "
        "new codebases face severe cognitive bottlenecks due to:\n"
        "1. Dynamic File Coupling: Plain text searches fail to display parent-child relationships and import hierarchies.\n"
        "2. Redundant Embedding Overheads: Re-embedding entire codebases on every minor edit is computationally expensive and locks databases.\n"
        "3. High API Credit Usage: Calling LLMs on raw files quickly exhausts rate limits and API budgets.\n"
        "4. Hallucinations: Standard LLMs hallucinate code details if not bounded by strict retrieval contexts."
    )
    add_body_paragraph(doc, p5)
    
    add_heading_styled(doc, "3.2 PROJECT OUTCOMES", 2)
    p6 = (
        "The development of RepoVerse AI successfully solved these bottlenecks through:\n"
        "1. 3D Space-Themed Galaxy Visualization: Implemented a Three.js interface displaying folders as stars and files as orbiting planets.\n"
        "2. Dynamic Skills Caching: Built a disk-based JSON caching layer (.repoverse/skills_cache.json) reducing repeat analysis costs to 0 tokens.\n"
        "3. Hybrid Static-AI Analysis: Implemented pure AST parsing for dependencies (0 tokens) and highly condensed prompts (< 1100 tokens) for LLMs.\n"
        "4. High-Fidelity RAG Search: Vector searches over ChromaDB provide direct file path citations for every agent response, eliminating hallucinations."
    )
    add_body_paragraph(doc, p6)
    
    add_heading_styled(doc, "3.3 SYSTEM ARCHITECTURE", 2)
    p7 = (
        "RepoVerse AI follows a decoupled architecture. The frontend client (React + Three.js) is served statically "
        "on Hugging Face. The backend server (FastAPI + LangGraph) runs inside a Docker container on Render. "
        "When a workspace is opened, the AST parser maps out structural nodes and stores them in ChromaDB. "
        "When a user chats or clicks a Skill, the backend queries the vector store, formats the conversation history, "
        "and streams LLM completions back via WebSockets."
    )
    add_body_paragraph(doc, p7)
    
    add_heading_styled(doc, "3.4 TECHNOLOGIES USED", 2)
    
    # Table of Technologies
    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Technology Layer'
    hdr_cells[1].text = 'Library/Framework'
    hdr_cells[2].text = 'Role in RepoVerse AI'
    
    # Style header
    for cell in hdr_cells:
        set_cell_background(cell, "7C3AED")
        set_cell_margins(cell, top=120, bottom=120)
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.name = 'Times New Roman'
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.size = Pt(10)
                
    tech_data = [
        ("Backend Framework", "FastAPI / Uvicorn", "Handles HTTP endpoints, WebSocket chat streams, and CORS middlewares."),
        ("Vector Store", "ChromaDB", "Maintains document chunk vector indexes and handles similarity searches."),
        ("LLM Orchestrator", "LangGraph / LangChain", "Orchestrates AI agents, manages state memory, and structures prompts."),
        ("3D Graphic Engine", "Three.js / React Three Fiber", "Renders the interactive 3D galaxy scene and orbital planets."),
        ("Embedding Engine", "BAAI/bge-small-en-v1.5", "Converts code chunks into dense numerical embedding vectors."),
        ("LLM API Provider", "Groq / Gemini / OpenRouter", "Executes fast grounded completes under strict prompt constraints."),
        ("Frontend client", "React (v18) / Vite / Tailwind", "Renders UI control dashboards, sidebars, and chat overlays.")
    ]
    
    for layer, lib, role in tech_data:
        row_cells = table.add_row().cells
        row_cells[0].text = layer
        row_cells[1].text = lib
        row_cells[2].text = role
        for cell in row_cells:
            set_cell_margins(cell, top=80, bottom=80)
            set_cell_background(cell, "F9FAFB")
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(9.5)

    doc.add_page_break()

    # ─────────────────────────────────────────────────────────────────────────
    # CHAPTER 4
    # ─────────────────────────────────────────────────────────────────────────
    add_heading_styled(doc, "4. SOURCE CODE OR SYSTEM SNAPSHOTS", 1)
    
    add_heading_styled(doc, "4.1 KEY IMPLEMENTATION SNIPPETS", 2)
    p8 = (
        "This section highlights critical backend logic implemented during the summer training internship. "
        "The backend is written in Python using FastAPI schemas and LangGraph frameworks, ensuring modularity."
    )
    add_body_paragraph(doc, p8)
    
    add_heading_styled(doc, "4.1.1 DYNAMIC SKILLS CACHING LAYER (cache.py)", 3)
    p_code1 = (
        "To prevent duplicate LLM calls and credit exhaustion, we built a JSON-based caching utility. "
        "It stores generated reports locally under .repoverse/skills_cache.json, serving them instantly on repeats:"
    )
    add_body_paragraph(doc, p_code1)
    
    # Code block 1 (Table container)
    c_table1 = doc.add_table(rows=1, cols=1)
    c_table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell1 = c_table1.rows[0].cells[0]
    set_cell_background(c_cell1, "F3F4F6")
    set_cell_margins(c_cell1, top=140, bottom=140, left=140, right=140)
    
    code_snippet1 = (
        "def get_cached(slug: str, workspace_dir: str) -> Optional[Dict[str, Any]]:\n"
        "    cache = _load_cache(workspace_dir)\n"
        "    key = f\"{slug}:{_workspace_hash(workspace_dir)}\"\n"
        "    result = cache.get(key)\n"
        "    if result is not None:\n"
        "        print(f\"SkillCache: Cache HIT for '{slug}' — 0 tokens used.\")\n"
        "    return result\n\n"
        "def set_cached(slug: str, workspace_dir: str, result: Dict[str, Any]) -> None:\n"
        "    cache = _load_cache(workspace_dir)\n"
        "    key = f\"{slug}:{_workspace_hash(workspace_dir)}\"\n"
        "    cache[key] = result\n"
        "    _save_cache(workspace_dir, cache)"
    )
    cp1 = c_cell1.paragraphs[0]
    cp1.paragraph_format.line_spacing = 1.05
    c_run1 = cp1.add_run(code_snippet1)
    c_run1.font.name = 'Courier New'
    c_run1.font.size = Pt(8.5)

    doc.add_paragraph("\n")

    add_heading_styled(doc, "4.1.2 LAZY LOAD EMBEDDINGS (vector_store.py)", 3)
    p_code2 = (
        "Render free instances only provide 512MB RAM. Eagerly importing PyTorch and SentenceTransformer "
        "on startup crashes the server. We solved this by lazy-loading the imports inside the property getter:"
    )
    add_body_paragraph(doc, p_code2)

    # Code block 2 (Table container)
    c_table2 = doc.add_table(rows=1, cols=1)
    c_table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell2 = c_table2.rows[0].cells[0]
    set_cell_background(c_cell2, "F3F4F6")
    set_cell_margins(c_cell2, top=140, bottom=140, left=140, right=140)
    
    code_snippet2 = (
        "class EmbeddingsManager:\n"
        "    def __init__(self):\n"
        "        self.model_name = settings.EMBEDDING_MODEL\n"
        "        self._model = None\n\n"
        "    @property\n"
        "    def model(self):\n"
        "        if self._model is None:\n"
        "            try:\n"
        "                from sentence_transformers import SentenceTransformer\n"
        "                self._model = SentenceTransformer(self.model_name)\n"
        "            except Exception as e:\n"
        "                from sentence_transformers import SentenceTransformer\n"
        "                self._model = SentenceTransformer(settings.EMBEDDING_MODEL_FALLBACK)\n"
        "        return self._model"
    )
    cp2 = c_cell2.paragraphs[0]
    cp2.paragraph_format.line_spacing = 1.05
    c_run2 = cp2.add_run(code_snippet2)
    c_run2.font.name = 'Courier New'
    c_run2.font.size = Pt(8.5)

    add_heading_styled(doc, "4.2 SYSTEM INTERFACE SNAPSHOTS", 2)
    p_snaps = (
        "The system interface comprises an interactive React client rendering a 3D canvas of code nodes, "
        "an input console to index GitHub repositories on demand, and an AI chat console mapping vector "
        "database retrieval results into direct code citations."
    )
    add_body_paragraph(doc, p_snaps)

    doc.add_page_break()

    # ─────────────────────────────────────────────────────────────────────────
    # BIBLIOGRAPHY
    # ─────────────────────────────────────────────────────────────────────────
    add_heading_styled(doc, "12. BIBLIOGRAPHY", 1)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p_bib = doc.add_paragraph()
    p_bib.paragraph_format.line_spacing = 1.25
    r_bib = p_bib.add_run(
        "• FastAPI Web Framework Documentation. https://fastapi.tiangolo.com/ - "
        "Consulted for REST API architectures, WebSockets, and startup lifecycles.\n\n"
        "• LangChain Documentation and Conceptual Guidelines. https://python.langchain.com/ - "
        "Utilized for constructing prompt structures, memory state, and vector chains.\n\n"
        "• Chroma DB: The AI-native open-source vector database. https://www.trychroma.com/ - "
        "Referenced for embedding indexing, persistent client setups, and similarity queries.\n\n"
        "• React Three Fiber (Three.js) Documentation. https://docs.pmnd.rs/react-three-fiber - "
        "Consulted for canvas settings, orbit control hooks, and 3D web rendering configurations.\n\n"
        "• Groq Developer Documentation. https://console.groq.com/docs - "
        "Utilized for setting model parameters (llama-3.3-70b-versatile) and token usage limits."
    )
    r_bib.font.name = 'Times New Roman'
    r_bib.font.size = Pt(11)

    doc.save(output_path)
    print(f"Report successfully saved to {output_path}!")

if __name__ == "__main__":
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "RepoVerse_AI_Summer_Training_Report.docx"))
    create_report(out, "Aryan Singh", "12408478")
