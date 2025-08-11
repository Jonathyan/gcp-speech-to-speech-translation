Perfect! Je hebt een solide basis en je wilt naar Iteratie 7 - multi-user broadcasting. Laten we dit opdelen in zeer kleine, LLM-vriendelijke micro-iteraties die veilig en incrementeel zijn.

## 🎯 Iteratie 7: Broadcasting - Micro-Iteratie Plan

### Overzicht Transformatie
**VAN:** Single WebSocket `/ws` (1-op-1)  
**NAAR:** Split endpoints `/ws/speak/{stream_id}` en `/ws/listen/{stream_id}` (1-op-veel)

---

## 📋 Micro-Iteratie 7A: ConnectionManager Foundation

### Step 7A.1: Create ConnectionManager Class (Test-First)
**Instructie voor LLM:**
```
Maak een nieuwe file `backend/connection_manager.py` met:

1. Een `ConnectionManager` klasse met:
   - `__init__()` method die een thread-safe dictionary initialiseert
   - `add_listener(stream_id: str, websocket: WebSocket)` method
   - `remove_listener(stream_id: str, websocket: WebSocket)` method
   - `get_listeners(stream_id: str) -> List[WebSocket]` method
   - `broadcast_to_stream(stream_id: str, audio_data: bytes)` async method

2. Gebruik `threading.Lock()` voor thread safety
3. Implementeer proper logging voor alle connection events
4. Handle edge cases (non-existent stream_id, already connected websocket)

Maak ook `tests/test_connection_manager.py` met unit tests voor alle methods.
```

**Success Criteria:**
- ✅ ConnectionManager class exists en all methods gedefinieerd
- ✅ Unit tests pass voor basic functionality
- ✅ Thread safety implemented met Lock
- ✅ Proper error handling en logging

---

### Step 7A.2: Test ConnectionManager Integration
**Instructie voor LLM:**
```
Maak `tests/test_connection_manager_integration.py` met:

1. Test dat meerdere WebSocket mocks kunnen worden toegevoegd aan één stream
2. Test dat broadcasting naar alle listeners in een stream werkt
3. Test dat verschillende stream_ids isolated zijn
4. Test dat connection cleanup werkt bij disconnection
5. Test concurrent access (multiple threads adding/removing connections)

Gebruik unittest.mock.Mock voor WebSocket objecten in tests.
```

**Success Criteria:**
- ✅ All integration tests pass
- ✅ Multiple listeners per stream werkt
- ✅ Stream isolation verified
- ✅ Concurrent access safe

---

## 📋 Micro-Iteratie 7B: Split WebSocket Endpoints

### Step 7B.1: Add New Endpoints (Test-First)
**Instructie voor LLM:**
```
Update `main.py` met nieuwe endpoints naast de bestaande `/ws`:

1. Voeg toe: `@app.websocket("/ws/speak/{stream_id}")`
2. Voeg toe: `@app.websocket("/ws/listen/{stream_id}")`
3. Laat de originele `/ws` endpoint bestaan voor backwards compatibility
4. Maak een global `connection_manager` instance

Implementeer basic endpoint structure:
- Speaker endpoint: accepts connection, logs stream_id
- Listener endpoint: accepts connection, adds to ConnectionManager

Maak `tests/test_new_endpoints.py` met tests die:
- Verificeren dat beide endpoints connection accepteren
- Testen dat stream_id parameter correct wordt geëxtraheerd
- Verificeren dat listeners worden toegevoegd aan ConnectionManager
```

**Success Criteria:**
- ✅ Nieuwe endpoints bestaan en accepteren connections
- ✅ Stream_id parameter extraction werkt
- ✅ Backwards compatibility: oude `/ws` endpoint nog steeds werkend
- ✅ Basic connection tests pass

---

### Step 7B.2: Implement Listener Logic
**Instructie voor LLM:**
```
Implementeer de `/ws/listen/{stream_id}` endpoint logica:

1. Add WebSocket to ConnectionManager bij connection
2. Implement connection lifecycle (connect → wait → disconnect)
3. Handle disconnection cleanup (remove from ConnectionManager)
4. Add proper error handling en logging
5. Implement keepalive/heartbeat voor connection stability

Update tests om te verificeren:
- Listener wordt correct toegevoegd en verwijderd
- Multiple listeners per stream_id werken
- Disconnection cleanup werkt correct
```

**Success Criteria:**
- ✅ Listeners worden correct beheerd in ConnectionManager
- ✅ Multiple listeners per stream werken
- ✅ Disconnection cleanup werkt
- ✅ Tests pass voor listener lifecycle

---

## 📋 Micro-Iteratie 7C: Speaker to Listener Broadcasting

### Step 7C.1: Implement Speaker Pipeline Logic
**Instructie voor LLM:**
```
Implementeer de `/ws/speak/{stream_id}` endpoint:

1. Gebruik bestaande `process_pipeline` function (STT→Translation→TTS)
2. Na pipeline completion: gebruik ConnectionManager.broadcast_to_stream()
3. Speaker krijgt GEEN response terug (anders dan listeners)
4. Handle alle bestaande resilience patterns (retry, circuit breaker, fallback)
5. Add logging voor pipeline execution en broadcasting events

Update tests:
- Test dat speaker pipeline wordt uitgevoerd
- Test dat result wordt gebroadcast naar listeners (niet naar speaker)
- Test met 0, 1, en multiple listeners
- Test error scenarios (pipeline failure, broadcast failure)
```

**Success Criteria:**
- ✅ Speaker pipeline execution werkt
- ✅ Broadcasting naar listeners werkt
- ✅ Speaker krijgt geen response
- ✅ Error handling en resilience patterns behouden

---

### Step 7C.2: End-to-End Broadcasting Test
**Instructie voor LLM:**
```
Maak `tests/test_broadcasting_e2e.py` met comprehensive test:

1. Test setup: 1 speaker + 2 listeners op zelfde stream_id
2. Speaker stuurt audio chunk
3. Verificeer dat beide listeners exact hetzelfde audio ontvangen
4. Test multiple streams parallel (isolation verification)
5. Test edge cases: listener disconnect tijdens broadcast, speaker disconnect

Test scenario:
- Stream "test-1": 1 speaker + 2 listeners
- Stream "test-2": 1 speaker + 1 listener  
- Beide streams tegelijk actief
- Verificeer cross-stream isolation
```

**Success Criteria:**
- ✅ End-to-end broadcasting werkt
- ✅ Multiple listeners receive same audio
- ✅ Stream isolation verified
- ✅ Edge cases handled gracefully

---

## 📋 Micro-Iteratie 7D: Performance & Production Readiness

### Step 7D.1: Performance Optimization
**Instructie voor LLM:**
```
Optimaliseer broadcasting performance:

1. Implement async broadcasting (parallel sends naar alle listeners)
2. Add connection pooling/reuse waar mogelijk
3. Implement broadcast timeouts (don't wait forever voor slow listeners)
4. Add metrics/monitoring voor broadcast latency en success rates
5. Handle "slow listener" scenario (disconnect na timeout)

Performance tests:
- Test broadcasting naar 10+ listeners simultaneously
- Measure broadcast latency per listener count
- Test met simulated slow/disconnected listeners
```

**Success Criteria:**
- ✅ Broadcasting is async/parallel
- ✅ Performance meets requirements (<1s broadcast latency)
- ✅ Slow listener handling implemented
- ✅ Performance tests pass

---

### Step 7D.2: Production Readiness & Monitoring
**Instructie voor LLM:**
```
Add production features:

1. Update health endpoints met connection metrics:
   - `/health/connections` - active streams en listener counts
   - Update `/health/full` met broadcasting test
2. Add connection limits (max listeners per stream, max total connections)
3. Implement connection cleanup job (remove stale connections)
4. Add comprehensive logging voor debugging
5. Update error handling voor production scenarios

Monitoring tests:
- Test health endpoints return connection stats
- Test connection limits enforcement
- Test cleanup job removes stale connections
```

**Success Criteria:**
- ✅ Health monitoring voor connections
- ✅ Connection limits implemented
- ✅ Cleanup mechanisms work
- ✅ Production-ready error handling

---

## 🚀 LLM Workflow Strategie

### Voor elke micro-iteratie:

1. **Test-First Approach:**
```bash
# LLM schrijft eerst failing tests
poetry run pytest tests/test_new_feature.py -v
# Verwacht: tests falen zoals bedoeld
```

2. **Implementatie:**
```bash
# LLM implementeert feature
# Run tests om te verificeren
poetry run pytest tests/test_new_feature.py -v
# Verwacht: tests slagen
```

3. **Regression Check:**
```bash
# Verificeer dat bestaande functionaliteit nog werkt
poetry run pytest -v
# Verwacht: alle tests slagen
```

4. **Integration Validation:**
```bash
# Test complete systeem
poetry run uvicorn gcp_speech_to_speech_translation.main:app --reload
# Manual test met health endpoints
curl http://localhost:8000/health/full
```

### Veiligheidsnet per stap:
- **Backwards compatibility:** Oude `/ws` endpoint blijft werken
- **Gradual rollout:** Nieuwe endpoints werken naast oude
- **Test isolation:** Elke micro-iteratie heeft eigen test suite
- **Easy rollback:** Elke stap is een aparte commit

## 🎯 Success Criteria voor Complete Iteratie 7

### Architectuur Achievement:
```
✅ OLD: /ws (1-op-1)
✅ NEW: /ws/speak/{stream_id} + /ws/listen/{stream_id} (1-op-veel)
✅ COMPATIBILITY: Oude endpoint nog steeds werkend
```

### Functional Achievement:
- ✅ Multiple listeners kunnen luisteren naar 1 speaker
- ✅ Stream isolation (verschillende stream_ids isolated)
- ✅ Real-time broadcasting van vertaalde audio
- ✅ Robust connection management en cleanup

### Quality Achievement:
- ✅ All existing tests blijven passing
- ✅ New comprehensive test coverage
- ✅ Performance optimized voor multiple listeners
- ✅ Production-ready monitoring en health checks

**Ready to start? Begin met Micro-Iteratie 7A.1! 🚀**