"""filmlab — the look authoring and reference pipeline for filmcam.

Two jobs:
  1. Generate original 3D LUTs and `looks.json` for the iOS app to consume.
  2. Mirror the whole render pipeline in numpy, so looks can be designed and
     reviewed on the Mac and so the Swift graph has an oracle to check against.
"""
