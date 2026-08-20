"""What the walk does not descend into.

Three sources, in order: a built-in list of directories that are never source, the
repository's `.gitignore` (the common subset — directory names, suffix globs, and
anchored paths), and `.edifyignore` when a repository needs to say something the
first two do not.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

# Directories that are never source in any stack we cover. Matched by exact name
# at any depth, which is the only rule that stays correct in a monorepo.
ALWAYS_SKIP_DIRS = frozenset(
    {
        ".git", ".hg", ".svn", ".edify", ".idea", ".vscode", ".vs",
        "node_modules", "bower_components", "vendor", "third_party",
        "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".tox",
        ".venv", "venv", "env", "virtualenv", ".eggs",
        "dist", "build", "out", "target", "bin", "obj", ".next", ".nuxt",
        ".svelte-kit", ".turbo", ".parcel-cache", ".cache", "coverage",
        ".gradle", ".terraform", "Pods", "DerivedData", ".dart_tool",
        "site-packages", ".pnpm-store", ".yarn",
        "__MACOSX", "Carthage",
    }
)

# macOS bundle directories. They are named by suffix rather than by name, and a
# `.app` or `.framework` is a build product whose innards are not anybody's source.
ALWAYS_SKIP_DIR_SUFFIXES = (".dSYM", ".app", ".framework", ".xcassets", ".lproj")

# Files the operating system writes into a source tree without being asked.
ALWAYS_SKIP_NAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini", ".localized", "Icon\r"})

ALWAYS_SKIP_SUFFIXES = frozenset(
    {
        ".min.js", ".min.css", ".map", ".lock", ".pyc", ".pyo", ".so", ".dll",
        ".dylib", ".exe", ".class", ".jar", ".war", ".o", ".a", ".wasm",
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".pdf",
        ".zip", ".gz", ".tar", ".7z", ".mp4", ".mp3", ".woff", ".woff2", ".ttf",
        ".eot", ".bin", ".db", ".sqlite", ".sqlite3", ".parquet",
    }
)

# Anything larger than this is generated, vendored, or data. Indexing it costs
# more than it returns and pollutes the map with names nobody wrote.
MAX_FILE_BYTES = 1_500_000


class IgnoreRules:
    def __init__(self, root: Path):
        self.root = root
        self.dir_names: set[str] = set(ALWAYS_SKIP_DIRS)
        self.globs: list[str] = []
        self.anchored: list[str] = []
        self._load(root / ".gitignore")
        self._load(root / ".edifyignore")

    def _load(self, path: Path) -> None:
        if not path.is_file():
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            if line.endswith("/"):
                stripped = line.rstrip("/")
                if "/" not in stripped:
                    self.dir_names.add(stripped)
                else:
                    self.anchored.append(stripped.lstrip("/"))
                continue
            if line.startswith("/"):
                self.anchored.append(line.lstrip("/"))
            elif "/" in line:
                self.anchored.append(line)
            else:
                self.globs.append(line)

    def skip_dir(self, name: str, rel: str) -> bool:
        if name in self.dir_names:
            return True
        if name.endswith(ALWAYS_SKIP_DIR_SUFFIXES):
            return True
        # `.claude/` holds generated command pointers, not source. `.github/` holds
        # the CI job whose real commands the conventions scrape reads, so it stays.
        if name.startswith(".") and name != ".github":
            return True
        return any(fnmatch.fnmatch(rel, pattern) for pattern in self.anchored)

    def skip_file(self, name: str, rel: str, size: int) -> bool:
        if name in ALWAYS_SKIP_NAMES:
            return True
        lowered = name.lower()
        if any(lowered.endswith(suffix) for suffix in ALWAYS_SKIP_SUFFIXES):
            return True
        if size > MAX_FILE_BYTES:
            return True
        if any(fnmatch.fnmatch(name, pattern) for pattern in self.globs):
            return True
        return any(fnmatch.fnmatch(rel, pattern) for pattern in self.anchored)
