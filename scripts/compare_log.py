#!/usr/bin/env python3

import sys

from parse_log import parse_log


# used in workaround for EAC bug where it doesn't put a space between vendor and model
def generate_single_space_insertions(s):
    for i in range(1, len(s)):
        yield s[:i] + " " + s[i:]

def compare_values(name, log1_val, log2_val, indent=0):
    if log1_val == log2_val:
        print("✅" + " "*(indent + 1) + f"{name} matches")
    else:
        print("❌" + " "*(indent + 1) + f"{name} differs")
        print("  " + " "*(indent + 1) + f"log 1: {log1_val}")
        print("  " + " "*(indent + 1) + f"log 2: {log2_val}")


def compare_tracks(log1, log2, track_index):
    both_eac = log1.ripper == "EAC" and log2.ripper == "EAC"
    neither_eac = log1.ripper != "EAC" and log2.ripper != "EAC"
    one_eac = not both_eac and not neither_eac

    track1 = log1.tracks[track_index]
    track2 = log2.tracks[track_index]
    print(f"Comparing tracks[{track_index}]")
    compare_values("track number",      track1.number,          track2.number,          indent=2)
    compare_values("start sector",      track1.cd_start_sector, track2.cd_start_sector, indent=2)
    compare_values("end sector",        track1.cd_end_sector,   track2.cd_end_sector,   indent=2)
    compare_values("pregap duration",   track1.pregap_duration, track2.pregap_duration, indent=2)
    if both_eac or neither_eac:
        compare_values("peak", track1.peak, track2.peak, indent=2)
    else:
        pass
    compare_values("EAC CRC32", track1.eac_crc32, track2.eac_crc32, indent=2)
    if neither_eac:
        compare_values("AccurateRip v1", track1.accurate_rip_v1, track2.accurate_rip_v1, indent=2)
        compare_values("AccurateRip v2", track1.accurate_rip_v2, track2.accurate_rip_v2, indent=2)


def compare_logs(log1, log2):
    both_eac = log1.ripper == "EAC" and log2.ripper == "EAC"
    neither_eac = log1.ripper != "EAC" and log2.ripper != "EAC"
    one_eac = not both_eac and not neither_eac
    if log1.drive is None or log2.drive is None:
        print("Warning: Can't determine if same drive used for rips.")
    elif (both_eac or neither_eac) and log1.drive != log2.drive:
        print("Warning: Different drives used for rips.")
    # workaround for EAC bug where it doesn't put a space between vendor and model
    elif one_eac:
        eac_log = log1 if log1.ripper == "EAC" else log2
        non_eac_log = log2 if log1.ripper == "EAC" else log1
        non_eac_drive = non_eac_log.drive
        possible_eac_drives = generate_single_space_insertions(eac_log.drive)
        if non_eac_drive not in possible_eac_drives:
            print("Warning: Different drives used for rips.")
        else:
            print("✅ drives match")
    else:
        print("✅ drives match")

    compare_values("track counts", len(log1.tracks), len(log2.tracks))
    for i in range(min(len(log1.tracks), len(log2.tracks))):
        compare_tracks(log1, log2, i)


log1 = parse_log(sys.argv[1])
log2 = parse_log(sys.argv[2])
compare_logs(log1, log2)
