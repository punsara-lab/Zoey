"""
Baby ZOEY Bridge - Integration with Main Engine

This module provides the bridge between Baby ZOEY (local learning system) and
the main ZOEY engine. It allows Baby ZOEY to handle inputs locally when confident,
and escalate to parent LLM when confused.
"""

import json
import re
import time
from typing import Any

import baby_zoey
import api
import brain_store


class BabyZOEYBridge:
    """
    Bridge between Baby ZOEY and the main engine.
    
    This allows the engine to:
    1. Try Baby ZOEY first for local, confident responses
    2. Escalate to parent LLM when Baby ZOEY is confused
    3. Learn from parent responses
    4. Track confidence and development
    """
    
    def __init__(self, log=None):
        self.log = log or print
        self.stats = {
            "baby_calls": 0,
            "baby_confident": 0,
            "baby_confused": 0,
            "parent_calls": 0,
            "learning_events": 0,
        }
        
    def process_input(self, user_input: str, messages: list, client=None, engine_log=None) -> dict:
        """
        Process user input through Baby ZOEY first, escalate to parent if needed.
        
        Args:
            user_input: The raw user input text
            messages: Current conversation history
            client: OpenAI/OpenRouter client for parent consultation
            engine_log: Engine's log function
            
        Returns:
            dict with response, source (baby/parent), confidence, etc.
        """
        _log = engine_log or self.log
        
        # Step 1: Try Baby ZOEY first
        _log("Baby ZOEY thinking...", "info")
        self.stats["baby_calls"] += 1
        
        # Define parent callback for when Baby ZOEY is confused
        def parent_callback(user_input: str, baby_state: dict, reason: str) -> str:
            """Consult parent LLM when Baby ZOEY is confused."""
            return self._consult_parent(
                user_input=user_input,
                baby_state=baby_state,
                messages=messages,
                client=client,
                log=_log
            )
        
        # Process through Baby ZOEY
        try:
            baby_result = baby_zoey.think(user_input, parent_callback=parent_callback)
        except Exception as e:
            _log(f"Baby ZOEY error: {e}", "error")
            # Fallback to parent
            baby_result = {
                "response": None,
                "source": "error",
                "confidence": 0.0,
            }
        
        # Step 2: Handle Baby ZOEY response
        source = baby_result.get("source", "unknown")
        confidence = baby_result.get("confidence", 0.0)
        
        # If Baby ZOEY responded confidently, use it
        if source in ["local_symbolic", "local_exploratory"] and confidence >= 0.5:
            self.stats["baby_confident"] += 1
            response = baby_result.get("response", "I'm thinking...")
            
            # Record learning
            self._record_interaction(user_input, response, "baby", confidence, baby_result)
            
            return {
                "response": response,
                "source": "baby_zoey",
                "confidence": confidence,
                "baby_state": baby_result.get("baby_state", {}),
                "learning_updates": baby_result.get("learning_updates", {}),
            }
        
        # Step 3: Baby ZOEY was confused or low confidence - use parent LLM
        self.stats["baby_confused"] += 1
        self.stats["parent_calls"] += 1
        
        _log("Baby ZOEY consulting parent...", "info")
        
        # Get parent response
        parent_response = self._consult_parent(
            user_input=user_input,
            baby_state=baby_result.get("baby_state", {}),
            messages=messages,
            client=client,
            log=_log
        )
        
        # Baby learns from parent response
        learning_updates = self._learn_from_parent(
            user_input=user_input,
            parent_response=parent_response,
            baby_result=baby_result,
            log=_log
        )
        
        self.stats["learning_events"] += 1
        
        # Record interaction
        self._record_interaction(user_input, parent_response, "parent", 0.7, baby_result)
        
        return {
            "response": parent_response,
            "source": "parent_llm",
            "confidence": 0.7,
            "baby_state": baby_result.get("baby_state", {}),
            "learning_updates": learning_updates,
        }
    
    def _consult_parent(self, user_input: str, baby_state: dict, messages: list, client=None, log=None) -> str:
        """Consult the parent LLM when Baby ZOEY is confused."""
        _log = log or self.log
        
        # Build prompt for parent
        context = f"""Baby ZOEY (a learning AI) is confused and needs guidance.

Baby's State:
- Confidence: {baby_state.get('blended_confidence', 'unknown')}
- Features detected: {baby_state.get('features', [])}
- Symbolic match: {baby_state.get('symbolic', {}).get('action', 'none')}
- Cellular activation: {baby_state.get('cellular', {}).get('active', 0)} cells
- Growing brain experiences: {baby_state.get('growing', {}).get('experiences', 0)}

The baby is learning through experience but encountered something new.
Please provide a helpful response to the user, and explain what the baby should learn from this.
"""
        
        # Add to messages
        temp_messages = messages.copy()
        temp_messages.append({"role": "system", "content": context})
        temp_messages.append({"role": "user", "content": user_input})
        
        # Call parent LLM
        try:
            if client:
                response = client.chat.completions.create(
                    model="anthropic/claude-3.5-sonnet",
                    messages=temp_messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                return response.choices[0].message.content
            else:
                # Fallback - no client available
                return "I'm here to help! (Baby ZOEY is learning but couldn't reach the parent LLM)"
        except Exception as e:
            _log(f"Parent consultation error: {e}", "error")
            return "I'm here! Let me try to help. (Baby ZOEY is still learning)"
    
    def _learn_from_parent(self, user_input: str, parent_response: str, baby_result: dict, log=None) -> dict:
        """Learn from the parent's response."""
        _log = log or self.log
        
        try:
            # Update Baby ZOEY's learning systems
            learning_updates = baby_zoey._update_all_systems(
                features=baby_result.get("features", []),
                reward=0.85,  # Learning from parent is positive
                confused=True  # We were confused, that's why we consulted
            )
            
            # Record the learning
            brain_store.remember(
                text=f"Baby learned from parent: '{user_input[:50]}...' → {parent_response[:50]}...",
                tags=["baby_learning", "parent_guidance"],
                source="baby_bridge"
            )
            
            _log("Baby ZOEY learned from parent response", "info")
            
            return learning_updates
            
        except Exception as e:
            _log(f"Learning update error: {e}", "error")
            return {}
    
    def _record_interaction(self, user_input: str, response: str, source: str, confidence: float, baby_result: dict):
        """Record the interaction for learning analysis."""
        try:
            brain_store.remember(
                text=f"User: {user_input}\nZoey ({source}): {response}",
                tags=["conversation", source, f"conf_{int(confidence*100)}"],
                source="baby_bridge"
            )
        except Exception:
            pass
    
    def get_stats(self) -> dict:
        """Get bridge statistics."""
        return self.stats.copy()


# Create singleton instance
_bridge_instance = None

def get_bridge(log=None) -> BabyZOEYBridge:
    """Get or create the Baby ZOEY bridge singleton."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = BabyZOEYBridge(log=log)
    return _bridge_instance


def process_with_baby(user_input: str, messages: list, client=None, log=None) -> dict:
    """
    Convenience function to process input through Baby ZOEY.
    
    Returns:
        dict with response, source, confidence, etc.
    """
    bridge = get_bridge(log=log)
    return bridge.process_input(user_input, messages, client=client, engine_log=log)


# =============================================================================
# Tool Integration (optional - for direct tool access)
# =============================================================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "ask_baby_zoey",
            "description": "Ask Baby ZOEY (the local learning system) for a response. Use when you want to test Baby's learning or when the query is simple enough for a child-level understanding.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question or input for Baby ZOEY."},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_baby_development",
            "description": "Check Baby ZOEY's development and learning progress. Shows experiences, learned rules, confidence levels, and growth statistics.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


def ask_baby_zoey(args: dict) -> str:
    """Ask Baby ZOEY directly for a response."""
    question = args.get("question", "")
    if not question:
        return "Please provide a question for Baby ZOEY."
    
    result = baby_zoey.think(question)
    
    response = result.get("response", "Baby ZOEY is thinking...")
    source = result.get("source", "unknown")
    confidence = result.get("confidence", 0.0)
    
    return (
        f"Baby ZOEY says: {response}\n\n"
        f"(Source: {source}, Confidence: {confidence:.2f})"
    )


def check_baby_development(args: dict) -> str:
    """Check Baby ZOEY's development status."""
    state = baby_zoey.get_state()
    
    lines = [
        "🍼 Baby ZOEY Development Report",
        "=" * 50,
        "",
        "🧠 Symbolic Brain:",
        f"  Rules: {state.get('symbolic', {}).get('rule_count', 0)}",
        f"  Experiences: {state.get('symbolic', {}).get('experiences', 0)}",
        "",
        "🦠 Cellular Brain:",
        f"  Generation: {state.get('cellular', {}).get('generation', 0)}",
        f"  Active Cells: {state.get('cellular', {}).get('active_cells', 0)}",
        f"  Learned Rules: {state.get('cellular', {}).get('learned_rules', 0)}",
        "",
        "🌱 Growing Brain:",
        f"  Experiences: {state.get('growing', {}).get('experiences', 0)}",
        f"  Neurons: {len(state.get('growing', {}).get('neurons', []))}",
        f"  Connections: {len(state.get('growing', {}).get('connections', []))}",
        "",
        "🌍 World Model:",
        f"  Observations: {state.get('world', {}).get('observations', 0)}",
        f"  Avg Surprise: {state.get('world', {}).get('average_surprise', 'N/A')}",
        "",
        "=" * 50,
    ]
    
    return "\n".join(lines)


DISPATCH = {
    "ask_baby_zoey": ask_baby_zoey,
    "check_baby_development": check_baby_development,
}
