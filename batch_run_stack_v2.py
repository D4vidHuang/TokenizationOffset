#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch runner for analyzer.py over Stack V2 dedup preprocessed outputs.

- Scans base_dir for subdirectories named like *_code_output
- For each such directory, runs analyzer.py for the specified languages
  with chunked saving to reduce memory usage.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


SUPPORTED_LANGUAGES = [
    "javascript", "typescript", "scala", "go",
    "c", "cpp", "csharp", "python", "rust",
]


def find_code_output_dirs(base_dir: Path):
    """Yield subdirectories in base_dir whose names end with _code_output."""
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in base_dir.iterdir() if p.is_dir() and p.name.endswith("_code_output")]


def normalize_language_name(name: str) -> str | None:
    """Map various aliases to our supported language keys."""
    if not name:
        return None
    n = name.strip().lower()
    aliases = {
        "python": "python", "py": "python",
        "javascript": "javascript", "js": "javascript", "node": "javascript",
        "typescript": "typescript", "ts": "typescript",
        "java": "java",
        "c": "c",
        "c++": "cpp", "cpp": "cpp", "cxx": "cpp",
        "c#": "csharp", "csharp": "csharp", "cs": "csharp",
        "go": "go", "golang": "go",
        "ruby": "ruby", "rb": "ruby",
        "rust": "rust", "rs": "rust",
        "scala": "scala",
    }
    lang = aliases.get(n)
    return lang if lang in SUPPORTED_LANGUAGES else None


def infer_language_from_dir(dir_name: str) -> str | None:
    """Infer language from a directory name like '<lang>_code_output'."""
    base = dir_name
    if base.endswith("_code_output"):
        base = base[: -len("_code_output")]
    return normalize_language_name(base)


def run_analyzer(analyzer_path: Path,
                 code_dir: Path,
                 language: str,
                 output_dir: Path,
                 flush_every: int,
                 models: list[str] | None,
                 extra_args: list[str] | None = None) -> int:
    """Run analyzer.py once for given args. Returns process return code."""
    cmd = [sys.executable, str(analyzer_path),
           "--language", language,
           "--code_dir", str(code_dir),
           "--output_dir", str(output_dir),
           "--flush_every", str(flush_every)]

    if models:
        cmd += ["--models", *models]

    if extra_args:
        cmd += list(extra_args)

    print("\n" + "=" * 100)
    print(f"Running analyzer for language={language} | code_dir={code_dir.name} | output_dir={output_dir}")
    print("=" * 100)
    proc = subprocess.run(cmd)
    return proc.returncode


def main():
    parser = argparse.ArgumentParser(description="Batch runner for analyzer.py over *_code_output directories")
    parser.add_argument("--base_dir", type=str,
                        default=os.path.expanduser("~/desktop/stack_v2_dedup_preprocess/"),
                        help="Base directory containing *_code_output subdirectories")
    parser.add_argument("--output_base", type=str,
                        default=str(Path(__file__).resolve().parent / "results" / "stack_v2"),
                        help="Base directory for analysis outputs")
    parser.add_argument("--languages", nargs="+", default=None,
                        help="Languages to analyze. If omitted, infer from each folder name (e.g., 'java_code_output' -> java)")
    parser.add_argument("--flush_every", type=int, default=5000,
                        help="Flush detailed report every N files (0 to disable)")
    parser.add_argument("--models", nargs="+", default=None,
                        help="Optional list of tokenizer models to run (defaults to analyzer's --model)")
    parser.add_argument("--extra", nargs=argparse.REMAINDER,
                        help="Extra args passed through to analyzer.py (must come after --)")

    args = parser.parse_args()

    base_dir = Path(args.base_dir).expanduser()
    output_base = Path(args.output_base)
    output_base.mkdir(parents=True, exist_ok=True)

    analyzer_path = Path(__file__).resolve().parent / "analyzer.py"
    if not analyzer_path.exists():
        print(f"Error: analyzer.py not found at {analyzer_path}")
        return 1

    targets = find_code_output_dirs(base_dir)
    if not targets:
        print(f"No *_code_output directories found under {base_dir}")
        return 1

    total = 0
    failures = 0
    for code_dir in targets:
        # Determine languages to run for this folder
        languages = args.languages
        if not languages:
            inferred = infer_language_from_dir(code_dir.name)
            if inferred:
                languages = [inferred]
            else:
                print(f"⚠️  Could not infer language from folder name: {code_dir.name}. Skipping.")
                continue

        # One output folder per dataset folder
        dataset_out = output_base / code_dir.name
        dataset_out.mkdir(parents=True, exist_ok=True)

        for language in languages:
            if language not in SUPPORTED_LANGUAGES:
                print(f"⚠️  Unsupported language requested: {language}. Skipping.")
                continue

            lang_out = dataset_out / language
            lang_out.mkdir(parents=True, exist_ok=True)

            rc = run_analyzer(
                analyzer_path=analyzer_path,
                code_dir=code_dir,
                language=language,
                output_dir=lang_out,
                flush_every=args.flush_every,
                models=args.models,
                extra_args=args.extra,
            )
            total += 1
            if rc != 0:
                print(f"❌ Failed: {code_dir.name} | {language} (rc={rc})")
                failures += 1
            else:
                print(f"✓ Done: {code_dir.name} | {language}")

    print("\n" + "=" * 80)
    print(f"Batch completed: {total - failures}/{total} successful")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())


