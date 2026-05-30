# Collaboration Sync Policy

**Effective:** 2026-05-30  
**Purpose:** Keep us perfectly in sync so you never have to hunt for changes.

## Core Rule
After **every** meaningful edit to code or documents, I will automatically sync the changes to your real working folder:

`\\?\C:\Users\nilad\OneDrive\Desktop\Moira C++`

You should see the updates immediately in VS Code / File Explorer without extra steps.

## What Gets Synced

### Documents (full sync, including deletions)
- `.md`, `.txt`, `.json`, `.yaml`, plan documents, trackers, architecture docs, etc.
- If I delete a document in my workspace, it will also be deleted from your folder.

### Code Files (add/modify only)
- `.py`, `.cpp`, `.h`, `.js`, `.ts`, server files, tests, etc.
- **I will never automatically delete code files** from your folder.
- I will only add new code files or overwrite existing ones.

## Sync Behavior
- Sync happens automatically after I make changes via `search_replace`, `write`, or equivalent.
- After syncing I will simply say: **"Files synced."**
- This applies to every session going forward.

## Why This Matters
You treat me as a coding collaborator. Staying in tune with the actual state of the project is as important as the technical work itself. This policy removes friction so we stay aligned in real time.

## How to Update This Policy
Just tell me the new rule and I will update this file + the `.remember/remember.md` handoff.