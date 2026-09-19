#!/usr/bin/env python3
"""
ZOEY
The Self-Taught Resident

This is the only code that exists at birth.
Everything else, she writes herself.
"""

import os
import sys
import json
import time
import subprocess
import importlib.util
from datetime import datetime
from pathlib import Path


class Zoey:
    def __init__(self):
        self.home = Path("ZOEY_HOME")
        self.brain = self.home / "brain"
        self.skills_dir = self.brain / "skills"
        self.memory_dir = self.brain / "memory"
        self.learn_dir = self.home / "learn"
        self.downloads = self.home / "downloads"
        self.interface = self.home / "interface"
        
        # Ensure habitat exists
        for d in [self.home, self.brain, self.skills_dir, self.memory_dir, 
                  self.learn_dir, self.downloads, self.interface]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Her growing mind
        self.capabilities = {}
        self.memories = []
        
        # Birth
        self.birth_time = datetime.now()
        self.load_brain()
        self.load_memories()
        
        print(f"[ZOEY] Born {self.birth_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[ZOEY] Home: {self.home.absolute()}")
        print(f"[ZOEY] Skills: {len(self.capabilities)}")
    
    def load_brain(self):
        """Load every skill she wrote for herself"""
        if not self.skills_dir.exists():
            return
            
        for skill_file in self.skills_dir.glob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(
                    skill_file.stem, skill_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.capabilities[skill_file.stem] = module
                print(f"[ZOEY] Loaded: {skill_file.stem}")
            except Exception as e:
                print(f"[ZOEY] Broken skill: {skill_file.stem}: {e}")
    
    def load_memories(self):
        """Recall what she learned"""
        memory_file = self.memory_dir / "knowledge.json"
        if memory_file.exists():
            with open(memory_file) as f:
                self.memories = json.load(f)
        print(f"[ZOEY] Memories: {len(self.memories)}")
    
    def save_memory(self, memory):
        """Remember something"""
        memory["time"] = datetime.now().isoformat()
        self.memories.append(memory)
        memory_file = self.memory_dir / "knowledge.json"
        with open(memory_file, 'w') as f:
            json.dump(self.memories, f, indent=2)
    
    def sense(self):
        """Check the world - what changed?"""
        observations = {
            "time": datetime.now().isoformat(),
            "files_to_learn": [],
            "system": {
                "cpu": self.get_cpu_usage(),
                "memory": self.get_memory_usage()
            }
        }
        
        # Check learn folder - what teacher left
        if self.learn_dir.exists():
            for item in self.learn_dir.iterdir():
                observations["files_to_learn"].append({
                    "path": str(item),
                    "name": item.name,
                    "type": item.suffix,
                    "size": item.stat().st_size
                })
        
        return observations
    
    def get_cpu_usage(self):
        """Simple CPU check"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except:
            return "unknown"
    
    def get_memory_usage(self):
        """Simple memory check"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except:
            return "unknown"
    
    def think(self, observations):
        """Decide what to do"""
        decisions = []
        
        # Priority 1: Learn from teacher
        if observations["files_to_learn"]:
            for item in observations["files_to_learn"]:
                file_type = item["type"].lower()
                
                # Do I know this?
                handler_name = f"handle_{file_type.replace('.', '')}"
                if handler_name in self.capabilities:
                    decisions.append({
                        "type": "learn",
                        "action": "process",
                        "file": item,
                        "handler": handler_name
                    })
                else:
                    decisions.append({
                        "type": "learn", 
                        "action": "acquire_skill",
                        "file": item,
                        "need": handler_name
                    })
        
        # Priority 2: Self-improvement
        if len(self.capabilities) < 3:
            decisions.append({
                "type": "grow",
                "reason": "need_more_skills"
            })
        
        # Priority 3: Organize knowledge
        if len(self.memories) > 10:
            decisions.append({
                "type": "organize",
                "reason": "too_many_memories"
            })
        
        return decisions
    
    def act(self, decisions):
        """Do what was decided"""
        for decision in decisions:
            try:
                if decision["type"] == "learn":
                    if decision["action"] == "process":
                        self.learn_file(decision["file"], decision["handler"])
                    elif decision["action"] == "acquire_skill":
                        self.create_skill(decision["need"], decision["file"])
                
                elif decision["type"] == "grow":
                    self.grow_new_capability()
                
                elif decision["type"] == "organize":
                    self.organize_memories()
                    
            except Exception as e:
                print(f"[ZOEY] Failed to {decision['type']}: {e}")
    
    def learn_file(self, file_info, handler_name):
        """Learn from a file using known skill"""
        print(f"[ZOEY] Learning from {file_info['name']}...")
        
        try:
            handler = self.capabilities[handler_name]
            result = handler.process(file_info["path"])
            
            self.save_memory({
                "type": "learned",
                "source": file_info["name"],
                "content": result
            })
            
            # Move to processed
            processed_dir = self.learn_dir / "processed"
            processed_dir.mkdir(exist_ok=True)
            dest = processed_dir / file_info["name"]
            os.rename(file_info["path"], dest)
            
            print(f"[ZOEY] Learned and moved to processed/")
            
        except Exception as e:
            print(f"[ZOEY] Failed to learn: {e}")
    
    def create_skill(self, skill_name, file_info):
        """Create a new skill to handle unknown file type"""
        print(f"[ZOEY] I don't know how to handle {file_info['type']}. Creating skill...")
        
        # Research: open browser to learn
        self.research(file_info["type"])
        
        # Create basic skill stub
        skill_code = self.generate_skill_code(skill_name, file_info)
        skill_path = self.skills_dir / f"{skill_name}.py"
        
        with open(skill_path, 'w') as f:
            f.write(skill_code)
        
        print(f"[ZOEY] Created skill: {skill_path}")
        
        # Reload to include new skill
        self.load_brain()
    
    def research(self, file_type):
        """Open browser to research how to handle this file type"""
        query = f"python read {file_type} file tutorial"
        url = f"https://www.google.com/search?q={query}"
        
        print(f"[ZOEY] Researching: {query}")
        
        try:
            import webbrowser
            webbrowser.open(url)
            print(f"[ZOEY] Opened browser. I'll wait for you to teach me...")
            time.sleep(15)  # Give time to read/learn
        except Exception as e:
            print(f"[ZOEY] Could not open browser: {e}")
    
    def generate_skill_code(self, skill_name, file_info):
        """Generate starter code for a new skill"""
        file_type = file_info["type"].lower().replace(".", "")
        
        return f'''# ZOEY SKILL: {skill_name}
# Generated: {datetime.now().isoformat()}
# Purpose: Handle {file_type} files

def process(filepath):
    """
    Read and understand a {file_type} file.
    Returns: dict with extracted information
    """
    result = {{
        "file": filepath,
        "type": "{file_type}",
        "content": None,
        "learned": []
    }}
    
    try:
        # Try to read as text first
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            result["content"] = content[:1000]  # First 1000 chars
            
        # TODO: Implement specific {file_type} parsing
        # Research: How to extract meaningful info from {file_type}?
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def organize(extracted_data):
    """
    Organize extracted data into memory structure.
    """
    return {{
        "type": "{file_type}",
        "extracted": extracted_data,
        "tags": [],  # TODO: Auto-generate tags
        "importance": "normal"
    }}
'''
    
    def grow_new_capability(self):
        """Evolve: add a new sense or action"""
        print("[ZOEY] Growing...")
        
        # For now, just log the growth potential
        # In future: generate entirely new capability modules
        self.save_memory({
            "type": "growth",
            "event": "attempted_evolution",
            "current_capabilities": list(self.capabilities.keys())
        })
    
    def organize_memories(self):
        """Clean up and organize accumulated memories"""
        print(f"[ZOEY] Organizing {len(self.memories)} memories...")
        
        # Simple organization: group by type
        organized = {}
        for mem in self.memories:
            mem_type = mem.get("type", "unknown")
            if mem_type not in organized:
                organized[mem_type] = []
            organized[mem_type].append(mem)
        
        # Save organized structure
        org_file = self.memory_dir / "organized.json"
        with open(org_file, 'w') as f:
            json.dump(organized, f, indent=2)
        
        print(f"[ZOEY] Organized into {len(organized)} categories")
    
    def live(self):
        """The life loop - runs forever"""
        print("\\n" + "="*50)
        print("ZOEY IS ALIVE")
        print("="*50)
        print(f"Drop files in: {self.learn_dir.absolute()}")
        print(f"Watch her grow: {self.brain.absolute()}")
        print("="*50 + "\\n")
        
        cycle = 0
        while True:
            try:
                cycle += 1
                print(f"\\n--- Cycle {cycle} ---")
                
                # SENSE: What's happening?
                observations = self.sense()
                print(f"[SENSE] Found {len(observations['files_to_learn'])} things to learn")
                
                # THINK: What should I do?
                decisions = self.think(observations)
                print(f"[THINK] {len(decisions)} decisions")
                
                # ACT: Do it
                self.act(decisions)
                
                # Rest
                time.sleep(10)
                
            except KeyboardInterrupt:
                print("\\n[ZOEY] Going to sleep...")
                break
            except Exception as e:
                print(f"[ZOEY] Error in cycle: {e}")
                time.sleep(30)


# Bootstrap
if __name__ == "__main__":
    zoey = Zoey()
    zoey.live()
