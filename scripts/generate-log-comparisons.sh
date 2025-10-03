#!/usr/bin/env bash

# TODO: Maybe make the following steps more sophisticated. Currently we just
# assume everything under logs/ is a directory with a log+cue, only one
# directory deep, etc. The search could be smarter and we could issue some sort
# of warning if a directory doesn't have at least 1 cue and log.

for d in logs/*; do
    if [ -e "$d"/eac.log ]; then
        ./scripts/compare_log.py "$d"/cyanrip.log "$d"/eac.log > "$d"/cyanrip_vs_eac_log.txt
    fi
    if [ -e "$d"/xld.log ]; then
        ./scripts/compare_log.py "$d"/cyanrip.log "$d"/xld.log > "$d"/cyanrip_vs_xld_log.txt
    fi
done
