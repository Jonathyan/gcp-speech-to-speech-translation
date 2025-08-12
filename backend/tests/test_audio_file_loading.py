import pytest
from pathlib import Path


def test_audio_file_loading():
    """
    Test dat het audio bestand correct kan worden geladen en gevalideerd.
    """
    # Path naar het test audio bestand
    audio_file_path = Path(__file__).parent / "fixtures" / "hallo_wereld.wav"
    
    # Skip test als audio bestand niet bestaat (niet in git)
    if not audio_file_path.exists():
        pytest.skip(f"Audio bestand niet gevonden: {audio_file_path}. Zie tests/fixtures/README.md")
    
    # Verificeer dat het bestand bestaat
    assert audio_file_path.exists(), f"Audio bestand niet gevonden: {audio_file_path}"
    
    # Laad het bestand als binaire data
    with open(audio_file_path, "rb") as f:
        audio_data = f.read()
    
    # Verificeer dat het bestand niet leeg is
    assert len(audio_data) > 0, "Audio bestand is leeg"
    
    # Verificeer dat het binaire data is
    assert isinstance(audio_data, bytes), "Audio data moet van type bytes zijn"
    
    # Basis WAV format check - WAV bestanden beginnen met "RIFF"
    assert audio_data[:4] == b'RIFF', "Bestand is geen geldig WAV bestand (mist RIFF header)"
    
    # Verificeer WAV signature op positie 8
    assert audio_data[8:12] == b'WAVE', "Bestand is geen geldig WAV bestand (mist WAVE signature)"
    
    # Verificeer minimale bestandsgrootte (WAV header is minimaal 44 bytes)
    assert len(audio_data) >= 44, f"WAV bestand te klein: {len(audio_data)} bytes"