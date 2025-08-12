### Stap-voor-stap: WAV Testen met WebSocket Client
# Stap 1: Maak test script
Creating a simple WebSocket client script to test WAV file translation

test_wav_client.py


# Stap 2: Start je server
Open een terminal en start je FastAPI server:

cd /Users/jonathyan/tech/lfhs-translate/gcp_s2t2st/gcp-speech-to-speech-translation
poetry run uvicorn gcp_speech_to_speech_translation.main:app --reload --host 0.0.0.0 --port 8000


# Stap 3: Run het test script
Open een tweede terminal en run het test script:

cd /Users/jonathyan/tech/lfhs-translate/gcp_s2t2st/gcp-speech-to-speech-translation
poetry run python test_wav_client.py



# Wat er gebeurt:
1. Script leest tests/fixtures/hallo_wereld.wav (Dutch audio)

2. Verbindt met je WebSocket server op localhost:8000/ws

3. Stuurt de WAV data als binary naar server

4. Server verwerkt: STT (Dutch→text) → Translation (Dutch→English) → TTS (text→English audio)

5. Ontvangt MP3 audio terug

6. Slaat op als output_english.mp3

# Verwacht resultaat:
🚀 Starting WAV translation test...
🎵 Reading WAV file: tests/fixtures/hallo_wereld.wav
📤 Sending 44100 bytes of Dutch audio...
🔗 Connected to WebSocket server
✅ Audio sent, waiting for translation...
📥 Received 15234 bytes of English audio
🎧 Saved translated audio to: output_english.mp3
🎉 Test completed successfully!


# Test je resultaat:
Speel output_english.mp3 af - je zou Engels gesproken "Hello world" moeten horen!

Klaar om te testen? Start gewoon de server en run het script! 🎯