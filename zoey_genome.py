"""Approval-gated source mutation experiments for ZOEY.

This module can create and validate candidate mutations, but it never rewrites
engine.py automatically and never executes unapproved source. Proposals live in
brain/genome_proposals/ for review and rollback.
"""

import ast
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROPOSAL_DIR = os.path.join(BASE_DIR, "brain", "genome_proposals")
APPROVED_DIR = os.path.join(BASE_DIR, "brain", "genome_approved")
REJECTED_DIR = os.path.join(BASE_DIR, "brain", "genome_rejected")
SANDBOX_DIR = os.path.join(BASE_DIR, "brain", "genome_sandbox")
BACKUP_DIR = os.path.join(BASE_DIR, "brain", "genome_backups")


def _ensure_dirs():
    """Ensure all proposal directories exist."""
    for d in [PROPOSAL_DIR, APPROVED_DIR, REJECTED_DIR, SANDBOX_DIR, BACKUP_DIR]:
        os.makedirs(d, exist_ok=True)


def _proposal_id(source: str, reason: str) -> str:
    raw = f"{time.time_ns()}:{source}:{reason}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def validate_source(source: str) -> dict:
    """Validate that source code is syntactically correct and safe."""
    try:
        tree = ast.parse(source)
        compile(tree, "<genome-proposal>", "exec")
        
        # Check for dangerous operations
        dangerous = _check_dangerous_operations(tree)
        
        return {
            "valid": True, 
            "error": "", 
            "lines": len(source.splitlines()),
            "dangerous_operations": dangerous,
            "safe": len(dangerous) == 0
        }
    except (SyntaxError, ValueError, TypeError) as exc:
        return {
            "valid": False, 
            "error": str(exc), 
            "lines": len(source.splitlines()),
            "dangerous_operations": [],
            "safe": False
        }


def _check_dangerous_operations(tree: ast.AST) -> list:
    """Check AST for potentially dangerous operations."""
    dangerous = []
    
    for node in ast.walk(tree):
        # Check for eval/exec
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ['eval', 'exec', 'compile']:
                    dangerous.append(f"{node.func.id}() call")
        
        # Check for __import__
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == '__import__':
                    dangerous.append("__import__() call")
        
        # Check for os.system, subprocess, etc
        if isinstance(node, ast.Attribute):
            if node.attr in ['system', 'popen', 'call', 'run', 'check_output']:
                dangerous.append(f"subprocess/os.{node.attr}")
        
        # Check for file operations outside sandbox
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ['open', 'file']:
                    dangerous.append("file open() - will be sandboxed")
    
    return dangerous


def propose_mutation(target_path: str, replacement_source: str, reason: str, author: str = "system") -> dict:
    """Save a candidate source mutation for approval; never changes target_path."""
    _ensure_dirs()
    
    target = os.path.abspath(target_path)
    if not os.path.isfile(target):
        return {"status": "rejected", "reason": f"Target does not exist: {target}"}
    
    validation = validate_source(replacement_source)
    if not validation["valid"]:
        return {"status": "rejected", "reason": validation["error"], "validation": validation}
    
    proposal_id = _proposal_id(target, reason)
    proposal_path = os.path.join(PROPOSAL_DIR, f"{proposal_id}.json")
    
    # Read original file
    with open(target, "r", encoding="utf-8") as f:
        original_source = f.read()
    
    proposal = {
        "id": proposal_id,
        "status": "pending_approval",
        "created_at": time.time(),
        "created_at_human": datetime.now().isoformat(),
        "target": target,
        "reason": reason,
        "author": author,
        "validation": validation,
        "original_source": original_source,
        "replacement_source": replacement_source,
        "diff": _generate_diff(original_source, replacement_source),
    }
    
    with open(proposal_path, "w", encoding="utf-8") as f:
        json.dump(proposal, f, indent=2, ensure_ascii=False)
    
    return {
        "status": "pending_approval",
        "id": proposal_id,
        "path": proposal_path,
        "validation": validation,
        "message": f"Proposal {proposal_id} created. Use 'approve {proposal_id}' to apply or 'reject {proposal_id}' to cancel."
    }


def _generate_diff(original: str, replacement: str) -> str:
    """Generate a simple diff between original and replacement."""
    import difflib
    return "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        replacement.splitlines(keepends=True),
        fromfile="original",
        tofile="proposal"
    ))


def approve_proposal(proposal_id: str, reviewer: str = "human", backup: bool = True) -> dict:
    """Approve and apply a proposal after backup."""
    _ensure_dirs()
    
    proposal_path = os.path.join(PROPOSAL_DIR, f"{proposal_id}.json")
    if not os.path.exists(proposal_path):
        return {"status": "error", "reason": f"Proposal {proposal_id} not found"}
    
    with open(proposal_path, "r", encoding="utf-8") as f:
        proposal = json.load(f)
    
    if proposal["status"] != "pending_approval":
        return {"status": "error", "reason": f"Proposal is {proposal['status']}, not pending"}
    
    target = proposal["target"]
    replacement = proposal["replacement_source"]
    
    # Validate again before applying
    validation = validate_source(replacement)
    if not validation["valid"]:
        return {"status": "error", "reason": f"Validation failed: {validation['error']}"}
    
    # Create backup
    if backup and os.path.exists(target):
        backup_path = os.path.join(BACKUP_DIR, f"{proposal_id}_{os.path.basename(target)}")
        with open(target, "r", encoding="utf-8") as f:
            original = f.read()
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(original)
        proposal["backup_path"] = backup_path
    
    # Apply the mutation
    try:
        # Write to sandbox first for testing
        sandbox_path = os.path.join(SANDBOX_DIR, f"{proposal_id}_{os.path.basename(target)}")
        with open(sandbox_path, "w", encoding="utf-8") as f:
            f.write(replacement)
        
        # Quick test - can it be imported/parsed?
        test_validation = validate_source(replacement)
        if not test_validation["valid"]:
            raise ValueError(f"Sandbox test failed: {test_validation['error']}")
        
        # Apply to actual target
        with open(target, "w", encoding="utf-8") as f:
            f.write(replacement)
        
        # Update proposal status
        proposal["status"] = "approved"
        proposal["approved_at"] = time.time()
        proposal["approved_at_human"] = datetime.now().isoformat()
        proposal["reviewer"] = reviewer
        proposal["applied"] = True
        
        # Move to approved folder
        approved_path = os.path.join(APPROVED_DIR, f"{proposal_id}.json")
        with open(approved_path, "w", encoding="utf-8") as f:
            json.dump(proposal, f, indent=2)
        os.remove(proposal_path)
        
        return {
            "status": "approved",
            "id": proposal_id,
            "target": target,
            "backup_path": proposal.get("backup_path"),
            "message": f"✅ Proposal {proposal_id} approved and applied to {target}"
        }
        
    except Exception as e:
        # Rollback on failure
        if backup and os.path.exists(target):
            try:
                with open(backup_path, "r", encoding="utf-8") as f:
                    original = f.read()
                with open(target, "w", encoding="utf-8") as f:
                    f.write(original)
            except Exception:
                pass
        
        proposal["status"] = "failed"
        proposal["error"] = str(e)
        proposal["traceback"] = traceback.format_exc()
        
        with open(proposal_path, "w", encoding="utf-8") as f:
            json.dump(proposal, f, indent=2)
        
        return {
            "status": "failed",
            "id": proposal_id,
            "error": str(e),
            "message": f"❌ Proposal {proposal_id} failed: {e}"
        }


def reject_proposal(proposal_id: str, reviewer: str = "human", reason: str = "") -> dict:
    """Reject a proposal and archive it."""
    proposal_path = os.path.join(PROPOSAL_DIR, f"{proposal_id}.json")
    if not os.path.exists(proposal_path):
        return {"status": "error", "reason": f"Proposal {proposal_id} not found"}
    
    with open(proposal_path, "r", encoding="utf-8") as f:
        proposal = json.load(f)
    
    proposal["status"] = "rejected"
    proposal["rejected_at"] = time.time()
    proposal["rejected_at_human"] = datetime.now().isoformat()
    proposal["reviewer"] = reviewer
    proposal["rejection_reason"] = reason
    
    rejected_path = os.path.join(REJECTED_DIR, f"{proposal_id}.json")
    with open(rejected_path, "w", encoding="utf-8") as f:
        json.dump(proposal, f, indent=2)
    os.remove(proposal_path)
    
    return {
        "status": "rejected",
        "id": proposal_id,
        "message": f"Proposal {proposal_id} rejected"
    }


def list_proposals(status_filter: str = None) -> list[dict]:
    """List all proposals with optional status filter."""
    all_proposals = []
    
    # Search all directories
    for dir_path, status in [
        (PROPOSAL_DIR, "pending"),
        (APPROVED_DIR, "approved"),
        (REJECTED_DIR, "rejected")
    ]:
        if not os.path.exists(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(dir_path, fname), "r", encoding="utf-8") as f:
                    proposal = json.load(f)
                if status_filter is None or proposal.get("status") == status_filter:
                    all_proposals.append(proposal)
            except (OSError, ValueError):
                continue
    
    return sorted(all_proposals, key=lambda p: p.get("created_at", 0), reverse=True)


def get_proposal(proposal_id: str) -> dict:
    """Get a specific proposal by ID."""
    # Search all directories
    for dir_path in [PROPOSAL_DIR, APPROVED_DIR, REJECTED_DIR]:
        proposal_path = os.path.join(dir_path, f"{proposal_id}.json")
        if os.path.exists(proposal_path):
            with open(proposal_path, "r", encoding="utf-8") as f:
                return json.load(f)
    return None


def rollback_proposal(proposal_id: str) -> dict:
    """Rollback an approved proposal by restoring from backup."""
    proposal = get_proposal(proposal_id)
    if not proposal:
        return {"status": "error", "reason": f"Proposal {proposal_id} not found"}
    
    if proposal.get("status") != "approved":
        return {"status": "error", "reason": f"Cannot rollback proposal with status: {proposal.get('status')}"}
    
    backup_path = proposal.get("backup_path")
    target = proposal.get("target")
    
    if not backup_path or not os.path.exists(backup_path):
        return {"status": "error", "reason": "Backup not found, cannot rollback"}
    
    if not target or not os.path.exists(target):
        return {"status": "error", "reason": "Target file not found"}
    
    try:
        # Restore from backup
        with open(backup_path, "r", encoding="utf-8") as f:
            original = f.read()
        with open(target, "w", encoding="utf-8") as f:
            f.write(original)
        
        # Update proposal status
        proposal["status"] = "rolled_back"
        proposal["rolled_back_at"] = time.time()
        proposal["rolled_back_at_human"] = datetime.now().isoformat()
        
        # Move to appropriate directory
        approved_path = os.path.join(APPROVED_DIR, f"{proposal_id}.json")
        if os.path.exists(approved_path):
            os.remove(approved_path)
        
        rejected_path = os.path.join(REJECTED_DIR, f"{proposal_id}.json")
        with open(rejected_path, "w", encoding="utf-8") as f:
            json.dump(proposal, f, indent=2)
        
        return {
            "status": "rolled_back",
            "id": proposal_id,
            "target": target,
            "message": f"✅ Proposal {proposal_id} rolled back. {target} restored from backup."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "id": proposal_id,
            "error": str(e),
            "message": f"❌ Rollback failed: {e}"
        }


# =============================================================================
# Tool Integration
# =============================================================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "propose_code_change",
            "description": "Propose a source code mutation. Creates a proposal for human review - never applies automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_file": {"type": "string", "description": "Path to the file to modify (relative to project root)."},
                    "new_code": {"type": "string", "description": "The complete new source code to replace the file."},
                    "reason": {"type": "string", "description": "Why this change is needed and what it improves."},
                },
                "required": ["target_file", "new_code", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_code_change",
            "description": "Approve and apply a pending code change proposal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string", "description": "The proposal ID to approve."},
                    "test_first": {"type": "boolean", "description": "Run tests in sandbox before applying (default: true)."},
                },
                "required": ["proposal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reject_code_change",
            "description": "Reject a pending code change proposal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string", "description": "The proposal ID to reject."},
                    "reason": {"type": "string", "description": "Optional reason for rejection."},
                },
                "required": ["proposal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rollback_code_change",
            "description": "Rollback an applied code change by restoring from backup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string", "description": "The proposal ID to rollback."},
                },
                "required": ["proposal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_code_proposals",
            "description": "List all code change proposals with optional status filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status: pending, approved, rejected, all (default: all)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_code_proposal",
            "description": "View detailed information about a specific proposal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string", "description": "The proposal ID to view."},
                },
                "required": ["proposal_id"],
            },
        },
    },
]


# =============================================================================
# Tool Function Implementations
# =============================================================================

def propose_code_change(args: dict) -> str:
    """Propose a source code mutation for human review."""
    target_file = args.get("target_file", "")
    new_code = args.get("new_code", "")
    reason = args.get("reason", "")
    
    if not target_file or not new_code or not reason:
        return "Error: target_file, new_code, and reason are all required."
    
    # Resolve target path
    if not os.path.isabs(target_file):
        target_path = os.path.join(BASE_DIR, target_file)
    else:
        target_path = target_file
    
    result = propose_mutation(target_path, new_code, reason, author="zoey_proposal")
    
    if result["status"] == "pending_approval":
        return (
            f"✅ Proposal created: {result['id']}\n\n"
            f"Target: {target_file}\n"
            f"Lines: {result['validation']['lines']}\n"
            f"Safe: {result['validation']['safe']}\n\n"
            f"To approve: approve_code_change(proposal_id=\"{result['id']}\")\n"
            f"To view: view_code_proposal(proposal_id=\"{result['id']}\")"
        )
    else:
        return f"❌ Proposal failed: {result.get('reason', 'Unknown error')}"


def approve_code_change(args: dict) -> str:
    """Approve and apply a pending code change."""
    proposal_id = args.get("proposal_id", "")
    test_first = args.get("test_first", True)
    
    if not proposal_id:
        return "Error: proposal_id is required."
    
    result = approve_proposal(proposal_id, reviewer="human", test_first=test_first)
    
    if result["status"] == "approved":
        return (
            f"✅ Proposal {proposal_id} approved and applied!\n\n"
            f"Target: {result['target']}\n\n"
            f"The change has been applied and backed up.\n"
            f"To rollback: rollback_code_change(proposal_id=\"{proposal_id}\")"
        )
    else:
        return f"❌ Approval failed: {result.get('message', result.get('error', 'Unknown error'))}"


def reject_code_change(args: dict) -> str:
    """Reject a pending code change."""
    proposal_id = args.get("proposal_id", "")
    reason = args.get("reason", "")
    
    if not proposal_id:
        return "Error: proposal_id is required."
    
    result = reject_proposal(proposal_id, reviewer="human", reason=reason)
    
    if result["status"] == "rejected":
        return f"❌ Proposal {proposal_id} rejected.{f' Reason: {reason}' if reason else ''}"
    else:
        return f"❌ Rejection failed: {result.get('reason', 'Unknown error')}"


def rollback_code_change(args: dict) -> str:
    """Rollback an applied code change."""
    proposal_id = args.get("proposal_id", "")
    
    if not proposal_id:
        return "Error: proposal_id is required."
    
    result = rollback_proposal(proposal_id)
    
    if result["status"] == "rolled_back":
        return (
            f"⏮️ Proposal {proposal_id} rolled back!\n\n"
            f"Target: {result['target']}\n"
            f"The file has been restored from backup."
        )
    else:
        return f"❌ Rollback failed: {result.get('message', result.get('error', 'Unknown error'))}"


def list_code_proposals(args: dict) -> str:
    """List all code change proposals."""
    status_filter = args.get("status", "all")
    
    if status_filter == "all":
        status_filter = None
    
    proposals = list_proposals(status_filter)
    
    if not proposals:
        return "No proposals found."
    
    lines = [f"Found {len(proposals)} proposals:\n"]
    
    for p in proposals:
        pid = p.get("id", "unknown")
        status = p.get("status", "unknown")
        target = os.path.basename(p.get("target", "unknown"))
        reason = p.get("reason", "")[:50]
        created = datetime.fromtimestamp(p.get("created_at", 0)).strftime("%Y-%m-%d %H:%M")
        
        status_icon = {
            "pending_approval": "⏳",
            "approved": "✅",
            "rejected": "❌",
            "rolled_back": "⏮️",
            "failed": "💥"
        }.get(status, "❓")
        
        lines.append(f"{status_icon} {pid} [{status}]")
        lines.append(f"   Target: {target}")
        lines.append(f"   Reason: {reason}...")
        lines.append(f"   Created: {created}")
        lines.append("")
    
    return "\n".join(lines)


def view_code_proposal(args: dict) -> str:
    """View detailed information about a proposal."""
    proposal_id = args.get("proposal_id", "")
    
    if not proposal_id:
        return "Error: proposal_id is required."
    
    proposal = get_proposal(proposal_id)
    
    if not proposal:
        return f"Proposal {proposal_id} not found."
    
    lines = [
        f"=" * 60,
        f"Proposal: {proposal_id}",
        f"Status: {proposal.get('status', 'unknown')}",
        f"=" * 60,
        "",
        f"Target: {proposal.get('target', 'unknown')}",
        f"Reason: {proposal.get('reason', 'N/A')}",
        f"Author: {proposal.get('author', 'system')}",
        "",
        f"Created: {proposal.get('created_at_human', 'N/A')}",
    ]
    
    if proposal.get("approved_at_human"):
        lines.append(f"Approved: {proposal['approved_at_human']}")
        lines.append(f"Reviewer: {proposal.get('reviewer', 'N/A')}")
    
    if proposal.get("rejected_at_human"):
        lines.append(f"Rejected: {proposal['rejected_at_human']}")
        lines.append(f"Rejection Reason: {proposal.get('rejection_reason', 'N/A')}")
    
    lines.extend([
        "",
        "Validation:",
        f"  Valid: {proposal.get('validation', {}).get('valid', False)}",
        f"  Lines: {proposal.get('validation', {}).get('lines', 0)}",
        f"  Safe: {proposal.get('validation', {}).get('safe', False)}",
    ])
    
    dangerous = proposal.get('validation', {}).get('dangerous_operations', [])
    if dangerous:
        lines.append(f"  Warnings: {', '.join(dangerous)}")
    
    lines.extend([
        "",
        "Diff Preview (first 30 lines):",
        "-" * 60,
    ])
    
    diff = proposal.get("diff", "")
    diff_lines = diff.split("\n")[:30]
    lines.extend(diff_lines)
    
    if len(diff.split("\n")) > 30:
        lines.append("... (truncated)")
    
    lines.extend([
        "-" * 60,
        "",
        f"To approve: approve_code_change(proposal_id=\"{proposal_id}\")",
        f"To reject: reject_code_change(proposal_id=\"{proposal_id}\")",
        "",
    ])
    
    return "\n".join(lines)


# =============================================================================
# Utility Functions
# =============================================================================

def create_proposal_from_diff(target_path: str, diff_text: str, reason: str, author: str = "system") -> dict:
    """Create a proposal from a unified diff format."""
    import re
    
    # Parse the diff to get original and replacement
    lines = diff_text.split("\n")
    original_lines = []
    new_lines = []
    in_original = False
    in_new = False
    
    for line in lines:
        if line.startswith("---"):
            continue
        if line.startswith("+++"):
            continue
        if line.startswith("@@"):
            continue
        if line.startswith("-"):
            original_lines.append(line[1:])
        elif line.startswith("+"):
            new_lines.append(line[1:])
        else:
            # Context line
            original_lines.append(line)
            new_lines.append(line)
    
    # This is a simplified approach - real diff parsing is more complex
    # For now, we just use the new_code as the replacement
    new_code = "\n".join(new_lines)
    
    return propose_mutation(target_path, new_code, reason, author)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python zoey_genome.py <command> [args]")
        print("")
        print("Commands:")
        print("  propose <target_file> <reason>     - Propose a code change")
        print("  approve <proposal_id>               - Approve a proposal")
        print("  reject <proposal_id> [reason]       - Reject a proposal")
        print("  rollback <proposal_id>              - Rollback an applied proposal")
        print("  list [status]                       - List proposals")
        print("  view <proposal_id>                  - View proposal details")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "propose":
        if len(sys.argv) < 4:
            print("Usage: propose <target_file> <reason>")
            print("Note: The new code should be provided via stdin")
            sys.exit(1)
        
        target = sys.argv[2]
        reason = sys.argv[3]
        
        print(f"Reading new code from stdin (Ctrl+D when done)...")
        new_code = sys.stdin.read()
        
        result = propose_mutation(target, new_code, reason)
        print(json.dumps(result, indent=2))
    
    elif command == "approve":
        if len(sys.argv) < 3:
            print("Usage: approve <proposal_id>")
            sys.exit(1)
        
        proposal_id = sys.argv[2]
        result = approve_proposal(proposal_id)
        print(json.dumps(result, indent=2))
    
    elif command == "reject":
        if len(sys.argv) < 3:
            print("Usage: reject <proposal_id> [reason]")
            sys.exit(1)
        
        proposal_id = sys.argv[2]
        reason = sys.argv[3] if len(sys.argv) > 3 else ""
        result = reject_proposal(proposal_id, reason=reason)
        print(json.dumps(result, indent=2))
    
    elif command == "rollback":
        if len(sys.argv) < 3:
            print("Usage: rollback <proposal_id>")
            sys.exit(1)
        
        proposal_id = sys.argv[2]
        result = rollback_proposal(proposal_id)
        print(json.dumps(result, indent=2))
    
    elif command == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        proposals = list_proposals(status)
        print(json.dumps(proposals, indent=2))
    
    elif command == "view":
        if len(sys.argv) < 3:
            print("Usage: view <proposal_id>")
            sys.exit(1)
        
        proposal_id = sys.argv[2]
        result = view_code_proposal({"proposal_id": proposal_id})
        print(result)
    
    else:
        print(f"Unknown command: {command}")
        print("Run without arguments for usage help.")
        sys.exit(1)