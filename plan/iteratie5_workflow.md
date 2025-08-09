# Iteratie 5: Google Translation API Integration - Micro Steps

## Voorbereiding voor LLM Agent

### Step 0: Context Setup
**Prompt voor LLM:**
```
Je gaat Iteratie 5 implementeren: integratie van Google Cloud Translation API.

HUIDIGE STATUS:
- ✅ Iteratie 1-4 voltooid
- ✅ STT werkt met Google Cloud Speech API 
- ✅ Mock Translation en TTS nog actief
- ✅ Resilience patterns werkend

ARCHITECTUUR CONTEXT:
- FastAPI backend met WebSockets
- Python Poetry project management  
- TDD approach met pytest
- Real STT → Mock Translation → Mock TTS pipeline
- Retry logic, circuit breaker, fallback patterns

PROJECT STRUCTUUR:
- /gcp_speech_to_speech_translation/
  - main.py (WebSocket handler)
  - services.py (STT/Translation/TTS functions)
  - config.py (environment settings)
  - resilience.py (circuit breaker)
- /tests/ (comprehensive test suite)

GOAL: Replace `mock_translation` with `real_translation` using Google Cloud Translation API
```

---

## Micro-Iteratie 5A: Test-First Development

### Step 5A.1: Create Test for Real Translation
**Prompt voor LLM:**
```
MICRO-STEP 5A.1: Create failing test for real translation API

Create a new test file: `tests/test_real_translation_integration.py`

REQUIREMENTS:
1. Test function: `test_real_translation_with_dutch_text()`
2. Skip test if no credentials (pytest.skip)
3. Call real_translation("hallo wereld") directly
4. Assert result contains English equivalent ("hello" or "world")
5. Test should FAIL initially (function doesn't exist yet)

EXAMPLE STRUCTURE:
```python
def test_real_translation_with_dutch_text():
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Call real function (will fail initially)
    result = await real_translation("hallo wereld")
    
    # Assert English words present
    assert "hello" in result.lower() or "world" in result.lower()
```

Run test to confirm it fails, then move to next step.
```

### Step 5A.2: Add Translation Dependencies  
**Prompt voor LLM:**
```
MICRO-STEP 5A.2: Add Google Translation API dependency

Add to pyproject.toml under [tool.poetry.dependencies]:
```toml
google-cloud-translate = "^3.12.0"
```

Then run: `poetry install`

Verify installation by importing in Python REPL:
```python
from google.cloud import translate
print("✅ Translation library installed")
```
```

---

## Micro-Iteratie 5B: Implementation

### Step 5B.1: Create Real Translation Function
**Prompt voor LLM:**
```
MICRO-STEP 5B.1: Implement real_translation function in services.py

Add to services.py:

REQUIREMENTS:
1. Function: `async def real_translation(text: str) -> str`
2. Use Google Cloud Translation API v3
3. Translate Dutch (nl) to English (en)
4. Include retry logic (same pattern as STT)
5. Include proper error handling for Google API errors
6. Add environment config options (source/target language)
7. Log input/output for debugging

PATTERN TO FOLLOW (based on real_speech_to_text):
- Environment config via os.getenv()
- Retry decorator from tenacity
- Google API exception handling
- Async execution with run_in_executor
- Proper logging

ENVIRONMENT VARIABLES TO ADD:
- TRANSLATION_SOURCE_LANG: "nl"
- TRANSLATION_TARGET_LANG: "en"
- TRANSLATION_TIMEOUT_S: "10.0"
```

### Step 5B.2: Update Config for Translation
**Prompt voor LLM:**
```
MICRO-STEP 5B.2: Add translation config to config.py

Add these settings to AppSettings class:

```python
# Translation configuratie
TRANSLATION_SOURCE_LANG: str = "nl"
TRANSLATION_TARGET_LANG: str = "en" 
TRANSLATION_TIMEOUT_S: float = 10.0
```

Verify settings load correctly by running:
```python
from gcp_speech_to_speech_translation.config import settings
print(f"Translation: {settings.TRANSLATION_SOURCE_LANG} → {settings.TRANSLATION_TARGET_LANG}")
```
```

---

## Micro-Iteratie 5C: Integration & Testing

### Step 5C.1: Replace Mock in Pipeline
**Prompt voor LLM:**
```
MICRO-STEP 5C.1: Replace mock_translation in main.py pipeline

In main.py, update the imports and process_pipeline function:

CHANGE:
```python
from .services import (
    real_speech_to_text,
    mock_text_to_speech,
    mock_translation,  # ← REMOVE THIS
)
```

TO:
```python
from .services import (
    real_speech_to_text,
    mock_text_to_speech,
    real_translation,  # ← ADD THIS
)
```

UPDATE process_pipeline function:
```python
async def process_pipeline(audio_chunk: bytes) -> bytes:
    text_result = await real_speech_to_text(audio_chunk)
    translation_result = await real_translation(text_result)  # ← CHANGE THIS
    output_audio = await mock_text_to_speech(translation_result)
    return output_audio
```
```

### Step 5C.2: Test Integration
**Prompt voor LLM:**
```
MICRO-STEP 5C.2: Test the integration

1. Run the specific translation test:
```bash
poetry run pytest tests/test_real_translation_integration.py -v
```

2. Run existing comprehensive tests to ensure no regression:
```bash  
poetry run pytest tests/test_iteration3_comprehensive.py -v
```

3. Test end-to-end with real audio (if you have the fixture):
```bash
poetry run pytest tests/test_real_stt_integration.py -v
```

EXPECTED RESULTS:
- ✅ Translation test passes
- ✅ All existing tests still pass  
- ✅ No performance regression
- ✅ Real STT → Real Translation → Mock TTS pipeline works
```

---

## Micro-Iteratie 5D: Health Check & Monitoring

### Step 5D.1: Add Translation Health Check
**Prompt voor LLM:**
```
MICRO-STEP 5D.1: Add health check endpoint for Translation API

Add to main.py:

```python
@app.get("/health/translation")
async def health_translation():
    """Health check endpoint for Google Cloud Translation service."""
    try:
        # Quick translation test
        from google.cloud import translate
        client = translate.TranslationServiceClient()
        
        # Test with minimal text
        test_result = await real_translation("test")
        
        return {
            "status": "ok", 
            "translation_client": "connected",
            "test_result": test_result
        }
    except Exception as e:
        return {
            "status": "error", 
            "translation_client": "disconnected",
            "error": str(e)
        }
```

Test endpoint:
```bash
poetry run uvicorn gcp_speech_to_speech_translation.main:app --reload
# Visit: http://localhost:8000/health/translation
```
```

---

## Error Scenarios & Troubleshooting

### Common Issues & Solutions
**Prompt voor LLM indien problemen:**
```
TROUBLESHOOTING GUIDE voor Iteratie 5:

IF: Import error "No module named 'google.cloud.translate'"
SOLUTION: Run `poetry install` and verify dependency in pyproject.toml

IF: Authentication error
SOLUTION: Verify GOOGLE_APPLICATION_CREDENTIALS points to valid service account

IF: "Invalid language code" error  
SOLUTION: Check TRANSLATION_SOURCE_LANG and TRANSLATION_TARGET_LANG settings

IF: Tests timeout
SOLUTION: Increase TRANSLATION_TIMEOUT_S in config or skip tests without credentials

IF: Quota exceeded error
SOLUTION: Check GCP quotas, implement rate limiting, or use mock fallback

DEBUG COMMANDS:
```bash
# Test credentials
gcloud auth application-default print-access-token

# Test translation directly
poetry run python -c "
from gcp_speech_to_speech_translation.services import real_translation
import asyncio
result = asyncio.run(real_translation('hallo wereld'))
print(f'Result: {result}')
"
```
```

---

## Success Criteria for Iteratie 5

✅ **Checklist:**
- [ ] Google Cloud Translation dependency installed
- [ ] real_translation function implemented with proper error handling  
- [ ] Configuration added for translation settings
- [ ] Mock replaced in main pipeline
- [ ] Translation-specific test passes
- [ ] All existing tests still pass
- [ ] Health check endpoint working
- [ ] End-to-end pipeline: Real STT → Real Translation → Mock TTS

✅ **Performance Targets:**
- Translation latency < 500ms for typical phrases
- No regression in overall pipeline timing
- Proper error handling and fallback behavior

✅ **Quality Gates:**
- All tests green
- No new linting errors
- Logging shows translation flow
- Health endpoint returns OK status
