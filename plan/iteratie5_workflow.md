# Iteratie 5: Google Translation API Integration - Micro-Steps (Instructies Only)

## Overzicht Transformatie
**VAN:** Real STT → Mock Translation → Mock TTS  
**NAAR:** Real STT → Real Translation → Mock TTS

---

## Micro-Iteratie 5A: Test-First Development

### Step 5A.1: Create Failing Test for Real Translation
**Wat moet de LLM doen:**
- Maak nieuw testbestand: `tests/test_real_translation_integration.py`
- Schrijf test die `real_translation("hallo wereld")` aanroept
- Test moet controleren of resultaat Engels bevat ("hello", "world", etc.)
- Test moet skippen als geen GCP credentials aanwezig
- Test moet FALEN omdat `real_translation` functie nog niet bestaat
- Voeg ook edge case tests toe (lege string, foutafhandeling)

**Verwacht resultaat:** Test faalt met ImportError of "function not found"

### Step 5A.2: Add Translation Dependencies
**Wat moet de LLM doen:**
- Voeg `google-cloud-translate` toe aan project dependencies via Poetry
- Installeer de dependency
- Verifieer installatie door import test uit te voeren
- Controleer dat vereiste methoden (`translate`, `detect_language`) beschikbaar zijn
- Verifieer dat dependency correct toegevoegd is aan `pyproject.toml`

**Verwacht resultaat:** Library geïnstalleerd en importeerbaar

---

## Micro-Iteratie 5B: Implementation

### Step 5B.1: Add Translation Config
**Wat moet de LLM doen:**
- Voeg translation configuratie toe aan `AppSettings` klasse in `config.py`
- Voeg velden toe voor: source language, target language, timeout
- Stel default waarden in (nl → en, 10s timeout)
- Verifieer dat configuratie correct geladen wordt
- Test dat settings toegankelijk zijn via `settings` object

**Verwacht resultaat:** Translation config beschikbaar via environment variables

### Step 5B.2: Implement real_translation Function
**Wat moet de LLM doen:**
- Implementeer `real_translation` functie in `services.py`
- Volg zelfde pattern als bestaande `real_speech_to_text` functie
- Gebruik Google Cloud Translation API v2 (`translate_v2`)
- Implementeer retry logic met exponential backoff
- Voeg proper error handling toe voor Google API errors
- Gebruik async executor pattern voor API calls
- Voeg uitgebreide logging toe voor debugging
- Configuratie via environment variables (zoals STT)

**Verwacht resultaat:** Werkende translation functie met resilience patterns

---

## Micro-Iteratie 5C: Integration

### Step 5C.1: Update Pipeline in main.py
**Wat moet de LLM doen:**
- Vervang `mock_translation` import door `real_translation` in main.py
- Update de `process_pipeline` functie om `real_translation` te gebruiken
- Behoud alle bestaande retry en error handling logic
- Zorg dat pipeline nu is: Real STT → Real Translation → Mock TTS

**Verwacht resultaat:** Pipeline gebruikt nu echte translation API

### Step 5C.2: Test Integration
**Wat moet de LLM doen:**
- Run de translation integration test (moet nu slagen)
- Run alle bestaande tests om regression te checken
- Test de WebSocket pipeline met real audio (indien beschikbaar)
- Voer handmatige pipeline test uit om end-to-end flow te verifiëren
- Meet en verifieer performance (translation latency)

**Verwacht resultaat:** Alle tests slagen, geen performance regressie

---

## Micro-Iteratie 5D: Health Check & Monitoring

### Step 5D.1: Add Translation Health Check
**Wat moet de LLM doen:**
- Voeg translation client initialization toe aan app startup event
- Maak global `translation_client` variabele (zoals bestaande `speech_client`)
- Implementeer `/health/translation` endpoint
- Health check moet translation API testen met minimal request
- Return status, client connection status, en test result
- Voeg proper error handling toe voor failed health checks

**Verwacht resultaat:** Health endpoint beschikbaar en werkend

### Step 5D.2: Final Integration Test
**Wat moet de LLM doen:**
- Test alle health endpoints (speech + translation)
- Run complete test suite om alles te verifiëren
- Test WebSocket met real pipeline (indien audio beschikbaar)
- Meet performance van translation requests
- Verifieer dat latency binnen acceptabele grenzen valt (<3s)
- Controleer dat alle resilience patterns nog werken

**Verwacht resultaat:** Volledige pipeline werkend met monitoring

---

## Success Criteria per Micro-Step

### 5A - Test-First Development
✅ **5A.1:** Test faalt zoals verwacht (functie bestaat niet)  
✅ **5A.2:** Google Cloud Translate library geïnstalleerd en werkend

### 5B - Implementation  
✅ **5B.1:** Translation configuratie toegankelijk via settings  
✅ **5B.2:** `real_translation` functie werkt met retry logic

### 5C - Integration
✅ **5C.1:** Pipeline gebruikt real translation (geen mock meer)  
✅ **5C.2:** Alle tests slagen, geen regressie

### 5D - Health Check & Monitoring
✅ **5D.1:** Health endpoint werkt en toont translation status  
✅ **5D.2:** Complete pipeline gevalideerd en performance OK

---

## Globale Success Criteria voor Iteratie 5

### Functioneel
- [ ] `real_translation` functie geïmplementeerd en werkend
- [ ] Pipeline transformatie compleet: Real STT → Real Translation → Mock TTS
- [ ] Alle bestaande tests blijven slagen
- [ ] Translation integration tests slagen
- [ ] Health monitoring voor translation beschikbaar

### Performance
- [ ] Translation latency < 3 seconden per request
- [ ] Geen significante vertraging in totale pipeline
- [ ] Concurrent translation requests mogelijk
- [ ] Memory usage blijft stabiel

### Quality & Resilience  
- [ ] Retry logic werkt bij API failures
- [ ] Circuit breaker patterns behouden
- [ ] Proper error handling en logging
- [ ] Graceful fallback bij translation failures
- [ ] No linting errors of warnings

### Monitoring & Ops
- [ ] Health endpoint returns meaningful status
- [ ] Translation client properly initialized at startup
- [ ] API errors logged met voldoende detail
- [ ] Performance metrics beschikbaar

---

## Post-Completion: Ready for Iteratie 6

**ACHIEVED PIPELINE:**
```
✅ Real STT (Dutch audio → Dutch text)
✅ Real Translation (Dutch text → English text)  
❌ Mock TTS (English text → mock audio)
```

**NEXT TARGET (Iteratie 6):**
```
✅ Real STT → ✅ Real Translation → ✅ Real TTS (English text → English audio)
```

**Preparation for Iteratie 6:**
- Translation working and stable
- Performance baseline established  
- Health monitoring in place
- Ready to tackle Text-to-Speech integration