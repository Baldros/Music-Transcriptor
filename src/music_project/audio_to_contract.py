from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import ceil
from typing import Any, Iterable, Literal, Mapping, Sequence

from .tg_writer import UNITS_PER_QUARTER, validate_contract

InstrumentName = Literal["guitar", "bass"]


@dataclass(frozen=True)
class RawNoteEvent:
    pitch_midi: int
    onset_seconds: float
    offset_seconds: float
    velocity: int = 90
    confidence: float | None = None
    source: str = "audio"


@dataclass(frozen=True)
class _QuantizedNote:
    pitch_midi: int
    onset_units: int
    offset_units: int
    velocity: int
    confidence: float | None
    source: str


class AudioToContractError(ValueError):
    pass


def build_monophonic_contract(
    note_events: Sequence[RawNoteEvent],
    *,
    bpm: int,
    title: str,
    instrument: InstrumentName = "guitar",
    time_signature: tuple[int, int] = (4, 4),
    quantization_value: int = 16,
    max_fret: int = 24,
    producer_name: str = "audio-to-contract-mvp",
    producer_version: str = "0.0.1",
) -> dict[str, Any]:
    if bpm <= 0:
        raise AudioToContractError("bpm must be positive")
    if quantization_value not in {4, 8, 16, 32, 64}:
        raise AudioToContractError("quantization_value must be one of 4, 8, 16, 32, 64")

    numerator, denominator = time_signature
    if numerator <= 0 or denominator not in {1, 2, 4, 8, 16, 32, 64}:
        raise AudioToContractError("unsupported time signature")

    profile = instrument_profile(instrument, max_fret=max_fret)
    measure_duration_units = _measure_duration_units(numerator, denominator)
    quantum_units = _duration_units(quantization_value, 0)
    quantized_notes = _quantize_note_events(note_events, bpm=bpm, quantum_units=quantum_units)

    last_unit = quantized_notes[-1].offset_units if quantized_notes else measure_duration_units
    measure_count = max(1, ceil(last_unit / measure_duration_units))
    total_duration_units = measure_count * measure_duration_units

    measures: list[dict[str, Any]] = [
        {
            "number": number,
            "start_units": (number - 1) * measure_duration_units,
            "duration_units": measure_duration_units,
            "events": [],
        }
        for number in range(1, measure_count + 1)
    ]

    cursor = 0
    event_counter = 1
    for note in quantized_notes:
        if note.onset_units > cursor:
            event_counter = _append_span(
                measures,
                start_units=cursor,
                end_units=note.onset_units,
                measure_duration_units=measure_duration_units,
                note=None,
                event_counter=event_counter,
            )
        if note.offset_units <= cursor:
            continue
        start_units = max(cursor, note.onset_units)
        event_counter = _append_span(
            measures,
            start_units=start_units,
            end_units=note.offset_units,
            measure_duration_units=measure_duration_units,
            note=note,
            event_counter=event_counter,
            tuning=profile["tuning"],
            max_fret=max_fret,
        )
        cursor = note.offset_units

    if cursor < total_duration_units:
        _append_span(
            measures,
            start_units=cursor,
            end_units=total_duration_units,
            measure_duration_units=measure_duration_units,
            note=None,
            event_counter=event_counter,
        )

    contract = {
        "contract": {
            "name": "MelodyScoreContract",
            "version": "0.1.0",
        },
        "producer": {
            "name": producer_name,
            "version": producer_version,
        },
        "project": {
            "title": title,
            "artist": "",
            "album": "",
            "author": "",
            "transcriber": "generated",
            "comments": "",
            "units_per_quarter": UNITS_PER_QUARTER,
            "tempo_map": [
                {
                    "measure": 1,
                    "bpm": bpm,
                    "beat_unit": 4,
                }
            ],
            "time_signatures": [
                {
                    "measure": 1,
                    "numerator": numerator,
                    "denominator": denominator,
                }
            ],
            "key_signatures": [
                {
                    "measure": 1,
                    "value": 0,
                }
            ],
        },
        "tracks": [
            {
                "id": f"{instrument}_1",
                "name": profile["track_name"],
                "kind": "fretted-string",
                "instrument": {
                    "gm_bank": 0,
                    "gm_program": profile["gm_program"],
                    "channel_name": profile["channel_name"],
                },
                "tuning": [
                    {"string": string_number, "pitch_midi": pitch_midi}
                    for string_number, pitch_midi in profile["tuning"]
                ],
                "max_fret": max_fret,
                "clef": profile["clef"],
                "measures": measures,
            }
        ],
    }
    validate_contract(contract)
    return contract


def instrument_profile(instrument: InstrumentName, *, max_fret: int = 24) -> dict[str, Any]:
    if max_fret < 0:
        raise AudioToContractError("max_fret must be non-negative")
    if instrument == "guitar":
        return {
            "track_name": "Guitar",
            "channel_name": "Steel String Acoustic Guitar",
            "gm_program": 25,
            "clef": "treble",
            "tuning": [(1, 64), (2, 59), (3, 55), (4, 50), (5, 45), (6, 40)],
        }
    if instrument == "bass":
        return {
            "track_name": "Bass",
            "channel_name": "Electric Bass",
            "gm_program": 33,
            "clef": "bass",
            "tuning": [(1, 43), (2, 38), (3, 33), (4, 28)],
        }
    raise AudioToContractError(f"unsupported instrument: {instrument}")


def assign_string_fret(
    pitch_midi: int,
    tuning: Sequence[tuple[int, int]],
    *,
    max_fret: int,
) -> tuple[int, int]:
    candidates: list[tuple[int, int]] = []
    for string_number, open_pitch in tuning:
        fret = pitch_midi - open_pitch
        if 0 <= fret <= max_fret:
            candidates.append((fret, string_number))
    if not candidates:
        raise AudioToContractError(f"pitch {pitch_midi} is outside the instrument range")
    fret, string_number = min(candidates)
    return string_number, fret


def split_duration_units(units: int) -> list[dict[str, Any]]:
    if units <= 0:
        raise AudioToContractError("duration units must be positive")

    durations = sorted(_supported_normal_durations(), key=lambda item: item["units"], reverse=True)
    remaining = units
    result: list[dict[str, Any]] = []
    while remaining > 0:
        match = next((duration for duration in durations if duration["units"] <= remaining), None)
        if match is None:
            raise AudioToContractError(f"cannot represent duration: {units}")
        result.append(dict(match))
        remaining -= match["units"]
    return result


def _quantize_note_events(
    note_events: Sequence[RawNoteEvent],
    *,
    bpm: int,
    quantum_units: int,
) -> list[_QuantizedNote]:
    quantized: list[_QuantizedNote] = []
    for event in sorted(note_events, key=lambda item: (item.onset_seconds, item.offset_seconds)):
        if event.offset_seconds <= event.onset_seconds:
            continue
        onset_units = _quantize_units(_seconds_to_units(event.onset_seconds, bpm), quantum_units)
        offset_units = _quantize_units(_seconds_to_units(event.offset_seconds, bpm), quantum_units)
        if offset_units <= onset_units:
            offset_units = onset_units + quantum_units
        velocity = min(127, max(1, int(event.velocity)))
        quantized.append(
            _QuantizedNote(
                pitch_midi=int(event.pitch_midi),
                onset_units=onset_units,
                offset_units=offset_units,
                velocity=velocity,
                confidence=event.confidence,
                source=event.source,
            )
        )

    normalized: list[_QuantizedNote] = []
    cursor = 0
    for event in quantized:
        onset_units = max(cursor, event.onset_units)
        if event.offset_units <= onset_units:
            continue
        normalized.append(
            _QuantizedNote(
                pitch_midi=event.pitch_midi,
                onset_units=onset_units,
                offset_units=event.offset_units,
                velocity=event.velocity,
                confidence=event.confidence,
                source=event.source,
            )
        )
        cursor = event.offset_units
    return normalized


def _append_span(
    measures: list[dict[str, Any]],
    *,
    start_units: int,
    end_units: int,
    measure_duration_units: int,
    note: _QuantizedNote | None,
    event_counter: int,
    tuning: Sequence[tuple[int, int]] | None = None,
    max_fret: int = 24,
) -> int:
    if end_units <= start_units:
        return event_counter

    cursor = start_units
    tied = False
    while cursor < end_units:
        measure_index = cursor // measure_duration_units
        measure_start = measure_index * measure_duration_units
        measure_end = measure_start + measure_duration_units
        span_end = min(end_units, measure_end)

        for duration in split_duration_units(span_end - cursor):
            event: dict[str, Any] = {
                "id": f"e{event_counter}",
                "offset_units": cursor - measure_start,
                "duration": duration,
                "notes": [],
            }
            if note is not None:
                if tuning is None:
                    raise AudioToContractError("tuning is required for note spans")
                string_number, fret = assign_string_fret(note.pitch_midi, tuning, max_fret=max_fret)
                note_payload: dict[str, Any] = {
                    "pitch_midi": note.pitch_midi,
                    "string": string_number,
                    "fret": fret,
                    "velocity": note.velocity,
                    "tied": tied,
                    "effects": [],
                }
                if note.confidence is not None:
                    note_payload["confidence"] = note.confidence
                if note.source:
                    note_payload["source"] = note.source
                event["notes"] = [note_payload]
                tied = True
            measures[measure_index]["events"].append(event)
            cursor += duration["units"]
            event_counter += 1
    return event_counter


def _supported_normal_durations() -> Iterable[dict[str, Any]]:
    values = (1, 2, 4, 8, 16, 32, 64)
    for value in values:
        for dots in (0, 1, 2):
            units = _duration_units(value, dots, strict=False)
            if units is None:
                continue
            yield {
                "value": value,
                "dots": dots,
                "tuplet": {
                    "enters": 1,
                    "times": 1,
                },
                "units": units,
            }


def _duration_units(value: int, dots: int, *, strict: bool = True) -> int | None:
    dot_factor = {0: Fraction(1, 1), 1: Fraction(3, 2), 2: Fraction(7, 4)}[dots]
    units = Fraction(UNITS_PER_QUARTER * 4, value) * dot_factor
    if units.denominator != 1:
        if not strict:
            return None
        raise AudioToContractError(f"unsupported duration value={value} dots={dots}")
    return units.numerator


def _measure_duration_units(numerator: int, denominator: int) -> int:
    units = Fraction(UNITS_PER_QUARTER * 4 * numerator, denominator)
    if units.denominator != 1:
        raise AudioToContractError("time signature cannot be represented as integer units")
    return units.numerator


def _seconds_to_units(seconds: float, bpm: int) -> int:
    return round(seconds * bpm * UNITS_PER_QUARTER / 60)


def _quantize_units(units: int, quantum_units: int) -> int:
    return int(round(units / quantum_units) * quantum_units)
