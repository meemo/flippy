"""
JSON metadata output for flippy, matching the C flippy JSON format.
"""

import json
from datetime import datetime


def ppm_meta_json(parser, file_path, file_size, exit_code=0,
                  silence_warnings=False, silence_notices=False):
    from cli import VERSION as __version__

    ts = parser.timestamp
    if isinstance(ts, datetime):
        ts = int(ts.timestamp())

    offsets = parser.track_offsets
    sizes = parser.track_sizes

    return {
        "flippy_version": __version__,
        "file_path": file_path,
        "file_size": file_size,
        "meta": {
            "current": {
                "username": parser.current_author_name,
                "fsid": parser.current_author_id,
                "file_name": parser.current_filename,
            },
            "parent": {
                "username": parser.parent_author_name,
                "fsid": parser.parent_author_id,
                "file_name": parser.parent_filename,
            },
            "root": {
                "username": parser.root_author_name,
                "fsid": parser.root_author_id,
                "file_name_fragment": parser.root_filename_fragment,
            },
            "animation_data_size": parser.animation_data_size,
            "frame_data_size": parser.frame_data_size,
            "sound_data_size": parser.sound_data_size,
            "frame_count": parser.frame_count,
            "format_version": parser.format_version,
            "lock": parser.lock,
            "thumbnail_frame_index": parser.thumbnail_index,
            "timestamp": ts,
        },
        "sound": {
            "bgm": {"size": sizes[0], "offset": offsets[0]},
            "se1": {"size": sizes[1], "offset": offsets[1]},
            "se2": {"size": sizes[2], "offset": offsets[2]},
            "se3": {"size": sizes[3], "offset": offsets[3]},
            "frame_speed_raw": parser.frame_speed,
            "framerate": parser.framerate,
        },
        "signature": {
            "valid": getattr(parser, "signature_valid", None),
        },
        "exit_code": exit_code,
    }


def kwz_meta_json(parser, file_path, file_size, exit_code=0,
                  silence_warnings=False, silence_notices=False):
    from cli import VERSION as __version__

    sizes = parser.track_sizes

    result = {
        "flippy_version": __version__,
        "file_path": file_path,
        "file_size": file_size,
        "meta": {
            "current": {
                "username": parser.current_author_name,
                "fsid": parser.current_author_id,
                "filename": parser.current_filename,
            },
            "parent": {
                "username": parser.parent_author_name,
                "fsid": parser.parent_author_id,
                "filename": parser.parent_filename,
            },
            "root": {
                "username": parser.root_author_name,
                "fsid": parser.root_author_id,
                "filename": parser.root_filename,
            },
            "creation_timestamp": parser.creation_timestamp,
            "modified_timestamp": parser.modified_timestamp,
            "locked": bool(parser.lock),
            "loop": bool(parser.loop),
            "frame_count": parser.frame_count,
            "thumbnail_frame_index": parser.thumbnail_index,
            "app_version": parser.app_version,
            "framerate": parser.framerate,
        },
        "sound": {},
        "signature": {
            "valid": getattr(parser, "signature_valid", None),
        },
        "exit_code": exit_code,
    }

    track_names = ["bgm", "se1", "se2", "se3", "se4"]
    for i, name in enumerate(track_names):
        if i < len(sizes):
            result["sound"][name] = {"encoded_size": sizes[i]} if sizes[i] > 0 else None
        else:
            result["sound"][name] = None

    return result
