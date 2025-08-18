#!/usr/bin/env python3
"""
Debug script to investigate the SpeechHelpers error in Google Cloud Speech-to-Text
"""

import logging
import inspect
from google.cloud import speech
from google.cloud.speech_v1 import SpeechClient
from google.cloud.speech_v1.services.speech import SpeechClient as SpeechServiceClient

def debug_speech_client():
    """Investigate the Google Cloud Speech client structure"""
    print("🔍 DEBUGGING GOOGLE CLOUD SPEECH CLIENT")
    print("=" * 60)
    
    # Create the client
    client = speech.SpeechClient()
    
    print(f"✅ Client created successfully")
    print(f"📋 Client type: {type(client)}")
    print(f"📋 Client class: {client.__class__}")
    print(f"📋 Client module: {client.__class__.__module__}")
    print()
    
    # Examine the streaming_recognize method
    print("🔍 EXAMINING streaming_recognize METHOD")
    print("-" * 40)
    
    streaming_method = getattr(client, 'streaming_recognize', None)
    if streaming_method:
        print(f"✅ streaming_recognize method exists")
        print(f"📋 Method type: {type(streaming_method)}")
        print(f"📋 Method: {streaming_method}")
        print()
        
        # Check if it's wrapped or monkey-patched
        if hasattr(streaming_method, '__wrapped__'):
            print(f"⚠️  Method is wrapped! Original: {streaming_method.__wrapped__}")
        
        # Get the method signature
        try:
            sig = inspect.signature(streaming_method)
            print(f"📋 Method signature: {sig}")
            print(f"📋 Parameters: {list(sig.parameters.keys())}")
        except Exception as e:
            print(f"❌ Could not get signature: {e}")
        
        # Check method resolution order
        print(f"📋 Method resolution: {streaming_method.__qualname__}")
        
    else:
        print("❌ streaming_recognize method not found!")
    
    print()
    
    # Check all methods starting with 'streaming'
    print("🔍 ALL STREAMING METHODS")
    print("-" * 30)
    streaming_methods = [attr for attr in dir(client) if 'streaming' in attr.lower()]
    for method_name in streaming_methods:
        method = getattr(client, method_name)
        print(f"📋 {method_name}: {type(method)}")
    
    print()
    
    # Check for SpeechHelpers in the module
    print("🔍 SEARCHING FOR SPEECHHELPERS")
    print("-" * 35)
    
    # Check in the speech module
    speech_attrs = dir(speech)
    helpers_attrs = [attr for attr in speech_attrs if 'helper' in attr.lower() or 'Helper' in attr]
    if helpers_attrs:
        print(f"⚠️  Found helper-related attributes in speech module: {helpers_attrs}")
        for attr in helpers_attrs:
            obj = getattr(speech, attr)
            print(f"   📋 {attr}: {type(obj)} - {obj}")
    else:
        print("✅ No SpeechHelpers found in speech module")
    
    # Check the client's __dict__ for any helpers
    client_attrs = [attr for attr in dir(client) if 'helper' in attr.lower() or 'Helper' in attr]
    if client_attrs:
        print(f"⚠️  Found helper-related attributes in client: {client_attrs}")
        for attr in client_attrs:
            obj = getattr(client, attr)
            print(f"   📋 {attr}: {type(obj)} - {obj}")
    
    print()
    
    # Try calling streaming_recognize with minimal args to see the exact error
    print("🔍 TESTING streaming_recognize CALL")
    print("-" * 40)
    
    try:
        # Create minimal request iterator
        def minimal_request_generator():
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                sample_rate_hertz=16000,
                language_code='nl-NL'
            )
            
            streaming_config = speech.StreamingRecognitionConfig(
                config=config,
                interim_results=True
            )
            
            yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
            # Don't yield audio data, just test the initial call
        
        print("📋 Creating minimal request generator...")
        requests = minimal_request_generator()
        
        print("📋 Calling streaming_recognize...")
        response_stream = client.streaming_recognize(requests)
        print(f"✅ streaming_recognize call successful!")
        print(f"📋 Response stream type: {type(response_stream)}")
        
        # Try to get the first response (this might fail but that's OK)
        try:
            first_response = next(iter(response_stream))
            print(f"✅ Got first response: {type(first_response)}")
        except Exception as e:
            print(f"⚠️  Expected error getting response (no audio): {e}")
        
    except Exception as e:
        print(f"❌ STREAMING_RECOGNIZE ERROR: {e}")
        print(f"📋 Error type: {type(e)}")
        print(f"📋 Error args: {e.args}")
        
        # Check if this is the SpeechHelpers error
        if "SpeechHelpers" in str(e):
            print("🎯 THIS IS THE SPEECHHELPERS ERROR!")
            print("🔍 Investigating further...")
            
            # Look for anything named SpeechHelpers
            import sys
            for module_name, module in sys.modules.items():
                if module and hasattr(module, 'SpeechHelpers'):
                    print(f"⚠️  Found SpeechHelpers in module: {module_name}")
                    helpers = getattr(module, 'SpeechHelpers')
                    print(f"   📋 SpeechHelpers type: {type(helpers)}")
                    print(f"   📋 SpeechHelpers dir: {dir(helpers)}")
        
    print()
    print("🔍 LIBRARY VERSION INFORMATION")
    print("-" * 40)
    
    try:
        import google.cloud.speech as gcs
        print(f"📋 google-cloud-speech version: {getattr(gcs, '__version__', 'unknown')}")
    except:
        pass
    
    try:
        import google.api_core
        print(f"📋 google-api-core version: {getattr(google.api_core, '__version__', 'unknown')}")
    except:
        pass
    
    try:
        import grpc
        print(f"📋 grpcio version: {getattr(grpc, '__version__', 'unknown')}")
    except:
        pass

def test_direct_streaming_call():
    """Test calling streaming_recognize directly with proper arguments"""
    print("\n🧪 TESTING DIRECT STREAMING CALL")
    print("=" * 50)
    
    client = speech.SpeechClient()
    
    # Create proper request with all required arguments
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code='nl-NL'
    )
    
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True
    )
    
    # Create a single request
    request = speech.StreamingRecognizeRequest(streaming_config=streaming_config)
    
    try:
        print("📋 Calling streaming_recognize with single request...")
        response_stream = client.streaming_recognize([request])
        print(f"✅ Success! Response stream: {type(response_stream)}")
        
        # Try to iterate (will likely fail without audio but that's expected)
        try:
            for response in response_stream:
                print(f"📋 Got response: {response}")
                break  # Just get the first one
        except Exception as e:
            print(f"⚠️  Expected iteration error (no audio): {e}")
            
    except Exception as e:
        print(f"❌ Direct call failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Set up logging to see what's happening
    logging.basicConfig(level=logging.DEBUG)
    
    try:
        debug_speech_client()
        
        print("\n" + "=" * 60)
        success = test_direct_streaming_call()
        
        if success:
            print("\n✅ DIAGNOSIS: The method call works, the issue is likely in how requests are being generated")
            print("💡 SOLUTION: Check the request generator implementation in streaming_stt.py")
        else:
            print("\n❌ DIAGNOSIS: There's a deeper issue with the streaming_recognize method")
            print("💡 SOLUTION: May need to investigate library versions or environment")
        
    except Exception as e:
        print(f"❌ Debug script failed: {e}")
        import traceback
        traceback.print_exc()
