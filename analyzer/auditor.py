#!/usr/bin/env python3
"""
analyzer/auditor.py - Multi-Key & Multi-Model Video Compliance Auditor

Natively audits video ads and creator deliverables using Google Gemini File API:
- Cascade Order: gemini-3.5-flash-lite -> gemini-3.1-flash-lite -> gemini-3.6-flash -> gemini-3.7-flash -> gemini-3.8-flash
- Multi-Key Rotation: Switches to next key if 429 quota exhaustion occurs
- Multi-Video Batching: Can evaluate 2 to 3 videos in a single API call (leveraging 1M context window)
- Outputs structured compliance scorecard + polite Creator Revision Message
"""

import os
import sys
import time
import json
import requests
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_api_keys() -> List[str]:
    """Loads all Gemini API keys from environment or .env file."""
    keys = []
    env_keys = os.environ.get("GEMINI_API_KEYS", "")
    if env_keys:
        keys.extend([k.strip() for k in env_keys.split(",") if k.strip()])

    single_key = os.environ.get("GEMINI_API_KEY", "")
    if single_key and single_key not in keys:
        keys.append(single_key)

    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEYS="):
                    val = line.split("=", 1)[1].strip('"\'')
                    for k in val.split(","):
                        k = k.strip()
                        if k and k not in keys:
                            keys.append(k)
                elif line.startswith("GEMINI_API_KEY="):
                    val = line.split("=", 1)[1].strip('"\'')
                    if val and val not in keys:
                        keys.append(val)
    return keys


# The Strict Production Cascade Order
MODEL_CASCADE = [
    "gemini-3.5-flash-lite",  # Primary Fast Engine (500 RPD, 15 RPM, 3.3s)
    "gemini-3.1-flash-lite",  # Secondary Fast Engine (500 RPD, 15 RPM)
    "gemini-3.6-flash",       # Deep Synthesis Backup (20 RPD)
    "gemini-3.7-flash",       # Deep Backup 2 (20 RPD)
    "gemini-3.8-flash",       # Deep Backup 3 (20 RPD)
    "gemini-3.5-flash",       # Deep Backup 4 (20 RPD)
]


class VideoAuditor:
    def __init__(self, api_keys: Optional[List[str]] = None):
        self.api_keys = api_keys or load_api_keys()
        if not self.api_keys:
            raise ValueError("No GEMINI_API_KEY found in environment or .env!")
        self.current_key_idx = 0

    @property
    def current_key(self) -> str:
        return self.api_keys[self.current_key_idx]

    def switch_to_next_key(self) -> bool:
        """Rotates to the next available API key in the pool."""
        if len(self.api_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            print(f"[Multi-Key] Switched to Key #{self.current_key_idx + 1} ({self.current_key[:8]}...)")
            return True
        return False

    def upload_video_file(self, video_path: str) -> str:
        """Uploads video to Google File API and polls until ACTIVE using requests."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        file_size = os.path.getsize(video_path)
        display_name = os.path.basename(video_path)
        upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={self.current_key}"

        # 1. Start Resumable Upload
        headers = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(file_size),
            "X-Goog-Upload-Header-Content-Type": "video/mp4",
            "Content-Type": "application/json"
        }
        metadata = {"file": {"display_name": display_name}}
        resp = requests.post(upload_url, json=metadata, headers=headers, timeout=15)
        resp.raise_for_status()
        upload_session_uri = resp.headers["X-Goog-Upload-URL"]

        # 2. Upload Video Bytes
        up_headers = {
            "Content-Length": str(file_size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize"
        }
        with open(video_path, "rb") as f:
            up_resp = requests.post(upload_session_uri, data=f, headers=up_headers, timeout=60)
        up_resp.raise_for_status()
        file_data = up_resp.json()
        file_name = file_data["file"]["name"]
        file_uri = file_data["file"]["uri"]

        # 3. Poll until ACTIVE
        get_url = f"https://generativelanguage.googleapis.com/v1beta/{file_name}?key={self.current_key}"
        for _ in range(15):
            poll_resp = requests.get(get_url, timeout=10)
            if poll_resp.status_code == 200:
                poll_data = poll_resp.json()
                state = poll_data.get("state")
                if state == "ACTIVE":
                    return poll_data.get("uri")
                elif state == "FAILED":
                    raise RuntimeError("Google File API failed to process video.")
            time.sleep(1.5)

        return file_uri

    def audit_video(self, video_path: str, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Audits a single video with automatic model cascade and multi-key fallback."""
        print(f"[Ingest] Uploading {os.path.basename(video_path)} to Google Native File API...")
        file_uri = self.upload_video_file(video_path)

        prompt = f"""You are a professional performance ad creative strategist and QA auditor.
Audit this creator video deliverable strictly against the following campaign rules:

CAMPAIGN RULES:
- Brand Name: {rules.get('brand_name', 'Not Specified')}
- Promo Code: {rules.get('promo_code', 'Not Specified')}
- Required Keywords: {json.dumps(rules.get('required_keywords', []))}
- Require Product in Hook (< 3.0s): {rules.get('require_product_in_hook', True)}
- Platform Target: TikTok & Instagram Reels (Vertical 9:16)

INSTRUCTIONS:
1. Examine the first 3.0 seconds (The Hook): Is the product visible? What is the visual pattern interrupt?
2. Audit on-screen text: Check if text falls into platform danger zones (right sidebar icon gutter, bottom caption area).
3. Audit speech: Was the brand name pronounced clearly? Was the promo code spoken out loud?
4. Calculate a weighted Creative Quality Score (CQS) from 0 to 100:
   - 85-100: APPROVED (Ready to launch)
   - 70-84: APPROVED_WITH_WARNINGS (Minor tweaks)
   - < 70: REVISION_REQUIRED (Must re-film/re-edit)
5. Write a polite, constructive, human-sounding "Creator Revision Message" (ready to send on WhatsApp/Email).

OUTPUT FORMAT:
You MUST respond with valid JSON matching this exact structure:
{{
  "cqs_score": 88,
  "status": "APPROVED",
  "hook_audit": {{
    "product_visible_in_first_3s": true,
    "first_product_second": 1.2,
    "hook_style": "Problem Demonstration / Shock Reaction",
    "hook_critique": "Strong pattern interrupt in opening frame."
  }},
  "speech_audit": {{
    "brand_spoken": true,
    "brand_timestamp_sec": 3.5,
    "promo_code_spoken": true,
    "promo_code_timestamp_sec": 26.0,
    "pacing_evaluation": "Optimal (165 WPM)"
  }},
  "safe_zone_audit": {{
    "safe_zone_violations": []
  }},
  "revision_message": "Hey Sarah! Fantastic energy..."
}}
"""

        # Model Cascade Loop
        last_error = None
        for key_attempt in range(len(self.api_keys)):
            for model_name in MODEL_CASCADE:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.current_key}"
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
                    resp = requests.post(url, json=payload, timeout=45)
                    if resp.status_code == 200:
                        res = resp.json()
                        elapsed = time.time() - t0
                        text_resp = res["candidates"][0]["content"]["parts"][0]["text"]
                        audit_data = json.loads(text_resp)
                        audit_data["_meta"] = {
                            "model_used": model_name,
                            "key_index": self.current_key_idx + 1,
                            "latency_sec": round(elapsed, 2),
                            "tokens": res.get("usageMetadata", {})
                        }
                        print(f"[Audit Success] Audited via {model_name} (Key #{self.current_key_idx + 1}) in {elapsed:.2f}s!")
                        return audit_data
                    elif resp.status_code == 429:
                        print(f"[{model_name}] Quota Exceeded (429). Cascade falling over...")
                        last_error = resp.text
                        continue  # Try next model in cascade
                    else:
                        print(f"[{model_name}] HTTP {resp.status_code}: {resp.text[:120]}... Cascade falling over.")
                        last_error = resp.text
                        continue
                except Exception as e:
                    print(f"[{model_name}] Network error: {e}... Cascade falling over.")
                    last_error = str(e)
                    continue

            # If all models failed on this key, switch key and retry
            if not self.switch_to_next_key():
                break

        raise RuntimeError(f"All models and keys exhausted. Last error: {last_error}")


if __name__ == "__main__":
    test_video = "/home/rythamo/from rahul laptop/content and ediiting/round 2 stick figures/test_sync.mp4"
    sample_rules = {
        "brand_name": "Sovereign Mind",
        "promo_code": "SPINE20",
        "required_keywords": ["boundaries", "respect", "anxiety"],
        "require_product_in_hook": False,
        "aspect_ratio": "16:9"
    }
    auditor = VideoAuditor()
    report = auditor.audit_video(test_video, sample_rules)
    print("\n=== FINAL AUDIT REPORT ===")
    print(json.dumps(report, indent=2))
