# Voice Commands Reference

This document lists all supported voice commands for Awaaz-e-Ilm.
Commands work in English, Urdu (native script), and Roman Urdu.

## Navigation Commands

| Intent | English | Urdu | Roman Urdu |
|--------|---------|------|------------|
| Go to chapter N | "Go to chapter 5" / "Open chapter five" | "باب پانچ پر جاؤ" | "Chapter paanch par jao" |
| Next chapter | "Next chapter" | "اگلا باب" | "Agla baab" |
| Previous chapter | "Previous chapter" / "Go back" | "پچھلا باب" | "Pichla baab" |

## Playback Control Commands

| Intent | English | Urdu | Roman Urdu |
|--------|---------|------|------------|
| Play | "Play" / "Resume" / "Start" | "چلاؤ" / "شروع کرو" | "Chalao" / "Shuru karo" |
| Pause | "Pause" / "Stop" | "رکو" / "بند کرو" | "Ruko" / "Band karo" |
| Repeat | "Repeat" / "Again" | "دوبارہ" | "Dobara" |
| Seek forward N seconds | "Forward thirty seconds" / "Skip 30 seconds" | "30 سیکنڈ آگے" | "Tees second aage" |
| Seek backward N seconds | "Back thirty seconds" / "Rewind 30 seconds" | "30 سیکنڈ پیچھے" | "Tees second peeche" |

## Speed Control Commands

| Intent | English | Urdu | Roman Urdu |
|--------|---------|------|------------|
| Set speed | "Speed 1.5x" / "Set speed to two" | "رفتار ڈیڑھ" | "Speed dairh" |
| Faster | "Faster" | "تیز" | "Tez" |
| Slower | "Slower" | "آہستہ" | "Aahista" |
| Normal speed | "Normal speed" | "معمول کی رفتار" | "Mamool ki raftar" |

## Language Commands

| Intent | English | Urdu | Roman Urdu |
|--------|---------|------|------------|
| Switch to English | "Read in English" / "Switch to English" | "انگریزی میں پڑھو" | "Angrezi mein parho" |
| Switch to Urdu | "Read in Urdu" / "Switch to Urdu" | "اردو میں پڑھو" | "Urdu mein parho" |

## System Commands

| Intent | English | Urdu | Roman Urdu |
|--------|---------|------|------------|
| Help | "Help" / "Commands" | "مدد" | "Madad" |

## Keyboard Shortcuts (alternative to voice)

| Key | Action |
|-----|--------|
| **Space** (hold) | Push-to-talk |
| **K** | Play / Pause |
| **J** | Back 30 seconds |
| **L** | Forward 30 seconds |
| **N** | Next chapter |
| **P** | Previous chapter |
| **?** | Show help |

## Notes on Urdu ASR Accuracy

Whisper's Urdu accuracy depends on the model size:
- `tiny` / `base`: Low accuracy for Urdu
- `small`: Acceptable for common commands
- `medium` / `large`: Recommended for Urdu

For best results, speak clearly and use the constrained grammar patterns shown above.
