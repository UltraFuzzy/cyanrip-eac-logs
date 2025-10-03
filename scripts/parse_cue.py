import sys
import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

# EAC log and cue files use old Windows encodings.
import chardet


@dataclass
class MSF:
    minute: int
    second: int
    frame:  int

    def __str__(self):
        return f"{self.minute:02}:{self.second:02}:{self.frame:02}"


@dataclass
class TrackFile:
    name: str
    main_track_number: Optional[int] = field(default=None)
    tracks:            List['Track'] = field(default_factory=list)

    def __eq__(self, other):
        if not isinstance(other, TrackFile):
            raise NotImplementedError
        return self.main_track_number == other.main_track_number

    def __str__(self):
        return f"File for track {self.main_track_number}"


@dataclass
class Index:
    file: TrackFile
    msf:  MSF

    def __str__(self):
        return f"{self.file}, {self.msf}"


@dataclass
class Track:
    number:    int
    title:     Optional[str]   = field(default=None)
    performer: Optional[str]   = field(default=None)
    isrc:      Optional[str]   = field(default=None)
    index00:   Optional[Index] = field(default=None)
    index01:   Optional[Index] = field(default=None)


@dataclass
class Cue:
    file_path: str
    ripper:    Literal['EAC', 'XLD', 'cyanrip']
    ripper_version: Optional[str]
    lines:     List[str]
    tracks:    List[Track]     = field(default_factory=list)
    files:     List[TrackFile] = field(default_factory=list)
    discid:    Optional[str]   = field(default=None)
    catalog:   Optional[str]   = field(default=None)
    performer: Optional[str]   = field(default=None)
    title:     Optional[str]   = field(default=None)


def is_xld_cue_heuristic(lines):
    for l in lines:
        if l.startswith("FILE") or l.startswith("TRACK"):
            return False
        elif l.startswith("REM REPLAYGAIN_ALBUM"):
            return True
    return False

skip_line_patterns = [
    # entries that don't need to match
    r"REM GENRE",
    r"REM DATE",

    # EAC entries
    r"FLAGS DCP",
    r'REM COMPOSER ""',

    # XLD ReplayGain entries
    r"REM REPLAYGAIN_",

    # cyanrip MusicBrainz-related entries
    r"REM MUSICBRAINZ",
    r"REM MEDIA_TYPE",
    r"REM RELEASE_ID",
    r"REM RELEASECOMMENT",
    r"REM PACKAGING",
    r"REM COUNTRY",
    r"REM STATUS",
    r"REM TOTALDISCS",
    r"REM DISC",
    r"REM FORMAT",
    r"REM BARCODE",

    # TODO cyanrip should write this as CATALOG
    r"MCN",

    # cyanrip line due to fixed bug
    r"PREGAP 00:00:00",
    # cyanrip generates valid track 1 PREGAP entries
    r"PREGAP",
]

def parse_cue(file_path):
    # EAC cue files tend to be Windows-1252.
    encoding = chardet.detect(open(file_path, 'rb').read())['encoding']
    lines = [l.strip() for l in open(file_path, mode='rt', encoding=encoding).readlines()]

    ripper = None
    ripper_version = None
    discid = None
    catalog = None
    performer = None
    title = None
    i = 0
    while not lines[i].startswith("FILE") and not lines[i].startswith("TRACK"):
        if lines[i].startswith("REM DISCID"):
            if discid is not None:
                print('ERROR: Multiple "REM DISCID" commands in {file_path}', file=sys.stderr)
            discid = re.match(r'REM DISCID "?(\w+)"?', lines[i])[1]
        elif lines[i].startswith('REM COMMENT "ExactAudioCopy'):
            ripper = "EAC"
            ripper_version = re.match(r'REM COMMENT "ExactAudioCopy v([0-9\.]+)', lines[i])[1]
        elif lines[i].startswith('REM COMMENT "cyanrip'):
            ripper = "cyanrip"
            ripper_version = re.match(r'REM COMMENT "cyanrip ([^"]+)"', lines[i])[1]
        elif lines[i].startswith('CATALOG '):
            catalog = re.match(r'CATALOG\s+(\w+)', lines[i])[1]
        elif lines[i].startswith('PERFORMER '):
            performer = re.match(r'PERFORMER\s+"([^"]*)"', lines[i])[1]
        elif lines[i].startswith('TITLE '):
            title = re.match(r'TITLE\s+"([^"]*)"', lines[i])[1]
        elif any(re.match(p, lines[i]) for p in skip_line_patterns):
            pass
        else:
            print(f"WARN: Unrecognized entry in cue file \"{file_path}\" line {i+1}: {lines[i]}", file=sys.stderr)
        i += 1
    if ripper is None and is_xld_cue_heuristic(lines):
        ripper = "XLD"
    if ripper is None:
        print(f'ERROR: Cannot identify ripper that created {file_path}', file=sys.stderr)

    tracks = []
    files = []
    cur_track = None
    cur_file = None
    while i < len(lines):
        if lines[i].startswith("FILE "):
            name = TrackFile(name=re.match(r'FILE\s+"([^"]*)"', lines[i])[1])
            if cur_file is not None:
                files.append(cur_file)
            cur_file = TrackFile(name=re.match(r'FILE\s+"([^"]*)"', lines[i])[1])

        elif lines[i].startswith("TRACK "):
            track_number = int(re.match(r"TRACK\s+(\d+)\s", lines[i])[1])
            if cur_track is not None and cur_track.number == track_number:
                print(f"WARN: {file_path} has multiple entries for track {cur_track.number:02} TRACK", file=sys.stderr)
                pass
            else:
                if cur_track is not None:
                    tracks.append(cur_track)
                cur_track = Track(number=track_number)

        elif lines[i].startswith("TITLE "):
            track_title = re.match(r'TITLE\s+"([^"]+)"', lines[i])[1]
            if cur_track.title is not None:
                if cur_track.title != track_title:
                    print(f"ERROR: {file_path} has multiple entries for track {cur_track.number:02} TITLE and they differ", file=sys.stderr)
                else:
                    print(f"WARN: {file_path} has multiple entries for track {cur_track.number:02} TITLE but they match", file=sys.stderr)
                    pass
            cur_track.title = track_title

        elif lines[i].startswith("PERFORMER "):
            track_performer = re.match(r'PERFORMER\s+"([^"]+)"', lines[i])[1]
            if cur_track.performer is not None:
                if cur_track.performer != track_performer:
                    print(f"ERROR: {file_path} has multiple entries for track {cur_track.number:02} PERFORMER and they differ", file=sys.stderr)
                else:
                    print(f"WARN: {file_path} has multiple entries for track {cur_track.number:02} PERFORMER but they match", file=sys.stderr)
                    pass
            cur_track.performer = track_performer

        elif lines[i].startswith("ISRC "):
            track_isrc = re.match(r'ISRC\s+(\w+)', lines[i])[1]
            if cur_track.isrc is not None:
                if cur_track.isrc != track_isrc:
                    print(f"ERROR: {file_path} has multiple entries for track {cur_track.number:02} ISRC and they differ", file=sys.stderr)
                else:
                    print(f"WARN: {file_path} has multiple entries for track {cur_track.number:02} ISRC but they match", file=sys.stderr)
                    pass
            cur_track.isrc = track_isrc

        elif lines[i].startswith("INDEX 00 "):
            ms = re.match(r"INDEX 00 (\d+):(\d+):(\d+)", lines[i])
            index00 = Index(file=cur_file, msf=MSF(minute=ms[1], second=ms[2], frame=ms[3]))
            if cur_track.index00 is not None:
                if cur_track.index00 != index00:
                    print(f"ERROR: {file_path} has multiple entries for track {cur_track.number:02} INDEX00 and they differ", file=sys.stderr)
                else:
                    print(f"WARN: {file_path} has multiple entries for track {cur_track.number:02} INDEX00 but they match", file=sys.stderr)
                    pass
            cur_track.index00 = index00

        elif lines[i].startswith("INDEX 01 "):
            ms = re.match(r"INDEX 01 (\d+):(\d+):(\d+)", lines[i])
            index01 = Index(file=cur_file, msf=MSF(minute=ms[1], second=ms[2], frame=ms[3]))
            if cur_track.index01 is not None:
                if cur_track.index01 != index01:
                    print(f"ERROR: {file_path} has multiple entries for track {cur_track.number:02} INDEX01 and they differ", file=sys.stderr)
                else:
                    print(f"WARN: {file_path} has multiple entries for track {cur_track.number:02} INDEX01 but they match", file=sys.stderr)
            cur_track.index01 = index01
            cur_file.main_track_number = cur_track.number

        elif any(re.match(p, lines[i]) for p in skip_line_patterns):
            pass

        else:
            print(f"WARN: Unrecognized entry in cue file \"{file_path}\" line {i+1}: {lines[i]}", file=sys.stderr)

        i += 1

    if cur_file is not None:
        files.append(cur_file)
        cur_file = None
    if cur_track is not None:
        tracks.append(cur_track)
        cur_track = None

    assert(ripper is not None)
    return Cue(
            file_path = file_path,
            lines     = lines,
            files     = files,
            ripper    = ripper,
            ripper_version=ripper_version,
            discid    = discid,
            catalog   = catalog,
            performer = performer,
            title     = title,
            tracks    = tracks,
            )
