#!/usr/bin/env bash
# Build the IRR demo video from rendered frames + narration segments.
# Reproducible: python3 render.py && bash build.sh
set -euo pipefail
cd "$(dirname "$0")"
ROOT=..
FRAMES=frames
AUDIO=$ROOT/audio
OUT=$ROOT/dist
mkdir -p "$OUT" tmp
python3 render.py >/dev/null

# Measured narration durations (ffprobe) — recomputed here, never assumed.
declare -A DUR
for s in s1 s2 s3 s4 s5; do
  DUR[$s]=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$AUDIO/$s.mp3")
done
PAD=0.30
declare -A SCENE
for s in s1 s2 s3 s4 s5; do
  SCENE[$s]=$(python3 -c "print(f'{float(\"${DUR[$s]}\") + $PAD:.3f}')")
done
echo "scene durations: s1=${SCENE[s1]} s2=${SCENE[s2]} s3=${SCENE[s3]} s4=${SCENE[s4]} s5=${SCENE[s5]}"

# State weights per scene (fractions of scene duration)
declare -A WEIGHTS=( [s1]="0.45 0.55" [s2]="0.30 0.35 0.35" [s3]="0.30 0.35 0.35" [s4]="0.30 0.35 0.35" [s5]="1.0" )

for s in s1 s2 s3 s4 s5; do
  manifest=$(python3 -c "import json;print(' '.join(json.load(open('$FRAMES/manifest.json'))['$s']))")
  list=tmp/$s.txt; : > "$list"
  python3 - <<PY >> "$list"
import sys
scene=float("${SCENE[$s]}")
weights=[float(x) for x in "${WEIGHTS[$s]}".split()]
files="$manifest".split()
for f,w in zip(files,weights):
    print(f"file '../frames/{f}'")
    print(f"duration {scene*w:.3f}")
print(f"file '../frames/{files[-1]}'")
PY
  ffmpeg -v error -y -f concat -safe 0 -i "$list" -i "$AUDIO/$s.mp3" \
    -filter_complex "[0:v]fps=30,format=yuv420p,fade=t=in:st=0:d=0.25,fade=t=out:st=$(python3 -c "print(f'{float(\"${SCENE[$s]}\")-0.25:.3f}')"):d=0.25[v];[1:a]apad,atrim=0:${SCENE[$s]}[a]" \
    -map "[v]" -map "[a]" -c:v libx264 -crf 20 -preset medium -c:a aac -b:a 128k -t "${SCENE[$s]}" "tmp/$s.mp4"
done

# Concatenate scenes
: > tmp/all.txt
for s in s1 s2 s3 s4 s5; do echo "file '$s.mp4'" >> tmp/all.txt; done
ffmpeg -v error -y -f concat -safe 0 -i tmp/all.txt -c:v libx264 -crf 21 -preset medium -c:a aac -b:a 128k -movflags +faststart "$OUT/irr-demo.mp4"

# 15-second silent preview (no audio track)
: > tmp/preview.txt
python3 - <<'PY' >> tmp/preview.txt
for f, dur in [("s1_b.png", 4.0), ("s2_c.png", 4.0), ("s3_c.png", 4.0), ("s5_a.png", 3.0)]:
    print(f"file '../frames/{f}'")
    print(f"duration {dur}")
print("file '../frames/s5_a.png'")
PY
ffmpeg -v error -y -f concat -safe 0 -i tmp/preview.txt -an -vf "fps=30,format=yuv420p" -c:v libx264 -crf 24 -preset medium -movflags +faststart -t 15 "$OUT/irr-preview-15s.mp4"

cp frames/poster.png "$OUT/poster.png"
echo "built:"; ls -la "$OUT"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/irr-demo.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/irr-preview-15s.mp4"
