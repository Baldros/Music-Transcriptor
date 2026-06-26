from __future__ import annotations

from dataclasses import dataclass
from math import log2
from pathlib import Path
from typing import Literal, Sequence

from .audio_to_contract import RawNoteEvent

PitchBackend = Literal["librosa-pyin", "torchaudio"]
DeviceName = Literal["auto", "cpu", "cuda"]


@dataclass(frozen=True)
class PitchFrame:
    time_seconds: float
    frequency_hz: float | None
    confidence: float | None
    rms: float


def transcribe_monophonic_audio(
    path: str | Path,
    *,
    backend: PitchBackend = "librosa-pyin",
    device: DeviceName = "auto",
    sample_rate: int = 22050,
    fmin_midi: int = 40,
    fmax_midi: int = 88,
    frame_length: int = 2048,
    hop_length: int = 256,
    min_note_ms: float = 80.0,
    min_confidence: float = 0.45,
    min_rms_ratio: float = 0.03,
) -> list[RawNoteEvent]:
    if backend == "librosa-pyin":
        frames = _pitch_frames_librosa_pyin(
            path,
            sample_rate=sample_rate,
            fmin_midi=fmin_midi,
            fmax_midi=fmax_midi,
            frame_length=frame_length,
            hop_length=hop_length,
        )
    elif backend == "torchaudio":
        frames = _pitch_frames_torchaudio(
            path,
            device=device,
            sample_rate=sample_rate,
            fmin_midi=fmin_midi,
            fmax_midi=fmax_midi,
            frame_length=frame_length,
            hop_length=hop_length,
        )
    else:
        raise ValueError(f"unsupported pitch backend: {backend}")

    return frames_to_note_events(
        frames,
        hop_seconds=hop_length / sample_rate,
        min_note_seconds=min_note_ms / 1000,
        min_confidence=min_confidence,
        min_rms_ratio=min_rms_ratio,
        source=backend,
    )


def frames_to_note_events(
    frames: Sequence[PitchFrame],
    *,
    hop_seconds: float,
    min_note_seconds: float,
    min_confidence: float,
    min_rms_ratio: float,
    source: str,
) -> list[RawNoteEvent]:
    if not frames:
        return []

    max_rms = max(frame.rms for frame in frames)
    rms_floor = max_rms * min_rms_ratio
    notes: list[RawNoteEvent] = []
    active: list[PitchFrame] = []
    active_pitch: int | None = None

    def flush() -> None:
        nonlocal active, active_pitch
        if not active or active_pitch is None:
            active = []
            active_pitch = None
            return
        onset = active[0].time_seconds
        offset = active[-1].time_seconds + hop_seconds
        if offset - onset >= min_note_seconds:
            avg_rms = sum(frame.rms for frame in active) / len(active)
            avg_confidence_values = [frame.confidence for frame in active if frame.confidence is not None]
            avg_confidence = (
                sum(avg_confidence_values) / len(avg_confidence_values) if avg_confidence_values else None
            )
            velocity = _rms_to_velocity(avg_rms, max_rms)
            notes.append(
                RawNoteEvent(
                    pitch_midi=active_pitch,
                    onset_seconds=onset,
                    offset_seconds=offset,
                    velocity=velocity,
                    confidence=avg_confidence,
                    source=source,
                )
            )
        active = []
        active_pitch = None

    for frame in frames:
        if not _is_voiced_frame(frame, rms_floor=rms_floor, min_confidence=min_confidence):
            flush()
            continue

        pitch = frequency_to_midi(frame.frequency_hz)
        if active_pitch is None:
            active = [frame]
            active_pitch = pitch
            continue

        if pitch == active_pitch:
            active.append(frame)
        else:
            flush()
            active = [frame]
            active_pitch = pitch

    flush()
    return notes


def frequency_to_midi(frequency_hz: float | None) -> int:
    if frequency_hz is None or frequency_hz <= 0:
        raise ValueError("frequency must be positive")
    return int(round(69 + 12 * log2(frequency_hz / 440.0)))


def midi_to_frequency(midi: int) -> float:
    return 440.0 * (2 ** ((midi - 69) / 12))


def _pitch_frames_librosa_pyin(
    path: str | Path,
    *,
    sample_rate: int,
    fmin_midi: int,
    fmax_midi: int,
    frame_length: int,
    hop_length: int,
) -> list[PitchFrame]:
    try:
        import librosa
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "librosa backend requires optional dependencies. Install with: "
            "py -3.11 -m pip install -e .[audio]"
        ) from exc

    y, sr = librosa.load(path, sr=sample_rate, mono=True)
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=librosa.midi_to_hz(fmin_midi),
        fmax=librosa.midi_to_hz(fmax_midi),
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length,
    )
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)

    frame_count = min(len(times), len(f0), len(rms), len(voiced_flag), len(voiced_prob))
    frames: list[PitchFrame] = []
    for index in range(frame_count):
        frequency = float(f0[index]) if bool(voiced_flag[index]) and not np.isnan(f0[index]) else None
        confidence = float(voiced_prob[index]) if not np.isnan(voiced_prob[index]) else None
        frames.append(
            PitchFrame(
                time_seconds=float(times[index]),
                frequency_hz=frequency,
                confidence=confidence,
                rms=float(rms[index]),
            )
        )
    return frames


def _pitch_frames_torchaudio(
    path: str | Path,
    *,
    device: DeviceName,
    sample_rate: int,
    fmin_midi: int,
    fmax_midi: int,
    frame_length: int,
    hop_length: int,
) -> list[PitchFrame]:
    try:
        import torch
        import torchaudio
    except ImportError as exc:
        raise RuntimeError(
            "torchaudio backend requires optional dependencies. Install PyTorch/torchaudio first, "
            "then install the project with: py -3.11 -m pip install -e .[torch]"
        ) from exc

    resolved_device = _resolve_torch_device(torch, device)
    waveform, sr = torchaudio.load(str(path))
    waveform = waveform.mean(dim=0, keepdim=True)
    if sr != sample_rate:
        waveform = torchaudio.functional.resample(waveform, sr, sample_rate)
        sr = sample_rate
    waveform = waveform.to(resolved_device)

    frequencies = torchaudio.functional.detect_pitch_frequency(
        waveform,
        sr,
        frame_time=hop_length / sr,
        freq_low=int(midi_to_frequency(fmin_midi)),
        freq_high=int(midi_to_frequency(fmax_midi)),
    ).squeeze(0)

    rms = _torch_frame_rms(waveform.squeeze(0), frame_length=frame_length, hop_length=hop_length)
    frame_count = min(int(frequencies.numel()), int(rms.numel()))
    frequencies_cpu = frequencies[:frame_count].detach().cpu().tolist()
    rms_cpu = rms[:frame_count].detach().cpu().tolist()

    frames = []
    for index, frequency in enumerate(frequencies_cpu):
        frequency_value = float(frequency)
        frames.append(
            PitchFrame(
                time_seconds=index * hop_length / sr,
                frequency_hz=frequency_value if frequency_value > 0 else None,
                confidence=None,
                rms=float(rms_cpu[index]),
            )
        )
    return frames


def _torch_frame_rms(waveform, *, frame_length: int, hop_length: int):
    import torch

    if waveform.numel() < frame_length:
        waveform = torch.nn.functional.pad(waveform, (0, frame_length - waveform.numel()))
    frames = waveform.unfold(0, frame_length, hop_length)
    return torch.sqrt(torch.mean(frames * frames, dim=1) + 1e-12)


def _resolve_torch_device(torch_module, device: DeviceName) -> str:
    if device == "auto":
        return "cuda" if torch_module.cuda.is_available() else "cpu"
    if device == "cuda" and not torch_module.cuda.is_available():
        raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is false")
    return device


def _is_voiced_frame(frame: PitchFrame, *, rms_floor: float, min_confidence: float) -> bool:
    if frame.frequency_hz is None:
        return False
    if frame.rms < rms_floor:
        return False
    if frame.confidence is not None and frame.confidence < min_confidence:
        return False
    return True


def _rms_to_velocity(rms: float, max_rms: float) -> int:
    if max_rms <= 0:
        return 80
    normalized = min(1.0, max(0.0, rms / max_rms))
    return int(round(35 + normalized * 80))

