"""Treaty text and WTO case excerpts, plus the deterministic checks on quotes and facts.

Each source is one text file in knowledge/treaty/ or knowledge/cases/:

    # Lines starting with '#' are comments and are ignored.
    @short: Korea – Beef (AB)
    @citation: Appellate Body Report, Korea — Measures Affecting ... (11 December 2000)
    @url: https://www.wto.org/...
    @summary: One sentence on the facts of the dispute (used to find similar disputes).

    [137 | lft]
    Verbatim text of paragraph 137 ...

The line in square brackets gives the pinpoint (paragraph number or other
locator) and the analysis steps the excerpt is relevant to. Each analysis step
only receives the excerpts tagged for it (narrow context).

All checks in this file are ordinary string matching. No AI is involved.
"""

import re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
SOURCE_FOLDERS = ["treaty", "cases"]   # treaty sources are listed first

LIKENESS_STEPS = ["physical_properties", "end_uses", "consumers", "tariff", "likeness"]
ALL_STEPS = ["scope"] + LIKENESS_STEPS + ["affecting", "lft"]

# Tags that may be used after the '|' in an excerpt header.
STEP_TAGS = {
    "all": ALL_STEPS,
    "like": LIKENESS_STEPS,
    "scope": ["scope"],
    "physical": ["physical_properties"],
    "end_uses": ["end_uses"],
    "consumers": ["consumers"],
    "tariff": ["tariff"],
    "likeness": ["likeness"],
    "affecting": ["affecting"],
    "lft": ["lft"],
}

EXCERPT_HEADER = re.compile(r"^\[\s*([^|\]]+?)\s*\|\s*([^\]]+?)\s*\]\s*$")
METADATA_LINE = re.compile(r"^@(\w+)\s*:\s*(.*)$")
NUMERIC_PINPOINT = re.compile(r"^[\d.]+(\s*[–-]\s*[\d.]+)?$")


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

def normalise_text(text):
    """Make matching robust to curly quotes, dashes, line breaks and case."""
    replacements = {
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", " ": " ", "­": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip().lower()


def normalise_quote(text):
    """Normalise a quoted passage and drop surrounding quote marks and end punctuation."""
    return normalise_text(text).strip(" \"'.,;:…")


def normalise_cite(text):
    """'Korea – Beef (AB) [137]' and 'Korea - Beef (AB), para 137' both become 'koreabeefab137'."""
    text = normalise_text(text)
    text = re.sub(r"\b(paras?|paragraphs?)\b|¶", "", text)
    return re.sub(r"[^a-z0-9:.]", "", text)


def make_cite(short, pinpoint):
    """Short citation with an AGLC-style pinpoint: paragraph numbers go in square brackets."""
    if NUMERIC_PINPOINT.match(pinpoint):
        return f"{short} [{pinpoint}]"
    return f"{short} {pinpoint}"


# ---------------------------------------------------------------------------
# Loading the knowledge files
# ---------------------------------------------------------------------------

def parse_source_file(path, kind):
    source = {
        "id": path.stem, "kind": kind, "short": path.stem, "citation": "", "url": "", "summary": "",
        "excerpts": [], "problems": [],
    }
    current = None
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        header = EXCERPT_HEADER.match(stripped)
        metadata = METADATA_LINE.match(stripped)
        if header:
            pinpoint, tags = header.group(1), header.group(2)
            steps = []
            for tag in (t.strip().lower() for t in tags.split(",")):
                if tag in STEP_TAGS:
                    steps += [s for s in STEP_TAGS[tag] if s not in steps]
                else:
                    source["problems"].append(f"line {line_number}: unknown step tag '{tag}'")
            current = {"pinpoint": pinpoint, "steps": steps, "lines": []}
            source["excerpts"].append(current)
        elif metadata and current is None:
            key = metadata.group(1).lower()
            if key in {"short", "citation", "url", "summary"}:
                source[key] = metadata.group(2).strip()
        elif current is not None:
            current["lines"].append(line)

    for excerpt in source["excerpts"]:
        excerpt["text"] = "\n".join(excerpt.pop("lines")).strip()
        excerpt["cite"] = make_cite(source["short"], excerpt["pinpoint"])
        excerpt["source_id"] = source["id"]
    if not source["citation"]:
        source["problems"].append("missing @citation line")
    return source


def load_library():
    """Read every source file. Returns a list of sources (treaty first, then cases A-Z)."""
    library = []
    for kind in SOURCE_FOLDERS:
        folder = KNOWLEDGE_DIR / kind
        if not folder.exists():
            continue
        sources = [parse_source_file(path, kind) for path in sorted(folder.glob("*.txt"))]
        library += sorted(sources, key=lambda s: s["short"].lower())
    return library


def filled_excerpts(source):
    return [e for e in source["excerpts"] if e["text"]]


def excerpts_for_step(step_key, library):
    """The excerpts (with text) that are tagged for this step."""
    return [e for source in library for e in filled_excerpts(source) if step_key in e["steps"]]


def format_authorities(excerpts):
    """The AUTHORITIES block sent to the model."""
    return "\n\n".join(f"SOURCE: {e['cite']}\nTEXT: {e['text']}" for e in excerpts)


# ---------------------------------------------------------------------------
# Checks (deterministic, no AI)
# ---------------------------------------------------------------------------

def check_quotes(quotes, excerpts):
    """Check each quote against the excerpt it cites.

    Returns (verified, failed). A failed quote records where (if anywhere) the
    text was actually found, so the pinpoint can be corrected later.
    """
    by_cite = {normalise_cite(e["cite"]): e for e in excerpts}
    verified, failed = [], []
    for quote in quotes:
        text = normalise_quote(quote["text"])
        if not text:
            continue
        cited = by_cite.get(normalise_cite(quote["source"]))
        if cited and text in normalise_text(cited["text"]):
            verified.append({"source": cited["cite"], "text": quote["text"],
                             "source_id": cited["source_id"], "status": "verified"})
            continue
        found = next((e for e in excerpts if text in normalise_text(e["text"])), None)
        if found and cited:
            reason = f"this text is in {found['cite']}, not in {cited['cite']}"
        elif found:
            reason = f"source label not recognised; the text is in {found['cite']}"
        else:
            reason = "this text does not appear in any authority provided"
        failed.append({"source": quote["source"], "text": quote["text"], "reason": reason,
                       "found_in": found})
    return verified, failed


def check_facts(facts, measure_text):
    """Mark each fact as verified if its quote appears word-for-word in the description."""
    description = normalise_text(measure_text)
    checked = []
    for fact in facts:
        quote = normalise_quote(fact["quote"])
        checked.append({**fact, "verified": bool(quote) and quote in description})
    return checked


def dispute_list(library):
    """The disputes the model may choose from when naming similar cases."""
    return "\n".join(f"- {s['short']}: {s['summary']}" for s in library
                     if s["kind"] == "cases" and s["summary"])


def match_similar_cases(items, library):
    """Keep only similar cases whose name matches a dispute in the library."""
    by_name = {normalise_cite(s["short"]): s for s in library if s["kind"] == "cases" and s["summary"]}
    matched = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        source = by_name.get(normalise_cite(str(item.get("case", ""))))
        if source and source["id"] not in {m["id"] for m in matched}:
            matched.append({"id": source["id"], "short": source["short"], "summary": source["summary"],
                            "url": source["url"], "why": str(item.get("why", ""))})
    return matched[:3]


def cited_sources(results, library):
    """Sources actually quoted in the analysis, in table-of-authorities order."""
    ids = {q["source_id"] for result in results.values() for q in result.get("quotes", [])}
    return [{k: s[k] for k in ("id", "kind", "short", "citation", "url")}
            for s in library if s["id"] in ids]
