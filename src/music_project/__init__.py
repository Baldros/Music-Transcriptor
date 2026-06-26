"""Core code for the music-to-TuxGuitar pipeline experiments."""

from .audio_to_contract import AudioToContractError, RawNoteEvent, build_monophonic_contract
from .tg_writer import (
    ContractValidationError,
    build_content_xml,
    contract_to_tg_bytes,
    load_contract,
    validate_contract,
    write_tg,
)

__all__ = [
    "AudioToContractError",
    "ContractValidationError",
    "RawNoteEvent",
    "build_content_xml",
    "build_monophonic_contract",
    "contract_to_tg_bytes",
    "load_contract",
    "validate_contract",
    "write_tg",
]
