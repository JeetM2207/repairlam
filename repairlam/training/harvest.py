"""Harvest successful multi-turn repair episodes from logs/*.jsonl for Self-Boosting LAM Training.

Implements Module 6: Self-Boosting LAM Training from the thesis proposal.
Extracts successful PLAUSIBLE episodes and clean ESCALATED episodes, converting them
into standard conversational Supervised Fine-Tuning (SFT) format for LoRA training.
"""

import json
import os
from pathlib import Path
from repairlam.agent.prompts import SYSTEM, tools_doc
from repairlam.tools.registry import tools_doc

ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT / "logs"
DATA_DIR = ROOT / "repairlam" / "training" / "data"

SYSTEM_PROMPT = SYSTEM.format(tools=tools_doc())

def harvest_trajectories(include_escalated=True):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    plausible_episodes = []
    escalated_episodes = []
    
    for log_file in LOGS_DIR.glob("*.jsonl"):
        lines = [line.strip() for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
        if not lines:
            continue
        try:
            summary = json.loads(lines[-1])
        except Exception:
            continue
        
        outcome = summary.get("outcome")
        if outcome not in ("PLAUSIBLE", "ESCALATED"):
            continue
        
        events = []
        for line in lines[:-1]:
            try:
                ev = json.loads(line)
                if ev.get("type") == "event":
                    events.append(ev)
            except Exception:
                continue
        
        if not events:
            continue
        
        # Build multi-turn conversational messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Initial user prompt with bug information and initial failure
        first_event = events[0]
        bug_id = first_event.get("bug_id", "Unknown")
        initial_user_prompt = f"Target Bug: {bug_id}\nInitial state: UNDERSTAND\n\nPlease locate and fix this bug."
        messages.append({"role": "user", "content": initial_user_prompt})
        
        for ev in events:
            thought = ev.get("thought", "")
            tool = ev.get("tool", "")
            args = ev.get("args", {})
            
            assistant_content = json.dumps({
                "thought": thought,
                "action": {
                    "tool": tool,
                    "args": args
                }
            }, indent=2)
            messages.append({"role": "assistant", "content": assistant_content})
            
            # Observation returned to model
            res_status = ev.get("result_status", "ok")
            res_summary = ev.get("result_summary", "")
            observation = f"[result:{res_status}] {res_summary}"
            messages.append({"role": "user", "content": observation})
            
        episode = {
            "id": summary.get("run_id", log_file.stem),
            "bug_id": bug_id,
            "outcome": outcome,
            "turns": len(events),
            "messages": messages
        }
        
        if outcome == "PLAUSIBLE":
            plausible_episodes.append(episode)
        elif include_escalated and outcome == "ESCALATED":
            # Only keep clean escalations with reasonable length
            if len(events) >= 5:
                escalated_episodes.append(episode)
                
    print(f"Harvested {len(plausible_episodes)} PLAUSIBLE episodes")
    print(f"Harvested {len(escalated_episodes)} clean ESCALATED episodes")
    
    all_episodes = plausible_episodes + escalated_episodes
    
    train_path = DATA_DIR / "sft_train.jsonl"
    val_path = DATA_DIR / "sft_val.jsonl"
    
    # 80/20 train/val split
    import random
    random.seed(42)
    random.shuffle(all_episodes)
    
    split_idx = max(1, int(len(all_episodes) * 0.85))
    train_data = all_episodes[:split_idx]
    val_data = all_episodes[split_idx:]
    
    with open(train_path, "w", encoding="utf-8") as f:
        for ep in train_data:
            f.write(json.dumps(ep) + "\n")
            
    with open(val_path, "w", encoding="utf-8") as f:
        for ep in val_data:
            f.write(json.dumps(ep) + "\n")
            
    print(f"Exported SFT dataset: {len(train_data)} train, {len(val_data)} validation -> {DATA_DIR}")
    return len(train_data), len(val_data)

if __name__ == "__main__":
    harvest_trajectories()
