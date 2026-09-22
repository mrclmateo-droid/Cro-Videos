"""Generación de subtítulos ASS con resaltado palabra por palabra y safe zones."""

_SENTENCE_END = (".", "?", "!", "…")


def _ass_color(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def _tag_color(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def _ts(t: float) -> str:
    cs = int(round(max(0.0, t) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\\", "").replace("\n", " ").strip()


def group_lines(words: list[dict], max_words: int, gap: float = 0.6) -> list[list[dict]]:
    lines: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur and (len(cur) >= max_words or w["s"] - cur[-1]["e"] >= gap):
            lines.append(cur)
            cur = []
        cur.append(w)
        if w["w"].rstrip("\"”’)").endswith(_SENTENCE_END):
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return lines


def build_ass(words: list[dict], style: dict, out_w: int, out_h: int, aspect: str) -> str:
    fs = int(min(out_w, out_h) * style["font_size_pct"] / 100)
    # Safe zone: en 9:16 la UI de TikTok/Reels/Shorts tapa ~25% inferior; se sube el texto.
    margin_v = int(out_h * (0.26 if aspect == "9:16" else 0.07))
    margin_lr = int(out_w * 0.08)
    bold = -1 if style["bold"] else 0
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {out_w}\nPlayResY: {out_h}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{style['font']},{fs},{_ass_color(style['primary_color'])},"
        f"{_ass_color(style['primary_color'])},{_ass_color(style['outline_color'])},&H64000000,"
        f"{bold},0,0,0,100,100,0,0,1,{style['outline_width']},{style['shadow']},2,"
        f"{margin_lr},{margin_lr},{margin_v},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    def dialogue(start: float, end: float, text: str) -> str:
        return f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{text}\n"

    lines = group_lines(words, int(style["max_words"]))
    base_c, hi_c = _tag_color(style["primary_color"]), _tag_color(style["highlight_color"])
    events: list[str] = []
    for li, line in enumerate(lines):
        texts = [_clean(w["w"]) for w in line]
        if style["uppercase"]:
            texts = [t.upper() for t in texts]
        next_line_start = lines[li + 1][0]["s"] if li + 1 < len(lines) else None

        if style["highlight_active_word"]:
            for i, w in enumerate(line):
                nxt = line[i + 1]["s"] if i + 1 < len(line) else None
                end = nxt if nxt is not None and nxt - w["e"] < 0.5 else w["e"] + 0.05
                if i == len(line) - 1 and next_line_start is not None:
                    end = min(end, next_line_start)
                parts = [
                    ("{\\1c" + hi_c + "}" + t + "{\\1c" + base_c + "}") if k == i else t
                    for k, t in enumerate(texts)
                ]
                events.append(dialogue(w["s"], max(end, w["s"] + 0.05), " ".join(parts)))
        else:
            end = line[-1]["e"] + 0.05
            if next_line_start is not None:
                end = min(end, next_line_start)
            events.append(dialogue(line[0]["s"], max(end, line[0]["s"] + 0.05), " ".join(texts)))
    return header + "".join(events)
