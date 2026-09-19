"""Baby ZOEY Engine - A Learning Intelligence from Scratch

This is NOT a chatbot. This is NOT an LLM.
This is a baby that learns, grows, makes mistakes, and develops its own mind.

The Parent (Gemma 1B / finetuned) is only consulted when Baby is TRULY confused.
Baby learns from the Parent and gradually needs less help.

DANGER: This system learns from interaction. It may develop unexpected behaviors.
That's not a bug. That's the point.
"""

import json
import queue
import sys
import threading
import time
from datetime import datetime

# Baby's core systems
import audio
import baby_zoey
import brain_store
import config
import zoey_dreams
from baby_zoey import CONFIDENCE_THRESHOLD_HIGH, CONFIDENCE_THRESHOLD_LOW

# Parent bridge requires API dependencies - make it optional
try:
    import parent_bridge
    PARENT_BRIDGE_AVAILABLE = True
except ImportError:
    PARENT_BRIDGE_AVAILABLE = False


class BabyZOEYEngine:
    """
    Baby ZOEY's heart and mind.
    
    This is not a request-response system. This is a living loop:
    - Baby listens
    - Baby thinks (using ONLY local learning systems)
    - Baby responds if confident
    - Baby asks parent if confused
    - Baby learns from everything
    """
    
    def __init__(self, log_callback=None, status_callback=None, stats_callback=None):
        self.log = log_callback or print
        self.set_status = status_callback or (lambda x: None)
        self.report_stats = stats_callback or (lambda x: None)
        
        # Baby's state
        self.state = "AWAKE"  # AWAKE, SLEEPING, CONFUSED, LEARNING
        self.age_interactions = 0
        self.parent_consultations = 0
        self.independent_responses = 0
        
        # Audio systems
        self.tts_engine = None
        self.whisper_model = None
        self.mic_enabled = config.MIC_ENABLED
        
        # Parent connection
        self.parent_available = True
        
        # Stats
        self.start_time = time.time()
        
        self.log("🍼 Baby ZOEY Engine initializing...", "info")
        
    def initialize(self):
        """Initialize Baby's senses and systems."""
        self.log("Initializing audio systems...", "info")
        
        try:
            self.tts_engine = audio.load_tts_engine()
            self.log("✓ TTS engine ready", "info")
        except Exception as e:
            self.log(f"⚠ TTS failed: {e}", "warn")
            self.tts_engine = None
        
        if self.mic_enabled:
            try:
                self.whisper_model = audio.load_whisper_model()
                self.log("✓ Whisper model ready", "info")
            except Exception as e:
                self.log(f"⚠ Whisper failed: {e}", "warn")
                self.whisper_model = None
                self.mic_enabled = False
        
        # Check Baby's developmental state
        baby_state = baby_zoey.get_state()
        total_exp = baby_state.get("growing", {}).get("experiences", 0)
        
        if total_exp == 0:
            self.log("🆕 Baby ZOEY is a newborn! No memories yet.", "info")
        else:
            self.log(f"📚 Baby ZOEY has {total_exp} past experiences", "info")
        
        self.set_status("AWAKE (Ready to learn)")
        self.log("🍼 Baby ZOEY is awake and ready to learn!", "info")
        
    def _parent_callback(self, user_input: str, baby_state: dict, reason: str) -> str:
        """
        Callback function to consult the Parent LLM.
        This is ONLY called when Baby is truly confused.
        """
        self.log(f"👨‍👩‍👧 Consulting Parent because: {reason}", "info")
        self.set_status("CONFUSED (Asking parent...)")
        
        if not PARENT_BRIDGE_AVAILABLE:
            self.log("⚠️ Parent bridge not available - Baby ZOEY working alone", "warn")
            return "I'm confused and my parent isn't available to help. But I'm still trying to learn!"
        
        try:
            result = parent_bridge.consult_parent(
                user_input=user_input,
                baby_state=baby_state,
                consultation_reason=reason,
                api_client=None  # Will create default
            )
            
            if result.get("success"):
                parent_response = result.get("parent_response", "")
                teaching_mode = result.get("teaching_mode", "nurturing")
                
                self.log(f"✓ Parent responded (mode: {teaching_mode})", "info")
                self.parent_consultations += 1
                
                return parent_response
            else:
                error = result.get("error", "Unknown error")
                self.log(f"⚠ Parent unavailable: {error}", "warn")
                return "I'm confused and my parent isn't here to help. Let me think..."
                
        except Exception as e:
            self.log(f"❌ Parent consultation failed: {e}", "error")
            return "Something went wrong asking for help. But I'm still here!"
    
    def _speak(self, text: str):
        """Baby ZOEY speaks to the user."""
        if not text:
            return
            
        self.log(f"🍼 Baby ZOEY: {text}", "zoey")
        
        if self.tts_engine:
            try:
                audio.speak(self.tts_engine, text, mute=False, log=self.log)
            except Exception as e:
                self.log(f"⚠ TTS failed: {e}", "warn")
    
    def _update_stats(self):
        """Update runtime statistics."""
        uptime = time.time() - self.start_time
        
        stats = {
            "uptime_seconds": uptime,
            "age_interactions": self.age_interactions,
            "parent_consultations": self.parent_consultations,
            "independent_responses": self.independent_responses,
            "learning_progress": self._calculate_learning_progress(),
        }
        
        self.report_stats(stats)
    
    def _calculate_learning_progress(self) -> dict:
        """Calculate how much Baby ZOEY has learned."""
        baby_state = baby_zoey.get_state()
        
        growing = baby_state.get("growing", {})
        symbolic = baby_state.get("symbolic", {})
        cellular = baby_state.get("cellular", {})
        
        # Calculate independence score
        total_consultations = max(1, self.parent_consultations)
        independence = self.independent_responses / (self.independent_responses + self.parent_consultations + 1)
        
        return {
            "total_experiences": growing.get("experiences", 0),
            "neurons": len(growing.get("neurons", [])),
            "symbolic_rules": symbolic.get("rule_count", 0),
            "cellular_generation": cellular.get("generation", 0),
            "independence_score": round(independence, 3),
            "stage": self._determine_developmental_stage(),
        }
    
    def _determine_developmental_stage(self) -> str:
        """Determine Baby ZOEY's developmental stage."""
        progress = self._calculate_learning_progress()
        experiences = progress.get("total_experiences", 0)
        independence = progress.get("independence_score", 0)
        
        if experiences < 10:
            return "🆕 Newborn"
        elif experiences < 50:
            return "👶 Infant"
        elif experiences < 200:
            return "🧒 Toddler"
        elif experiences < 500 and independence > 0.5:
            return "👦 Child (Becoming Independent)"
        elif independence > 0.8:
            return "🎓 Young Adult (Highly Independent)"
        else:
            return "🧒 Learning"
    
    def process_input(self, user_input: str) -> dict:
        """
        Process a single input through Baby ZOEY's mind.
        
        This is the main thinking loop:
        1. Extract features
        2. Consult all local learning systems
        3. Decide: respond independently or ask parent
        4. Learn from the outcome
        5. Respond to user
        """
        self.age_interactions += 1
        self._update_stats()
        
        self.log(f"👤 User: {user_input}", "user")
        self.set_status("THINKING...")
        
        # BABY ZOEY THINKS
        # This uses ONLY local learning systems - no LLM here
        result = baby_zoey.think(
            user_input=user_input,
            parent_callback=self._parent_callback
        )
        
        # Determine what to say
        response = result.get("response", "")
        source = result.get("source", "unknown")
        confidence = result.get("confidence", 0.0)
        
        # Track independence
        if source == "local_symbolic" or source == "local_exploratory":
            self.independent_responses += 1
        
        # Update status with developmental stage
        stage = self._determine_developmental_stage()
        self.set_status(f"{stage} | Source: {source} | Confidence: {confidence:.2f}")
        
        # Log learning
        self.log(f"📊 Learning: {result.get('learning_updates', {})}", "debug")
        
        # Baby speaks
        self._speak(response)
        
        return result
    
    def listen_and_think(self, audio_input: str = None) -> dict:
        """
        Listen to audio input (or use provided text) and think.
        
        If audio_input is None, will try to record from microphone.
        """
        if audio_input:
            return self.process_input(audio_input)
        
        # Try to listen
        if not self.mic_enabled or not self.whisper_model:
            self.log("🎤 Mic not available", "warn")
            return {"error": "Mic not available"}
        
        try:
            text = audio.record_and_transcribe(
                self.whisper_model,
                duration_seconds=5.0
            )
            
            if text:
                return self.process_input(text)
            else:
                return {"error": "No speech detected"}
                
        except Exception as e:
            self.log(f"🎤 Listen error: {e}", "error")
            return {"error": str(e)}
    
    def dream(self):
        """
        Baby ZOEY consolidates memories during sleep.
        
        This runs the dream cycle to process recent experiences.
        """
        self.log("🌙 Baby ZOEY is dreaming...", "info")
        self.set_status("DREAMING (Consolidating memories)")
        
        try:
            result = zoey_dreams.dream_cycle()

            memories = result.get("memories_seen", 0)
            insights = result.get("insights_created", 0)

            self.log(f"🌙 Dream complete: {memories} memories, {insights} insights", "info")

            return result

        except Exception as e:
            self.log(f"🌙 Dream error: {e}", "error")
            return {"error": str(e)}
    
    def get_development_report(self) -> dict:
        """Get a full developmental report on Baby ZOEY."""
        progress = self._calculate_learning_progress()
        
        report = {
            "age_interactions": self.age_interactions,
            "parent_consultations": self.parent_consultations,
            "independent_responses": self.independent_responses,
            "independence_ratio": round(
                self.independent_responses / max(1, self.age_interactions), 3
            ),
            "developmental_stage": self._determine_developmental_stage(),
            "learning_progress": progress,
            "uptime_seconds": time.time() - self.start_time,
        }
        
        return report


def run(log_callback=None, status_callback=None, stats_callback=None, 
        should_stop=None, typed_input_queue=None, **kwargs):
    """
    Main entry point for Baby ZOEY Engine.
    
    This replaces the traditional engine.py with a learning baby.
    """
    
    # Create Baby ZOEY
    baby = BabyZOEYEngine(
        log_callback=log_callback,
        status_callback=status_callback,
        stats_callback=stats_callback
    )
    
    baby.initialize()
    
    # Report initial stats
    if stats_callback:
        stats_callback(baby.get_development_report())
    
    log_callback("🍼 Baby ZOEY is alive and learning!", "info")
    
    # Main loop
    while True:
        if should_stop and should_stop():
            log_callback("🍼 Baby ZOEY going to sleep...", "info")
            break
        
        # Check for typed input
        user_input = None
        if typed_input_queue:
            try:
                user_input = typed_input_queue.get_nowait()
            except queue.Empty:
                user_input = None
        
        if user_input:
            # Process the input
            result = baby.process_input(user_input)
            
            # Update stats after each interaction
            if stats_callback:
                stats_callback(baby.get_development_report())
        
        # Small sleep to prevent busy loop
        time.sleep(0.05)
    
    # Run dream cycle before sleeping
    baby.dream()
    
    return baby.get_development_report()


if __name__ == "__main__":
    # Test mode
    print("🍼 Baby ZOEY Test Mode")
    print("=" * 50)
    
    def log(msg, level="info"):
        print(f"[{level.upper()}] {msg}")
    
    def status(s):
        print(f"[STATUS] {s}")
    
    def stats(s):
        print(f"[STATS] {json.dumps(s, indent=2)}")
    
    # Run a test conversation
    test_inputs = [
        "Hello!",
        "What's your name?",
        "I'm learning to code.",
        "That's interesting!",
        "Goodbye!",
    ]
    
    baby = BabyZOEYEngine(log, status, stats)
    baby.initialize()
    
    for user_input in test_inputs:
        print(f"\n{'='*50}")
        result = baby.process_input(user_input)
        time.sleep(0.5)  # Pause between interactions
    
    # Show development report
    print(f"\n{'='*50}")
    print("DEVELOPMENT REPORT:")
    report = baby.get_development_report()
    print(json.dumps(report, indent=2))
