from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audio_backends import transcribe_monophonic_audio
from .audio_to_contract import AudioToContractError, build_monophonic_contract
from .tg_writer import ContractValidationError, write_tg


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe a simple monophonic audio file into a TuxGuitar .tg file."
    )
    parser.add_argument("input", type=Path, help="Path to a monophonic WAV/MP3/etc. audio file.")
    parser.add_argument("output", type=Path, help="Path to the output .tg file.")
    parser.add_argument("--bpm", type=int, required=True, help="Tempo in beats per minute. Required for this MVP.")
    parser.add_argument("--title", default=None, help="Song title. Defaults to the input file stem.")
    parser.add_argument("--instrument", choices=["guitar", "bass"], default="guitar")
    parser.add_argument("--backend", choices=["librosa-pyin", "torchaudio"], default="librosa-pyin")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--quantization", type=int, choices=[4, 8, 16, 32, 64], default=16)
    parser.add_argument("--sample-rate", type=int, default=22050)
    parser.add_argument("--fmin-midi", type=int, default=40)
    parser.add_argument("--fmax-midi", type=int, default=88)
    parser.add_argument("--contract-output", type=Path, default=None, help="Optional path to save the generated contract JSON.")
    args = parser.parse_args()

    try:
        notes = transcribe_monophonic_audio(
            args.input,
            backend=args.backend,
            device=args.device,
            sample_rate=args.sample_rate,
            fmin_midi=args.fmin_midi,
            fmax_midi=args.fmax_midi,
        )
        contract = build_monophonic_contract(
            notes,
            bpm=args.bpm,
            title=args.title or args.input.stem,
            instrument=args.instrument,
            quantization_value=args.quantization,
        )
        if args.contract_output is not None:
            args.contract_output.parent.mkdir(parents=True, exist_ok=True)
            with args.contract_output.open("w", encoding="utf-8") as fp:
                json.dump(contract, fp, indent=2)
                fp.write("\n")
        write_tg(contract, args.output)
    except (RuntimeError, AudioToContractError, ContractValidationError) as exc:
        parser.exit(2, f"audio-to-tg failed: {exc}\n")

    print(f"{args.output} ({len(notes)} notes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

