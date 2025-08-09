# Iteratie 6: Google Text-to-Speech API Integration - Micro Steps

## Voorbereiding voor LLM Agent

### Step 0: Context Setup
**Prompt voor LLM:**
```
Je gaat Iteratie 6 implementeren: integratie van Google Cloud Text-to-Speech API.

HUIDIGE STATUS NA ITERATIE 5:
- ✅ Real STT → Real Translation → Mock TTS pipeline
- ✅ All resilience patterns working
- ✅ Health checks for STT and Translation

GOAL: Replace `mock_text_to_speech` with `real_text_to_speech` using Google Cloud TTS API

KEY CONSIDERATIONS:
- TTS returns binary audio data (different from text-based APIs)
- Need proper audio format configuration (MP3/WAV/LINEAR16)
- Audio encoding/sample rate must match client expectations
- Larger response payloads than STT/Translation
```

---

## Micro-Iteratie 6A: Test-First Development  

### Step 6A.1: Create Test for Real TTS
**Prompt voor LLM:**
```
MICRO-STEP 6A.1: Create failing test for real TTS API

Create: `tests/test_real_tts_integration.py`

REQUIREMENTS:
1. Test function: `test_real_tts_with_english_text()`
2. Skip test if no credentials
3. Call real_text_to_speech("hello world") directly  
4. Assert result is bytes, not empty, reasonable size (>1000 bytes)
5. Optionally validate audio format headers

EXAMPLE STRUCTURE:
```python
def test_real_tts_with_english_text():
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    result = await real_text_to_speech("hello world")
    
    # Basic validations
    assert isinstance(result, bytes)
    assert len(result) > 1000  # Audio should be substantial
    assert len(result) < 1000000  # But not unreasonably large
    
    # Optional: Check for MP3 header if using MP3 format
    # assert result[:3] == b'ID3' or result[:2] == b'\xff\xfb'
```

Run test to confirm failure, then proceed.
```

### Step 6A.2: Add TTS Dependencies
**Prompt voor LLM:**
```
MICRO-STEP 6A.2: Add Google TTS API dependency

Add to pyproject.toml:
```toml
google-cloud-texttospeech = "^2.16.0"
```

Run: `poetry install`

Verify:
```python
from google.cloud import texttospeech
print("✅ TTS library installed")
```
```

---

## Micro-Iteratie 6B: Implementation

### Step 6B.1: Create Real TTS Function
**Prompt voor LLM:**
```
MICRO-STEP 6B.1: Implement real_text_to_speech function

Add to services.py:

REQUIREMENTS:
1. Function: `async def real_text_to_speech(text: str) -> bytes`
2. Use Google Cloud TTS API
3. Configure voice (language: en-US, name: en-US-Wavenet-D)
4. Audio format: MP3 (good compression for web)
5. Include retry logic and error handling
6. Environment configuration for voice/format
7. Proper logging

VOICE CONSIDERATIONS:
- Wavenet voices: higher quality, more expensive
- Standard voices: good quality, cheaper
- Gender options: MALE, FEMALE, NEUTRAL

AUDIO FORMATS:
- MP3: Good compression, web-friendly
- LINEAR16: Uncompressed, larger files
- OGG_OPUS: Good compression, modern browsers

EXAMPLE CONFIG:
```python
# TTS configuratie
TTS_LANGUAGE_CODE: str = "en-US"
TTS_VOICE_NAME: str = "en-US-Wavenet-D"  
TTS_VOICE_GENDER: str = "NEUTRAL"
TTS_AUDIO_FORMAT: str = "MP3"
TTS_TIMEOUT_S: float = 15.0
```
```

### Step 6B.2: Update Config for TTS
**Prompt voor LLM:**
```
MICRO-STEP 6B.2: Add TTS config to config.py

Add to AppSettings class:

```python
# Text-to-Speech configuratie
TTS_LANGUAGE_CODE: str = "en-US"
TTS_VOICE_NAME: str = "en-US-Wavenet-D"
TTS_VOICE_GENDER: str = "NEUTRAL"  # MALE, FEMALE, NEUTRAL
TTS_AUDIO_FORMAT: str = "MP3"      # MP3, LINEAR16, OGG_OPUS
TTS_TIMEOUT_S: float = 15.0
```

Verify:
```python
from gcp_speech_to_speech_translation.config import settings
print(f"TTS Voice: {settings.TTS_VOICE_NAME}")
print(f"TTS Format: {settings.TTS_AUDIO_FORMAT}")
```
```

---

## Micro-Iteratie 6C: Integration & Testing

### Step 6C.1: Replace Mock in Pipeline
**Prompt voor LLM:**
```
MICRO-STEP 6C.1: Replace mock_text_to_speech in main.py

UPDATE imports:
```python
from .services import (
    real_speech_to_text,
    real_translation,
    real_text_to_speech,  # ← CHANGE THIS
)
```

UPDATE process_pipeline function:
```python
async def process_pipeline(audio_chunk: bytes) -> bytes:
    text_result = await real_speech_to_text(audio_chunk)
    translation_result = await real_translation(text_result)
    output_audio = await real_text_to_speech(translation_result)  # ← CHANGE THIS
    return output_audio
```

COMPLETE PIPELINE NOW: Real STT → Real Translation → Real TTS ✅
```

### Step 6C.2: Test Integration & Performance
**Prompt voor LLM:**
```
MICRO-STEP 6C.2: Comprehensive testing

1. Test TTS specifically:
```bash
poetry run pytest tests/test_real_tts_integration.py -v
```

2. Test full pipeline with all real APIs:
```bash
poetry run pytest tests/test_real_stt_integration.py -v
```

3. Performance test - check total latency:
```bash
poetry run pytest tests/test_iteration3_comprehensive.py::TestHappyPath::test_successful_pipeline -v -s
```

4. Manual end-to-end test:
```bash
poetry run python -c "
import asyncio
from gcp_speech_to_speech_translation.services import real_speech_to_text, real_translation, real_text_to_speech

async def test_full_pipeline():
    # Use dummy audio bytes for testing
    audio_in = b'\\x00' * 1000  # Will likely fail STT, but tests TTS
    try:
        text = await real_speech_to_text(audio_in)
        translation = await real_translation('hallo wereld')
        audio_out = await real_text_to_speech(translation)
        print(f'Success! Audio output: {len(audio_out)} bytes')
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(test_full_pipeline())
"
```

PERFORMANCE EXPECTATIONS:
- Total pipeline latency: 2-5 seconds (depending on text length)
- TTS latency: 1-3 seconds (text-dependent)
- Audio output: 5-50KB for typical phrases
```

---

## Micro-Iteratie 6D: Health Check & Optimization

### Step 6D.1: Add TTS Health Check
**Prompt voor LLM:**
```
MICRO-STEP 6D.1: Add TTS health check endpoint

Add to main.py:

```python
@app.get("/health/tts")
async def health_tts():
    """Health check endpoint for Google Cloud Text-to-Speech service."""
    try:
        # Quick TTS test with minimal text
        test_audio = await real_text_to_speech("test")
        
        return {
            "status": "ok",
            "tts_client": "connected", 
            "test_audio_size": len(test_audio),
            "voice": f"{settings.TTS_VOICE_NAME}",
            "format": settings.TTS_AUDIO_FORMAT
        }
    except Exception as e:
        return {
            "status": "error",
            "tts_client": "disconnected",
            "error": str(e)
        }

@app.get("/health/full")
async def health_full_pipeline():
    """Health check for the complete pipeline."""
    try:
        # Test minimal pipeline
        dummy_text = "hello"
        audio_result = await real_text_to_speech(dummy_text)
        
        return {
            "status": "ok",
            "pipeline": "stt+translation+tts",
            "components": {
                "speech_to_text": "connected",
                "translation": "connected", 
                "text_to_speech": "connected"
            },
            "test_audio_size": len(audio_result)
        }
    except Exception as e:
        return {
            "status": "error",
            "pipeline": "degraded",
            "error": str(e)
        }
```

Test endpoints:
```bash
curl http://localhost:8000/health/tts
curl http://localhost:8000/health/full
```
```

### Step 6D.2: Performance Optimization
**Prompt voor LLM:**
```
MICRO-STEP 6D.2: Optimize for production readiness

OPTIMIZATIONS TO CONSIDER:

1. **Client Connection Pooling** (add to real_text_to_speech):
```python
# Initialize client once, reuse connections
_tts_client = None

def get_tts_client():
    global _tts_client
    if _tts_client is None:
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client
```

2. **Response Size Monitoring** (add logging):
```python
# Log audio size for monitoring
audio_size_kb = len(audio_content) / 1024
logging.info(f"TTS: Generated {audio_size_kb:.1f}KB audio for {len(text)} chars")
```

3. **Format Configuration** (environment-based):
```python
# Allow format switching via environment
audio_format = getattr(texttospeech.AudioEncoding, settings.TTS_AUDIO_FORMAT)
```

4. **Timeout Tuning** (adjust for text length):
```python
# Dynamic timeout based on text length
estimated_duration = max(5.0, len(text) * 0.1)  # 100ms per character
timeout = min(estimated_duration, settings.TTS_TIMEOUT_S)
```

PERFORMANCE TARGETS:
- TTS latency: <2s for sentences <100 chars
- Audio compression: MP3 ~10KB for 10-word sentences
- Memory efficiency: Stream large audio responses
```

---

## Error Scenarios & Troubleshooting

### Common Issues for Iteratie 6
**Prompt voor LLM indien problemen:**
```
TROUBLESHOOTING GUIDE voor Iteratie 6:

IF: "Audio format not supported" error
SOLUTION: Check TTS_AUDIO_FORMAT setting, use MP3/LINEAR16/OGG_OPUS

IF: "Voice not found" error  
SOLUTION: Verify TTS_VOICE_NAME exists in selected language
LIST VOICES: `gcloud ml speech voices list --filter="languageCode:en-US"`

IF: Large audio files (>1MB)
SOLUTION: Check text length, consider audio format compression, add size limits

IF: TTS quota exceeded
SOLUTION: Monitor usage, implement caching for repeated phrases, use Standard voices

IF: Audio playback issues in browser
SOLUTION: Ensure MP3 format, check CORS headers, validate audio encoding

DEBUG COMMANDS:
```bash
# Test TTS directly
poetry run python -c "
import asyncio
from gcp_speech_to_speech_translation.services import real_text_to_speech
audio = asyncio.run(real_text_to_speech('hello world'))
print(f'Audio size: {len(audio)} bytes')
with open('test_output.mp3', 'wb') as f:
    f.write(audio)
print('Saved to test_output.mp3')
"

# Check available voices
gcloud ml speech voices list --filter="languageCode:en-US" --limit=10
```
```

---

## Success Criteria for Iteratie 6

✅ **Checklist:**
- [ ] Google Cloud TTS dependency installed
- [ ] real_text_to_speech function with proper audio config
- [ ] TTS configuration added (voice, format, timeout)
- [ ] Mock replaced in main pipeline  
- [ ] TTS-specific test passes
- [ ] Full pipeline test passes (STT→Translation→TTS)
- [ ] Health check endpoints working
- [ ] Performance within acceptable ranges

✅ **Performance Targets:**
- TTS latency: <3s for typical phrases (10-20 words)
- Audio size: 5-50KB for sentences 
- Total pipeline: <6s end-to-end
- Memory usage: No significant increase

✅ **Quality Gates:**
- All tests pass (including existing ones)
- Audio output playable in browsers
- Proper error handling and fallbacks
- Health endpoints return valid status
- No performance regression

---

## Post-Completion: Ready for Iteratie 7

After successful completion of Iteratie 6:

🎯 **ACHIEVEMENT:** Complete Real-Time Translation Pipeline
- ✅ Real Speech-to-Text (Dutch audio → Dutch text)
- ✅ Real Translation (Dutch text → English text)  
- ✅ Real Text-to-Speech (English text → English audio)

🚀 **NEXT:** Iteratie 7 - Broadcasting to Multiple Listeners
- Transform from 1-on-1 to 1-to-many architecture
- Implement ConnectionManager for WebSocket broadcasting
- Add stream_id concept for multiple concurrent streams
