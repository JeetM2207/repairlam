"""Structured event log. One JSONL file per run."""
import json, time, os
from pathlib import Path
from datetime import datetime, timezone


class EventLog:
    def __init__(self, run_id: str, log_dir: str):
        self.run_id = run_id
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        self.path = Path(log_dir) / f"{run_id}.jsonl"
        self.turn = 0
        self.t0 = time.time()
        self.tokens_in = 0
        self.tokens_out = 0

    def _write(self, obj: dict):
        obj["ts"] = datetime.now(timezone.utc).isoformat()
        obj["run_id"] = self.run_id
        with open(self.path, "a") as f:
            f.write(json.dumps(obj) + "\n")

    def event(self, bug_id, state, thought=None, tool=None, args=None,
              result_status=None, result_summary=None,
              tokens_in=0, tokens_out=0, latency_ms=0, model=None):
        self.turn += 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self._write({
            "type": "event", "bug_id": bug_id, "turn": self.turn,
            "state": state, "thought": thought, "tool": tool, "args": args,
            "result_status": result_status, "result_summary": result_summary,
            "tokens_in": tokens_in, "tokens_out": tokens_out,
            "latency_ms": latency_ms, "model": model,
        })

    def summary(self, bug_id, outcome, model=None, **extra):
        rec = {
            "type": "run_summary", "bug_id": bug_id, "outcome": outcome,
            "turns_used": self.turn, "model": model,
            "total_tokens_in": self.tokens_in,
            "total_tokens_out": self.tokens_out,
            "wall_clock_s": round(time.time() - self.t0, 1),
        }
        rec.update(extra)
        self._write(rec)
        return rec
