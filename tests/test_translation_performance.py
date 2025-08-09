import os
import time
import pytest
from gcp_speech_to_speech_translation.services import real_translation


@pytest.mark.asyncio
async def test_translation_performance():
    """Test translation performance to ensure latency is within acceptable limits (<3s)."""
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    test_cases = [
        'hallo wereld',
        'dit is een langere zin om de performance te testen',
        'goedemorgen, hoe gaat het met je vandaag?',
        'korte tekst',
        'een zeer lange zin met veel woorden om te kijken hoe de API omgaat met langere teksten'
    ]
    
    total_time = 0
    max_latency = 0
    results = []
    
    for text in test_cases:
        start_time = time.time()
        result = await real_translation(text)
        latency = (time.time() - start_time) * 1000
        
        total_time += latency
        max_latency = max(max_latency, latency)
        results.append((text, result, latency))
        
        # Assert individual request is under 3 seconds
        assert latency < 3000, f"Translation took {latency:.0f}ms (>3s): '{text}'"
    
    avg_latency = total_time / len(test_cases)
    
    # Print performance summary
    print(f"\n📊 Translation Performance Summary:")
    print(f"Average Latency: {avg_latency:.0f}ms")
    print(f"Max Latency: {max_latency:.0f}ms")
    
    for text, result, latency in results:
        print(f"  {latency:.0f}ms - '{text[:30]}...' → '{result[:30]}...'")
    
    # Assert overall performance
    assert avg_latency < 1000, f"Average latency {avg_latency:.0f}ms too high"
    assert max_latency < 3000, f"Max latency {max_latency:.0f}ms exceeds 3s limit"


@pytest.mark.asyncio
async def test_translation_edge_cases():
    """Test translation with edge cases to verify resilience."""
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Test empty string
    result = await real_translation("")
    assert isinstance(result, str)
    
    # Test single word
    result = await real_translation("hallo")
    assert "hello" in result.lower()
    
    # Test with numbers and punctuation
    result = await real_translation("het is 5 uur!")
    assert isinstance(result, str)
    assert len(result) > 0