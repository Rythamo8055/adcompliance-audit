#!/usr/bin/env python3
"""
analyzer/competitor_analyzer.py - Competitor Video Ad Reverse-Engineer & Creative Deconstruction Engine

Takes any winning competitor video ad (from Meta Ad Library, TikTok Creative Center, or YouTube)
and reverse-engineers:
1. Hook Taxonomy & Pattern Interrupt (0-3s)
2. 6-Stage Narrative & Storyboard Funnel Breakdown
3. Audio, Pacing, and Psychological Triggers
4. Offer & Risk Reversal Mechanics
5. "Steal & Adapt" Counter-Creative Brief for YOUR brand
"""

import os
import sys
import time
import json
import requests
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from analyzer.auditor import VideoAuditor, MODEL_CASCADE


class CompetitorAdAnalyzer:
    def __init__(self, auditor: Optional[VideoAuditor] = None):
        self.auditor = auditor or VideoAuditor()

    def analyze_competitor_ad(
        self,
        video_path: str,
        target_brand_name: str = "Our Brand",
        target_product_category: str = "D2C Health & Wellness",
        target_product_usp: str = "Clinically backed root-cause solution"
    ) -> Dict[str, Any]:
        """
        Reverse-engineers a competitor's ad and auto-generates a counter-brief for our brand.
        """
        print(f"[Competitor Intel] Ingesting competitor ad: {os.path.basename(video_path)}...")
        file_uri = self.auditor.upload_video_file(video_path)

        prompt = f"""You are a world-class Direct-to-Consumer (D2C) Performance Creative Strategist and Media Buyer.
Your job is to reverse-engineer this winning competitor video ad and extract its psychological formula so we can beat it.

TARGET BRAND CONTEXT (The brand we want to create a counter-ad for):
- Brand Name: {target_brand_name}
- Product Category: {target_product_category}
- Core USP: {target_product_usp}

TASK:
Perform a deep forensic deconstruction of this competitor ad across 5 dimensions:

1. HOOK FORENSICS (0.0s - 3.0s):
   - Hook Type (e.g. Negative Agitation, Curiosity Gap, Us vs Them, Authority/Doctor, Visual Pattern Interrupt, ASMR)
   - Exact first spoken line (verbatim quote)
   - Visual Pattern Interrupt: What exact visual action stopped the scroll?
   - Retention Score (1-10) and why it worked.

2. NARRATIVE & SCRIPT STORYBOARD BREAKDOWN:
   Break the ad down into its chronological structural beats with exact timestamps:
   - [00:00 - XX:XX]: Hook & Problem
   - [XX:XX - XX:XX]: Problem Agitation / Emotional Pain Point
   - [XX:XX - XX:XX]: The Mechanism / Root Cause / Discovery
   - [XX:XX - XX:XX]: Product Demo & Visual Proof
   - [XX:XX - XX:XX]: Social Proof / Results
   - [XX:XX - End]: Offer, Guarantee & Call to Action (CTA)

3. PSYCHOLOGICAL & PACING SIGNALS:
   - Words Per Minute (Pacing) and Speech Energy
   - Emotional Arc (e.g., Frustration -> Realization -> Relief -> Excitement)
   - Transition Velocity (fast cuts vs long takes)
   - Audio / Music dynamic and tone

4. OFFER & VALUE PROPOSITION DECONSTRUCTION:
   - What promise or guarantee are they making?
   - What is the pricing/discount hook?
   - How do they overcome the viewer's skepticism?

5. "STEAL & ADAPT" COUNTER-CREATIVE BRIEF FOR {target_brand_name}:
   Produce a ready-to-hand-off Creator Brief for {target_brand_name} that borrows the competitor's winning psychology but positions our product as the superior alternative:
   - Recommended Opening Hook Line (0-3s)
   - Visual Direction for the Creator
   - 3 Key Talking Points
   - Recommended CTA

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this schema:
{{
  "competitor_summary": {{
    "detected_brand": "Brand Name or Unknown",
    "core_angle": "Summary of the ad's main angle",
    "ad_format": "UGC Selfie / Studio / Stick Animation / Sketch / etc.",
    "overall_virality_score": 85
  }},
  "hook_forensics": {{
    "hook_archetype": "Negative Agitation",
    "opening_line_verbatim": "...",
    "visual_pattern_interrupt": "...",
    "hook_retention_score": 9,
    "why_it_hooks": "..."
  }},
  "chronological_storyboard": [
    {{
      "timestamp_range": "00:00 - 00:03",
      "stage": "Hook",
      "visual_action": "...",
      "audio_script": "...",
      "psychological_intent": "..."
    }}
  ],
  "creative_metrics": {{
    "estimated_wpm": 160,
    "pacing_style": "High Energy Conversational",
    "emotional_arc": "Anxiety -> Skepticism -> Hope -> Action"
  }},
  "counter_brief_for_our_brand": {{
    "campaign_concept": "...",
    "opening_hook_script": "...",
    "visual_hook_direction": "...",
    "core_body_script": "...",
    "cta_script": "..."
  }}
}}
"""

        # Model Cascade Loop
        last_error = None
        for key_attempt in range(len(self.auditor.api_keys)):
            for model_name in MODEL_CASCADE:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.auditor.current_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}},
                            {"text": prompt}
                        ]
                    }],
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                }

                t0 = time.time()
                try:
                    resp = requests.post(url, json=payload, timeout=60)
                    if resp.status_code == 200:
                        res = resp.json()
                        elapsed = time.time() - t0
                        text_resp = res["candidates"][0]["content"]["parts"][0]["text"]
                        analysis_data = json.loads(text_resp)
                        analysis_data["_meta"] = {
                            "model_used": model_name,
                            "key_index": self.auditor.current_key_idx + 1,
                            "latency_sec": round(elapsed, 2),
                            "tokens": res.get("usageMetadata", {})
                        }
                        print(f"[Competitor Intel Success] Reverse-engineered via {model_name} in {elapsed:.2f}s!")
                        return analysis_data
                    elif resp.status_code == 429:
                        print(f"[{model_name}] Quota Exceeded (429). Cascade falling over...")
                        last_error = resp.text
                        continue
                    else:
                        print(f"[{model_name}] HTTP {resp.status_code}: {resp.text[:120]}...")
                        last_error = resp.text
                        continue
                except Exception as e:
                    print(f"[{model_name}] Error: {e}...")
                    last_error = str(e)
                    continue

            if not self.auditor.switch_to_next_key():
                break

        raise RuntimeError(f"All models exhausted. Last error: {last_error}")


if __name__ == "__main__":
    test_video = "/home/rythamo/from rahul laptop/content and ediiting/round 2 stick figures/test_sync.mp4"
    analyzer = CompetitorAdAnalyzer()
    intel = analyzer.analyze_competitor_ad(
        video_path=test_video,
        target_brand_name="Traya Health",
        target_product_category="Hair Health & Root Cause Treatment",
        target_product_usp="Personalized 3-science treatment targeting stress, gut, and genetics"
    )
    print("\n" + "="*50)
    print("COMPETITOR REVERSE-ENGINEERED INTELLIGENCE REPORT")
    print("="*50)
    print(json.dumps(intel, indent=2))
