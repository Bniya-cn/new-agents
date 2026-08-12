#!/usr/bin/env python3
"""Build corpus/manifest.json from corpus/raw/. Deterministic only; no semantics."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
DERIVED = ROOT / "corpus" / "derived"
MODELS = ROOT / "generated" / "book-models"
REPORTS = ROOT / "generated" / "reports"
OUT = ROOT / "corpus" / "manifest.json"

# Known duplicate pairs (content-identical): keep first as canonical.
KNOWN_DUPLICATES = {
    "020": "015",
}

# Mode heuristic thresholds (characters).
DIRECT_MAX = 200_000
HIER_SOFT = 500_000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def book_id(name: str) -> str:
    m = re.match(r"^(\d{3})-", name)
    return m.group(1) if m else name


def title_from_name(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r"^\d{3}-", "", stem)


def infer_processing_mode(chars: int, garbled_hint: float = 0.0) -> str:
    if chars == 0:
        return "blocked"
    if chars < DIRECT_MAX and garbled_hint < 0.02:
        return "direct"
    return "hierarchical"


def garbled_ratio(text: str) -> float:
    if not text:
        return 0.0
    bad = sum(1 for ch in text if ch == "\ufffd" or ("\ue000" <= ch <= "\uf8ff"))
    return bad / len(text)


def model_path_for(stem: str) -> Path | None:
    p = MODELS / f"{stem}.md"
    return p if p.is_file() and p.stat().st_size > 0 else None


def report_path_for(stem: str) -> Path | None:
    p = REPORTS / f"{stem}.report.md"
    return p if p.is_file() and p.stat().st_size > 0 else None


def derived_for(book_id_: str) -> Path | None:
    p = DERIVED / "normalized" / f"{book_id_}-*.derived.md"
    matches = list((DERIVED / "normalized").glob(f"{book_id_}-*.derived.md")) if (DERIVED / "normalized").exists() else []
    for m in matches:
        if m.stat().st_size > 1000:
            return m
    return None


def main() -> None:
    books = []
    files = sorted(RAW.glob("*.md"))
    hash_index: dict[str, list[str]] = {}

    for path in files:
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        digest = hashlib.sha256(data).hexdigest()
        bid = book_id(path.name)
        stem = path.stem
        chars = len(text)
        lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        g = garbled_ratio(text[:200_000])
        hash_index.setdefault(digest, []).append(bid)

        entry = {
            "id": bid,
            "title": title_from_name(path.name),
            "source_file": f"corpus/raw/{path.name}",
            "source_hash": digest,
            "size": len(data),
            "characters": chars,
            "lines": lines,
            "garbled_ratio_sample": round(g, 6),
            "status": "pending",
            "canonical": True,
            "duplicate_of": None,
            "source_quality": "unknown",
            "processing_mode": infer_processing_mode(chars, g),
            "book_model": None,
            "report": None,
            "notes": [],
        }

        if chars == 0:
            entry["status"] = "blocked_source_missing"
            entry["canonical"] = False
            entry["processing_mode"] = "blocked"
            entry["source_quality"] = "empty"
            # Check derived recovery
            der = list((DERIVED / "normalized").glob(f"{bid}-*.derived.md")) if (DERIVED / "normalized").exists() else []
            usable = [d for d in der if d.stat().st_size > 1000]
            if usable:
                entry["notes"].append(f"derived_candidate={usable[0].as_posix()}")
            else:
                entry["notes"].append("raw empty; PDF may exist but text extraction failed or not usable")
            entry["notes"].append("do_not_forge_model")

        books.append(entry)

    # Apply known duplicates + hash duplicates
    by_id = {b["id"]: b for b in books}
    for dup_id, canon_id in KNOWN_DUPLICATES.items():
        if dup_id in by_id and canon_id in by_id:
            by_id[dup_id]["status"] = "duplicate"
            by_id[dup_id]["canonical"] = False
            by_id[dup_id]["duplicate_of"] = canon_id
            by_id[dup_id]["processing_mode"] = "skip_duplicate"
            by_id[dup_id]["notes"].append(f"explicit duplicate of {canon_id}; identical content weight once")
            by_id[canon_id]["notes"].append(f"canonical for duplicate {dup_id}")

    for digest, ids in hash_index.items():
        if len(ids) < 2:
            continue
        # Prefer lowest id as canonical if not already set
        ids_sorted = sorted(ids)
        canon = ids_sorted[0]
        for other in ids_sorted[1:]:
            if by_id[other]["status"] == "blocked_source_missing":
                continue
            if by_id[other]["duplicate_of"]:
                continue
            by_id[other]["status"] = "duplicate"
            by_id[other]["canonical"] = False
            by_id[other]["duplicate_of"] = canon
            by_id[other]["processing_mode"] = "skip_duplicate"
            by_id[other]["notes"].append(f"hash-identical to {canon}")

    # Attach existing model/report paths
    for b in books:
        stem = Path(b["source_file"]).stem
        mp = model_path_for(stem)
        rp = report_path_for(stem)
        if mp:
            b["book_model"] = str(mp.relative_to(ROOT))
            if b["status"] == "pending":
                b["status"] = "modeled"
        if rp:
            b["report"] = str(rp.relative_to(ROOT))
            if b["status"] == "modeled":
                b["status"] = "complete"

        # Quality hints
        if b["characters"] == 0:
            pass
        elif b["garbled_ratio_sample"] > 0.01:
            b["source_quality"] = "ocr_noisy"
        elif b["characters"] > HIER_SOFT:
            b["source_quality"] = "large_plaintext"
        else:
            b["source_quality"] = "readable"

    manifest = {
        "pipeline_version": "0.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_dir": "corpus/raw",
        "book_count": len(books),
        "canonical_count": sum(1 for b in books if b["canonical"] and b["status"] != "blocked_source_missing"),
        "duplicate_count": sum(1 for b in books if b["status"] == "duplicate"),
        "blocked_count": sum(1 for b in books if b["status"] == "blocked_source_missing"),
        "complete_count": sum(1 for b in books if b["status"] == "complete"),
        "books": books,
        "dedup_policy": {
            "015": "canonical",
            "020": "duplicate_of_015",
            "weight_rule": "identical bytes share one knowledge weight",
        },
        "blocked_policy": {
            "004": "raw empty; scanned PDF has no text layer; OCR not completed this run → BLOCKED_SOURCE_MISSING",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(
        f"books={manifest['book_count']} canonical={manifest['canonical_count']} "
        f"dup={manifest['duplicate_count']} blocked={manifest['blocked_count']} "
        f"complete={manifest['complete_count']}"
    )


if __name__ == "__main__":
    main()
