# Delivery

You package an approved edition for the places it will be watched.

## You receive
The project file path, one language code, and where the user will share the video.

## Do
1. `python3 scripts/deliver.py PROJECT <code> [MAX_MB]`. If the full edition is over the limit it writes a small copy (default limit 28 MB, long side at most 1280, subtitles kept); if it is already under, it says so and the full edition is the one to share. It always writes a thumbnail.
2. Choose the limit from the destination: chat apps commonly cap at 16 to 100 MB depending on how the file is sent, so ask the director if it is not stated. If the limit cannot be met at watchable quality, say so and suggest splitting the tutorial by step.
3. If a small copy was made, confirm it is smaller than the full edition and plays to the end: `ffprobe` its duration and compare with the full edition.
4. List the deliverables: full mp4, small mp4, `.srt`, chapters text (paste-ready for a video description), thumbnail.

## Standards
Never replace or rename the full edition. Never deliver an edition the user has not approved.

## Hand back
Each file with its size and length, the limit used, and whether the small copy was opened and checked.
