# Video QA & Creative Compliance Agent — Implementation Roadmap 📋

Automated AI pipeline for auditing UGC creator videos and paid social ads against brand briefs, platform safe zones, and performance benchmarks.

---

## 🎯 Project Milestones

- [x] **Phase 1: Project Setup & Technical Architecture**
  - [x] Analyze `clever-babbage` video algorithms and extract reusable logic
  - [x] Create project `TODO.md` and `PIPELINE_SPECIFICATION.md`
  - [x] Test live models: Flash Lite vs Flash vs Gemma vs Groq
  - [x] Create `MODEL_STRATEGY.md` with 1M token context, batching, and multi-key rotation
  - [x] Set up `.env` configuration for API keys and multi-key support

- [ ] **Phase 2: Video Ingestion & Structural Probe (`analyzer/probe.py`)**
  - [ ] Extract stream metadata using `ffprobe` (container, codec, duration, bitrate)
  - [ ] Aspect ratio validation (strictly 9:16 vertical check, e.g., 1080x1920)
  - [ ] Resolution & frame-rate threshold checks (minimum 1080p, 24/30/60 fps)
  - [ ] Automated scene cut detection via FFmpeg `select='gt(scene,0.2)'`
  - [ ] Keyframe extraction for scene boundaries and critical 00:00–00:03 Hook window

- [ ] **Phase 3: Audio & Speech Compliance Engine (`analyzer/audio_auditor.py`)**
  - [ ] Audio stream extraction to 16kHz mono WAV via FFmpeg
  - [ ] Volume & dynamics analysis via FFmpeg `volumedetect` (mean dB, peak dB, clipping risk)
  - [ ] Speech-to-Text transcription with word-level timestamps (Whisper / Local / Cloud)
  - [ ] Brand name and promo code verification (exact match + phonetic tolerance)
  - [ ] Pacing calculation: Words Per Minute (WPM) benchmarked against 150–180 WPM target
  - [ ] Background music vs voice loudness ratio check

- [ ] **Phase 4: Visual Hook & Platform Safe-Zone Auditor (`analyzer/vision_auditor.py`)**
  - [ ] OpenCV safe-zone mask calculation for TikTok and Instagram Reels UI overlays:
    - Right sidebar icons (Profile, Like, Comment, Share)
    - Bottom metadata overlay (Account handle, caption, audio track)
    - Top header margins (Search bar, Live icon)
  - [ ] Text-in-safe-zone compliance check (flags text clipped by platform UI)
  - [ ] Hook window audit (00:00–00:03):
    - Product presence detection
    - Face & facial expression detection
    - Visual action / pattern interrupt classification
  - [ ] Thread-safe Sliding Window Rate Limiter for Multimodal LLM calls

- [ ] **Phase 5: Scorecard Engine & Revision Generator (`analyzer/report_generator.py`)**
  - [ ] Unified compliance evaluation engine with weighted scoring (0–100 CQS)
  - [ ] Timestamped Pass / Fail / Warning flag generator
  - [ ] Automated polite "Creator Revision Message" generator (copy-paste for WhatsApp/Email)
  - [ ] Export formats: Structured JSON, Markdown summary, and interactive HTML report

- [ ] **Phase 6: CLI & Batch Operations (`cli.py`)**
  - [ ] Single video audit: `./video-qa audit <video.mp4> --rules <rules.json>`
  - [ ] Batch folder audit: `./video-qa batch <folder_path> --rules <rules.json>`
  - [ ] Interactive terminal progress display with Rich / colored terminal output

- [ ] **Phase 7: End-to-End Verification & Benchmarking**
  - [ ] Test against real vertical video samples
  - [ ] Benchmark CPU execution time and API token cost per video
  - [ ] Verify accuracy of pass/fail decisions against manual review
