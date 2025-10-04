#!/usr/bin/env python3

import sys
import os

from parse_log import parse_log


def compare_values(name, log1_val, log2_val, log1_ripper, log2_ripper):
    if log1_val == log2_val:
        print(f"✅ {name} matches")
    else:
        log1_ripper = f"({log1_ripper})"
        log2_ripper = f"({log2_ripper})"
        ripper_str_width = max(len(log1_ripper), len(log2_ripper))
        print(f"❌ {name} differs")
        print(f"   log 1 {log1_ripper:<{ripper_str_width}}: {log1_val}")
        print(f"   log 2 {log2_ripper:<{ripper_str_width}}: {log2_val}")


def compare_tracks(log1, log2, track_index):
    both_eac = log1.ripper == "EAC" and log2.ripper == "EAC"
    neither_eac = log1.ripper != "EAC" and log2.ripper != "EAC"
    # one_eac = not both_eac and not neither_eac

    track1 = log1.tracks[track_index]
    track2 = log2.tracks[track_index]
    print(f"Comparing tracks[{track_index}]")
    compare_values("track number",      track1.number,          track2.number,          log1.ripper, log2.ripper)
    compare_values("start sector",      track1.cd_start_sector, track2.cd_start_sector, log1.ripper, log2.ripper)
    compare_values("end sector",        track1.cd_end_sector,   track2.cd_end_sector,   log1.ripper, log2.ripper)
    compare_values("pregap duration",   track1.pregap_duration, track2.pregap_duration, log1.ripper, log2.ripper)
    if both_eac or neither_eac:
        compare_values("peak", track1.peak, track2.peak, log1.ripper, log2.ripper)
    else:
        pass

    compare_values("EAC CRC32", track1.eac_crc32, track2.eac_crc32, log1.ripper, log2.ripper)
    if track1.eac_crc32 != track2.eac_crc32:
        # warn about CRC mismatches in first and last track that may be due to
        # different read offsets
        is_first_track = track_index == 0
        is_last_track  = (track_index == (len(log1.tracks) - 1)
                       or track_index == (len(log2.tracks) - 1))
        either_has_neg_read_offset = log1.read_offset < 0 or log2.read_offset < 0
        either_has_pos_read_offset = log1.read_offset > 0 or log2.read_offset > 0
        if ((is_first_track and either_has_neg_read_offset)
                or (is_last_track and either_has_pos_read_offset)):
            print("   EAC CRC32 mismatch contributed to by differing read offsets")

    both_have_accurate_rip = neither_eac
    if both_have_accurate_rip:
        compare_values("AccurateRip v1", track1.accurate_rip_v1, track2.accurate_rip_v1, log1.ripper, log2.ripper)
        compare_values("AccurateRip v2", track1.accurate_rip_v2, track2.accurate_rip_v2, log1.ripper, log2.ripper)


# used for workaround of EAC quirk where log doesn't have a space between vendor and model strings
def generate_single_space_insertions(s):
    for i in range(1, len(s)):
        yield s[:i] + " " + s[i:]


def compare_logs(log1, log2):
    print(f'Comparing log files "{os.path.basename(log1.file_path)}" and "{os.path.basename(log2.file_path)}"')
    both_eac = log1.ripper == "EAC" and log2.ripper == "EAC"
    neither_eac = log1.ripper != "EAC" and log2.ripper != "EAC"
    one_eac = not both_eac and not neither_eac
    if log1.drive is None:
        print(f'🟡 WARNING: Log "{log1.file_path}" lacks drive info.')
    if log2.drive is None:
        print(f'🟡 WARNING: Log "{log2.file_path} "lacks drive info.')
    if log1.drive is None or log2.drive is None:
        print("🟡 WARNING: Can't determine if same drive used for rips.")
    elif (both_eac or neither_eac) and log1.drive != log2.drive:
        print("🟡 WARNING: Different drives used for rips.")
    # workaround for EAC quirk where log doesn't have a space between vendor and model strings
    elif one_eac:
        eac_log = log1 if log1.ripper == "EAC" else log2
        non_eac_log = log2 if log1.ripper == "EAC" else log1
        non_eac_drive = non_eac_log.drive
        possible_eac_drives = generate_single_space_insertions(eac_log.drive)
        if non_eac_drive not in possible_eac_drives:
            print("🟡 WARNING: Different drives used for rips.")
        else:
            print("✅ drive used matches")
    else:
        print("✅ drive used matches")

    if log1.read_offset != log2.read_offset:
        print("🟡 WARNING: Different read offsets used for rips.")
    else:
        print("✅ read offset matches")

    compare_values("track count", len(log1.tracks), len(log2.tracks), log1.ripper, log2.ripper)
    for i in range(min(len(log1.tracks), len(log2.tracks))):
        compare_tracks(log1, log2, i)


# TODO proper argument parsing if this becomes more than a quick disposable script
compare_logs(parse_log(sys.argv[1]), parse_log(sys.argv[2]))
