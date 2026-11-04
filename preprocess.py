#!/usr/bin/env python3
"""Clean raw Luganda chat data into Hugging Face-ready JSONL.

Usage: python preprocess.py [data_dir] [out_dir]   (defaults: data processed)

Merges every model folder in data_dir into out_dir/all.jsonl.
Each line: {"id", "source", "source_file", "messages": [{"role", "content"}]}
with roles normalised to user/assistant.

Fails loudly instead of dropping anything it doesn't understand: an unparsed
line inside a conversation, an unknown role or file type, a non-alternating
dialogue, an empty message, a duplicate id or an unscrubbed name/model mention
all raise. Name scrubs and typo fixes live in FIXES.
"""
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

ROLES = {"user": "user", "helper": "assistant", "assistant": "assistant"}
HEADING = re.compile(r"^#+ Conversation (\d+).*$", re.M)  # "### Conversation 001: Title"
TURN = re.compile(r"^\*\*(User|Helper)\\?:\*\*\s*(.*)$")  # "**User\:** text"
SEPARATOR = re.compile(r"^---\s*$", re.M)
APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})

# Whole-word (old, new) replacements, applied in order (specific phrases before bare names).
FIXES = [
    # Generator identity and the author's name leaked into the dialogues -> generic assistant.
    ("Osobola okumpita ChatGPT.", "Sirina linnya; ndi muyambi wa AI."),
    ("Erinnya lyange ye Qwen.", "Sirina linnya; ndi muyambi wa AI."),
    ("kampuni eyitibwa OpenAI", "kampuni ya tekinologiya"),
    ("OpenAI", "Kampuni eyo"),
    ("Alibaba Group", "kampuni ya tekinologiya"),
    ("name = 'Henry'", "name = 'Nakato'"),
    ("Henry", "mukwano gwange"),
    # Typos: casing, Luganda n+b/n+l spelling rules, dropped/extra letters, garbled words.
    ("bikEndedde", "bikendedde"),
    ("Nbadde", "Mbadde"),
    ("Nlutandise", "Ndutandise"),
    ("emilimu", "emirimu"),
    ("oyagela", "oyagala"),
    ("Abaano", "Abaana"),
    ("olunnaku", "olunaku"),
    ("emmottoka", "emmotoka"),
    ("ojjuukira", "ojjukira"),
    ("okunnamba", "okunnyamba"),
    ("kyinza", "kiyinza"),
    ("obukowu", "obukoowu"),
    ("somero", "ssomero"),
    ("kituo", "kifo"),  # Swahili slip
    ("sodda", "sooda"),
    ("Zgyemu", "Zigyemu"),
    ("Luwobo", "Luwombo"),
    ("Nkusubira", "Nkusuubira"),
    ("munange", "munnange"),
    ("Nsose", "Nsoose"),
    ("Baawe", "Bawe"),
    ("amaka gaawe", "amaka go"),
    ("Teddi", "Nedda"),
    ("si nzitoya", "si muntu"),
    ("ku nzitoya yo", "ku buzito bwo"),
    ("Olina emitima?", "Olina omutima?"),
    ("bwebaza bwebaza", "bwebaza"),
    ("Tegeza okubategeza", "Gezaako okubategeeza"),
    ("Webale", "Weebale"),
    ("webale", "weebale"),
]
FIXES = [(re.compile(rf"(?<!\w){re.escape(old)}(?!\w)"), new) for old, new in FIXES]
LEAKS = re.compile(r"henry|chat ?gpt|openai|qwen|alibaba", re.I)


def clean(s):
    # Mixed ’/' apostrophes (ky’oyagala vs ky'oyagala) would split the same Luganda word in two.
    s = unicodedata.normalize("NFC", s).translate(APOSTROPHES).strip()
    for pattern, new in FIXES:
        s = pattern.sub(new, s)
    return s


def md_unescape(s):
    # Markdown escapes (\! \: \() and HTML entities (&#124;) from the chat export.
    return html.unescape(re.sub(r"\\([^\w\s])", r"\1", s))


def parse_markdown(path):
    """chatgpt-5.5: markdown batches; preamble before the first heading and the
    progress notes after the final '---' are generation chatter, not data."""
    text = path.read_text(encoding="utf-8")
    heads = list(HEADING.finditer(text))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = SEPARATOR.split(text[h.end():end], 1)[0]
        msgs = []
        for line in body.splitlines():
            if not line.strip():
                continue
            m = TURN.match(line)
            if not m:
                raise ValueError(f"{path}: unparsed line in conversation {h[1]}: {line!r}")
            msgs.append({"role": ROLES[m[1].lower()], "content": clean(md_unescape(m[2]))})
        yield int(h[1]), msgs


def parse_json(path):
    """gemini: [{id, turns: [{role, content}]}]
    qwen: {metadata?, conversations: [{id, topic, turns: [{role, text}]}]} (metadata is a generation note)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    for c in data["conversations"] if isinstance(data, dict) else data:
        msgs = [
            {"role": ROLES[t["role"]], "content": clean(t["content"] if "content" in t else t["text"])}
            for t in c["turns"]
        ]
        yield c["id"], msgs


PARSERS = {".txt": parse_markdown, ".json": parse_json}


def validate(rec):
    roles = [m["role"] for m in rec["messages"]]
    if len(roles) < 2 or roles[0] != "user" or any(a == b for a, b in zip(roles, roles[1:])):
        raise ValueError(f"{rec['id']} ({rec['source_file']}): bad role order {roles}")
    if not all(m["content"] for m in rec["messages"]):
        raise ValueError(f"{rec['id']} ({rec['source_file']}): empty message")
    if any(LEAKS.search(m["content"]) for m in rec["messages"]):
        raise ValueError(f"{rec['id']} ({rec['source_file']}): name/model mention left unscrubbed, add it to FIXES")


def write_jsonl(path, recs):
    with path.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main(data_dir="data", out_dir="processed"):
    data_dir, out_dir = Path(data_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    everything, seen = [], set()
    for src in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        recs = []
        for f in sorted(src.iterdir(), key=lambda p: int(p.stem)):  # numbered batches: 1.json, 2.json, ...
            for sid, msgs in PARSERS[f.suffix](f):
                rec = {
                    "id": f"{src.name}-{sid:04d}",
                    "source": src.name,
                    "source_file": f"{src.name}/{f.name}",
                    "messages": msgs,
                }
                validate(rec)
                if rec["id"] in seen:
                    raise ValueError(f"duplicate id {rec['id']} in {f}")
                seen.add(rec["id"])
                recs.append(rec)
        print(f"{src.name}: {len(recs)} conversations, {sum(len(r['messages']) for r in recs)} messages")
        everything += recs
    write_jsonl(out_dir / "all.jsonl", everything)
    print(f"all: {len(everything)} conversations -> {out_dir / 'all.jsonl'}")


if __name__ == "__main__":
    main(*sys.argv[1:])
