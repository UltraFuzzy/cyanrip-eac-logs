import re
import codecs
from dataclasses import dataclass, field
from typing import List, Literal, Optional
from types import SimpleNamespace

# EAC log and cue files use old Windows encodings.
import chardet


@dataclass
class Track:
    number: int
    cd_start_sector: int
    cd_end_sector:   int
    pregap_duration: Optional[float]
    peak:            str
    eac_crc32:       str
    accurate_rip_v1: Optional[str]
    accurate_rip_v2: Optional[str]


@dataclass
class Log:
    file_path:      str
    ripper:         Literal['EAC', 'XLD', 'cyanrip']
    ripper_version: str
    drive:          Optional[str]
    read_offset:    int
    tracks:         List[Track]


def parse_log_eac(file_path):
    # Exact Audio Copy V1.8 from 15. July 2024
    # [...]
    # Used drive  : HL-DT-STBD-RE BU40N   Adapter: 1  ID: 1
    # [...]
    # Read offset correction                      : 6
    # [...]
    # TOC of the extracted CD
    #
    #      Track |   Start  |  Length  | Start sector | End sector 
    #     ---------------------------------------------------------
    #         1  |  0:00.00 |  4:07.29 |         0    |    18553   
    #         2  |  4:07.29 |  3:41.26 |     18554    |    35154   
    #         3  |  7:48.55 |  3:48.26 |     35155    |    52280   
    #         4  | 11:37.06 |  3:12.72 |     52281    |    66752   
    #         5  | 14:50.03 |  3:28.40 |     66753    |    82392   
    #         6  | 18:18.43 |  4:14.34 |     82393    |   101476   
    #         7  | 22:33.02 |  1:00.72 |    101477    |   106048   
    #         8  | 23:33.74 |  4:01.64 |    106049    |   124187   
    #         9  | 27:35.63 |  3:23.02 |    124188    |   139414   
    #        10  | 30:58.65 |  2:32.50 |    139415    |   150864   
    #        11  | 33:31.40 |  3:43.07 |    150865    |   167596   
    #        12  | 37:14.47 |  0:49.24 |    167597    |   171295   
    #        13  | 38:03.71 |  7:16.11 |    171296    |   204006   
    # [...]
    # Track  1
    # [...]
    #      Pre-gap length  0:00:02.00
    # [...]
    #      Peak level 96.6 %
    #      Copy CRC 64960678
    file_bytes = open(file_path, 'rb').read()
    encoding = chardet.detect(file_bytes)['encoding']
    lines = codecs.decode(file_bytes, encoding).splitlines()

    ms = re.match("\uFEFF?" + r"Exact Audio Copy (V([\d\.]+)\s+from\s+(\d+\.?\s+[A-Za-z]+\s+\d+))", lines[0])
    if not ms:
        raise ValueError
    version_full_str = ms[1]
    # version_num_str  = ms[2]
    # version_date_str = ms[3]
    ripper = "EAC"
    ripper_version = version_full_str

    i = 1
    while not re.match(r"Used\s+drive\s+:", lines[i]):
        i += 1
    drive = re.match(r"Used\s+drive\s+:\s+(.*\S)\s+Adapter", lines[i])[1]
    while not re.match(r"Read offset correction\s+:", lines[i]):
        i += 1
    read_offset = int(re.match(r"Read offset correction\s+:\s+([+-]?\d+)", lines[i])[1])

    track_sectors = []
    while not lines[i].startswith("TOC of the extracted CD"):
        i += 1
    while not re.match(r"\s+\d+\s+\|", lines[i]):
        i += 1
    while re.match(r"\s+\d+\s+\|", lines[i]):
        ms = re.match(r"\s+(\d+)\s+\|\s+[\d:\.]+\s+\|\s+[\d:\.]+\s+\|\s+(\d+)\s+\|\s+(\d+)", lines[i])
        track_number = int(ms[1])
        track_cd_start_sector = ms[2]
        track_cd_end_sector = ms[3]
        track_sectors.append((track_number, track_cd_start_sector, track_cd_end_sector))
        i += 1

    tracks = []
    while True:
        while not re.match(r"Track\s+\d+", lines[i]):
            i += 1
            if i == len(lines):
                break
        if i == len(lines):
            break
        track_number = int(re.match(r"Track\s+(\d+)", lines[i])[1])
        while not re.match(r"\s+Pre-gap\s+length", lines[i]) and not re.match(r"\s+Peak\s+level", lines[i]):
            i += 1
        if not re.match(r"\s+Pre-gap\s+length", lines[i]):
            track_pregap_duration = 0.0
        else:
            ms = re.match(r"\s+Pre-gap\s+length\s+(\d+):(\d+):(\d+\.\d*)", lines[i])
            track_pregap_duration = 3600*float(ms[1]) + 60*float(ms[2]) + float(ms[3])
            # track_pregap_duration = math.floor(1000*track_pregap_duration)/1000
        while not re.match(r"\s+Peak\s+level", lines[i]):
            i += 1
        track_peak = re.match(r"\s+Peak\s+level\s+(\d+\.\d+)", lines[i])[1]
        while not re.match(r"\s+Copy\s+CRC", lines[i]):
            i += 1
        track_eac_crc32 = re.match(r"\s+Copy\s+CRC\s+(\w+)", lines[i])[1]

        _, track_cd_start_sector, track_cd_end_sector = next(ts for ts in track_sectors if ts[0] == track_number)
        tracks.append(Track(
            number = track_number,
            cd_start_sector = track_cd_start_sector,
            cd_end_sector = track_cd_end_sector,
            pregap_duration = track_pregap_duration,
            peak = track_peak,
            eac_crc32 = track_eac_crc32,
            accurate_rip_v1 = None,
            accurate_rip_v2 = None,
            ))

    return Log(
            file_path      = file_path,
            ripper         = ripper,
            ripper_version = ripper_version,
            read_offset    = read_offset,
            drive          = drive,
            tracks         = tracks,
        )


def parse_log_xld(file_path):
    # X Lossless Decoder version 20250302 (157.2)
    # [...]
    # Used drive : HL-DT-ST BD-RE BU40N (revision 1.00)
    # [...]
    # Read offset correction  : 6
    # [...]
    # TOC of the extracted CD
    #      Track |   Start  |  Length  | Start sector | End sector 
    #     ---------------------------------------------------------
    #         1  | 00:00:00 | 04:07:29 |         0    |    18553   
    #         2  | 04:07:29 | 03:41:26 |     18554    |    35154   
    #         3  | 07:48:55 | 03:48:26 |     35155    |    52280   
    #         4  | 11:37:06 | 03:12:72 |     52281    |    66752   
    #         5  | 14:50:03 | 03:28:40 |     66753    |    82392   
    #         6  | 18:18:43 | 04:14:34 |     82393    |   101476   
    #         7  | 22:33:02 | 01:00:72 |    101477    |   106048   
    #         8  | 23:33:74 | 04:01:64 |    106049    |   124187   
    #         9  | 27:35:63 | 03:23:02 |    124188    |   139414   
    #        10  | 30:58:65 | 02:32:50 |    139415    |   150864   
    #        11  | 33:31:40 | 03:43:07 |    150865    |   167596   
    #        12  | 37:14:47 | 00:49:24 |    167597    |   171295   
    #        13  | 38:03:71 | 07:16:11 |    171296    |   204006   
    # [...]
    # Track 01
    #     Filename : /private/tmp/xld/Hope is a Cult/Track 01.flac
    #     Pre-gap length : 00:02:00
    # [...]
    #     Peak                     : 0.965973
    #     CRC32 hash               : 64960678
    # [...]
    #     AccurateRip v1 signature : A4C817F9
    #     AccurateRip v2 signature : 8BD95123
    file_bytes = open(file_path, 'rb').read()
    encoding = chardet.detect(file_bytes)['encoding']
    lines = codecs.decode(file_bytes, encoding).splitlines()

    ms = re.match(r"X Lossless Decoder version ((\d+)\s+\((.+)\))", lines[0])
    if not ms:
        raise ValueError
    version_full_str = ms[1]
    # version_num_str  = ms[2]
    # version_date_str = ms[3]
    ripper = "XLD"
    ripper_version = version_full_str

    i = 1
    while not re.match(r"Used\s+drive\s+:", lines[i]):
        i += 1
    drive = re.match(r"Used\s+drive\s+:\s+(.*\S)\s+\(revision", lines[i])[1]
    while not re.match(r"Read offset correction\s+:", lines[i]):
        i += 1
    read_offset = int(re.match(r"Read offset correction\s+:\s+([+-]?\d+)", lines[i])[1])

    track_sectors = []
    while not lines[i].startswith("TOC of the extracted CD"):
        i += 1
    while not re.match(r"\s+\d+\s+\|", lines[i]):
        i += 1
    while re.match(r"\s+\d+\s+\|", lines[i]):
        ms = re.match(r"\s+(\d+)\s+\|\s+[\d:\.]+\s+\|\s+[\d:\.]+\s+\|\s+(\d+)\s+\|\s+(\d+)", lines[i])
        track_number = int(ms[1])
        track_cd_start_sector = ms[2]
        track_cd_end_sector = ms[3]
        track_sectors.append((track_number, track_cd_start_sector, track_cd_end_sector))
        i += 1

    tracks = []
    while True:
        while not re.match(r"Track\s+\d+", lines[i]):
            i += 1
            if i == len(lines):
                break
        if i == len(lines):
            break
        track_number = int(re.match(r"Track\s+(\d+)", lines[i])[1])
        while not re.match(r"\s+Pre-gap\s+length\s+:", lines[i]) and not re.match(r"\s+Peak\s+:", lines[i]):
            i += 1
        if not re.match(r"\s+Pre-gap\s+length\s+:", lines[i]):
            track_pregap_duration = 0.0
        else:
            ms = re.match(r"\s+Pre-gap\s+length\s+:\s+(\d+):(\d+):(\d+)", lines[i])
            # XLD reports duration in mm:ss with hundreths of seconds following last colon.
            track_pregap_duration = 60*float(ms[1]) + float(ms[2]) + float(ms[3])/100.0
            # track_pregap_duration = math.floor(1000*track_pregap_duration)/1000
        while not re.match(r"\s+Peak\s+:", lines[i]):
            i += 1
        track_peak = re.match(r"\s+Peak\s+:\s+(\d+\.\d+)", lines[i])[1]
        while not re.match(r"\s+CRC32\s+hash\s+:", lines[i]):
            i += 1
        track_eac_crc32 = re.match(r"\s+CRC32\s+hash\s+:\s+(\w+)", lines[i])[1]
        while not re.match(r"\s+AccurateRip\s+v1", lines[i]):
            i += 1
        track_accurate_rip_v1 = re.match(r"\s+AccurateRip\s+v1\s+signature\s+:\s+(\w+)", lines[i])[1]
        while not re.match(r"\s+AccurateRip\s+v2", lines[i]):
            i += 1
        track_accurate_rip_v2 = re.match(r"\s+AccurateRip\s+v2\s+signature\s+:\s+(\w+)", lines[i])[1]

        _, track_cd_start_sector, track_cd_end_sector = next(ts for ts in track_sectors if ts[0] == track_number)
        tracks.append(Track(
            number = track_number,
            cd_start_sector = track_cd_start_sector,
            cd_end_sector = track_cd_end_sector,
            pregap_duration = track_pregap_duration,
            peak = track_peak,
            eac_crc32 = track_eac_crc32,
            accurate_rip_v1 = track_accurate_rip_v1,
            accurate_rip_v2 = track_accurate_rip_v2,
            ))

    return Log(
            file_path      = file_path,
            ripper         = ripper,
            ripper_version = ripper_version,
            read_offset    = read_offset,
            drive          = drive,
            tracks         = tracks
        )


def parse_log_cyanrip(file_path):
    # cyanrip 0.9.3.1-uf0.5 (c194065)
    # Drive used:     HL-DT-ST BD-RE BU40N (revision 1.00)
    # [...]
    # Offset:         +6 samples
    # [...]
    # Tracks:
    # Track 1 ripped and encoded successfully!
    # [...]
    #   Sample peak relative amplitude (precise):
    #     Peak:        0.965973
    #   Sample peak relative amplitude (precise):
    #     Peak:        0.965973
    # [...]
    #     Pregap LSN:  0 (duration: 00:00:00.000)
    #     Start LSN:   0
    #     End LSN:     18553 (with offset: 18554)
    # [...]
    #   EAC CRC32:     64960678
    #   Accurip:       not found
    #     Accurip v1:  A4C817F9
    #     Accurip v2:  8BD95123
    file_bytes = open(file_path, 'rb').read()
    encoding = chardet.detect(file_bytes)['encoding']
    lines = codecs.decode(file_bytes, encoding).splitlines()

    ms = re.match(r"cyanrip\s+(([\w\.-]+)\s+\((\w+)\))", lines[0])
    if not ms:
        raise ValueError
    version_full_str   = ms[1]
    # version_num_str    = ms[2]
    # version_commit_str = ms[3]
    ripper = "cyanrip"
    ripper_version = version_full_str

    i = 1
    # "Drive used:" not present in logs from old cyanrip versions
    while not lines[i].startswith("Drive used:") and not lines[i].startswith("Offset:"):
        i += 1
    if not lines[i].startswith("Drive used:"):
        drive = None
    else:
        drive = re.match(r"Drive used:\s+(\S.*\S)\s+\(revision", lines[i])[1]

    while not lines[i].startswith("Offset:"):
        i += 1
    read_offset = int(re.match(r"Offset:\s+([+-]?\d+)", lines[i])[1])

    tracks = []
    while i < len(lines):
        while not re.match(r"Track\s+\d+", lines[i]):
            i += 1
            if i == len(lines):
                break
        if i == len(lines):
            break
        track_number = int(re.match(r"Track\s(\d+)", lines[i])[1])

        j = i
        while i < len(lines) and not re.match(r"\s+Sample peak relative amplitude \(precise\):", lines[i]):
            i += 1
        if i == len(lines):
            i = j
            track_peak = None
        else:
            i += 1
            track_peak = re.match(r"\s+Peak:\s+(\d+\.\d+)", lines[i])[1]

        while not re.match(r"\s+Pregap\s+LSN:", lines[i]):
            i += 1
        # cyanrip reports duration in hh:mm:ss with thousandths of seconds following decimal point
        if re.match(r"\s+Pregap\s+LSN:\s+none", lines[i]):
            track_pregap_duration = None
        else:
            ms = re.match(r"\s+Pregap\s+LSN:\s+-?\d+\s+\(duration:\s+([0-9]+):(\d+):(\d+\.\d*)\)", lines[i])
            track_pregap_duration = 3600*float(ms[1]) + 60*float(ms[2]) + float(ms[3])

        while not re.match(r"\s+Start\s+LSN:", lines[i]):
            i += 1
        track_cd_start_sector = re.match(r"\s+Start\s+LSN:\s+(\d+)", lines[i])[1]

        while not re.match(r"\s+End\s+LSN:", lines[i]):
            i += 1
        track_cd_end_sector = re.match(r"\s+End\s+LSN:\s+(\d+)", lines[i])[1]

        while not re.match(r"\s+EAC\s+CRC32:", lines[i]):
            i += 1
        track_eac_crc32 = re.match(r"\s+EAC\s+CRC32:\s+(\w+)" , lines[i])[1]

        while not re.match(r"\s+Accurip\s+v1:", lines[i]):
            i += 1
        track_accurate_rip_v1 = re.match(r"\s+Accurip\s+v1:\s+(\w+)", lines[i])[1]

        while not re.match(r"\s+Accurip\s+v2:", lines[i]):
            i += 1
        track_accurate_rip_v2 = re.match(r"\s+Accurip\s+v2:\s+(\w+)", lines[i])[1]

        tracks.append(Track(
            number = track_number,
            cd_start_sector = track_cd_start_sector,
            cd_end_sector = track_cd_end_sector,
            pregap_duration = track_pregap_duration,
            peak = track_peak,
            eac_crc32 = track_eac_crc32,
            accurate_rip_v1 = track_accurate_rip_v1,
            accurate_rip_v2 = track_accurate_rip_v2,
            ))

    return Log(
            file_path      = file_path,
            ripper         = ripper,
            ripper_version = ripper_version,
            read_offset    = read_offset,
            drive          = drive,
            tracks         = tracks,
        )


def parse_log(file_path):
    for parse_fn in (parse_log_eac, parse_log_xld, parse_log_cyanrip):
        try:
            return parse_fn(file_path)
        except ValueError:
            pass
        # any other exception type is likely due to errors in this script
        # itself so don't attempt to catch or handle them
    raise ValueError(f'Unable to parse log file "{file_path}"')
