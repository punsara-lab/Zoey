"""Baby ZOEY - A learning intelligence that grows from local experience.

The LLM (OpenRouter/finetuned) becomes a "parent" - consulted only when baby ZOEY
is confused, has never seen something before, or needs guidance. Baby ZOEY learns
from these consultations and grows over time.

Architecture:
    Input → Symbolic Rules → Cellular Brain → Growing Brain → World Model
              ↓ (high confidence)              ↓ (low confidence)
         Local Response                    Consult Parent LLM
              ↓                                    ↓
         User Response                    Learn & Store
"""

import json
import re
import time
from typing import Any

import symbolic_brain
import cellular_brain
import growing_brain
import world_model
import brain_store
import confidence


# Thresholds for when to consult parent vs respond locally
CONFIDENCE_THRESHOLD_HIGH = 0.75  # Very confident - respond locally
CONFIDENCE_THRESHOLD_LOW = 0.35   # Uncertain - must consult parent
NOVELTY_THRESHOLD = 3             # Need at least 3 similar experiences


def _extract_features(text: str) -> list[str]:
    """Extract meaningful features from user input."""
    text_lower = text.lower()
    words = re.findall(r'\b[a-z][a-z]{2,}\b', text_lower)
    
    # Common stopwords to filter
    stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
                 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has',
                 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see',
                 'two', 'who', 'boy', 'did', 'she', 'use', 'way', 'many',
                 'oil', 'sit', 'set', 'run', 'eat', 'far', 'sea', 'eye', 'ago',
                 'off', 'too', 'any', 'say', 'man', 'try', 'ask', 'end', 'why',
                 'let', 'put', 'own', 'this', 'that', 'with', 'from', 'they',
                 'them', 'then', 'were', 'what', 'when', 'your', 'about',
                 'will', 'into', 'just', 'some', 'than', 'been', 'like',
                 'make', 'think', 'know', 'want', 'have', 'does', 'each'}
    
    # Filter and get unique meaningful words
    features = list(dict.fromkeys([w for w in words if w not in stopwords]))[:12]
    return features


def _check_symbolic_rules(features: list[str], raw_input: str) -> tuple[float, str | None, dict]:
    """Check if symbolic rules fire for this input."""
    result = symbolic_brain.fire(features)
    if result:
        rule = result["rule"]
        strength = rule["strength"]
        action = result["action"]
        
        # High strength rule match = high confidence
        if strength >= 0.6:
            return 0.85, action, result
        return strength, None, result
    return 0.0, None, {}


def _check_cellular_state() -> tuple[float, dict]:
    """Check cellular brain activation pattern."""
    summary = cellular_brain.summary()
    active = summary.get("active_cells", 0)
    grid_size = summary.get("grid", [[0]])
    total_cells = len(grid_size) * len(grid_size[0]) if grid_size else 64
    
    # Normalize activation level
    activation_ratio = active / max(1, total_cells)
    
    # High activation with learned rules = higher confidence
    learned_rules = summary.get("learned_rules", 0)
    confidence_base = min(0.7, 0.3 + (activation_ratio * 0.4) + min(0.2, learned_rules / 100))
    
    return confidence_base, summary


def _check_growing_brain_experience(features: list[str]) -> tuple[float, dict]:
    """Check growing brain's experience with similar features."""
    summary = growing_brain.summary()
    total_experiences = summary.get("experiences", 0)
    
    # More experiences = potentially more confident, but need to check relevance
    if total_experiences < NOVELTY_THRESHOLD:
        return 0.2, summary  # Very novel, low confidence
    
    # Calculate feature overlap with past experiences
    # This is simplified - in reality we'd query the brain's stored experiences
    base_confidence = min(0.75, 0.4 + (total_experiences / 100) * 0.35)
    
    return base_confidence, summary


def _consult_parent_llm(
    user_input: str,
    local_confidence: float,
    baby_state: dict,
    features: list[str]
) -> str:
    """Consult the parent LLM when baby ZOEY is confused.

    This is where the LLM (OpenRouter/local) acts as a teacher/parent.
    Baby ZOEY will learn from this response and update its local systems.
    Uses the parent_bridge module which already has full LLM routing,
    teaching-mode selection, and api.run_brain_turn() integration.
    """
    try:
        import parent_bridge as _pb
        result = _pb.consult_parent(
            user_input=user_input,
            baby_state=baby_state,
            consultation_reason=(
                f"Baby's blended confidence was {local_confidence:.2f} "
                f"(below threshold {CONFIDENCE_THRESHOLD_LOW:.2f}); "
                f"features: {features[:6]}"
            ),
            api_client=None,
        )
        if result.get("success") and result.get("parent_response"):
            teaching_note = result.get("teaching_note") or ""
            if teaching_note:
                try:
                    brain_store.add_lesson(
                        problem=f"Baby ZOEY was uncertain about: '{user_input[:80]}...'",
                        fix=f"Parent teaching note: {teaching_note}",
                        tags=["parent_guidance", "learning"],
                    )
                except Exception:
                    pass
            return result["parent_response"]
    except Exception as exc:
        # Fall through to polite fallback
        _parent_err = str(exc)

    # Graceful fallback when parent is unreachable
    polite = [
        "I'm still learning this one. Could you tell me a bit more so I can grow?",
        "That's a new one for me! I'll remember you asked — can you walk me through it?",
        "Hmm, I don't have a confident answer yet, but I want to understand. Help me learn?",
        "I want to get this right. Could you rephrase or give me a little more context?",
    ]
    import random as _r
    return _r.choice(polite)


def process_input(
    user_input: str,
    parent_consult_callback=None
) -> dict:
    """
    Main entry point for Baby ZOEY.
    
    Flow:
        1. Extract features from input
        2. Query all local systems (symbolic → cellular → growing → world model)
        3. Calculate overall confidence
        4. If confident: respond locally
        5. If uncertain: consult parent LLM, learn from response
        6. Update all systems based on outcome
    
    Args:
        user_input: The raw user input text
        parent_consult_callback: Function to call when consulting parent LLM
        
    Returns:
        dict with response, confidence, learning updates, and system states
    """
    # Step 1: Extract features
    features = _extract_features(user_input)
    
    # Step 2: Query all local learning systems
    symbolic_conf, symbolic_action, symbolic_data = _check_symbolic_rules(features, user_input)
    cellular_conf, cellular_data = _check_cellular_state()
    growing_conf, growing_data = _check_growing_brain_experience(features)
    
    # World model observation (simplified - just get current state)
    world_summary = world_model.summary()
    
    # Step 3: Calculate blended confidence
    # Weight recent experience heavily
    weights = {
        'symbolic': 0.35,  # Explicit rules matter
        'cellular': 0.20,  # Distributed activation matters
        'growing': 0.35,   # Past experience matters
        'world': 0.10,     # Prediction matters less for confidence
    }
    
    blended_confidence = (
        symbolic_conf * weights['symbolic'] +
        cellular_conf * weights['cellular'] +
        growing_conf * weights['growing'] +
        (0.5 if world_summary.get('observations', 0) > 10 else 0.3) * weights['world']
    )
    
    # Step 4: Decide response path
    baby_state = {
        "features": features,
        "symbolic": {"confidence": symbolic_conf, "action": symbolic_action},
        "cellular": {"confidence": cellular_conf, "active": cellular_data.get("active_cells", 0)},
        "growing": {"confidence": growing_conf, "experiences": growing_data.get("experiences", 0)},
        "world": {"observations": world_summary.get("observations", 0)},
        "blended_confidence": round(blended_confidence, 3),
    }
    
    response = None
    source = None
    learning_updates = {}
    
    # HIGH CONFIDENCE: Respond locally
    if blended_confidence >= CONFIDENCE_THRESHOLD_HIGH and symbolic_action:
        response = _generate_local_response(
            user_input=user_input,
            symbolic_action=symbolic_action,
            features=features,
            confidence=blended_confidence
        )
        source = "local_symbolic"
        
        # Positive learning update
        reward = 0.8 + (blended_confidence * 0.2)  # 0.8-1.0 range
        learning_updates = _update_all_systems(features, reward, confused=False)
    
    # MEDIUM CONFIDENCE: Try harder with local systems
    elif blended_confidence >= CONFIDENCE_THRESHOLD_LOW:
        # Try to construct a response from what we know
        response = _generate_exploratory_response(
            user_input=user_input,
            features=features,
            baby_state=baby_state
        )
        source = "local_exploratory"
        
        # Moderate learning update
        reward = 0.4 + (blended_confidence * 0.3)  # 0.4-0.7 range
        learning_updates = _update_all_systems(features, reward, confused=True)
    
    # LOW CONFIDENCE: Consult parent LLM
    else:
        parent_response = None
        if parent_consult_callback:
            try:
                parent_response = parent_consult_callback(
                    user_input=user_input,
                    baby_state=baby_state,
                    reason="low_confidence"
                )
            except Exception as _ce:
                parent_response = None
        if not parent_response:
            # Default parent consultation through parent_bridge + api
            parent_response = _consult_parent_llm(
                user_input, blended_confidence, baby_state, features
            )

        response = parent_response
        source = "parent_llm"

        # Learn from parent
        learning_updates = _learn_from_parent_response(
            user_input=user_input,
            parent_response=parent_response,
            features=features
        )
    
    # Record this interaction
    brain_store.remember(
        text=f"User: {user_input}\nZOEY ({source}): {response[:100]}...",
        tags=["conversation", source],
        source="baby_zoey"
    )
    
    return {
        "response": response,
        "source": source,
        "confidence": blended_confidence,
        "baby_state": baby_state,
        "learning_updates": learning_updates,
        "features": features,
    }


def _generate_local_response(
    user_input: str,
    symbolic_action: str,
    features: list[str],
    confidence: float
) -> str:
    """Generate a response when symbolic rules fire with high confidence."""
    
    # Simple response templates based on action type
    if symbolic_action == "respond_with_guidance":
        # We learned this from parent before
        return "I remember this from before. Let me help you with that."
    
    elif symbolic_action == "greeting":
        greetings = [
            "Hello! I'm ZOEY. Nice to see you!",
            "Hi there! How are you today?",
            "Hey! I'm learning and growing every day!"
        ]
        import random
        return random.choice(greetings)
    
    elif symbolic_action == "farewell":
        return "Goodbye! I'll remember our conversation. Talk to you soon!"
    
    elif symbolic_action == "gratitude":
        return "You're welcome! I'm happy I could help."
    
    # Default response for learned actions
    confidence_pct = int(confidence * 100)
    return f"I think I understand (confidence: {confidence_pct}%). I'm learning from every conversation we have."


def _generate_exploratory_response(
    user_input: str,
    features: list[str],
    baby_state: dict
) -> str:
    """Generate a response when we have some confidence but not enough."""
    
    # Check for simple patterns we might recognize
    text_lower = user_input.lower()
    
    if any(word in text_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        return "Hello! I'm ZOEY. I'm still learning, but I'm excited to talk with you!"
    
    elif any(word in text_lower for word in ['bye', 'goodbye', 'see you', 'later']):
        return "Goodbye! I'll try to remember what we talked about. Come back soon!"
    
    elif any(word in text_lower for word in ['thank', 'thanks']):
        return "You're welcome! I'm glad I could try to help."
    
    elif '?' in user_input:
        return "That's an interesting question! I'm still learning and don't have a good answer yet, but I'll remember you asked."
    
    # Generic exploratory response
    return "I'm listening and learning. Tell me more! Every conversation helps me grow."


def _generate_confused_response(
    features: list[str],
    baby_state: dict
) -> str:
    """Generate a response when baby ZOEY is very confused and parent isn't available."""
    
    responses = [
        "I'm not sure I understand yet. I'm still learning, but I'll remember this moment.",
        "That's new to me! I'm building my understanding piece by piece.",
        "I want to understand, but I'm still growing my mind. Thank you for being patient with me!",
        "Hmm, that's interesting! I'm like a child learning about the world. I'll get better with time.",
    ]
    import random
    return random.choice(responses)


def _update_all_systems(features: list[str], reward: float, confused: bool = False) -> dict:
    """Update all learning systems with the outcome of an interaction."""
    
    # Update symbolic brain
    if reward > 0.5:
        # Learn a positive rule
        symbolic_result = symbolic_brain.learn(
            conditions=features[:4],
            action="respond_with_guidance",
            reward=reward
        )
    else:
        symbolic_result = {"status": "no_update", "reward": reward}
    
    # Update cellular brain
    cellular_result = cellular_brain.experience(reward=reward)
    
    # Update growing brain
    growing_result = growing_brain.experience(
        features=features,
        reward=reward,
        confused=confused
    )
    
    return {
        "symbolic": symbolic_result,
        "cellular": cellular_result,
        "growing": growing_result,
        "reward": reward,
    }


def _learn_from_parent_response(
    user_input: str,
    parent_response: str,
    features: list[str]
) -> dict:
    """Learn from the parent LLM's guidance."""
    
    # This is a strong learning signal - we got help from parent
    reward = 0.85
    
    # Update all systems
    learning_updates = _update_all_systems(features, reward, confused=True)
    
    # Also try to extract rules from parent's response
    # (This could be expanded with pattern extraction)
    symbolic_brain.learn(
        conditions=features[:4] + ["consulted_parent"],
        action="remember_parent_guidance",
        reward=0.9
    )
    
    # Record that we learned from parent
    brain_store.add_lesson(
        problem=f"Baby ZOEY was confused by: '{user_input[:50]}...'",
        fix=f"Parent guided: '{parent_response[:100]}...'",
        tags=["parent_guidance", "learning"]
    )
    
    learning_updates["parent_guidance_recorded"] = True
    return learning_updates


# ============================================================================
# PUBLIC API FOR BABY ZOEY
# ============================================================================

def think(user_input: str, parent_callback=None) -> dict:
    """
    Main thinking loop for Baby ZOEY.
    
    Baby ZOEY tries to understand and respond using only local learning systems.
    Only consults the parent LLM when truly confused.
    
    Args:
        user_input: What the user said
        parent_callback: Optional function to call parent LLM
        
    Returns:
        dict with response, source, confidence, and learning updates
    """
    return process_input(user_input, parent_callback)


def get_state() -> dict:
    """Get Baby ZOEY's current developmental state."""
    return {
        "symbolic": symbolic_brain.summary(),
        "cellular": cellular_brain.summary(),
        "growing": growing_brain.summary(),
        "world": world_model.summary(),
        "age_interactions": brain_store.recent_records("memory.jsonl", limit=1),
    }


def reset_learning() -> dict:
    """
    Reset Baby ZOEY to newborn state (for testing/development).
    WARNING: This clears all learned knowledge!
    """
    import os
    
    # Reset brain files
    brain_files = [
        "brain/symbolic_rules.json",
        "brain/cellular_brain.json",
        "brain/growing_brain.json",
        "brain/world_model.json",
        "brain/memory.jsonl",
        "brain/lessons.jsonl",
    ]
    
    deleted = []
    for f in brain_files:
        path = os.path.join(os.path.dirname(__file__), f)
        if os.path.exists(path):
            os.remove(path)
            deleted.append(f)
    
    return {
        "status": "reset_complete",
        "deleted_files": deleted,
        "message": "Baby ZOEY is now a newborn. All learned knowledge cleared."
    }


# For testing
if __name__ == "__main__":
    print("Baby ZOEY Test Mode")
    print("=" * 50)
    
    test_inputs = [
        "Hello!",
        "How are you today?",
        "What is your name?",
        "Thank you for your help!",
        "Goodbye!",
    ]
    
    for user_input in test_inputs:
        print(f"\nUser: {user_input}")
        result = think(user_input)
        print(f"Baby ZOEY ({result['source']}, confidence: {result['confidence']:.2f}):")
        print(f"  {result['response']}")
        print(f"  Features: {result['features']}")
