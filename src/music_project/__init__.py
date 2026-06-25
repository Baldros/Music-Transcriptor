"""Core code for the music-to-TuxGuitar pipeline experiments."""

from .tg_writer import (
    ContractValidationError,
    build_content_xml,
    contract_to_tg_bytes,
    load_contract,
    validate_contract,
    write_tg,
)

__all__ = [
    "ContractValidationError",
    "build_content_xml",
    "contract_to_tg_bytes",
    "load_contract",
    "validate_contract",
    "write_tg",
]
