/**
 * WAV Audio Encoder for Speech-to-Speech Translation
 * 
 * Generates LINEAR16 PCM WAV files directly in the browser using Web Audio API.
 * This eliminates the need for server-side audio conversion and provides 
 * optimal compatibility with Google Cloud Speech-to-Text API.
 */

class WAVEncoder {
    constructor(sampleRate = 16000, channels = 1, bitDepth = 16) {
        this.sampleRate = sampleRate;
        this.channels = channels;
        this.bitDepth = bitDepth;
        this.bytesPerSample = bitDepth / 8;
        this.blockAlign = channels * this.bytesPerSample;
    }

    /**
     * Encode Float32Array audio buffer to WAV format
     * @param {Float32Array} audioBuffer - Audio data from Web Audio API
     * @returns {ArrayBuffer} WAV file data
     */
    encode(audioBuffer) {
        const length = audioBuffer.length;
        const dataLength = length * this.bytesPerSample;
        const headerLength = 44;
        const totalLength = headerLength + dataLength;
        
        const arrayBuffer = new ArrayBuffer(totalLength);
        const view = new DataView(arrayBuffer);
        
        // Write WAV header
        this._writeWAVHeader(view, dataLength);
        
        // Convert float samples to 16-bit PCM
        this._writeAudioData(view, headerLength, audioBuffer);
        
        return arrayBuffer;
    }

    /**
     * Write WAV file header
     * @param {DataView} view - DataView for the output buffer
     * @param {number} dataLength - Length of audio data in bytes
     */
    _writeWAVHeader(view, dataLength) {
        const fileSize = 36 + dataLength;
        
        // RIFF chunk descriptor
        this._writeString(view, 0, 'RIFF');
        view.setUint32(4, fileSize, true);                    // File size - 8
        this._writeString(view, 8, 'WAVE');
        
        // fmt sub-chunk
        this._writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);                         // Sub-chunk size (16 for PCM)
        view.setUint16(20, 1, true);                          // Audio format (1 = PCM)
        view.setUint16(22, this.channels, true);              // Number of channels
        view.setUint32(24, this.sampleRate, true);            // Sample rate
        view.setUint32(28, this.sampleRate * this.blockAlign, true); // Byte rate
        view.setUint16(32, this.blockAlign, true);            // Block align
        view.setUint16(34, this.bitDepth, true);              // Bits per sample
        
        // data sub-chunk
        this._writeString(view, 36, 'data');
        view.setUint32(40, dataLength, true);                 // Data chunk size
    }

    /**
     * Convert float audio data to 16-bit PCM and write to buffer
     * @param {DataView} view - DataView for the output buffer
     * @param {number} offset - Byte offset to start writing audio data
     * @param {Float32Array} audioBuffer - Input audio data
     */
    _writeAudioData(view, offset, audioBuffer) {
        for (let i = 0; i < audioBuffer.length; i++) {
            // Convert float (-1.0 to 1.0) to 16-bit signed integer
            const sample = Math.max(-1, Math.min(1, audioBuffer[i]));
            const pcmSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
            view.setInt16(offset + i * 2, pcmSample, true);
        }
    }

    /**
     * Write ASCII string to DataView
     * @param {DataView} view - DataView to write to
     * @param {number} offset - Byte offset
     * @param {string} string - String to write
     */
    _writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }
}

/**
 * Professional Audio Recorder using Web Audio API
 * 
 * Replaces MediaRecorder with a more reliable approach that generates
 * LINEAR16 WAV audio directly, eliminating conversion issues.
 */
class ProfessionalAudioRecorder {
    constructor(config = {}) {
        this.audioContext = null;
        this.sourceNode = null;
        this.processorNode = null;
        this.mediaStream = null;
        this.wavEncoder = new WAVEncoder(16000, 1, 16);
        this.isRecording = false;
        this.onDataAvailable = null;
        this.chunkBuffer = [];
        this.chunkSize = config.chunkSize || 2048; // Reduced from 4096 for lower latency
        this.chunkIntervalMs = config.chunkIntervalMs || 250; // CRITICAL FIX: 250ms instead of 2000ms!
        this.lastChunkTime = 0;
        
        console.log(`ProfessionalAudioRecorder initialized: chunkSize=${this.chunkSize}, chunkInterval=${this.chunkIntervalMs}ms`);
    }

    /**
     * Start recording audio
     * @param {object} constraints - Audio constraints
     * @returns {Promise<void>}
     */
    async startRecording(constraints = {}) {
        try {
            // Request microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    ...constraints.audio
                }
            });

            // Create audio context with optimal settings
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000,
                latencyHint: 'interactive'
            });

            // Create source node from media stream
            this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

            // Create processor node for real-time audio processing
            // Note: ScriptProcessorNode is deprecated but AudioWorklet requires more setup
            this.processorNode = this.audioContext.createScriptProcessor(this.chunkSize, 1, 1);
            
            // Set up audio processing
            this.processorNode.onaudioprocess = (event) => {
                if (!this.isRecording) return;
                
                const inputBuffer = event.inputBuffer;
                const audioData = inputBuffer.getChannelData(0); // Get mono channel
                
                // Add to chunk buffer
                this.chunkBuffer.push(new Float32Array(audioData));
                
                // Check if it's time to send a chunk
                const now = Date.now();
                if (now - this.lastChunkTime >= this.chunkIntervalMs) {
                    this._processChunkBuffer();
                    this.lastChunkTime = now;
                }
            };

            // Connect audio nodes
            this.sourceNode.connect(this.processorNode);
            this.processorNode.connect(this.audioContext.destination);

            this.isRecording = true;
            this.lastChunkTime = Date.now();
            
            console.log('Professional audio recording started with Web Audio API');
            console.log(`Sample rate: ${this.audioContext.sampleRate}Hz, Chunk size: ${this.chunkSize}`);

        } catch (error) {
            console.error('Failed to start professional audio recording:', error);
            throw error;
        }
    }

    /**
     * Stop recording audio
     */
    stopRecording() {
        if (!this.isRecording) return;

        this.isRecording = false;

        // Process any remaining chunks
        if (this.chunkBuffer.length > 0) {
            this._processChunkBuffer();
        }

        // Clean up audio nodes
        if (this.processorNode) {
            this.processorNode.disconnect();
            this.processorNode = null;
        }

        if (this.sourceNode) {
            this.sourceNode.disconnect();
            this.sourceNode = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Stop media stream
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        console.log('Professional audio recording stopped');
    }

    /**
     * Process accumulated audio chunks and generate WAV data
     */
    _processChunkBuffer() {
        if (this.chunkBuffer.length === 0) return;

        // Calculate total length
        const totalLength = this.chunkBuffer.reduce((sum, chunk) => sum + chunk.length, 0);
        
        // Combine all chunks into single buffer
        const combinedBuffer = new Float32Array(totalLength);
        let offset = 0;
        
        for (const chunk of this.chunkBuffer) {
            combinedBuffer.set(chunk, offset);
            offset += chunk.length;
        }

        // Encode to WAV format
        const wavData = this.wavEncoder.encode(combinedBuffer);
        
        // Create blob and call callback
        const blob = new Blob([wavData], { type: 'audio/wav' });
        
        if (this.onDataAvailable) {
            this.onDataAvailable({ data: blob });
        }

        // Clear buffer for next chunk
        this.chunkBuffer = [];
        
        console.log(`Processed audio chunk: ${totalLength} samples → ${wavData.byteLength} bytes WAV`);
    }

    /**
     * Set callback for audio data availability
     * @param {function} callback - Function to call with audio data
     */
    setOnDataAvailable(callback) {
        this.onDataAvailable = callback;
    }

    /**
     * Get current recording state
     * @returns {boolean} Whether recording is active
     */
    getRecordingState() {
        return this.isRecording;
    }

    /**
     * Get audio context sample rate
     * @returns {number} Sample rate in Hz
     */
    getSampleRate() {
        return this.audioContext ? this.audioContext.sampleRate : 16000;
    }
}

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { WAVEncoder, ProfessionalAudioRecorder };
}

// Global for browser
if (typeof window !== 'undefined') {
    window.WAVEncoder = WAVEncoder;
    window.ProfessionalAudioRecorder = ProfessionalAudioRecorder;
}