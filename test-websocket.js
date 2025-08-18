#!/usr/bin/env node

const WebSocket = require('ws');

// Test WebSocket connection to the backend
const WS_URL = 'wss://streaming-stt-service-ysw2dobxea-ew.a.run.app';
const STREAM_ID = 'test-connection';

console.log('🔍 Testing WebSocket connection to backend...');

// Test speaker connection
const speakerUrl = `${WS_URL}/ws/speak/${STREAM_ID}`;
console.log(`📡 Connecting to speaker endpoint: ${speakerUrl}`);

const speakerWs = new WebSocket(speakerUrl);

speakerWs.on('open', () => {
    console.log('✅ Speaker WebSocket connected successfully!');
    
    // Test listener connection
    const listenerUrl = `${WS_URL}/ws/listen/${STREAM_ID}`;
    console.log(`👂 Connecting to listener endpoint: ${listenerUrl}`);
    
    const listenerWs = new WebSocket(listenerUrl);
    
    listenerWs.on('open', () => {
        console.log('✅ Listener WebSocket connected successfully!');
        
        // Send test message to verify broadcasting works
        console.log('📤 Testing message broadcasting...');
        speakerWs.send(JSON.stringify({
            type: 'test',
            message: 'Hello from test script'
        }));
        
        setTimeout(() => {
            console.log('✅ WebSocket connection test completed successfully!');
            console.log('🎯 Both speaker and listener endpoints are working.');
            speakerWs.close();
            listenerWs.close();
            process.exit(0);
        }, 2000);
    });
    
    listenerWs.on('message', (data) => {
        console.log('📥 Listener received:', data.toString());
    });
    
    listenerWs.on('error', (error) => {
        console.error('❌ Listener WebSocket error:', error.message);
        speakerWs.close();
        process.exit(1);
    });
});

speakerWs.on('error', (error) => {
    console.error('❌ Speaker WebSocket error:', error.message);
    console.error('🔧 This might indicate a backend connectivity issue.');
    process.exit(1);
});

speakerWs.on('close', (code, reason) => {
    console.log(`🔌 Speaker WebSocket closed: ${code} ${reason}`);
});

// Timeout after 10 seconds
setTimeout(() => {
    console.error('⏱️  Connection test timed out');
    process.exit(1);
}, 10000);