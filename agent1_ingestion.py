#!/usr/bin/env python3
"""
Agent 1 — Repository Ingestion Agent
Converts local path or Git URL to a flat repomix bundle.
"""

import subprocess
import os
import sys
import shutil
import tempfile
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class IngestionResult:
    success: bool
    flat_file_path: str
    source_type: str          # "local" | "git"
    source_path: str
    file_size_bytes: int
    detected_language: str
    detected_framework: str
    error: Optional[str] = None


FRAMEWORK_SIGNATURES = {
    "laravel":     ["artisan", "composer.json", "app/Http/Controllers"],
    "django":      ["manage.py", "settings.py", "wsgi.py"],
    "express":     ["package.json", "app.js", "routes/"],
    "nestjs":      ["nest-cli.json", "src/main.ts"],
    "springboot":  ["pom.xml", "src/main/java", "Application.java"],
    "rails":       ["Gemfile", "config/routes.rb", "app/controllers"],
    "fastapi":     ["main.py", "requirements.txt"],  # + fastapi in requirements
    "gin":         ["go.mod", "main.go"],
    "aspnet":      ["*.csproj", "Program.cs", "Startup.cs"],
}

LANGUAGE_MAP = {
    "laravel": "PHP",
    "django": "Python",
    "fastapi": "Python",
    "express": "JavaScript",
    "nestjs": "TypeScript",
    "springboot": "Java",
    "rails": "Ruby",
    "gin": "Go",
    "aspnet": "C#",
}


def detect_framework(path: str) -> tuple[str, str]:
    """Detect framework and language from directory structure."""
    for framework, signatures in FRAMEWORK_SIGNATURES.items():
        for sig in signatures:
            check = Path(path) / sig
            # Check direct file/dir
            if check.exists():
                return framework, LANGUAGE_MAP.get(framework, "Unknown")
            # Glob pattern
            if "*" in sig:
                matches = list(Path(path).glob(sig))
                if matches:
                    return framework, LANGUAGE_MAP.get(framework, "Unknown")
    return "unknown", "Unknown"


def clone_repo(git_url: str, target_dir: str) -> str:
    """Clone a git repository to target_dir."""
    print(f"[Agent 1] Cloning {git_url}...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", git_url, target_dir],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")
    return target_dir


def run_repomix(source_dir: str, output_path: str) -> None:
    """Run repomix to create flat bundle from source_dir."""
    print(f"[Agent 1] Running repomix on {source_dir}...")

    # repomix config — exclude common non-essential files
    repomix_config = {
        "output": {
            "filePath": output_path,
            "style": "plain",
            "removeComments": False,
            "removeEmptyLines": False,
            "showLineNumbers": True,
            "copyToClipboard": False,
        },
        "ignore": {
            "useGitignore": True,
            "useDefaultPatterns": True,
            "customPatterns": [
                "node_modules/**",
                "vendor/**",
                ".git/**",
                "storage/**",
                "tests/**",               # File test bisa dibuang untuk analisis logika utama
                "public/**",              # Gambar, CSS, Minified JS di sini dibuang saja
                "resources/assets/**",    # Assets mentah
                "*.min.js",
                "*.css",
                "*.scss",
                "*.json",                 # File JSON besar (seperti package-lock) sering ikut terbawa
                "*.lock",
                "*.log"
            ]
        }
    }

    config_path = Path(source_dir) / ".repomix-config.json"
    with open(config_path, "w") as f:
        json.dump(repomix_config, f, indent=2)

    result = subprocess.run(
        ["repomix", "--config", str(config_path), "--output", output_path, source_dir],
        capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace"
    )

    # Cleanup config
    config_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"repomix failed: {result.stderr}")

    print(f"[Agent 1] ✅ repomix output: {output_path}")


def run(source: str, output_dir: str = "./output") -> IngestionResult:
    """
    Main entry point for Agent 1.
    
    Args:
        source: Local directory path OR Git URL
        output_dir: Where to save the flat bundle
    
    Returns:
        IngestionResult with flat_file_path pointing to repomix output
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = str(Path(output_dir) / "flat_codebase.txt")
    temp_dir = None

    try:
        # Determine source type
        if source.startswith("http") or source.startswith("git@"):
            source_type = "git"
            temp_dir = tempfile.mkdtemp(prefix="agent1_repo_")
            working_dir = clone_repo(source, temp_dir)
        else:
            source_type = "local"
            working_dir = os.path.abspath(source)
            if not os.path.isdir(working_dir):
                raise ValueError(f"Directory not found: {working_dir}")

        # Detect framework
        print(f"[Agent 1] Menganalisis struktur proyek untuk deteksi framework...", flush=True)
        framework, language = detect_framework(working_dir)
        print(f"[Agent 1] Terdeteksi: {framework} ({language})", flush=True)

        # Run repomix
        print(f"[Agent 1] Memulai proses pemaketan kode (Repomix)...", flush=True)
        run_repomix(working_dir, output_path)

        file_size = Path(output_path).stat().st_size

        return IngestionResult(
            success=True,
            flat_file_path=output_path,
            source_type=source_type,
            source_path=source,
            file_size_bytes=file_size,
            detected_language=language,
            detected_framework=framework,
        )

    except Exception as e:
        return IngestionResult(
            success=False,
            flat_file_path="",
            source_type="unknown",
            source_path=source,
            file_size_bytes=0,
            detected_language="Unknown",
            detected_framework="unknown",
            error=str(e),
        )
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "."
    result = run(source)
    print(json.dumps(asdict(result), indent=2))
