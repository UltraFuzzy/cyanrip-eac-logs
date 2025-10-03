#!/usr/bin/env python3

import sys

from parse_cue import parse_cue


def compare_values(name, cue1_val, cue2_val, indent=0):
    if cue1_val == cue2_val:
        print("✅" + " "*(indent + 1) + f"{name} matches")
    else:
        print("❌" + " "*(indent + 1) + f"{name} differs")
        print("  " + " "*(indent + 1) + f"cue 1: {cue1_val}")
        print("  " + " "*(indent + 1) + f"cue 2: {cue2_val}")


def compare_tracks(t1, t2):
    compare_values("track number",  t1.number,    t2.number,    indent=2)
    if t1.title is not None and t2.title is not None:
        compare_values("TITLE",     t1.title,     t2.title,     indent=2)
    if t1.performer is not None and t2.performer is not None:
        compare_values("PERFORMER", t1.performer, t2.performer, indent=2)
    if t1.isrc is not None and t2.isrc is not None:
        compare_values("ISRC",      t1.isrc,      t2.isrc,      indent=2)
    if t1.index00 is not None or t2.index00 is not None:
        t1_index00 = None if t1.index00 is None else (t1.index00[0].main_track_number, t1.index00[1])
        t2_index00 = None if t2.index00 is None else (t2.index00[0].main_track_number, t2.index00[1])
        compare_values("INDEX 00", t1_index00, t2_index00, indent=2)
    t1_index01 = (t1.index01[0].main_track_number, t1.index01[1])
    t2_index01 = (t2.index01[0].main_track_number, t2.index01[1])
    compare_values("INDEX 01", t1_index01, t2_index01, indent=2)


def compare_cues(cue1, cue2):
    if cue1.discid is not None and cue2.discid is not None:
        compare_values("DISCID",  cue1.discid, cue2.discid)
    if cue1.catalog is not None and cue2.catalog is not None:
        compare_values("CATALOG", cue1.catalog, cue2.catalog)
    if cue1.performer is not None and cue2.performer is not None:
        compare_values("album PERFORMER", cue1.performer, cue2.performer)
    if cue1.title is not None and cue2.title is not None:
        compare_values("album TITLE", cue1.title, cue2.title)
    for t1, t2 in zip(cue1.tracks, cue2.tracks):
        print(f"Comparing track {t1.number:02} and {t2.number:02}")
        compare_tracks(t1, t2)


compare_cues(parse_cue(sys.argv[1]), parse_cue(sys.argv[2]))

