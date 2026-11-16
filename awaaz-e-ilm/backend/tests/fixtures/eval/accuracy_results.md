# OCR Accuracy Evaluation

| Fixture | Lang | Description | Tess no-pre | Tess + pre | Easy no-pre | Easy + pre | High-contrast? |
|---------|------|-------------|-------------|------------|-------------|------------|----------------|
| `en_short` | EN | English short — pangram, 36 px | 100.0% ★ (conf 96) | 100.0% ★ (conf 96) | 97.7% ★ (conf 90) | 97.7% ★ (conf 89) | ✓ |
| `en_medium` | EN | English medium — quote, multi-line, 32 px | 100.0% ★ (conf 95) | 100.0% ★ (conf 96) | 82.8% ▲ (conf 82) | 82.8% ▲ (conf 85) | ✓ |
| `en_long` | EN | English long — paragraph, 28 px | 100.0% ★ (conf 96) | 100.0% ★ (conf 96) | 99.3% ★ (conf 84) | 99.3% ★ (conf 82) | ✓ |
| `ur_short` | UR | Urdu short — single sentence, 40 px | 100.0% ★ (conf 92) | 100.0% ★ (conf 92) | 10.7% ▼ (conf 54) | 10.7% ▼ (conf 53) | ✓ |
| `ur_medium` | UR | Urdu medium — two sentences, 36 px | 98.8% ★ (conf 88) | 98.8% ★ (conf 88) | 31.7% ▼ (conf 58) | 31.7% ▼ (conf 56) | ✓ |
| `ur_long` | UR | Urdu long — paragraph, 36 px (wider line spacing for Tesseract) | 98.8% ★ (conf 87) | 42.2% ▼ (conf 88) | 7.5% ▼ (conf 49) | 6.8% ▼ (conf 49) | ✓ |


Legend: ★ ≥90%  ▲ 70–89%  ▼ <70%  conf=Tesseract confidence (0–100)
