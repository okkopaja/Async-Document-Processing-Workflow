"""Field extraction stage — derive structured data from parsed text."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.workers.pipelines.parse_stage import ParsedDocument


@dataclass
class ExtractedResult:
	"""Result of field extraction from parsed document."""

	title: str
	category: str
	summary: str
	keywords: list[str]
	file_type: str
	size_bytes: int
	original_filename: str
	raw_text: str
	structured_json: dict[str, Any] = field(default_factory=dict)


def extract_stage(parsed: ParsedDocument, original_filename: str, size_bytes: int) -> ExtractedResult:
	"""
	Extract structured fields from parsed document text.

	Args:
	    parsed: ParsedDocument from parse_stage
	    original_filename: Original uploaded filename
	    size_bytes: File size in bytes

	Returns:
	    ExtractedResult with extracted fields
	"""
	# Extract title
	title = _extract_title(parsed.raw_text, original_filename)

	# Extract category
	category = _extract_category(parsed.raw_text, parsed.file_type)

	# Extract summary
	summary = _extract_summary(parsed.raw_text)

	# Extract keywords
	keywords = _extract_keywords(parsed.raw_text)

	# Build structured JSON
	structured_json = {
		"title": title,
		"category": category,
		"summary": summary,
		"keywords": keywords,
		"fileType": parsed.file_type,
		"originalFilename": original_filename,
		"sizeBytes": size_bytes,
		"statistics": {
			"lineCount": parsed.line_count,
			"charCount": parsed.char_count,
			"wordCount": len(parsed.raw_text.split()),
		},
	}

	return ExtractedResult(
		title=title,
		category=category,
		summary=summary,
		keywords=keywords,
		file_type=parsed.file_type,
		size_bytes=size_bytes,
		original_filename=original_filename,
		raw_text=parsed.raw_text,
		structured_json=structured_json,
	)


def _extract_title(raw_text: str, filename: str) -> str:
	"""Extract or derive title from text."""
	if not raw_text:
		return filename

	# Try first non-empty line
	lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
	if lines:
		first_line = lines[0]
		# Strip markdown heading markers
		first_line = first_line.lstrip("#").strip()
		if len(first_line) > 3:
			return first_line[:200]  # Limit to 200 chars

	# Fall back to filename
	return Path(filename).stem[:200]


def _extract_category(raw_text: str, file_type: str) -> str:
	"""Heuristic category detection."""
	text_lower = raw_text.lower()

	# File-type-based categories
	if file_type in ("csv", "json"):
		return "Data"

	# Keyword-based heuristics
	keywords = {
		"Invoice": ["invoice", "bill", "amount due", "payment terms"],
		"Report": ["report", "summary", "executive", "findings"],
		"Manual": ["manual", "guide", "instructions", "tutorial"],
		"Notes": ["notes", "meeting", "agenda", "discussion"],
		"Contract": ["agreement", "terms and conditions", "contract", "legal"],
		"Financial": ["revenue", "expense", "balance", "profit", "financial"],
	}

	for category, keywords_list in keywords.items():
		if any(kw in text_lower for kw in keywords_list):
			return category

	return "Document"


def _extract_summary(raw_text: str, max_length: int = 200) -> str:
	"""Extract or synthesize a summary."""
	if not raw_text:
		return ""

	# Clean up text
	lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
	text = " ".join(lines)

	# Return first N chars
	if len(text) <= max_length:
		return text
	return text[:max_length].rsplit(" ", 1)[0] + "..."


def _extract_keywords(raw_text: str, max_keywords: int = 10) -> list[str]:
	"""Extract top keywords by frequency (excluding stop words)."""
	if not raw_text:
		return []

	# Common stop words
	stop_words = {
		"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
		"of", "with", "is", "are", "was", "were", "be", "been", "being",
		"have", "has", "had", "do", "does", "did", "will", "would", "could",
		"should", "may", "might", "must", "can", "this", "that", "these",
		"those", "i", "you", "he", "she", "it", "we", "they", "what", "which",
		"who", "when", "where", "why", "how", "all", "each", "every", "both",
		"few", "more", "most", "other", "some", "such", "no", "nor", "not",
		"only", "same", "so", "than", "too", "very", "as", "from", "by",
		"the", "or", "by", "if", "as", "any",
	}

	# Tokenize and filter
	words = raw_text.lower().split()
	filtered = [
		word.strip(".,;:!?\"'()[]{}") for word in words
		if word.lower().strip(".,;:!?\"'()[]{}") not in stop_words
		and len(word.strip(".,;:!?\"'()[]{}")) > 2
	]

	# Count frequency
	freq = {}
	for word in filtered:
		freq[word] = freq.get(word, 0) + 1

	# Sort by frequency and return top N
	sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
	return [word for word, count in sorted_keywords[:max_keywords]]
