#!/usr/bin/env bash

# TODO: same comment as generate-log-comparisons.sh

for d in logs/*; do
    if [ -e "$d"/eac.cue ]; then
        ./scripts/compare_cue.py "$d"/cyanrip.cue "$d"/eac.cue > "$d"/cyanrip_vs_eac_cue.txt
    fi
    if [ -e "$d"/xld.cue ]; then
        ./scripts/compare_cue.py "$d"/cyanrip.cue "$d"/xld.cue > "$d"/cyanrip_vs_xld_cue.txt
    fi
done
