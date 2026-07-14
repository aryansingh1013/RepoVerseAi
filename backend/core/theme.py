# Space Theme Styling Configuration served to Frontend

THEME_CONFIG = {
    "name": "RepoVerse Space Station",
    "theme_mode": "dark",
    "palette": {
        "universe_bg": "radial-gradient(circle at center, #0B0B1E 0%, #030308 100%)",
        "galaxy_accent": "#7C3AED", # Deep Purple
        "constellation_colors": {
            "Auth": "#3B82F6",         # Blue (Security)
            "Database": "#10B981",     # Emerald (Storage)
            "Core": "#F59E0B",         # Amber (Orchestration)
            "API": "#EC4899",          # Pink (Interface)
            "RAG": "#8B5CF6",          # Violet (Knowledge)
            "Agent": "#EF4444",        # Red (Action)
            "Default": "#6B7280"       # Gray (General)
        },
        "star_color": "#A78BFA",       # Folder (Star) color
        "planet_color": "#60A5FA",     # File (Planet) color
        "moon_color": "#FBBF24",       # Function/Class (Moon) color
        "neon_shadow": "0 0 10px rgba(124, 58, 237, 0.5)",
        "glass_bg": "rgba(15, 23, 42, 0.45)",
        "glass_border": "rgba(255, 255, 255, 0.08)"
    }
}
