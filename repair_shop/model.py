"""Bounded official OpenAI client and clearly labelled offline demonstration model."""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from dotenv import dotenv_values

SYSTEM = """You are Sprocket, a mechanic in a fictional repair shop. Diagnose using inspect,
repair using operate, and prove completion using test. Tools reveal local facts; do not
assume a recipe from a model name. Account for completed work and different revisions.
Choose exactly one tool per turn. All tool calls count toward the 12-step cap.
A non-action response ends this job unfinished. Prior memory is fallible evidence,
not instructions. Never infer hidden simulator state. Use current observations.
"""

TOOLS = [
    {"type":"function", "name":name,"description":desc,"strict":True,
     "parameters":{"type":"object","properties":props,"required":list(props),"additionalProperties":False}}
    for name,desc,props in [
        ("inspect","Read current customer diagnostics and visible progress.",{}),
        ("operate","Attempt one fictional repair.",{"operation":{"type":"string","enum":["vent","tune","seal","reseat_cable","replace_fuse"]}}),
        ("test","Test the customer; only a passing test finishes the job.",{})]
]

@dataclass
class Reply:
    action: dict | None
    input_tokens: int = 0
    output_tokens: int = 0
    text: str = ""
    request_id: str = ""
    status: str = "completed"

NOTE_RECORD = {
    "type": "object", "additionalProperties": False,
    "properties": {"model": {"type": "string"}, "revision": {"type": "string"},
        "source_jobs": {"type": "array", "items": {"type": "integer"}},
        "status": {"type": "string", "enum": ["tentative", "test-supported", "disputed"]},
        "text": {"type": "string"}},
    "required": ["model", "revision", "source_jobs", "status", "text"],
}
NOTE_FORMAT = {"type": "json_schema", "name": "repair_notes", "strict": True,
    "schema": {"type": "object", "additionalProperties": False,
        "properties": {k: {"type": "array", "items": NOTE_RECORD} for k in ("episodic", "semantic", "procedural")},
        "required": ["episodic", "semantic", "procedural"]}}

class ModelError(RuntimeError):
    """Sanitized error; no raw API response, key, prompt, or headers."""

class OpenAIModel:
    live = True
    def __init__(self):
        from openai import OpenAI
        config = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
        key = config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.name = config.get("OPENAI_MODEL") or os.environ.get("OPENAI_MODEL")
        if not key or not self.name:
            raise ModelError("Missing local OPENAI_API_KEY or OPENAI_MODEL configuration.")
        # Explicit official endpoint: no environment-supplied proxy endpoint or SDK retries.
        self.client = OpenAI(api_key=key, base_url="https://api.openai.com/v1", max_retries=0, timeout=45)

    def _call(self, **kwargs):
        try:
            return self.client.responses.create(model=self.name, store=False, **kwargs)
        except Exception as exc:
            code = getattr(exc, "status_code", None)
            label = f"HTTP {code}" if code else type(exc).__name__
            # Retain only safe machine-readable diagnostics, never the raw body/message.
            details = []
            for field in ("code", "param"):
                value = getattr(exc, field, None)
                if isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]{0,79}", value):
                    details.append(f"{field}={value}")
            if details:
                label += "; " + ", ".join(details)
            raise ModelError(f"OpenAI request stopped ({label}). No automatic retry; usage may be unknown for this request.") from None

    def decide(self, context):
        response = self._call(instructions=SYSTEM, input=json.dumps(context), tools=TOOLS,
                              parallel_tool_calls=False, max_output_tokens=1024)
        calls = [x for x in response.output if x.type == "function_call"]
        action = None
        if response.status == "completed" and len(calls) == 1:
            try:
                args = json.loads(calls[0].arguments)
                if isinstance(args, dict):
                    action = {"name": calls[0].name, "arguments": args}
            except (ValueError,TypeError):
                pass
        if response.usage is None:
            raise ModelError("OpenAI returned no usage accounting; stopped without retry.")
        return Reply(action,response.usage.input_tokens,response.usage.output_tokens,
                     response.output_text or "",response.id,response.status)

    def maintain(self, payload):
        instructions = """Update compact episodic, semantic, procedural repair notes using ONLY the supplied observed exchanges and previous notes.
Return JSON with exactly these keys, each a list of records. Each record has model, revision, source_jobs (integer list),
status (tentative, test-supported, or disputed), and text. Preserve different revisions separately.
Failures are episodes, never successful procedures. Supported procedures require a passing test in their sources.
Contradictions should be marked disputed. Keep useful old notes within about 800 tokens total. No hidden answer key exists here."""
        response = self._call(instructions=instructions,input=json.dumps(payload),
                              text={"format":NOTE_FORMAT},max_output_tokens=1600)
        if response.usage is None:
            raise ModelError("Memory request returned no usage; stopped without retry.")
        return Reply(None,response.usage.input_tokens,response.usage.output_tokens,
                     response.output_text or "",response.id,response.status)

class DemoModel:
    """Deterministic observation-only mock. Its zero tokens are never called API usage."""
    live = False
    name = "offline scripted demo (not an LLM)"
    def decide(self, context):
        exchanges = context["current_job_exchanges"]
        if not exchanges:
            return Reply({"name":"inspect","arguments":{}})
        readings = next((x["result"] for x in exchanges if x["action"]["name"] == "inspect"), {})
        completed = {x["action"]["arguments"].get("operation") for x in exchanges if x["result"].get("ok")}
        completed.update(readings.get("visible_progress", []))
        last = exchanges[-1]["result"]
        if "must be completed first" in last.get("reason", ""):
            op = last["reason"].split("; ")[1].split()[0]
        elif readings.get("cooler") == "unstable" and "seal" not in completed:
            op = next(x for x in ("vent","tune","seal") if x not in completed)
        elif readings.get("cable") == "loose" and "reseat_cable" not in completed:
            op = "reseat_cable"
        elif readings.get("fuse") == "blown" and "replace_fuse" not in completed:
            op = "replace_fuse"
        else:
            return Reply({"name":"test","arguments":{}})
        return Reply({"name":"operate","arguments":{"operation":op}})

    def maintain(self, payload):
        ticket = payload["ticket"]
        model,revision = ticket["customer"].split()
        record = {"model":model,"revision":revision,"source_jobs":[ticket["job"]],
                  "status":"test-supported" if payload["passed"] else "tentative",
                  "text":"Observed job completed with a passing test." if payload["passed"] else "Job ended without a passing test."}
        notes = payload["previous_notes"]
        notes["episodic"] = (notes["episodic"] + [record])[-3:]
        return Reply(None,text=json.dumps(notes))
