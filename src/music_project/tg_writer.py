from __future__ import annotations

import io
import json
import zipfile
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from xml.etree import ElementTree as ET

UNITS_PER_QUARTER = 720720
TG_PRECISE_START_OFFSET = UNITS_PER_QUARTER
TG_FILE_FORMAT_VERSION = "2.0.0"
TG_XML_VERSION = (2, 1, 0)

SUPPORTED_DURATION_VALUES = {1, 2, 4, 8, 16, 32, 64}
SUPPORTED_CLEFS = {"treble", "bass", "tenor", "alto"}
SUPPORTED_EFFECTS = {
    "vibrato",
    "deadNote",
    "slide",
    "hammer",
    "ghostNote",
    "accentuatedNote",
    "heavyAccentuatedNote",
    "palmMute",
    "staccato",
    "tapping",
    "slapping",
    "popping",
    "fadeIn",
    "letRing",
}

TOP_LEVEL_KEYS = {"contract", "producer", "project", "tracks", "extensions"}
CONTRACT_KEYS = {"name", "version", "extensions"}
PRODUCER_KEYS = {"name", "version", "extensions"}
PROJECT_KEYS = {
    "title",
    "artist",
    "album",
    "author",
    "date",
    "copyright",
    "writer",
    "transcriber",
    "comments",
    "units_per_quarter",
    "tempo_map",
    "time_signatures",
    "key_signatures",
    "extensions",
}
TEMPO_KEYS = {"measure", "bpm", "beat_unit", "extensions"}
TIME_SIGNATURE_KEYS = {"measure", "numerator", "denominator", "extensions"}
KEY_SIGNATURE_KEYS = {"measure", "value", "extensions"}
TRACK_KEYS = {
    "id",
    "name",
    "kind",
    "instrument",
    "tuning",
    "max_fret",
    "clef",
    "measures",
    "extensions",
}
INSTRUMENT_KEYS = {"gm_bank", "gm_program", "channel_name", "extensions"}
TUNING_KEYS = {"string", "pitch_midi", "extensions"}
MEASURE_KEYS = {"number", "start_units", "duration_units", "events", "extensions"}
EVENT_KEYS = {"id", "offset_units", "duration", "notes", "direction", "extensions"}
DURATION_KEYS = {"value", "dots", "tuplet", "units", "extensions"}
TUPLET_KEYS = {"enters", "times", "extensions"}
NOTE_KEYS = {
    "pitch_midi",
    "string",
    "fret",
    "velocity",
    "tied",
    "effects",
    "confidence",
    "source",
    "extensions",
}


class ContractValidationError(ValueError):
    def __init__(self, code: str, path: str, message: str) -> None:
        self.code = code
        self.path = path
        self.message = message
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"{self.code} at {self.path}: {self.message}"


def load_contract(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ContractValidationError("INVALID_TYPE", "$", "contract root must be an object")
    return data


def validate_contract(score: Mapping[str, Any]) -> None:
    _require_mapping(score, "$")
    _reject_unknown(score, TOP_LEVEL_KEYS, "$")

    contract = _required_mapping(score, "contract", "$")
    _reject_unknown(contract, CONTRACT_KEYS, "$.contract")
    if contract.get("name") != "MelodyScoreContract" or contract.get("version") != "0.1.0":
        raise ContractValidationError(
            "UNSUPPORTED_CONTRACT_VERSION",
            "$.contract",
            "expected MelodyScoreContract v0.1.0",
        )

    if "producer" in score:
        producer = _required_mapping(score, "producer", "$")
        _reject_unknown(producer, PRODUCER_KEYS, "$.producer")

    project = _required_mapping(score, "project", "$")
    _reject_unknown(project, PROJECT_KEYS, "$.project")
    if _required_int(project, "units_per_quarter", "$.project") != UNITS_PER_QUARTER:
        raise ContractValidationError(
            "INVALID_UNITS_PER_QUARTER",
            "$.project.units_per_quarter",
            f"expected {UNITS_PER_QUARTER}",
        )

    tracks = _required_sequence(score, "tracks", "$")
    if not tracks:
        raise ContractValidationError("MISSING_TRACKS", "$.tracks", "at least one track is required")

    measure_count = _read_measure_count(tracks)
    tempo_map = _validate_tempo_map(project, measure_count)
    time_signatures = _validate_time_signatures(project, measure_count)
    _validate_key_signatures(project, measure_count)

    cumulative_start = 0
    expected_measure_durations: list[int] = []
    for measure_number in range(1, measure_count + 1):
        signature = _effective_entry(time_signatures, measure_number)
        duration = _measure_duration_units(signature["numerator"], signature["denominator"])
        expected_measure_durations.append(duration)
        cumulative_start += duration

    for track_index, track_value in enumerate(tracks):
        track_path = f"$.tracks[{track_index}]"
        track = _require_mapping(track_value, track_path)
        _validate_track(track, track_path, measure_count, expected_measure_durations, time_signatures)

    # Keep the tempo map validation effective. It is also used by the writer.
    for measure_number in range(1, measure_count + 1):
        _effective_entry(tempo_map, measure_number)


def build_content_xml(score: Mapping[str, Any]) -> bytes:
    validate_contract(score)

    project = score["project"]
    tracks = score["tracks"]
    measure_count = len(tracks[0]["measures"])
    tempo_map = _sorted_entries(project["tempo_map"])
    time_signatures = _sorted_entries(project["time_signatures"])
    key_signatures = _validate_key_signatures(project, measure_count)

    root = ET.Element("TuxGuitarFile")
    ET.SubElement(
        root,
        "TGVersion",
        {
            "major": str(TG_XML_VERSION[0]),
            "minor": str(TG_XML_VERSION[1]),
            "revision": str(TG_XML_VERSION[2]),
        },
    )
    song = ET.SubElement(root, "TGSong")
    _write_song_metadata(song, project)
    _write_channels(song, tracks)
    _write_measure_headers(song, tempo_map, time_signatures, measure_count)
    _write_tracks(song, tracks, key_signatures)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True, short_empty_elements=True)


def write_tg(score: Mapping[str, Any], output_path: str | Path) -> Path:
    content_xml = build_content_xml(score)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("version.txt", f"TuxGuitar_file_format {TG_FILE_FORMAT_VERSION}")
        archive.writestr("content.xml", content_xml)
    return output


def contract_to_tg_bytes(score: Mapping[str, Any]) -> bytes:
    content_xml = build_content_xml(score)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("version.txt", f"TuxGuitar_file_format {TG_FILE_FORMAT_VERSION}")
        archive.writestr("content.xml", content_xml)
    return buffer.getvalue()


def _write_song_metadata(song: ET.Element, project: Mapping[str, Any]) -> None:
    fields = [
        ("name", "title"),
        ("artist", "artist"),
        ("album", "album"),
        ("author", "author"),
        ("date", "date"),
        ("copyright", "copyright"),
        ("writer", "writer"),
        ("transcriber", "transcriber"),
        ("comments", "comments"),
    ]
    for xml_name, contract_name in fields:
        _node(song, xml_name, project.get(contract_name, ""))


def _write_channels(song: ET.Element, tracks: Sequence[Mapping[str, Any]]) -> None:
    for index, track in enumerate(tracks, start=1):
        instrument = track.get("instrument", {})
        channel = ET.SubElement(song, "TGChannel")
        _node(channel, "id", index)
        _node(channel, "bank", instrument.get("gm_bank", 0))
        _node(channel, "program", instrument.get("gm_program", 25))
        _node(channel, "volume", 127)
        _node(channel, "balance", 64)
        _node(channel, "chorus", 0)
        _node(channel, "reverb", 0)
        _node(channel, "phaser", 0)
        _node(channel, "tremolo", 0)
        _node(channel, "name", instrument.get("channel_name", track["name"]))


def _write_measure_headers(
    song: ET.Element,
    tempo_map: Sequence[Mapping[str, Any]],
    time_signatures: Sequence[Mapping[str, Any]],
    measure_count: int,
) -> None:
    for measure_number in range(1, measure_count + 1):
        tempo = _effective_entry(tempo_map, measure_number)
        signature = _effective_entry(time_signatures, measure_number)
        header = ET.SubElement(song, "TGMeasureHeader")
        ET.SubElement(
            header,
            "timeSignature",
            {
                "numerator": str(signature["numerator"]),
                "denominator": str(signature["denominator"]),
            },
        )
        tempo_attrs = {}
        if tempo.get("beat_unit", 4) != 4:
            tempo_attrs["base"] = str(tempo["beat_unit"])
        _node(header, "tempo", tempo["bpm"], tempo_attrs)


def _write_tracks(
    song: ET.Element,
    tracks: Sequence[Mapping[str, Any]],
    key_signatures: Sequence[Mapping[str, Any]],
) -> None:
    palette = [(255, 0, 0), (0, 96, 192), (0, 128, 72), (176, 96, 0)]
    for index, track in enumerate(tracks, start=1):
        track_node = ET.SubElement(song, "TGTrack", {"maxFret": str(track.get("max_fret", 24))})
        _node(track_node, "name", track["name"])
        _node(track_node, "channelId", index)
        r, g, b = palette[(index - 1) % len(palette)]
        ET.SubElement(track_node, "color", {"R": str(r), "G": str(g), "B": str(b)})
        for string in sorted(track["tuning"], key=lambda item: item["string"]):
            _node(track_node, "TGString", string["pitch_midi"])
        _node(track_node, "TGLyric", "", {"from": "1"})
        _write_measures(track_node, track, key_signatures)


def _write_measures(
    track_node: ET.Element,
    track: Mapping[str, Any],
    key_signatures: Sequence[Mapping[str, Any]],
) -> None:
    clef = track.get("clef", "treble")
    for measure in track["measures"]:
        key_signature = _effective_entry(key_signatures, measure["number"])["value"]
        measure_node = ET.SubElement(track_node, "TGMeasure")
        _node(measure_node, "clef", clef)
        _node(measure_node, "keySignature", key_signature)
        for event in measure["events"]:
            _write_beat(measure_node, measure, event)


def _write_beat(
    measure_node: ET.Element,
    measure: Mapping[str, Any],
    event: Mapping[str, Any],
) -> None:
    beat = ET.SubElement(measure_node, "TGBeat")
    precise_start = TG_PRECISE_START_OFFSET + measure["start_units"] + event["offset_units"]
    _node(beat, "preciseStart", precise_start)
    _write_voice(beat, event)

    # TuxGuitar writes two voices per beat. The second voice is empty by default.
    empty_voice = ET.SubElement(beat, "voice", {"empty": "true"})
    _write_duration(
        empty_voice,
        {
            "value": 4,
            "dots": 0,
            "tuplet": {"enters": 1, "times": 1},
            "units": UNITS_PER_QUARTER,
        },
    )


def _write_voice(beat: ET.Element, event: Mapping[str, Any]) -> None:
    notes = event.get("notes", [])
    attrs = {}
    if not notes:
        attrs["empty"] = "true"
    if event.get("direction") in {"up", "down"}:
        attrs["direction"] = event["direction"]
    voice = ET.SubElement(beat, "voice", attrs)
    _write_duration(voice, event["duration"])
    previous_velocity: int | None = None
    for note in notes:
        note_attrs = {
            "value": str(note["fret"]),
            "string": str(note["string"]),
        }
        if previous_velocity != note["velocity"]:
            note_attrs["velocity"] = str(note["velocity"])
        if note.get("tied", False):
            note_attrs["tiedNote"] = "true"
        note_node = ET.SubElement(voice, "note", note_attrs)
        for effect in note.get("effects", []):
            ET.SubElement(note_node, effect)
        previous_velocity = note["velocity"]


def _write_duration(parent: ET.Element, duration: Mapping[str, Any]) -> None:
    attrs = {"value": str(duration["value"])}
    if duration["dots"] == 1:
        attrs["dotted"] = "dotted"
    elif duration["dots"] == 2:
        attrs["dotted"] = "doubleDotted"
    duration_node = ET.SubElement(parent, "duration", attrs)
    tuplet = duration["tuplet"]
    if tuplet["enters"] != 1 or tuplet["times"] != 1:
        ET.SubElement(
            duration_node,
            "divisionType",
            {"enters": str(tuplet["enters"]), "times": str(tuplet["times"])},
        )


def _node(parent: ET.Element, tag: str, text: Any = "", attrs: Mapping[str, Any] | None = None) -> ET.Element:
    node = ET.SubElement(parent, tag, {key: str(value) for key, value in (attrs or {}).items()})
    node.text = "" if text is None else str(text)
    return node


def _validate_track(
    track: Mapping[str, Any],
    path: str,
    measure_count: int,
    expected_measure_durations: Sequence[int],
    time_signatures: Sequence[Mapping[str, Any]],
) -> None:
    _reject_unknown(track, TRACK_KEYS, path)
    if track.get("kind") != "fretted-string":
        raise ContractValidationError("UNSUPPORTED_TRACK_KIND", f"{path}.kind", "only fretted-string is supported")
    if "instrument" in track:
        instrument = _required_mapping(track, "instrument", path)
        _reject_unknown(instrument, INSTRUMENT_KEYS, f"{path}.instrument")

    tuning = _required_sequence(track, "tuning", path)
    tuning_by_string = _validate_tuning(tuning, f"{path}.tuning")
    max_fret = _required_int(track, "max_fret", path)
    if max_fret < 0:
        raise ContractValidationError("INVALID_FRET", f"{path}.max_fret", "max_fret must be non-negative")
    clef = track.get("clef", "treble")
    if clef not in SUPPORTED_CLEFS:
        raise ContractValidationError("UNSUPPORTED_CLEF", f"{path}.clef", f"unsupported clef {clef!r}")

    measures = _required_sequence(track, "measures", path)
    if len(measures) != measure_count:
        raise ContractValidationError(
            "INVALID_MEASURE_COUNT",
            f"{path}.measures",
            f"expected {measure_count} measures",
        )

    cumulative_start = 0
    for measure_index, measure_value in enumerate(measures):
        measure_path = f"{path}.measures[{measure_index}]"
        measure = _require_mapping(measure_value, measure_path)
        _validate_measure(
            measure,
            measure_path,
            measure_index + 1,
            cumulative_start,
            expected_measure_durations[measure_index],
            tuning_by_string,
            max_fret,
        )
        cumulative_start += expected_measure_durations[measure_index]

    for measure_number in range(1, measure_count + 1):
        _effective_entry(time_signatures, measure_number)


def _validate_measure(
    measure: Mapping[str, Any],
    path: str,
    expected_number: int,
    expected_start: int,
    expected_duration: int,
    tuning_by_string: Mapping[int, int],
    max_fret: int,
) -> None:
    _reject_unknown(measure, MEASURE_KEYS, path)
    if _required_int(measure, "number", path) != expected_number:
        raise ContractValidationError("INVALID_MEASURE_NUMBER", f"{path}.number", f"expected {expected_number}")
    if _required_int(measure, "start_units", path) != expected_start:
        raise ContractValidationError("INVALID_MEASURE_START", f"{path}.start_units", f"expected {expected_start}")
    if _required_int(measure, "duration_units", path) != expected_duration:
        raise ContractValidationError(
            "INVALID_MEASURE_DURATION",
            f"{path}.duration_units",
            f"expected {expected_duration}",
        )

    events = _required_sequence(measure, "events", path)
    expected_offset = 0
    for event_index, event_value in enumerate(events):
        event_path = f"{path}.events[{event_index}]"
        event = _require_mapping(event_value, event_path)
        _reject_unknown(event, EVENT_KEYS, event_path)
        offset = _required_int(event, "offset_units", event_path)
        if offset > expected_offset:
            raise ContractValidationError("EVENT_GAP", f"{event_path}.offset_units", f"expected {expected_offset}")
        if offset < expected_offset:
            raise ContractValidationError("EVENT_OVERLAP", f"{event_path}.offset_units", f"expected {expected_offset}")
        duration = _required_mapping(event, "duration", event_path)
        event_duration = _validate_duration(duration, f"{event_path}.duration")
        notes = _required_sequence(event, "notes", event_path)
        _validate_notes(notes, f"{event_path}.notes", tuning_by_string, max_fret)
        expected_offset += event_duration

    if expected_offset < expected_duration:
        raise ContractValidationError("EVENT_GAP", f"{path}.events", f"measure ends at {expected_offset}")
    if expected_offset > expected_duration:
        raise ContractValidationError("EVENT_OVERLAP", f"{path}.events", f"measure ends at {expected_offset}")


def _validate_duration(duration: Mapping[str, Any], path: str) -> int:
    _reject_unknown(duration, DURATION_KEYS, path)
    value = _required_int(duration, "value", path)
    dots = _required_int(duration, "dots", path)
    units = _required_int(duration, "units", path)
    tuplet = _required_mapping(duration, "tuplet", path)
    _reject_unknown(tuplet, TUPLET_KEYS, f"{path}.tuplet")
    enters = _required_int(tuplet, "enters", f"{path}.tuplet")
    times = _required_int(tuplet, "times", f"{path}.tuplet")

    if value not in SUPPORTED_DURATION_VALUES:
        raise ContractValidationError("INVALID_DURATION_VALUE", f"{path}.value", f"unsupported value {value}")
    if dots not in {0, 1, 2}:
        raise ContractValidationError("INVALID_DOTS", f"{path}.dots", "dots must be 0, 1, or 2")
    if enters <= 0 or times <= 0:
        raise ContractValidationError("INVALID_TUPLET", f"{path}.tuplet", "enters and times must be positive")

    dot_factor = {0: Fraction(1, 1), 1: Fraction(3, 2), 2: Fraction(7, 4)}[dots]
    expected = Fraction(UNITS_PER_QUARTER * 4, value) * dot_factor * Fraction(times, enters)
    if expected.denominator != 1 or expected.numerator != units:
        raise ContractValidationError(
            "DURATION_NOTATION_MISMATCH",
            path,
            f"notation resolves to {expected}, but units is {units}",
        )
    return units


def _validate_notes(
    notes: Sequence[Any],
    path: str,
    tuning_by_string: Mapping[int, int],
    max_fret: int,
) -> None:
    used_strings: set[int] = set()
    for note_index, note_value in enumerate(notes):
        note_path = f"{path}[{note_index}]"
        note = _require_mapping(note_value, note_path)
        _reject_unknown(note, NOTE_KEYS, note_path)
        pitch_midi = _required_int(note, "pitch_midi", note_path)
        string = _required_int(note, "string", note_path)
        fret = _required_int(note, "fret", note_path)
        velocity = _required_int(note, "velocity", note_path)
        tied = note.get("tied")
        effects = _required_sequence(note, "effects", note_path)

        if string not in tuning_by_string:
            raise ContractValidationError("INVALID_STRING", f"{note_path}.string", f"unknown string {string}")
        if string in used_strings:
            raise ContractValidationError("DUPLICATE_STRING_IN_CHORD", f"{note_path}.string", f"string {string}")
        used_strings.add(string)
        if fret < 0 or fret > max_fret:
            raise ContractValidationError("INVALID_FRET", f"{note_path}.fret", f"fret must be between 0 and {max_fret}")
        if not 0 <= velocity <= 127:
            raise ContractValidationError("INVALID_VELOCITY", f"{note_path}.velocity", "velocity must be 0..127")
        if not isinstance(tied, bool):
            raise ContractValidationError("INVALID_TYPE", f"{note_path}.tied", "tied must be a boolean")
        expected_pitch = tuning_by_string[string] + fret
        if pitch_midi != expected_pitch:
            raise ContractValidationError(
                "TAB_PITCH_MISMATCH",
                note_path,
                f"pitch_midi {pitch_midi} does not match string {string} + fret {fret} ({expected_pitch})",
            )
        for effect_index, effect in enumerate(effects):
            if not isinstance(effect, str) or effect not in SUPPORTED_EFFECTS:
                raise ContractValidationError(
                    "UNSUPPORTED_EFFECT",
                    f"{note_path}.effects[{effect_index}]",
                    f"unsupported effect {effect!r}",
                )


def _validate_tuning(tuning: Sequence[Any], path: str) -> dict[int, int]:
    if not tuning:
        raise ContractValidationError("INVALID_TUNING", path, "at least one string is required")
    tuning_by_string: dict[int, int] = {}
    for index, value in enumerate(tuning):
        item_path = f"{path}[{index}]"
        item = _require_mapping(value, item_path)
        _reject_unknown(item, TUNING_KEYS, item_path)
        string = _required_int(item, "string", item_path)
        pitch = _required_int(item, "pitch_midi", item_path)
        if string in tuning_by_string:
            raise ContractValidationError("INVALID_TUNING", f"{item_path}.string", f"duplicate string {string}")
        tuning_by_string[string] = pitch
    expected = list(range(1, len(tuning_by_string) + 1))
    if sorted(tuning_by_string) != expected:
        raise ContractValidationError("INVALID_TUNING", path, f"strings must be consecutive: {expected}")
    return tuning_by_string


def _validate_tempo_map(project: Mapping[str, Any], measure_count: int) -> list[Mapping[str, Any]]:
    entries = _required_sequence(project, "tempo_map", "$.project")
    if not entries:
        raise ContractValidationError("MISSING_TEMPO", "$.project.tempo_map", "tempo_map must include measure 1")
    seen: set[int] = set()
    result: list[Mapping[str, Any]] = []
    for index, entry_value in enumerate(entries):
        path = f"$.project.tempo_map[{index}]"
        entry = _require_mapping(entry_value, path)
        _reject_unknown(entry, TEMPO_KEYS, path)
        measure = _required_int(entry, "measure", path)
        bpm = _required_int(entry, "bpm", path)
        beat_unit = _required_int(entry, "beat_unit", path)
        if measure < 1 or measure > measure_count:
            raise ContractValidationError("INVALID_TEMPO", f"{path}.measure", "measure out of range")
        if measure in seen:
            raise ContractValidationError("INVALID_TEMPO", f"{path}.measure", f"duplicate measure {measure}")
        if bpm <= 0:
            raise ContractValidationError("INVALID_TEMPO", f"{path}.bpm", "bpm must be positive")
        if beat_unit not in SUPPORTED_DURATION_VALUES:
            raise ContractValidationError("INVALID_TEMPO", f"{path}.beat_unit", "unsupported beat unit")
        seen.add(measure)
        result.append(entry)
    if 1 not in seen:
        raise ContractValidationError("MISSING_TEMPO", "$.project.tempo_map", "tempo_map must include measure 1")
    return _sorted_entries(result)


def _validate_time_signatures(project: Mapping[str, Any], measure_count: int) -> list[Mapping[str, Any]]:
    entries = _required_sequence(project, "time_signatures", "$.project")
    if not entries:
        raise ContractValidationError(
            "MISSING_TIME_SIGNATURE",
            "$.project.time_signatures",
            "time_signatures must include measure 1",
        )
    seen: set[int] = set()
    result: list[Mapping[str, Any]] = []
    for index, entry_value in enumerate(entries):
        path = f"$.project.time_signatures[{index}]"
        entry = _require_mapping(entry_value, path)
        _reject_unknown(entry, TIME_SIGNATURE_KEYS, path)
        measure = _required_int(entry, "measure", path)
        numerator = _required_int(entry, "numerator", path)
        denominator = _required_int(entry, "denominator", path)
        if measure < 1 or measure > measure_count:
            raise ContractValidationError("INVALID_TIME_SIGNATURE", f"{path}.measure", "measure out of range")
        if measure in seen:
            raise ContractValidationError(
                "INVALID_TIME_SIGNATURE", f"{path}.measure", f"duplicate measure {measure}"
            )
        if numerator <= 0:
            raise ContractValidationError("INVALID_TIME_SIGNATURE", f"{path}.numerator", "must be positive")
        if denominator not in SUPPORTED_DURATION_VALUES:
            raise ContractValidationError("INVALID_TIME_SIGNATURE", f"{path}.denominator", "unsupported denominator")
        _measure_duration_units(numerator, denominator)
        seen.add(measure)
        result.append(entry)
    if 1 not in seen:
        raise ContractValidationError(
            "MISSING_TIME_SIGNATURE",
            "$.project.time_signatures",
            "time_signatures must include measure 1",
        )
    return _sorted_entries(result)


def _validate_key_signatures(project: Mapping[str, Any], measure_count: int) -> list[Mapping[str, Any]]:
    entries = project.get("key_signatures", [{"measure": 1, "value": 0}])
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        raise ContractValidationError("INVALID_TYPE", "$.project.key_signatures", "must be a list")
    if not entries:
        return [{"measure": 1, "value": 0}]
    seen: set[int] = set()
    result: list[Mapping[str, Any]] = []
    for index, entry_value in enumerate(entries):
        path = f"$.project.key_signatures[{index}]"
        entry = _require_mapping(entry_value, path)
        _reject_unknown(entry, KEY_SIGNATURE_KEYS, path)
        measure = _required_int(entry, "measure", path)
        _required_int(entry, "value", path)
        if measure < 1 or measure > measure_count:
            raise ContractValidationError("INVALID_KEY_SIGNATURE", f"{path}.measure", "measure out of range")
        if measure in seen:
            raise ContractValidationError("INVALID_KEY_SIGNATURE", f"{path}.measure", f"duplicate measure {measure}")
        seen.add(measure)
        result.append(entry)
    if 1 not in seen:
        result.append({"measure": 1, "value": 0})
    return _sorted_entries(result)


def _measure_duration_units(numerator: int, denominator: int) -> int:
    value = Fraction(UNITS_PER_QUARTER * 4 * numerator, denominator)
    if value.denominator != 1:
        raise ContractValidationError("INVALID_MEASURE_DURATION", "$.project.time_signatures", "non-integer duration")
    return value.numerator


def _read_measure_count(tracks: Sequence[Any]) -> int:
    first_track = _require_mapping(tracks[0], "$.tracks[0]")
    measures = _required_sequence(first_track, "measures", "$.tracks[0]")
    if not measures:
        raise ContractValidationError("INVALID_MEASURE_COUNT", "$.tracks[0].measures", "at least one measure is required")
    return len(measures)


def _sorted_entries(entries: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(entries, key=lambda item: item["measure"])


def _effective_entry(entries: Sequence[Mapping[str, Any]], measure_number: int) -> Mapping[str, Any]:
    current: Mapping[str, Any] | None = None
    for entry in entries:
        if entry["measure"] > measure_number:
            break
        current = entry
    if current is None:
        raise ContractValidationError("MISSING_MEASURE_MAP_ENTRY", "$.project", f"missing entry for measure {measure_number}")
    return current


def _reject_unknown(obj: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ContractValidationError("UNKNOWN_FIELD", f"{path}.{unknown[0]}", "unknown field outside extensions")


def _required_mapping(obj: Mapping[str, Any], key: str, path: str) -> Mapping[str, Any]:
    if key not in obj:
        raise ContractValidationError("MISSING_FIELD", f"{path}.{key}", "required field is missing")
    return _require_mapping(obj[key], f"{path}.{key}")


def _required_sequence(obj: Mapping[str, Any], key: str, path: str) -> Sequence[Any]:
    if key not in obj:
        raise ContractValidationError("MISSING_FIELD", f"{path}.{key}", "required field is missing")
    value = obj[key]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ContractValidationError("INVALID_TYPE", f"{path}.{key}", "must be a list")
    return value


def _required_int(obj: Mapping[str, Any], key: str, path: str) -> int:
    if key not in obj:
        raise ContractValidationError("MISSING_FIELD", f"{path}.{key}", "required field is missing")
    value = obj[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractValidationError("INVALID_TYPE", f"{path}.{key}", "must be an integer")
    return value


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractValidationError("INVALID_TYPE", path, "must be an object")
    return value
