---
name: anchored-edit
description: Makes a code change through a find-and-replace edit tool without a silent miss, a wrong-site match, or a mangled move.
kind: skill
role: implementer
phase: 3 4 5 6
tech: any
provenance: adapted
license: Apache-2.0 github.com/Aider-AI/aider@5dc9490bb35f9729ef2c95d00a19ccd30c26339c
---

# Anchored edit

## What you're doing

Changing a file through a tool that finds a literal block of existing text and
replaces it. The tool cannot tell an edit that landed where you meant from one that
landed on the first lookalike, or one that matched nothing. Each step below closes one
of those gaps before the done-check has to find it.

## How the work goes

1. Read the current file range before writing the anchor. The search text is copied
   from that read, character for character — comments, docstrings, trailing
   whitespace, indentation — never retyped from memory or an earlier version
   (`aider/coders/editblock_prompts.py:134`).
2. If the code sits inside a container — JSON string, XML, quoted template, escaped
   literal — anchor on the file's literal bytes, escapes and markup included, not on
   the code as it reads once unescaped (`:135`).
3. Check uniqueness: grep the file for the anchor. The tool replaces the first
   occurrence only (`:137`). More than one hit → add surrounding lines until it is one.
4. Keep each edit small: the changing lines plus only the context that uniqueness
   needs. Split a large change into several edits, each touching one region (`:141-144`).
5. Moving code inside a file is two edits — delete at the source, insert at the
   destination — never one edit spanning both (`:148`).
6. A new file is an empty anchor plus the full contents, at the full path including
   its directory (`:152-155`). Renames go through the shell, not an edit (`:161`).
7. After the batch, re-read each touched range and confirm the change is there once.

## When you're stuck

- **Anchor not found.** The file changed since you read it, or the anchor was retyped.
  Re-read and re-copy; do not loosen the anchor until it matches something.
- **Edit landed in the wrong place.** The anchor matched an earlier duplicate — a
  repeated import, a copy-pasted handler. Undo, widen the anchor, re-apply.
- **Long unchanged runs in the anchor.** Every extra line is another chance for a
  mismatch and a larger diff to review; trim to the region that changes.
- **Path written decorated.** Bold, quotes or escaping around the path make the tool
  open a different file or create a new one (`:123`).

## What you hand back

For each file: the edits applied, and the re-read showing each change present exactly
once at the intended site. Any anchor that needed widening, with why.
