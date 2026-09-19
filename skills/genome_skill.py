"""
ZOEY Genome Skill - Self-Modification with Human Approval

This skill exposes the zoey_genome capabilities as tools that ZOEY can use
to propose, review, and manage code changes - but always with human approval.
"""

import sys
import os

# Add parent directory to path so we can import zoey_genome
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import zoey_genome


def propose_code_change(args: dict) -> str:
    """
    Propose a source code mutation for human review.
    
    This creates a proposal that must be approved before it's applied.
    The proposal is validated for syntax and safety before being saved.
    """
    target_file = args.get("target_file", "")
    new_code = args.get("new_code", "")
    reason = args.get("reason", "")
    
    if not target_file or not new_code or not reason:
        return "Error: target_file, new_code, and reason are all required."
    
    # Call zoey_genome to create the proposal
    result = zoey_genome.propose_code_change(args)
    return result


def approve_code_change(args: dict) -> str:
    """
    Approve and apply a pending code change proposal.
    
    This will:
    1. Create a backup of the original file
    2. Apply the proposed changes
    3. Validate the changes work
    4. Archive the proposal as approved
    
    You can rollback later if needed.
    """
    proposal_id = args.get("proposal_id", "")
    test_first = args.get("test_first", True)
    
    if not proposal_id:
        return "Error: proposal_id is required."
    
    result = zoey_genome.approve_code_change(args)
    return result


def reject_code_change(args: dict) -> str:
    """
    Reject a pending code change proposal.
    
    This archives the proposal as rejected. The original file is not modified.
    """
    proposal_id = args.get("proposal_id", "")
    reason = args.get("reason", "")
    
    if not proposal_id:
        return "Error: proposal_id is required."
    
    result = zoey_genome.reject_code_change(args)
    return result


def rollback_code_change(args: dict) -> str:
    """
    Rollback an applied code change by restoring from backup.
    
    This will:
    1. Find the backup created when the proposal was approved
    2. Restore the original file from backup
    3. Archive the proposal as rolled_back
    
    This is useful if an approved change causes issues.
    """
    proposal_id = args.get("proposal_id", "")
    
    if not proposal_id:
        return "Error: proposal_id is required."
    
    result = zoey_genome.rollback_code_change(args)
    return result


def list_code_proposals(args: dict) -> str:
    """
    List all code change proposals with optional status filter.
    
    Shows pending, approved, rejected, and rolled_back proposals.
    """
    result = zoey_genome.list_code_proposals(args)
    return result


def view_code_proposal(args: dict) -> str:
    """
    View detailed information about a specific proposal.
    
    Shows the full diff, validation results, status history, and actions taken.
    """
    result = zoey_genome.view_code_proposal(args)
    return result


# =============================================================================
# Tool Definitions for Integration
# =============================================================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "propose_code_change",
            "description": "Propose a source code mutation. Creates a proposal for human review - never applies automatically. Validates syntax and checks for dangerous operations.",
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
            "description": "Approve and apply a pending code change proposal. Creates backup, validates changes, and archives the proposal. Can rollback later if needed.",
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
            "description": "Reject a pending code change proposal. Archives it as rejected without modifying any files.",
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
            "description": "Rollback an applied code change by restoring from backup. Archives the proposal as rolled_back.",
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
            "description": "List all code change proposals with optional status filter (pending, approved, rejected, rolled_back).",
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
            "description": "View detailed information about a specific proposal including full diff and validation results.",
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


DISPATCH = {
    "propose_code_change": propose_code_change,
    "approve_code_change": approve_code_change,
    "reject_code_change": reject_code_change,
    "rollback_code_change": rollback_code_change,
    "list_code_proposals": list_code_proposals,
    "view_code_proposal": view_code_proposal,
}
