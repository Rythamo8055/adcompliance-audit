#!/usr/bin/env python3
"""
run_live_audit_test.py - Executes live compliance and flaw audit on real brand ads.
"""

import os
import sys
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from analyzer.auditor import VideoAuditor
from analyzer.probe import probe_video_structure

def run_test():
    auditor = VideoAuditor()
    
    ads_to_test = [
        {
            "name": "Traya Health - Hair Diagnosis Campaign Ad",
            "path": "/home/rythamo/Documents/antigravity/brave-hubble/test_ads/traya_ad.mp4",
            "rules": {
                "brand_name": "Traya Health",
                "promo_code": "TRAYA20",
                "required_keywords": ["hair", "root cause", "diagnosis", "Ayurveda", "Dermatology"],
                "require_product_in_hook": True,
                "target_platforms": ["Instagram Reels", "TikTok"],
                "banned_claims": ["100% cure", "miracle", "overnight"]
            }
        },
        {
            "name": "Pilgrim - 24K Gold Face Serum Campaign Ad",
            "path": "/home/rythamo/Documents/antigravity/brave-hubble/test_ads/pilgrim_ad.mp4",
            "rules": {
                "brand_name": "Pilgrim",
                "promo_code": "PILGRIM20",
                "required_keywords": ["24K Gold", "Jeju Island", "radiant", "serum"],
                "require_product_in_hook": True,
                "target_platforms": ["Instagram Reels", "TikTok"],
                "banned_claims": ["whitens skin permanently", "instant fairness"]
            }
        }
    ]

    all_results = []

    for ad in ads_to_test:
        print("\n" + "="*70)
        print(f"AUDITING REAL BRAND AD: {ad['name']}")
        print("="*70)

        # 1. Deterministic Fast FFmpeg Probe (<0.3s)
        t0 = time.time()
        probe_res = probe_video_structure(ad["path"])
        probe_time = time.time() - t0
        print(f"[1. Deterministic FFmpeg Probe ({probe_time:.2f}s)]")
        print(f"  • Aspect Ratio: {probe_res.get('aspect_ratio_label')}")
        print(f"  • Is 9:16 Vertical: {probe_res.get('is_vertical_9_16')}")
        print(f"  • Resolution 1080p: {probe_res.get('meets_resolution_1080p')}")
        print(f"  • Audio Mean Vol: {probe_res.get('audio', {}).get('mean_volume_db')} dB (Clipping: {probe_res.get('audio', {}).get('clipping_detected')})")

        # 2. Multimodal Gemini Video Audit
        print(f"\n[2. Multimodal Gemini Compliance Audit...]")
        audit_res = auditor.audit_video(ad["path"], ad["rules"])
        
        combined = {
            "ad_name": ad["name"],
            "file_path": ad["path"],
            "preflight_probe": probe_res,
            "creative_audit": audit_res
        }
        all_results.append(combined)

        print("\n[Audit Scorecard]")
        print(f"  • Creative Quality Score (CQS): {audit_res.get('cqs_score')}/100")
        print(f"  • Status: {audit_res.get('status')}")
        print(f"  • Product in Hook (<3s): {audit_res.get('hook_audit', {}).get('product_visible_in_first_3s')} (at {audit_res.get('hook_audit', {}).get('first_product_second')}s)")
        print(f"  • Brand Spoken: {audit_res.get('speech_audit', {}).get('brand_spoken')}")
        print(f"  • Promo Code Spoken: {audit_res.get('speech_audit', {}).get('promo_code_spoken')}")
        print(f"  • Safe Zone Violations: {len(audit_res.get('safe_zone_audit', {}).get('safe_zone_violations', []))}")
        print(f"\n[Polite Creator Revision Note]:\n{audit_res.get('revision_message')}\n")

    out_file = "/home/rythamo/Documents/antigravity/brave-hubble/test_ads/live_audit_results.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nComplete structured results written to {out_file}")

if __name__ == "__main__":
    run_test()
