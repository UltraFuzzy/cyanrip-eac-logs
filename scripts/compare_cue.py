#!/usr/bin/env python3

import sys
import os

from parse_cue import parse_cue


# Some metadata in a cue file, such as album and track titles, might be read from
# the CD itself, entered manually, or pulled from a database like MusicBrainz.
# When given just a cue file we have no way of knowing where these data came
# from and since we only want to compare how different rippers read a CD these
# should be ignored for now. In the future, we might want to test how different
# rippers read these data from disc using "known offline" cue files.
COMPARE_POTENTIALLY_EXTERNAL_METADATA = False


def compare_values(name, cue1_val, cue2_val, cue1_ripper, cue2_ripper):
    if cue1_val == cue2_val:
        print(f"✅ {name} matches")
    else:
        cue1_ripper = f"({cue1_ripper})"
        cue2_ripper = f"({cue2_ripper})"
        ripper_str_width = max(len(cue1_ripper), len(cue2_ripper))
        print(f"❌ {name} differs")
        print(f"   cue 1 {cue1_ripper:<{ripper_str_width}}: {cue1_val}")
        print(f"   cue 2 {cue2_ripper:<{ripper_str_width}}: {cue2_val}")


def compare_tracks(cue1, cue2, t1, t2):
    compare_values("track number",  t1.number,    t2.number,    cue1.ripper, cue2.ripper)
    if COMPARE_POTENTIALLY_EXTERNAL_METADATA:
        compare_values("TITLE",     t1.title,     t2.title,     cue1.ripper, cue2.ripper)
        compare_values("PERFORMER", t1.performer, t2.performer, cue1.ripper, cue2.ripper)
    # TODO: ISRCs are usually on the disc but can still potentially have been
    # pulled from a database. This one should be a priority to revisit.
    if COMPARE_POTENTIALLY_EXTERNAL_METADATA:
        compare_values("ISRC", t1.isrc, t2.isrc, cue1.ripper, cue2.ripper)

    # For INDEX 00 entries, we compare the time and also try to be clever about
    # comparing their layout in the ripped track files. The file names don't
    # need to match but what should match is "track X has its pregap in the
    # file that primarily contains track Y". For lack of a better name, I'm
    # calling this the "shape" of an index.
    # XXX: This assumes ripping with a typical track output strategy and would need
    # to be changed if we ever wanted to test less common track output
    # strategies where there isn't a simple one-to-one correspondence
    # between files and a primary track.

    compare_values("INDEX 00", t1.index00, t2.index00, cue1.ripper, cue2.ripper)

    # The `.main_track_number` values are currently determined from the INDEX 01
    # entries so the file check is superfluous here but that could change in
    # the future.
    compare_values("INDEX 01", t1.index01, t2.index01, cue1.ripper, cue2.ripper)


def compare_cues(cue1, cue2):
    print(f'Comparing cue files "{os.path.basename(cue1.file_path)}" and "{os.path.basename(cue2.file_path)}"')
    if cue1.discid is not None and cue2.discid is not None:
        compare_values("DISCID",  cue1.discid, cue2.discid,               cue1.ripper, cue2.ripper)
    # TODO: cyanrip doesn't include MCN properly in cue files, labels it "MCN" instead of "CATALOG"
    if cue1.catalog is not None and cue2.catalog is not None:
        compare_values("CATALOG", cue1.catalog, cue2.catalog,             cue1.ripper, cue2.ripper)
    if COMPARE_POTENTIALLY_EXTERNAL_METADATA:
        compare_values("album PERFORMER", cue1.performer, cue2.performer, cue1.ripper, cue2.ripper)
        compare_values("album TITLE", cue1.title, cue2.title,             cue1.ripper, cue2.ripper)
    for i, (t1, t2) in enumerate(zip(cue1.tracks, cue2.tracks)):
        print(f"Comparing tracks[{i}]")
        compare_tracks(cue1, cue2, t1, t2)


# TODO proper argument parsing if this becomes more than a quick disposable script
compare_cues(parse_cue(sys.argv[1]), parse_cue(sys.argv[2]))
