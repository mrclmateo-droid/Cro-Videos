"""Presets de edición. En el MVP un preset controla el estilo de subtítulos.
Los otros presets del producto (Educational, Storytelling, Cinematic, Business, Creator)
requieren zoom/ritmo/tipografías propias y se agregan cuando existan esas funciones."""

BASE_STYLE = {
    "font": "Liberation Sans",
    "font_size_pct": 6.5,
    "primary_color": "#FFFFFF",
    "highlight_color": "#FFD400",
    "outline_color": "#000000",
    "outline_width": 3.0,
    "shadow": 1.0,
    "bold": True,
    "uppercase": False,
    "max_words": 3,
    "highlight_active_word": True,
}

PRESETS: dict[str, dict] = {
    "clean_minimal": {
        "label": "Clean Minimal",
        "caption": {
            "font_size_pct": 5.5, "bold": False, "outline_width": 2.0, "shadow": 0.0,
            "max_words": 5, "highlight_active_word": False,
        },
    },
    "podcast_viral": {
        "label": "Podcast Viral",
        "caption": {"max_words": 3, "highlight_color": "#FFD400"},
    },
    "high_energy": {
        "label": "High Energy",
        "caption": {
            "font_size_pct": 8.0, "uppercase": True, "outline_width": 4.0,
            "max_words": 2, "highlight_color": "#00E5FF",
        },
    },
}

DEFAULT_PRESET = "podcast_viral"


def caption_style(preset: str) -> dict:
    return {**BASE_STYLE, **PRESETS[preset]["caption"]}
