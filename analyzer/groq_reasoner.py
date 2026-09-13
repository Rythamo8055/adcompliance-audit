#!/usr/bin/env python3
"""
analyzer/groq_reasoner.py - Groq-Powered Creative Reasoning & Ad Recreation Engine
with automatic fallback to Gemini 3.5 Flash-Lite.

Roles:
1. Archetype Classification (Performance UGC vs Studio Commercial vs Clinical Explainer)
2. In-Depth Creative Reasoning & Scorecard Logic
3. "Ad Recreation Pack" Generator (Shot-by-shot creator script, 3 hook variations, visual cues)
"""

import os
import sys
import json
import requests
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from analyzer.auditor import VideoAuditor, MODEL_CASCADE


class GroqReasoner:
    def __init__(self, groq_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        # Check .env if not found
        if not self.groq_api_key:
            env_path = os.path.join(PROJECT_ROOT, ".env")
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("GROQ_API_KEY="):
                            self.groq_api_key = line.split("=", 1)[1].strip().strip('"\'')
                            break

        self.auditor_fallback = VideoAuditor()

    def call_groq_reasoning(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Calls Groq Qwen / Llama reasoning model with low latency."""
        if not self.groq_api_key:
            return None

        # Primary reasoning models on Groq
        models_to_try = [
            "qwen-2.5-32b",
            "deepseek-r1-distill-qwen-32b",
            "llama-3.3-70b-versatile"
        ]

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }

        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt or "You are an elite D2C performance creative director and ad strategist."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            }

            try:
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    print(f"[Groq Reasoner] Successfully reasoned via {model}!")
                    return content
                elif resp.status_code == 429:
                    print(f"[Groq Reasoner] {model} rate limited (429), trying next...")
                    continue
                else:
                    print(f"[Groq Reasoner] HTTP {resp.status_code}: {resp.text[:100]}...")
                    continue
            except Exception as e:
                print(f"[Groq Reasoner] Connection error: {e}")
                continue

        return None

    def call_gemini_fallback(self, prompt: str, system_prompt: str = "") -> str:
        """Fallback to Gemini 3.5 Flash-Lite for reasoning when Groq is unavailable or rate limited."""
        print("[Reasoner Fallback] Routing reasoning to Gemini 3.5 Flash-Lite...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={self.auditor_fallback.current_key}"
        payload = {
            "contents": [{
                "parts": [{"text": f"{system_prompt}\n\n{prompt}"}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        resp = requests.post(url, json=payload, timeout=25)
        resp.raise_for_status()
        res = resp.json()
        return res["candidates"][0]["content"]["parts"][0]["text"]

    def generate_ad_recreation_pack(
        self,
        competitor_analysis: Dict[str, Any],
        target_brand: str,
        target_product: str,
        target_usp: str
    ) -> Dict[str, Any]:
        """
        Takes competitor deconstruction and generates a full "Ad Recreation Pack":
        - Shot-by-Shot Creator Director's Script
        - 3 Alternative Hook Scripts (A/B testing)
        - Visual Scene Layout & Pacing
        - Copy-paste WhatsApp Creator Brief
        """
        system_prompt = "You are an elite D2C performance creative director. You create viral, high-converting video ad recreation scripts that borrow competitor psychology without copying."
        
        prompt = f"""
COMPETITOR ANALYSIS DATA:
{json.dumps(competitor_analysis, indent=2)}

TARGET BRAND PROFILE:
- Brand Name: {target_brand}
- Product: {target_product}
- Core USP: {target_usp}

TASK:
Generate a complete, production-ready "AD RECREATION PACK" for {target_brand} to remake this winning ad concept for our product:

1. 3 HIGH-CONVERTING HOOK VARIATIONS (0-3s for A/B testing):
   - Hook A: Problem / Agitation Hook
   - Hook B: Negative / Pattern Interrupt Hook
   - Hook C: Demonstration / Visual Curiosity Hook

2. SHOT-BY-SHOT DIRECTOR'S STORYBOARD (Table/List):
   For each scene:
   - Scene timestamp / duration
   - Visual Action (what the creator/camera does)
   - On-Screen Text Overlay (placement and exact text)
   - Voiceover / Spoken Words
   - Audio / SFX cue

3. CREATOR DIRECT-MESSAGE BRIEF (Ready to copy-paste into WhatsApp / Email):
   - Clear, polite, human instructions
   - Dos and Don'ts

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this schema:
{{
  "ad_recreation_title": "...",
  "target_brand": "{target_brand}",
  "core_angle": "...",
  "hook_variations": [
    {{
      "hook_id": "Hook_A",
      "hook_type": "Problem / Pain Agitation",
      "spoken_script": "...",
      "visual_action": "...",
      "on_screen_text": "..."
    }},
    {{
      "hook_id": "Hook_B",
      "hook_type": "Negative Pattern Interrupt",
      "spoken_script": "...",
      "visual_action": "...",
      "on_screen_text": "..."
    }},
    {{
      "hook_id": "Hook_C",
      "hook_type": "Visual Curiosity / Demo",
      "spoken_script": "...",
      "visual_action": "...",
      "on_screen_text": "..."
    }}
  ],
  "shot_by_shot_storyboard": [
    {{
      "scene_number": 1,
      "timing_sec": "00:00 - 00:03",
      "visual_direction": "...",
      "spoken_dialogue": "...",
      "text_overlay": "...",
      "sound_effects": "..."
    }}
  ],
  "creator_whatsapp_brief": "Hey [Creator Name]! Excited to collaborate..."
}}
"""
        # Try Groq reasoning first
        result_text = self.call_groq_reasoning(prompt, system_prompt)
        engine_used = "Groq Qwen/Llama"

        # Fallback to Gemini Flash-Lite if Groq key is absent or exhausted
        if not result_text:
            result_text = self.call_gemini_fallback(prompt, system_prompt)
            engine_used = "Gemini 3.5 Flash-Lite (Fallback Engine)"

        try:
            parsed = json.loads(result_text)
            parsed["_engine_used"] = engine_used
            return parsed
        except Exception as e:
            return {
                "error": f"Failed to parse JSON: {e}",
                "raw_text": result_text,
                "_engine_used": engine_used
            }


if __name__ == "__main__":
    reasoner = GroqReasoner()
    sample_intel = {
        "detected_brand": "Competitor",
        "core_angle": "Emotional stress causing physical burnout and hair fall",
        "hook_archetype": "Us vs Them / Cultural Pain Point"
    }
    pack = reasoner.generate_ad_recreation_pack(
        competitor_analysis=sample_intel,
        target_brand="Traya Health",
        target_product="Hair Growth Serum & Scalp Oil",
        target_usp="Ayurvedic & Dermatological root-cause formulation"
    )
    print("\n=== GENERATED AD RECREATION PACK ===")
    print(json.dumps(pack, indent=2))
