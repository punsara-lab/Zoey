#!/usr/bin/env python3
"""
Run Baby ZOEY - A Learning Intelligence from Scratch

This is NOT a chatbot. This is NOT an LLM.
This is a baby that learns, grows, makes mistakes, and develops its own mind.

Usage:
    python run_baby_zoey.py              # Interactive mode
    python run_baby_zoey.py --voice      # With voice I/O
    python run_baby_zoey.py --reset     # Reset to newborn state
    python run_baby_zoey.py --report    # Show development report
"""

import argparse
import json
import os
import sys
import time

# Ensure we can find the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import baby_engine
import baby_zoey


def print_banner():
    """Print Baby ZOEY banner."""
    print("""
    🍼 Baby ZOEY 🍼
    A Learning Intelligence from Scratch
    
    ⚠️  WARNING: This is not a chatbot.
    This is a baby that learns from YOU.
    
    It will make mistakes. It will grow.
    It will become unique to your interactions.
    
    Type 'help' for commands, 'exit' to sleep.
    """)


def print_help():
    """Print help message."""
    print("""
Baby ZOEY Commands:
-------------------
help        - Show this help
status      - Show current developmental state
report      - Full development report
reset       - Reset Baby ZOEY to newborn (⚠️ DESTROYS ALL MEMORIES)
learn       - Show what Baby ZOEY has learned
sleep       - Put Baby ZOEY to sleep (save state, exit)
<anything>  - Talk to Baby ZOEY!
    """)


def print_status(baby_state: dict):
    """Print Baby ZOEY's current status."""
    print(f"\n🍼 Baby ZOEY Status:")
    print(f"  Stage: {baby_state.get('developmental_stage', 'Unknown')}")
    print(f"  Interactions: {baby_state.get('age_interactions', 0)}")
    print(f"  Parent Help Needed: {baby_state.get('parent_consultations', 0)}")
    print(f"  Independent Responses: {baby_state.get('independent_responses', 0)}")
    
    progress = baby_state.get('learning_progress', {})
    print(f"  Experiences: {progress.get('total_experiences', 0)}")
    print(f"  Neurons: {progress.get('neurons', 2)}")
    print(f"  Rules Learned: {progress.get('symbolic_rules', 0)}")


def print_report():
    """Print full development report."""
    report = baby_zoey.get_state()
    
    print("\n" + "="*60)
    print("📊 BABY ZOEY DEVELOPMENT REPORT")
    print("="*60)
    
    print("\n🧠 Symbolic Brain (Rules):")
    symbolic = report.get("symbolic", {})
    print(f"  Rules: {symbolic.get('rule_count', 0)}")
    print(f"  Experiences: {symbolic.get('experiences', 0)}")
    
    print("\n🦠 Cellular Brain (Patterns):")
    cellular = report.get("cellular", {})
    print(f"  Generation: {cellular.get('generation', 0)}")
    print(f"  Active Cells: {cellular.get('active_cells', 0)}")
    print(f"  Learned Rules: {cellular.get('learned_rules', 0)}")
    
    print("\n🌱 Growing Brain (Topology):")
    growing = report.get("growing", {})
    print(f"  Experiences: {growing.get('experiences', 0)}")
    print(f"  Neurons: {len(growing.get('neurons', []))}")
    print(f"  Connections: {len(growing.get('connections', []))}")
    
    print("\n🌍 World Model:")
    world = report.get("world", {})
    print(f"  Observations: {world.get('observations', 0)}")
    print(f"  Avg Surprise: {world.get('average_surprise', 'N/A')}")
    
    print("\n" + "="*60)


def confirm_reset():
    """Confirm before resetting Baby ZOEY."""
    print("\n⚠️  WARNING: This will ERASE ALL MEMORIES")
    print("Baby ZOEY will become a newborn again.")
    print("This cannot be undone!\n")
    
    confirm = input("Type 'RESET' to confirm: ")
    return confirm == "RESET"


def interactive_mode(args):
    """Run Baby ZOEY in interactive mode."""
    
    print_banner()
    
    # Create Baby ZOEY engine
    def log(msg, level="info"):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level.upper()}] {msg}")
    
    def status(s):
        pass  # Could update a status line
    
    def stats(s):
        pass  # Could display stats
    
    # Initialize
    baby = baby_engine.BabyZOEYEngine(log, status, stats)
    baby.initialize()
    
    print("\nBaby ZOEY is ready! Start talking to her.")
    print("(Type 'help' for commands, 'exit' to sleep)\n")
    
    # Main loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() == 'exit':
                print("\n🌙 Putting Baby ZOEY to sleep...")
                baby.dream()
                print("✨ Goodnight! Baby ZOEY is dreaming...\n")
                break
            
            elif user_input.lower() == 'help':
                print_help()
                continue
            
            elif user_input.lower() == 'status':
                status_dict = baby.get_development_report()
                print_status(status_dict)
                continue
            
            elif user_input.lower() == 'report':
                print_report()
                continue
            
            elif user_input.lower() == 'reset':
                if confirm_reset():
                    result = baby_zoey.reset_learning()
                    print(f"\n✅ {result['message']}")
                    print("Please restart Baby ZOEY to begin fresh.\n")
                    break
                else:
                    print("\nReset cancelled. Baby ZOEY's memories are safe.\n")
                continue
            
            elif user_input.lower() == 'learn':
                print_report()
                continue
            
            # Process the input
            result = baby.process_input(user_input)
            
            # Update stats display
            baby._update_stats()
            
        except KeyboardInterrupt:
            print("\n\n🌙 Interrupt received. Putting Baby ZOEY to sleep...")
            baby.dream()
            print("✨ Goodnight!\n")
            break
        
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Baby ZOEY - A Learning Intelligence from Scratch"
    )
    
    parser.add_argument(
        "--voice", "-v",
        action="store_true",
        help="Enable voice input/output (if available)"
    )
    
    parser.add_argument(
        "--report", "-r",
        action="store_true",
        help="Show development report and exit"
    )
    
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset Baby ZOEY to newborn (DESTROYS ALL MEMORIES)"
    )
    
    args = parser.parse_args()
    
    if args.report:
        print_report()
        return
    
    if args.reset:
        if confirm_reset():
            result = baby_zoey.reset_learning()
            print(f"\n✅ {result['message']}")
            print("Baby ZOEY is now a newborn.\n")
        return
    
    # Run interactive mode
    interactive_mode(args)


if __name__ == "__main__":
    main()
