# Extended Streaming Test Documentation

## Purpose

This test suite validates the **5-minute stream restart logic** implemented in `backend/streaming_stt.py`. The Google Cloud Speech-to-Text streaming API has a hard 5-minute limit, and our implementation proactively restarts streams at the 4:40 mark to prevent service interruptions.

## Test Overview

### Test Duration: 15 minutes
- **Expected restarts**: 3 times (at 4:40, 9:20, 14:00)
- **Validation**: Seamless operation without data loss
- **Audio generation**: Synthetic LINEAR16 PCM resembling Dutch speech patterns

## Validation Criteria

### ✅ **Stream Continuity**
- Stream continues seamlessly after 4:40 mark
- Test completes 95% of target duration (14.25+ minutes)
- No forced disconnections or timeout errors

### ✅ **No Audio Data Loss**  
- All audio chunks successfully sent to server
- No dropped chunks during restart transitions
- Chunk success rate >99%

### ✅ **Transcript Continuity**
- Maximum 1 minor transcript gap allowed
- No gaps >10 seconds during restart
- Server continues processing audio through restart

### ✅ **Error Tolerance**
- Error rate <1% of total operations
- No critical errors during restart process
- Health endpoint remains responsive

## Files

### `test_extended_streaming.py`
**Comprehensive test harness** with:
- Synthetic audio generation (LINEAR16 PCM, 16kHz mono)
- Real-time WebSocket streaming (100ms chunks)
- Performance metrics tracking
- Automatic validation and reporting
- JSON report generation

### `run_streaming_test.sh`
**Test runner script** that:
- Checks backend status
- Installs test dependencies with poetry
- Runs 15-minute test with poetry
- Provides pass/fail summary


## Usage

### Quick Test
```bash
# Automated test with backend management
./run_streaming_test.sh
```

### Manual Test
```bash
# 1. Start backend
poetry run uvicorn backend.main:app --reload

# 2. In separate terminal, install deps and run test
poetry add numpy websockets aiohttp --group dev
poetry run python test_extended_streaming.py
```

## Expected Output

### Console Progress
```
🚀 Starting Extended Streaming Test
   Duration: 15 minutes
   WebSocket: ws://localhost:8000/ws/speak/extended-test
   Expected restart interval: 280s

✅ WebSocket connected successfully
📊 Progress: 1.0/15 minutes, 600 chunks sent, 15 transcripts received
🔄 Stream duration limit approaching, scheduling restart...  # At 4:40
✅ Stream restart completed successfully
📊 Progress: 5.0/15 minutes, 3000 chunks sent, 75 transcripts received
...
```

### Final Report
```
📊 EXTENDED STREAMING TEST REPORT
================================================================
✅ Test Duration: 15.0/15 minutes (100.0%)
📊 Chunks Sent: 9,000 (success rate: 99.8%)
📝 Transcripts Received: 225
🔄 Stream Restarts: 3 (expected: 3)
⚠️  Data Loss Events: 0
❌ Error Events: 2 (0.02%)

🔍 VALIDATION RESULTS:
  ✅ PASS Stream Continuity: Achieved 100.0% of target duration
  ✅ PASS Seamless Restart: Data loss events: 0
  ✅ PASS Transcript Continuity: Transcript gaps: 0, largest: 0.0s
  ✅ PASS Error Tolerance: Error rate: 0.02%

🏆 OVERALL TEST RESULT: ✅ PASSED
```

## Test Architecture

### Audio Generation
- **Synthetic speech patterns**: Multi-frequency sine waves with formants
- **Realistic variation**: Random noise and frequency modulation  
- **Dutch-like characteristics**: Frequency ranges typical of Dutch speech
- **Continuous stream**: 100ms chunks at 16kHz sample rate

### Monitoring Systems
- **Performance tracking**: Processing times, memory usage
- **Health monitoring**: Backend status via HTTP health checks
- **Error detection**: WebSocket errors, timeout events
- **Restart detection**: Log analysis for restart events

### Validation Logic
- **Mathematical validation**: Statistical analysis of performance metrics
- **Temporal validation**: Precise timing of restart events
- **Continuity validation**: Gap analysis in transcript flow
- **Reliability validation**: Error rate calculations

## Troubleshooting

### Common Issues

**Backend not starting**
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill existing process if needed
lsof -ti:8000 | xargs kill -9
```

**Test dependencies missing**
```bash
# Install with poetry
poetry add numpy websockets aiohttp --group dev
```

**Google Cloud credentials**
```bash
# Ensure credentials are set
export GOOGLE_APPLICATION_CREDENTIALS="credentials/service-account.json"
```

### Debug Mode
Add to test script for verbose output:
```python
logging.getLogger().setLevel(logging.DEBUG)
```

## Integration with CI/CD

This test can be integrated into continuous integration:

```yaml
# GitHub Actions example
- name: Extended Streaming Test
  run: |
    export GOOGLE_APPLICATION_CREDENTIALS="${{ secrets.GCP_CREDENTIALS }}"
    ./run_streaming_test.sh
  timeout-minutes: 20  # Allow for 15min test + setup
```

## Performance Benchmarks

### Expected Performance (15-minute test)
- **Chunks sent**: ~9,000 (100ms × 900 seconds)
- **Processing time**: <10ms per chunk average
- **Memory usage**: <100MB sustained
- **CPU usage**: <20% sustained
- **Network throughput**: ~150KB/s upload

### Restart Behavior
- **Restart trigger**: Exactly at 4:40, 9:20, 14:00
- **Restart duration**: <200ms typical
- **Audio gap**: 0ms (seamless)
- **Transcript gap**: <1 second acceptable

This comprehensive test ensures the 5-minute stream restart logic works reliably in production scenarios.