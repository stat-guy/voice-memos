#!/usr/bin/env python3
"""
Cohere Transcribe MPS — voice-memos skill transcription engine
Model: CohereLabs/cohere-transcribe-03-2026
Device: Apple Silicon GPU via PyTorch MPS (fp16)
Speed: ~46x RTFx

Usage (via env vars to safely handle paths with spaces):
    AUDIO_PATH="/path/to/memo.m4a" OUTPUT_PATH="/tmp/transcript.txt" \
        python transcribe_cohere_mps.py
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

MODEL_ID = "CohereLabs/cohere-transcribe-03-2026"
SAMPLE_RATE = 16000
LANGUAGE = "en"
CHUNK_SECONDS = 20
BATCH_SIZE = 8
MAX_NEW_TOKENS = 256


def get_audio_path() -> Path:
    val = os.environ.get("AUDIO_PATH", "").strip()
    if not val:
        print("ERROR: AUDIO_PATH env var not set", file=sys.stderr)
        sys.exit(1)
    p = Path(val)
    if not p.exists():
        print(f"ERROR: Audio file not found: {p}", file=sys.stderr)
        sys.exit(1)
    return p


def get_output_path() -> Path:
    val = os.environ.get("OUTPUT_PATH", "/tmp/voice_memo_transcript.txt").strip()
    return Path(val)


def decode_audio(path: Path) -> np.ndarray:
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error",
        "-i", str(path),
        "-vn", "-sn", "-dn",
        "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "s16le", "pipe:1",
    ]
    result = subprocess.run(cmd, check=True, capture_output=True)
    audio_i16 = np.frombuffer(result.stdout, dtype=np.int16)
    return audio_i16.astype(np.float32) / 32768.0


def chunk_audio(audio: np.ndarray) -> list[np.ndarray]:
    size = CHUNK_SECONDS * SAMPLE_RATE
    return [audio[i:i + size] for i in range(0, len(audio), size)]


def prepare_batch(processor: AutoProcessor, audios: list[np.ndarray]) -> dict:
    inputs = processor(
        audio=audios,
        language=LANGUAGE,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt",
        padding=True,
    )
    moved = {}
    for key, value in inputs.items():
        if not torch.is_tensor(value):
            moved[key] = value
            continue
        value = value.to("mps")
        if value.is_floating_point():
            value = value.to(torch.float16)
        moved[key] = value
    return moved


def main() -> int:
    total_start = time.time()
    audio_path = get_audio_path()
    output_path = get_output_path()

    if not torch.backends.mps.is_available():
        print("ERROR: MPS not available — requires Apple Silicon Mac", file=sys.stderr)
        sys.exit(1)

    print(f"Loading model ({MODEL_ID})...", flush=True)
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(MODEL_ID, torch_dtype=torch.float16)
    model.to("mps")
    model.eval()
    print(f"Model loaded in {time.time() - total_start:.1f}s", flush=True)

    print(f"Decoding audio: {audio_path.name}", flush=True)
    audio = decode_audio(audio_path)
    audio_duration = len(audio) / SAMPLE_RATE
    print(f"Duration: {audio_duration/60:.1f} min", flush=True)

    chunks = chunk_audio(audio)
    total_batches = math.ceil(len(chunks) / BATCH_SIZE)
    print(f"Transcribing {len(chunks)} chunks in {total_batches} batches...", flush=True)

    t0 = time.time()
    transcripts: list[str] = []

    with output_path.open("w", encoding="utf-8") as out_f:
        for batch_idx in range(total_batches):
            batch = chunks[batch_idx * BATCH_SIZE:(batch_idx + 1) * BATCH_SIZE]
            inputs = prepare_batch(processor, batch)

            torch.mps.synchronize()
            with torch.inference_mode():
                generated = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)
            torch.mps.synchronize()

            decoded = [t.strip() for t in processor.batch_decode(generated, skip_special_tokens=True)]
            transcripts.extend(decoded)

            for text in decoded:
                out_f.write(text + "\n\n")
            out_f.flush()

            done = min((batch_idx + 1) * BATCH_SIZE, len(chunks))
            pct = done / len(chunks) * 100
            print(f"  {pct:.0f}% ({done}/{len(chunks)}) — {time.time() - t0:.0f}s elapsed", flush=True)

    elapsed = time.time() - t0
    rtfx = audio_duration / elapsed
    print(f"\nDone in {elapsed:.1f}s | RTFx: {rtfx:.1f}x", flush=True)
    print(f"Transcript saved to {output_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
