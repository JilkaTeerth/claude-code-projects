# Wardrobe catalogue

Claude Code used on a non code, life admin problem.

48 photos of my clothes went through a pipeline: delete HEIC duplicates, identify each garment's type and brand with vision, sort into 8 typed folders, rename each file by brand, and write `INVENTORY.md` plus a CSV manifest.

The pattern is reusable for any physical collection (books, squash gear, tech). I give the expected file count up front as a checksum and Claude reports the real number against it.

## What's in `src/`

`INVENTORY.md`. Photos are left out.
