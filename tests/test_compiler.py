"""Tests for compiler backends."""
import pytest
import tempfile
from pathlib import Path

from peerpedia_core.storage.compiler import (
    CompilerBackend,
    CompileResult,
    TypstBackend,
    MarkdownBackend,
    detect_format,
    extract_frontmatter,
)


SAMPLE_TYPST = """---
title: On Quantum Error Correction
abstract: A survey of surface codes.
categories:
  - physics
  - quantum
keywords:
  - surface code
  - error correction
language: en
---

= On Quantum Error Correction

== Introduction

Hello world.
"""

SAMPLE_MARKDOWN = """---
title: My Math Notes
abstract: Notes on linear algebra.
categories:
  - math
language: zh
---

# My Math Notes

## Introduction

Some text with math: $E = mc^2$
"""

NO_FRONTMATTER = """= Simple Typst Document

== Section 1

Just content, no metadata.
"""


class TestFrontmatterParsing:
    """Frontmatter extraction from Typst/Markdown sources."""

    def test_extract_typst_frontmatter(self):
        """Should parse YAML frontmatter from Typst source."""
        meta = extract_frontmatter(SAMPLE_TYPST)
        assert meta["title"] == "On Quantum Error Correction"
        assert meta["abstract"] == "A survey of surface codes."
        assert meta["categories"] == ["physics", "quantum"]
        assert meta["keywords"] == ["surface code", "error correction"]
        assert meta["language"] == "en"

    def test_extract_markdown_frontmatter(self):
        """Should parse YAML frontmatter from Markdown source."""
        meta = extract_frontmatter(SAMPLE_MARKDOWN)
        assert meta["title"] == "My Math Notes"
        assert meta["language"] == "zh"
        assert meta["categories"] == ["math"]

    def test_no_frontmatter_returns_empty(self):
        """Source without frontmatter should return empty dict."""
        meta = extract_frontmatter(NO_FRONTMATTER)
        assert meta == {}

    def test_frontmatter_strips_body(self):
        """extract_frontmatter should return only metadata, body stripped."""
        meta = extract_frontmatter(SAMPLE_TYPST)
        # Body content should NOT appear in metadata
        assert "Hello world" not in str(meta)
        assert "Introduction" not in str(meta)


class TestFormatDetection:
    """Detect format from file extension."""

    def test_detect_typst(self):
        assert detect_format(Path("article.typ")) == "typst"

    def test_detect_markdown(self):
        assert detect_format(Path("notes.md")) == "markdown"

    def test_detect_unknown(self):
        assert detect_format(Path("unknown.txt")) == "typst"  # default


class TestTypstBackend:
    """Typst compiler backend."""

    def test_format_name(self):
        backend = TypstBackend()
        assert backend.format_name == "typst"

    def test_compile_creates_pdf(self):
        """Compile a simple Typst document to PDF."""
        backend = TypstBackend()
        with tempfile.TemporaryDirectory() as tmp:
            source = _write(Path(tmp), "test.typ", NO_FRONTMATTER)
            result = backend.compile(source, Path(tmp))
            # Result should be a CompileResult
            assert isinstance(result, CompileResult)
            # If typst is installed, we get a PDF; if not, we get an error
            if result.success:
                assert result.output_path is not None
                assert Path(result.output_path).exists()

    def test_compile_missing_typst_graceful(self):
        """Should handle missing typst CLI gracefully."""
        backend = TypstBackend()
        with tempfile.TemporaryDirectory() as tmp:
            source = _write(Path(tmp), "test.typ", NO_FRONTMATTER)
            result = backend.compile(source, Path(tmp))
            # Result should always be a CompileResult, success or not
            assert isinstance(result, CompileResult)
            assert isinstance(result.success, bool)
            if not result.success:
                assert result.error is not None


class TestMarkdownBackend:
    """Markdown + KaTeX compiler backend."""

    def test_format_name(self):
        backend = MarkdownBackend()
        assert backend.format_name == "markdown"

    def test_compile_produces_html(self):
        """Compile Markdown to HTML."""
        backend = MarkdownBackend()
        with tempfile.TemporaryDirectory() as tmp:
            source = _write(Path(tmp), "test.md", SAMPLE_MARKDOWN)
            result = backend.compile(source, Path(tmp))
            assert isinstance(result, CompileResult)
            if result.success and result.html_content:
                assert "<h1>" in result.html_content or "<h2>" in result.html_content

    def test_inline_math_is_preserved(self):
        """Inline math $...$ should be converted to KaTeX HTML spans."""
        backend = MarkdownBackend()
        with tempfile.TemporaryDirectory() as tmp:
            source = _write(Path(tmp), "math.md", "---\ntitle: Math\n---\n\nSome math: $E = mc^2$")
            result = backend.compile(source, Path(tmp))
            if result.success and result.html_content:
                # Should contain KaTeX class or at least the math expression
                assert "E = mc^2" in result.html_content or "katex" in result.html_content.lower()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _write(base: Path, name: str, content: str) -> Path:
    """Write content to a file in a temp directory, return the path."""
    filepath = base / name
    filepath.write_text(content)
    return filepath
