from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from music_project.tg_writer import ContractValidationError, build_content_xml, write_tg


def load_example() -> dict:
    with (ROOT / "examples" / "simple_melody_contract.json").open("r", encoding="utf-8") as fp:
        return json.load(fp)


class TuxGuitarWriterTests(unittest.TestCase):
    def test_builds_expected_tuxguitar_xml(self) -> None:
        xml = build_content_xml(load_example())
        root = ET.fromstring(xml)

        self.assertEqual(root.tag, "TuxGuitarFile")
        self.assertEqual(root.findtext("./TGSong/name"), "Example melody")
        self.assertEqual(root.findtext("./TGSong/TGChannel/program"), "25")

        beats = root.findall("./TGSong/TGTrack/TGMeasure/TGBeat")
        self.assertEqual(
            [beat.findtext("preciseStart") for beat in beats],
            ["720720", "1441440", "2162160", "2882880"],
        )

        notes = root.findall("./TGSong/TGTrack/TGMeasure/TGBeat/voice/note")
        self.assertEqual(
            [(note.attrib["string"], note.attrib["value"]) for note in notes],
            [("2", "1"), ("2", "3"), ("1", "0"), ("1", "1")],
        )

    def test_writes_tg_zip(self) -> None:
        score = load_example()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "example.tg"
            write_tg(score, output)

            with zipfile.ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()), {"version.txt", "content.xml"})
                self.assertEqual(archive.read("version.txt").decode("utf-8"), "TuxGuitar_file_format 2.0.0")
                ET.fromstring(archive.read("content.xml"))

    def test_rejects_pitch_that_does_not_match_tab_position(self) -> None:
        score = load_example()
        bad_score = copy.deepcopy(score)
        bad_score["tracks"][0]["measures"][0]["events"][0]["notes"][0]["pitch_midi"] = 61

        with self.assertRaises(ContractValidationError) as raised:
            build_content_xml(bad_score)

        self.assertEqual(raised.exception.code, "TAB_PITCH_MISMATCH")

    def test_rejects_event_gaps(self) -> None:
        score = load_example()
        bad_score = copy.deepcopy(score)
        bad_score["tracks"][0]["measures"][0]["events"][1]["offset_units"] = 720721

        with self.assertRaises(ContractValidationError) as raised:
            build_content_xml(bad_score)

        self.assertEqual(raised.exception.code, "EVENT_GAP")

    def test_defaults_empty_key_signatures_to_zero(self) -> None:
        score = load_example()
        score["project"]["key_signatures"] = []

        xml = build_content_xml(score)
        root = ET.fromstring(xml)

        self.assertEqual(root.findtext("./TGSong/TGTrack/TGMeasure/keySignature"), "0")


if __name__ == "__main__":
    unittest.main()
