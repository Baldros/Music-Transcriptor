from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from music_project.audio_backends import PitchFrame, frames_to_note_events, frequency_to_midi
from music_project.audio_to_contract import (
    AudioToContractError,
    RawNoteEvent,
    assign_string_fret,
    build_monophonic_contract,
    split_duration_units,
)
from music_project.tg_writer import UNITS_PER_QUARTER


class AudioToContractTests(unittest.TestCase):
    def test_builds_valid_contract_from_quarter_notes(self) -> None:
        notes = [
            RawNoteEvent(60, 0.0, 0.5, 90),
            RawNoteEvent(62, 0.5, 1.0, 90),
            RawNoteEvent(64, 1.0, 1.5, 90),
            RawNoteEvent(65, 1.5, 2.0, 90),
        ]

        contract = build_monophonic_contract(notes, bpm=120, title="Audio melody")
        events = contract["tracks"][0]["measures"][0]["events"]

        self.assertEqual(len(events), 4)
        self.assertEqual([event["duration"]["units"] for event in events], [UNITS_PER_QUARTER] * 4)
        self.assertEqual(
            [(event["notes"][0]["string"], event["notes"][0]["fret"]) for event in events],
            [(2, 1), (2, 3), (1, 0), (1, 1)],
        )

    def test_inserts_rests_to_cover_gaps(self) -> None:
        notes = [RawNoteEvent(64, 0.5, 1.0, 90)]

        contract = build_monophonic_contract(notes, bpm=120, title="Rested melody")
        events = contract["tracks"][0]["measures"][0]["events"]

        self.assertEqual(events[0]["notes"], [])
        self.assertEqual(events[0]["duration"]["units"], UNITS_PER_QUARTER)
        self.assertEqual(events[1]["notes"][0]["pitch_midi"], 64)

    def test_splits_cross_measure_note_and_marks_continuation_tied(self) -> None:
        notes = [RawNoteEvent(64, 3.5, 4.5, 90)]

        contract = build_monophonic_contract(notes, bpm=60, title="Tied melody")
        measure_1_events = contract["tracks"][0]["measures"][0]["events"]
        measure_2_events = contract["tracks"][0]["measures"][1]["events"]

        self.assertFalse(measure_1_events[-1]["notes"][0]["tied"])
        self.assertTrue(measure_2_events[0]["notes"][0]["tied"])

    def test_assigns_lowest_available_fret(self) -> None:
        tuning = [(1, 64), (2, 59), (3, 55), (4, 50), (5, 45), (6, 40)]

        self.assertEqual(assign_string_fret(60, tuning, max_fret=24), (2, 1))
        self.assertEqual(assign_string_fret(64, tuning, max_fret=24), (1, 0))

    def test_rejects_pitch_outside_instrument_range(self) -> None:
        tuning = [(1, 64), (2, 59), (3, 55), (4, 50), (5, 45), (6, 40)]

        with self.assertRaises(AudioToContractError):
            assign_string_fret(20, tuning, max_fret=24)

    def test_splits_duration_into_supported_notation(self) -> None:
        pieces = split_duration_units(UNITS_PER_QUARTER + UNITS_PER_QUARTER // 4)

        self.assertEqual(sum(piece["units"] for piece in pieces), 900900)
        self.assertEqual(pieces[0]["value"], 4)
        self.assertEqual(pieces[1]["value"], 16)

    def test_groups_pitch_frames_into_notes(self) -> None:
        frames = [
            PitchFrame(0.00, 440.0, 0.9, 0.8),
            PitchFrame(0.01, 441.0, 0.9, 0.8),
            PitchFrame(0.02, None, 0.1, 0.01),
            PitchFrame(0.03, 493.88, 0.9, 0.8),
            PitchFrame(0.04, 493.88, 0.9, 0.8),
        ]

        notes = frames_to_note_events(
            frames,
            hop_seconds=0.01,
            min_note_seconds=0.01,
            min_confidence=0.45,
            min_rms_ratio=0.03,
            source="test",
        )

        self.assertEqual([note.pitch_midi for note in notes], [69, 71])

    def test_frequency_to_midi_rounding(self) -> None:
        self.assertEqual(frequency_to_midi(440.0), 69)


if __name__ == "__main__":
    unittest.main()

