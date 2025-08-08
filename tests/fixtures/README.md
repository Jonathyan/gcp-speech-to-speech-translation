# Test Audio Fixtures

Deze directory bevat audio bestanden voor testing.

## Benodigde bestanden:
- `hallo_wereld.wav` - Nederlandse test audio voor STT testing

## Audio bestanden genereren:
```bash
# Gebruik macOS say command om test audio te maken
say -v "Xander" -o tests/fixtures/hallo_wereld.wav "Hallo wereld, dit is een test"
```

**Note:** Audio bestanden worden niet in git opgeslagen vanwege grootte.