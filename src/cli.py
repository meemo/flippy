#!/usr/bin/env python3
"""
flippy - Command-line tool for Nintendo Flipnote Studio animations.

Uses flipnote.py for parsing and libugomemo (via ctypes) for performance.
"""

import sys
import os
import json
import struct
import wave
import argparse

from flipnote.ppm import Parser as PPMParser
from flipnote.kwz import Parser as KWZParser

from meta import ppm_meta_json, kwz_meta_json

VERSION = "0.1.0"


def _confirm_overwrite(path, force=False):
    if force or not os.path.exists(path):
        return True
    try:
        response = input(f"Overwrite {path}? (y/N) ").strip().lower()
        return response == "y"
    except (EOFError, KeyboardInterrupt):
        print("", file=sys.stderr)
        return False


def detect_format(path):
    with open(path, "rb") as f:
        magic = f.read(4)
    if magic[:4] == b"PARA":
        return "ppm"
    elif magic[:1] == b"K":
        return "kwz"
    elif magic[:4] == b"UGAR":
        ext = os.path.splitext(path)[1].lower()
        return ext.lstrip(".")
    elif magic[:4] == b"KPCF" or magic[:4] == b"KDER":
        return "kwzpcf"
    else:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".lst", ".pls"):
            return ext.lstrip(".")
        return None


def open_parser(path):
    fmt = detect_format(path)
    if fmt == "ppm":
        return PPMParser.open(path), fmt
    elif fmt == "kwz":
        return KWZParser.open(path), fmt
    else:
        return None, fmt


def _json_dumps(obj, minified=False):
    if minified:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(obj, ensure_ascii=False, indent=4)


def cmd_meta(args):
    parser, fmt = open_parser(args.input)
    if parser is None:
        print(f"Unsupported format for: {args.input}", file=sys.stderr)
        return 1

    file_size = os.path.getsize(args.input)

    if fmt == "ppm":
        result = ppm_meta_json(parser, args.input, file_size,
                               silence_warnings=args.silence_warnings,
                               silence_notices=args.silence_notices)
    elif fmt == "kwz":
        result = kwz_meta_json(parser, args.input, file_size,
                               silence_warnings=args.silence_warnings,
                               silence_notices=args.silence_notices)
    else:
        result = {"error": f"meta not supported for format: {fmt}"}

    print(_json_dumps(result, minified=args.minified))
    parser.unload()
    return 0


def cmd_extract_audio(args):
    parser, fmt = open_parser(args.input)
    if parser is None:
        print(f"Unsupported format: {args.input}", file=sys.stderr)
        return 1

    track = args.track
    if isinstance(track, str) and track != "mix":
        track = int(track)

    if track == "mix" and fmt != "kwz":
        print("Track mixing is only supported for KWZ files", file=sys.stderr)
        return 1

    if track == "mix":
        import numpy as np
        tracks = []
        max_len = 0
        for i in range(5):
            if hasattr(parser, 'has_audio_track') and parser.has_audio_track(i):
                samples = parser.decode_audio_track(i)
                tracks.append(samples)
                max_len = max(max_len, len(samples))
        if not tracks:
            print("No audio tracks have data", file=sys.stderr)
            return 1
        mixed = np.zeros(max_len, dtype=np.int32)
        for t in tracks:
            mixed[:len(t)] += t.astype(np.int32)
        mixed = mixed // len(tracks)
        mixed = np.clip(mixed, -32768, 32767).astype(np.int16)
        samples = mixed
        sample_rate = 16364
    else:
        samples = parser.decode_audio_track(track)
        sample_rate = 8192 if fmt == "ppm" else 16364

    if not _confirm_overwrite(args.output, args.force):
        return 0

    with wave.open(args.output, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(samples.tobytes())

    print(f"Wrote {len(samples)} samples to {args.output}", file=sys.stderr)
    parser.unload()
    return 0


def cmd_extract_thumbnail(args):
    parser, fmt = open_parser(args.input)
    if parser is None:
        print(f"Unsupported format: {args.input}", file=sys.stderr)
        return 1

    if not _confirm_overwrite(args.output, args.force):
        return 0

    if fmt == "ppm":
        thumb = parser.decode_thumbnail()
        _write_bmp(args.output, thumb)
    elif fmt == "kwz":
        data = parser.get_thumbnail()
        with open(args.output, "wb") as f:
            f.write(data)
    else:
        print(f"Thumbnails not supported for format: {fmt}", file=sys.stderr)
        return 1

    print(f"Wrote thumbnail to {args.output}", file=sys.stderr)
    parser.unload()
    return 0


def cmd_extract_frames(args):
    parser, fmt = open_parser(args.input)
    if parser is None:
        print(f"Unsupported format: {args.input}", file=sys.stderr)
        return 1

    os.makedirs(args.output_dir, exist_ok=True)

    for i in range(parser.frame_count):
        frame = parser.decode_frame(i)
        path = os.path.join(args.output_dir, f"{i + 1:04d}.bmp")
        _write_bmp(path, frame)

    print(f"Extracted {parser.frame_count} frames to {args.output_dir}/", file=sys.stderr)
    parser.unload()
    return 0


def _write_bmp(path, pixels):
    import numpy as np
    height, width = pixels.shape[:2]
    row_size = width * 3
    padding = (4 - (row_size % 4)) % 4
    image_size = (row_size + padding) * height

    header = struct.pack("<2sIHHI", b"BM",
                         14 + 40 + image_size, 0, 0, 14 + 40)
    dib = struct.pack("<IiiHHIIiiII", 40,
                      width, height, 1, 24, 0, image_size, 0, 0, 0, 0)

    with open(path, "wb") as f:
        f.write(header)
        f.write(dib)
        pad_bytes = b"\x00" * padding
        for y in range(height - 1, -1, -1):
            row = pixels[y]
            bgr = np.stack([row[:, 2], row[:, 1], row[:, 0]], axis=1)
            f.write(bgr.tobytes())
            if padding:
                f.write(pad_bytes)


def main():
    parser = argparse.ArgumentParser(
        prog="flippy",
        description="Command-line tool for Nintendo Flipnote Studio animations",
    )
    parser.add_argument("--version", action="version", version=f"flippy {VERSION}")

    subparsers = parser.add_subparsers(dest="command")

    # meta
    p_meta = subparsers.add_parser("meta", help="Display file metadata as JSON")
    p_meta.add_argument("input", help="Input file (.ppm, .kwz, .ugo, etc.)")
    p_meta.add_argument("--silence-warnings", action="store_true")
    p_meta.add_argument("--silence-notices", action="store_true")
    p_meta.add_argument("--minified", action="store_true", help="Output minified JSON")

    # extract
    p_extract = subparsers.add_parser("extract", help="Extract data from flipnote files")
    extract_sub = p_extract.add_subparsers(dest="extract_cmd")

    p_audio = extract_sub.add_parser("audio", help="Extract audio track to WAV")
    p_audio.add_argument("--track", required=True, help="Track number (0-4) or 'mix'")
    p_audio.add_argument("--initial-step-index", type=int, default=None)
    p_audio.add_argument("--force", action="store_true", help="Overwrite without confirmation")
    p_audio.add_argument("input", help="Input file")
    p_audio.add_argument("output", help="Output WAV file")

    p_thumb = extract_sub.add_parser("thumbnail", help="Extract thumbnail")
    p_thumb.add_argument("--force", action="store_true", help="Overwrite without confirmation")
    p_thumb.add_argument("input", help="Input file")
    p_thumb.add_argument("output", help="Output file")

    p_frames = extract_sub.add_parser("frames", help="Extract all frames as BMP")
    p_frames.add_argument("--force", action="store_true", help="Overwrite without confirmation")
    p_frames.add_argument("input", help="Input file")
    p_frames.add_argument("output_dir", help="Output directory")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "meta":
        return cmd_meta(args)
    elif args.command == "extract":
        if args.extract_cmd == "audio":
            return cmd_extract_audio(args)
        elif args.extract_cmd == "thumbnail":
            return cmd_extract_thumbnail(args)
        elif args.extract_cmd == "frames":
            return cmd_extract_frames(args)
        else:
            p_extract.print_help()
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
