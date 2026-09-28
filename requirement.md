# Requirements — Hindi Voice-to-Voice Assistant (Pipeline POC)

## 1. Overview

**Problem**: No open-source end-to-end speech-to-speech model (e.g. Kyutai Moshi, Qwen2.5-Omni) currently supports Hindi speech input/output. Training one from scratch is not viable at low cost — it requires large-scale multi-GPU pretraining of both a neural audio codec and a speech-text transformer.

**Solution**: Build a cascaded (pipeline) voice assistant that chains three existing, pretrained, commercially-licensed open-source components — no foundation-model pretraining required. Only the TTS voice is optionally finetuned.

**Goal of this POC**: Prove that mic-in → Hindi speech understanding → reasoning → Hindi speech-out works end-to-end on a single consumer GPU, at acceptable turn-taking latency, at effectively zero cost beyond electricity.

## 2. Architecture

```
[Mic Input]
    │
    ▼
[VAD] ── detects end of user speech
    │
    ▼
[ASR: IndicWhisper] ── Hindi speech → Hindi text
    │
    ▼
[LLM: local Hindi-capable text model via llama.cpp/Ollama] ── text → response text
    │
    ▼
[TTS: Indic Parler-TTS] ── Hindi text → Hindi speech
    │
    ▼
[Speaker Output]
```

The pipeline is turn-based (not full-duplex): the system waits for the user to finish speaking (via VAD), processes the turn through all three stages, then plays back the response.

## 3. Components & Requirements

### 3.1 Voice Activity Detection (VAD)
- Detect start/end of user speech from a live microphone stream.
- Trigger ASR only after end-of-speech is detected (avoid transcribing silence/partial utterances).
- Candidate: `webrtcvad` or `silero-vad` (both lightweight, CPU-only, no GPU budget needed).

### 3.2 Automatic Speech Recognition (ASR)
- **Model**: IndicWhisper
- **License**: Apache 2.0 — no commercial restriction
- **Input**: Hindi audio (16kHz mono recommended)
- **Output**: Hindi text transcript
- **Training required**: None — used pretrained, as-is
- **Requirement**: Transcription must complete within a bounded time budget suitable for turn-based conversation (see NFR-2, latency budget).

### 3.3 Reasoning (LLM)
- **Model**: Any Hindi-capable local text LLM (e.g. a quantized 7–8B class model), served via `llama.cpp` or Ollama.
- **Quantization**: Q4 (or similar 4-bit GGUF) to fit within available VRAM.
- **License**: Must be a commercially-permissive license (e.g. Apache 2.0/Llama-community-license-compliant) — verify per chosen model before use.
- **Input**: Hindi text transcript (+ conversation history/context)
- **Output**: Hindi text response
- **Training required**: None for POC — use an existing instruction-tuned checkpoint with demonstrated Hindi capability.

### 3.4 Text-to-Speech (TTS)
- **Model**: Indic Parler-TTS
- **License**: Apache 2.0
- **Input**: Hindi text response from the LLM
- **Output**: Hindi speech audio, streamed or generated per-turn
- **Training required**: None for baseline POC. Optional stretch goal: LoRA finetune on a small custom Hindi voice dataset to improve voice quality/consistency (established as feasible on 6GB VRAM in prior discussion).

### 3.5 Orchestration
- A single Python script/service coordinating the pipeline:
  1. Capture mic audio continuously
  2. Run VAD to segment utterances
  3. On end-of-speech, send segment to ASR
  4. Send ASR text + conversation history to LLM
  5. Send LLM response text to TTS
  6. Play resulting audio through speakers
  7. Loop
- Must maintain short conversation history/context across turns (in-memory is sufficient for POC).

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | **Hardware**: Must run entirely on a single NVIDIA RTX 3050 (6GB VRAM) desktop, no cloud GPU dependency. |
| NFR-2 | **Latency**: End-to-end turn latency (end-of-speech → start of audio playback) target of 1–3 seconds. This is a turn-based system, not full-duplex — sub-second full-duplex latency (as in Moshi) is explicitly out of scope. |
| NFR-3 | **Cost**: No paid API calls, no cloud compute, no paid datasets. All components run locally on owned hardware. |
| NFR-4 | **Licensing**: Every component used (ASR, LLM, TTS) must be under a license that permits commercial use without per-use fees (Apache 2.0 or equivalent). Components under non-commercial licenses (e.g. CC-BY-NC) are explicitly disallowed. |
| NFR-5 | **Language**: Hindi speech in, Hindi speech out, for the POC. (English is a known-working stretch case since all three components also support English, but is not the primary validation target.) |
| NFR-6 | **Offline capability**: Once models are downloaded, the pipeline should run without requiring an internet connection. |

## 5. Out of Scope (for this POC)

- Full-duplex / barge-in conversation (interrupting the assistant mid-response)
- Multi-speaker diarization
- Any foundation-model pretraining or large-scale finetuning of ASR/LLM
- Production-grade deployment (containerization, scaling, monitoring) — POC is a local script
- Telephony/PSTN integration ("actual phone calls") — POC validates the audio pipeline only, via mic/speaker
- Multilingual support beyond Hindi + English
- Mobile/embedded deployment

## 6. Success Criteria

The POC is considered successful if:

1. A user can speak a Hindi sentence into a microphone and receive a spoken Hindi response that is contextually relevant.
2. The full pipeline (VAD → ASR → LLM → TTS → playback) runs end-to-end on the RTX 3050 6GB without out-of-memory errors.
3. Average turn latency is within the 1–3 second NFR-2 target across at least 10 consecutive test turns.
4. Transcription (ASR) is legible/accurate enough for the LLM to produce a coherent response for common conversational Hindi input (informal benchmark, no formal WER target for POC).
5. All components used are verified under commercially-permissive licenses.

## 7. Assumptions & Risks

| Type | Description | Mitigation |
|---|---|---|
| Assumption | User has a working microphone and speaker on the dev machine. | N/A — standard dev environment. |
| Assumption | Chosen local LLM checkpoint has adequate Hindi fluency out of the box. | Evaluate 2–3 candidate models early; pick best Hindi performer. |
| Risk | 6GB VRAM may be tight if ASR, LLM, and TTS models are all loaded simultaneously. | Load/unload models sequentially per stage if needed, or run ASR/TTS on CPU if VRAM-constrained, accepting higher latency. |
| Risk | Turn-based latency may exceed the 1–3s target on first pass. | Profile each stage independently; stream TTS generation where possible; consider smaller/faster LLM quantization. |
| Risk | IndicWhisper transcription quality may degrade with background noise or informal/code-mixed (Hindi-English) speech. | Test with representative sample utterances; document known limitations. |

## 8. Deliverables

- Working local Python script/application implementing the pipeline described in Section 2.
- Setup/README instructions for installing and running on the target hardware.
- Short demo recording or live demo showing a multi-turn Hindi conversation.
- Brief writeup of measured latency per stage and end-to-end.
