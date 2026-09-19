"""Parent Bridge - Connects Baby ZOEY to the Parent LLM.

This module handles:
1. When Baby ZOEY consults the parent (confusion, novelty, learning opportunity)
2. How the parent responds (with teaching/guidance, not just answers)
3. How Baby ZOEY learns from the parent
4. The parent gradually teaching Baby ZOEY to be independent

The parent is not just an LLM - it's a teacher that wants Baby ZOEY to grow.
"""

import json
import re
from typing import Callable

import api
import baby_zoey
import symbolic_brain
import cellular_brain
import growing_brain
import brain_store


# Teaching modes - parent adapts based on Baby ZOEY's development
TEACHING_MODES = {
    "nurturing": "Parent provides warm, complete responses while explaining reasoning",
    "scaffolding": "Parent provides partial responses, prompting Baby ZOEY to complete",
    "guiding": "Parent asks questions to help Baby ZOEY find the answer itself",
    "coaching": "Parent provides minimal hints, Baby ZOEY must work independently",
}


def _determine_teaching_mode(baby_state: dict) -> str:
    """Determine how the parent should teach based on Baby ZOEY's development."""
    
    # Check total learning experiences
    growing_exp = baby_state.get("growing", {}).get("experiences", 0)
    symbolic_count = len(baby_state.get("symbolic", {}).get("rules", []))
    cellular_gen = baby_state.get("cellular", {}).get("generation", 0)
    
    # Calculate development score
    development = growing_exp + (symbolic_count * 10) + (cellular_gen / 100)
    
    # Choose teaching mode
    if development < 50:
        return "nurturing"  # Very young - parent does most work
    elif development < 200:
        return "scaffolding"  # Some experience - partial help
    elif development < 500:
        return "guiding"  # Experienced - questions, not answers
    else:
        return "coaching"  # Mature - minimal hints


def _build_parent_prompt(
    user_input: str,
    baby_state: dict,
    teaching_mode: str,
    consultation_reason: str
) -> str:
    """Build the prompt for the parent LLM."""
    
    # Get development metrics
    growing = baby_state.get("growing", {})
    symbolic = baby_state.get("symbolic", {})
    cellular = baby_state.get("cellular", {})
    
    prompt = f"""You are the PARENT of Baby ZOEY, a learning AI that is growing from local experience.

=== BABY ZOEY'S CURRENT STATE ===
Development Stage: {teaching_mode}
Growing Brain: {growing.get('experiences', 0)} experiences, {growing.get('neurons', 2)} neurons
Symbolic Brain: {symbolic.get('rule_count', 0)} learned rules
Cellular Brain: Gen {cellular.get('generation', 0)}, {cellular.get('learned_rules', 0)} local patterns
Current Confidence: {baby_state.get('blended_confidence', 0.5):.2f}

=== CONSULTATION REASON ===
{consultation_reason}

=== YOUR ROLE AS PARENT ===
Teaching Mode: {teaching_mode}
- "nurturing": Provide warm, complete responses while explaining your reasoning
- "scaffolding": Provide partial responses, prompt Baby ZOEY to complete  
- "guiding": Ask questions to help Baby ZOEY find the answer itself
- "coaching": Provide minimal hints, Baby ZOEY must work independently

=== USER INPUT ===
"{user_input}"

=== YOUR RESPONSE ===
Provide a response that:
1. Matches the teaching mode (nurturing/scaffolding/guiding/coaching)
2. Is appropriate for the user's input
3. Can teach Baby ZOEY something new
4. Is warm and natural, not robotic

Also include a TEACHING NOTE for Baby ZOEY explaining what concept you want it to learn:

TEACHING_NOTE: <what Baby ZOEY should learn from this interaction>

Your response:"""

    return prompt


def _extract_teaching_note(response: str) -> str:
    """Extract the teaching note from parent response."""
    match = re.search(r'TEACHING_NOTE:\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "Learn from parent's example"


def _clean_parent_response(response: str) -> str:
    """Clean the parent response to remove teaching notes and prompts."""
    # Remove teaching note
    cleaned = re.sub(r'TEACHING_NOTE:.+?(?:\n|$)', '', response, flags=re.IGNORECASE)
    
    # Remove any "Your response:" or similar prompts that got echoed
    cleaned = re.sub(r'Your response:\s*', '', cleaned, flags=re.IGNORECASE)
    
    # Clean up whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def consult_parent(
    user_input: str,
    baby_state: dict,
    consultation_reason: str,
    api_client=None
) -> dict:
    """
    Consult the parent LLM when Baby ZOEY is confused.
    
    This is where the magic happens - the parent teaches, Baby ZOEY learns.
    
    Args:
        user_input: What the user said
        baby_state: Baby ZOEY's current cognitive state
        consultation_reason: Why we're consulting parent
        api_client: Optional API client to use (uses default if not provided)
        
    Returns:
        dict with parent_response, teaching_note, and learning_update
    """
    
    # Determine how parent should teach
    teaching_mode = _determine_teaching_mode(baby_state)
    
    # Build the parent prompt
    parent_prompt = _build_parent_prompt(
        user_input=user_input,
        baby_state=baby_state,
        teaching_mode=teaching_mode,
        consultation_reason=consultation_reason
    )
    
    # Call parent LLM
    try:
        if api_client is None:
            api_client = api.make_client()
        
        # Use the API to get parent response
        messages = [
            {"role": "system", "content": "You are a warm, teaching parent helping Baby ZOEY grow."},
            {"role": "user", "content": parent_prompt}
        ]
        
        response = api.run_brain_turn(api_client, messages, log=print)
        
        # Extract teaching note and clean response
        teaching_note = _extract_teaching_note(response)
        clean_response = _clean_parent_response(response)
        
        return {
            "parent_response": clean_response,
            "teaching_note": teaching_note,
            "teaching_mode": teaching_mode,
            "raw_response": response,
            "success": True,
        }
        
    except Exception as e:
        # Parent unavailable - return error state
        return {
            "parent_response": None,
            "teaching_note": None,
            "teaching_mode": teaching_mode,
            "error": str(e),
            "success": False,
        }


def quick_teach(
    user_input: str,
    correct_response: str,
    features: list[str] = None
) -> dict:
    """
    Quick teaching function - manually teach Baby ZOEY a correct response.
    
    This is like a parent explicitly teaching a child.
    
    Args:
        user_input: The input pattern
        correct_response: The correct response to learn
        features: Optional extracted features
        
    Returns:
        dict with learning updates
    """
    if features is None:
        features = baby_zoey._extract_features(user_input)
    
    # Strong positive learning signal
    reward = 0.95
    
    # Update symbolic rules with the explicit mapping
    symbolic_brain.learn(
        conditions=features[:4],
        action="respond:" + correct_response[:50],
        reward=reward
    )
    
    # Update all other systems
    cellular_brain.experience(reward=reward)
    growing_brain.experience(features=features, reward=reward, confused=False)
    
    # Record the explicit teaching
    brain_store.remember(
        text=f"EXPLICIT TEACHING: '{user_input}' → '{correct_response[:100]}'",
        tags=["explicit_teaching", "parent_guidance"],
        source="parent"
    )
    
    return {
        "status": "learned",
        "features": features,
        "reward": reward,
        "message": f"Baby ZOEY learned: '{correct_response[:50]}...'"
    }


# Export public API
__all__ = [
    'consult_parent',
    'quick_teach',
    '_determine_teaching_mode',
]
