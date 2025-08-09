# Iteratie 6: Google Text-to-Speech API Integration - Micro-Steps (Instructies Only)

## Overzicht Transformatie
**VAN:** Real STT → Real Translation → Mock TTS  
**NAAR:** Real STT → Real Translation → Real TTS

---

## Micro-Iteratie 6A: Test-First Development

### Step 6A.1: Create Failing Test for Real TTS
**Wat moet de LLM doen:**
- Maak nieuw testbestand: `tests/test_real_tts_integration.py`
- Schrijf test die `real_text_to_speech("hello world")` aanroept
- Test moet controleren dat resultaat bytes is (audio data)
- Verifieer dat audio niet leeg is en redelijke grootte heeft (>1000 bytes, <1MB)
- Test moet skippen als geen GCP credentials aanwezig
- Test moet FALEN omdat `real_text_to_speech` functie nog niet bestaat
- Voeg edge case tests toe (lege string, lange tekst, special characters)
- Optioneel: valideer audio format headers (MP3/WAV signatures)

**Verwacht resultaat:** Test faalt met ImportError of "function not found"

### Step 6A.2: Add TTS Dependencies
**Wat moet de LLM doen:**
- Voeg `google-cloud-texttospeech` toe aan project dependencies via Poetry
- Installeer de dependency
- Verifieer installatie door import test uit te voeren
- Controleer dat vereiste methoden en classes beschikbaar zijn
- Test dat TTS client interface werkt (zonder credentials)
- Verifieer dependency correct toegevoegd aan `pyproject.toml`

**Verwacht resultaat:** TTS library geïnstalleerd en importeerbaar

---

## Micro-Iteratie 6B: Implementation

### Step 6B.1: Add TTS Configuration
**Wat moet de LLM doen:**
- Voeg TTS configuratie toe aan `AppSettings` klasse in `config.py`
- Voeg velden toe voor: language code, voice name, voice gender, audio format, timeout
- Stel production-ready defaults in (en-US, Wavenet voice, MP3 format)
- Overweeg different voice options (Standard vs Wavenet vs Neural2)
- Overweeg audio formats (MP3 voor web, LINEAR16 voor kwaliteit, OGG_OPUS voor compressie)
- Verifieer dat configuratie correct geladen wordt via environment variables

**Verwacht resultaat:** TTS configuratie beschikbaar en aanpasbaar

### Step 6B.2: Implement real_text_to_speech Function
**Wat moet de LLM doen:**
- Implementeer `real_text_to_speech` functie in `services.py`
- Volg zelfde pattern als bestaande `real_speech_to_text` en `real_translation`
- Gebruik Google Cloud Text-to-Speech API
- Implementeer retry logic met exponential backoff
- Voeg proper error handling toe voor Google API errors
- Gebruik async executor pattern voor API calls
- Configureer voice parameters (language, name, gender)
- Configureer audio output format en encoding
- Voeg uitgebreide logging toe (inclusief audio size metrics)
- Handle verschillende text lengtes en potentiële rate limits

**Verwacht resultaat:** Werkende TTS functie die audio bytes produceert

---

## Micro-Iteratie 6C: Integration

### Step 6C.1: Update Pipeline in main.py
**Wat moet de LLM doen:**
- Vervang `mock_text_to_speech` import door `real_text_to_speech` in main.py
- Update de `process_pipeline` functie om `real_text_to_speech` te gebruiken
- Behoud alle bestaande retry en error handling logic
- Zorg dat pipeline nu is: Real STT → Real Translation → Real TTS
- Update any timeout configurations voor langere TTS processing tijd
- Verifieer dat alle resilience patterns (circuit breaker, fallback) nog werken

**Verwacht resultaat:** Complete real-time translation pipeline werkend

### Step 6C.2: Test Complete Pipeline Integration
**Wat moet de LLM doen:**
- Run de TTS integration test (moet nu slagen)
- Run alle bestaande tests om regression te checken
- Test de complete WebSocket pipeline met real audio input
- Voer end-to-end test uit: Dutch audio → English audio
- Meet totale pipeline latency (STT + Translation + TTS)
- Test met verschillende tekst lengtes en complexiteit
- Verifieer audio output quality en playback capability
- Test concurrent pipeline requests

**Verwacht resultaat:** Complete pipeline werkt, alle tests slagen

---

## Micro-Iteratie 6D: Health Check & Optimization

### Step 6D.1: Add TTS Health Check
**Wat moet de LLM doen:**
- Voeg TTS client initialization toe aan app startup event
- Maak global `tts_client` variabele (zoals bestaande clients)
- Implementeer `/health/tts` endpoint
- Health check moet TTS API testen met minimal text
- Return status, client connection status, audio output size, voice config
- Implementeer `/health/full` endpoint voor complete pipeline health
- Test alle services samen (STT + Translation + TTS)
- Voeg proper error handling toe voor failed health checks

**Verwacht resultaat:** Complete health monitoring voor alle pipeline components

### Step 6D.2: Performance Optimization & Final Validation
**Wat moet de LLM doen:**
- Implementeer TTS client connection pooling en reuse
- Add audio output size monitoring en logging
- Optimize timeout settings based on text length
- Test different audio formats voor performance vs quality trade-offs
- Implementeer response streaming voor large audio outputs (indien nodig)
- Meet en optimize memory usage voor audio processing
- Run comprehensive performance tests (latency, throughput, concurrency)
- Test audio playback compatibility in different browsers
- Validate complete user journey: speak Dutch → hear English

**Verwacht resultaat:** Production-ready pipeline met optimized performance

---

## Success Criteria per Micro-Step

### 6A - Test-First Development
✅ **6A.1:** TTS test faalt zoals verwacht (functie bestaat niet)  
✅ **6A.2:** Google Cloud TTS library geïnstalleerd en werkend

### 6B - Implementation  
✅ **6B.1:** TTS configuratie toegankelijk via settings (voice, format, etc.)  
✅ **6B.2:** `real_text_to_speech` functie produceert valide audio bytes

### 6C - Integration
✅ **6C.1:** Pipeline gebruikt real TTS (geen mock meer)  
✅ **6C.2:** Complete end-to-end pipeline werkt (Dutch audio → English audio)

### 6D - Health Check & Optimization
✅ **6D.1:** Health endpoints voor TTS en complete pipeline werkend  
✅ **6D.2:** Performance geoptimaliseerd, production-ready

---

## Globale Success Criteria voor Iteratie 6

### Functioneel
- [ ] `real_text_to_speech` functie geïmplementeerd en produceert audio
- [ ] Complete pipeline: Real STT → Real Translation → Real TTS
- [ ] End-to-end werking: Dutch speech input → English speech output
- [ ] Alle bestaande tests blijven slagen
- [ ] TTS integration tests slagen
- [ ] Audio output speelbaar in web browsers

### Performance
- [ ] TTS latency < 3 seconden voor typische zinnen (10-20 woorden)
- [ ] Complete pipeline latency < 8 seconden end-to-end
- [ ] Audio output size redelijk (5-50KB voor zinnen)
- [ ] Memory usage stabiel bij audio processing
- [ ] Concurrent pipeline requests mogelijk

### Audio Quality & Formats
- [ ] Audio output kwaliteit acceptabel voor spraakbegrip
- [ ] Audio format geschikt voor web playback (MP3/OGG)
- [ ] Audio encoding compatible met verschillende browsers
- [ ] Voice quality en natuurlijkheid acceptabel
- [ ] Proper audio sample rate en bitrate

### Quality & Resilience  
- [ ] Retry logic werkt bij TTS API failures
- [ ] Circuit breaker patterns behouden voor complete pipeline
- [ ] Proper error handling en logging voor audio processing
- [ ] Graceful fallback bij TTS failures
- [ ] Audio size limits en validation
- [ ] No memory leaks bij audio processing

### Monitoring & Ops
- [ ] Health endpoints voor TTS en complete pipeline
- [ ] TTS client properly initialized at startup
- [ ] Audio processing metrics logged (size, duration, format)
- [ ] API errors logged met voldoende detail
- [ ] Performance metrics voor complete pipeline

---

## Special Considerations voor TTS

### Audio Format Decisions
**Wat moet de LLM overwegen:**
- MP3: Good compression, universal web support, reasonable quality
- LINEAR16: Uncompressed, larger files, highest quality
- OGG_OPUS: Good compression, modern browsers, good quality
- Consider target platform: web browser audio playback capabilities

### Voice Selection Strategy
**Wat moet de LLM overwegen:**
- Standard voices: Lower cost, good quality
- Wavenet voices: Higher quality, more natural, higher cost
- Neural2 voices: Latest technology, best quality, highest cost
- Gender selection: NEUTRAL default, configurable via environment

### Performance Trade-offs
**Wat moet de LLM overwegen:**
- Text length vs processing time (longer text = longer TTS processing)
- Audio quality vs file size vs processing speed
- Real-time requirements vs quality requirements
- Concurrent request handling vs resource usage

---

## Post-Completion: Complete Real-Time Translation Pipeline

**ACHIEVED PIPELINE:**
```
✅ Real STT (Dutch audio → Dutch text)
✅ Real Translation (Dutch text → English text)  
✅ Real TTS (English text → English audio)
```

**COMPLETE USER JOURNEY:**
```
🎤 Dutch Speech Input → 🔄 Processing → 🔊 English Speech Output
```

**Readiness for Production:**
- Complete end-to-end real-time translation
- Full health monitoring and observability
- Performance optimized for web deployment
- Ready for Iteratie 7: Multi-user broadcasting

**Next Phase Preview (Iteratie 7):**
- Transform from 1-on-1 to 1-to-many architecture
- Implement ConnectionManager for WebSocket broadcasting  
- Add stream_id concept for multiple concurrent translation streams
- Enable multiple listeners per speaker