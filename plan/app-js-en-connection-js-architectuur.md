⏺ Ik ga eerst de relevante bestanden bekijken om een accuraat diagram te
  maken:

⏺ Read(frontend/src/app.js)
  ⎿  Read 71 lines (ctrl+r to expand)

⏺ Read(frontend/src/connection.js)
  ⎿  Read 655 lines (ctrl+r to expand)

⏺ Nu ga ik een gedetailleerd ASCII architectuur diagram maken van hoe
  app.js en connection.js samenwerken:

  ┌─────────────────────────────────────────────────────────────────────────────────────────┐
  │                    FRONTEND ARCHITECTUUR: APP.JS ↔ CONNECTION.JS.                       │
  ├─────────────────────────────────────────────────────────────────────────────────────────┤
  │                                                                                         │
  │ ┌─────────────────────────────────────────────────────────────────────────────────────┐ │
  │ │                                   APP.JS                                            │ │
  │ │                            (Main Entry Point)                                       │ │
  │ │                                                                                     │ │
  │ │  🚀 APPLICATIE OPSTARTEN                                                            │ │
  │ │  ┌─────────────────────┐                                                            │ │
  │ │  │ DOMContentLoaded    │   ──────────────────────────────────────────────────────┐  │ │
  │ │  │ Event Listener      │                                                         │  │ │
  │ │  └─────────────────────┘                                                         │  │ │
  │ │            │                                                                     │  │ │
  │ │            ▼                                                                     │  │ │
  │ │  ┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────────┐  │  │ │
  │ │  │ Browser             │    │ UI Initialisatie    │    │ Global  Functions    │  │  │ │
  │ │  │ Compatibility       │    │ window.AppUI        │    │ Export voor  Tests   │  │  │ │
  │ │  │ Check               │    │ .initializeUI()     │    │                      │  │  │ │
  │ │  └─────────────────────┘    └─────────────────────┘    └──────────────────────┘  │  │ │
  │ │                                                                                  │  │ │
  │ │                                     ▼                                            │  │ │
  │ │  ┌─────────────────────────────────────────────────────────────────────────────┐ │  │ │
  │ │  │                          KNOP ENABLEMENT                                    │ │  │ │
  │ │  │  • start-broadcast button →  window.AppConnection.connectWebSocket()        │ │  │ │
  │ │  │  • join-listener button   →  window.AppConnection.connectWebSocket()        │ │  │ │
  │ │  └─────────────────────────────────────────────────────────────────────────────┘ │  │ │
  │ └─────────────────────────────────────────────────────────────────────────────────────┘ │
  │                                            │                                           │
  │                                            ▼                                           │
  │ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
  │ │                                CONNECTION.JS                                       │ │
  │ │                           (WebSocket Management)                                   │ │
  │ ├────────────────────────────────────────────────────────────────────────────────────┤ │
  │ │                                                                                    │ │
  │ │  📡 WEBSOCKET VERBINDING MANAGEMENT                                                │ │
  │ │  ┌─────────────────────┐                                                           │ │
  │ │  │ connectWebSocket()  │                                                           │ │
  │ │  │ (url, mode,         │                                                           │ │
  │ │  │  streamId)          │                                                           │ │
  │ │  └─────────────────────┘                                                           │ │
  │ │            │                                                                       │ │
  │ │            ▼                                                                       │ │
  │ │  ┌─────────────────────────────────────────────────────────────────────────────┐   │ │
  │ │  │                      MODE BEPALING                                          │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  mode === 'broadcast'  → /ws/speak/{streamId}                               │   │ │
  │ │  │  mode === 'streaming'  → /ws/stream/{streamId}  ⭐ REALTIME VERTALING       │   │ │
  │ │  │  mode === 'listener'   → /ws/listen/{streamId}                              │   │ │
  │ │  └─────────────────────────────────────────────────────────────────────────────┘   │ │
  │ │                                     │                                              │ │
  │ │                                     ▼                                              │ │
  │ │  ┌─────────────────────────────────────────────────────────────────────────────┐   │ │
  │ │  │                     WEBSOCKET LIFECYCLE                                     │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  onopen   ──► retryCount = 0                                                │   │ │
  │ │  │           ──► handleConnectionSuccess(mode)                                 │   │ │
  │ │  │           ──► window.AppUI.updateStatus("Verbonden...")                     │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  onclose  ──► handleCleanDisconnect() OR                                    │   │ │
  │ │  │           ──► handleConnectionError(url, mode, streamId)                    │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  onerror  ──► handleConnectionError() met retry logica                      │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  onmessage ──► handleIncomingMessage() OF                                   │   │ │
  │ │  │            ──► handleIncomingAudioData()                                    │   │ │
  │ │  └─────────────────────────────────────────────────────────────────────────────┘   │ │
  │ │                                     │                                              │ │
  │ │                                     ▼                                              │ │
  │ │  ┌─────────────────────────────────────────────────────────────────────────────┐   │ │
  │ │  │                    MESSAGE VERWERKING                                       │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  📨 TEXT BERICHTEN:                                                         │   │ │
  │ │  │     • JSON Control Messages                                                 │   │ │
  │ │  │       - type: 'keepalive' → handleKeepalivePing()                           │   │ │
  │ │  │       - type: 'audio_start' → handleAudioStreamStart()                      │   │ │
  │ │  │       - type: 'audio_end' → handleAudioStreamEnd()                          │   │ │
  │ │  │       - type: 'error' → console.error()                                     │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  🔊 AUDIO DATA:                                                             │   │ │
  │ │  │     • ArrayBuffer/Blob → processAudioData()                                 │   │ │
  │ │  │     • MP3 playback via HTML5 Audio API                                      │   │ │
  │ │  │     • Test markers → playTestBeep()                                         │   │ │
  │ │  └─────────────────────────────────────────────────────────────────────────────┘   │ │
  │ │                                     │                                              │ │
  │ │                                     ▼                                              │ │
  │ │  ┌─────────────────────────────────────────────────────────────────────────────┐   │ │
  │ │  │                     AUDIO VERWERKING                                        │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  🎧 initializeAudioPlayer()                                                 │   │ │
  │ │  │     │                                                                       │   │ │
  │ │  │     ▼                                                                       │   │ │
  │ │  │  processAudioData(audioData)                                                │   │ │
  │ │  │     │                                                                       │   │ │
  │ │  │     ├─► ArrayBuffer/Blob Check                                              │   │ │
  │ │  │     ├─► Test Marker Detection                                               │   │ │
  │ │  │     ├─► MP3 Blob Creation                                                   │   │ │
  │ │  │     └─► HTML5 Audio Playback                                                │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  📊 AUDIO STATISTIEKEN:                                                     │   │ │
  │ │  │     • chunksReceived, bytesReceived                                         │   │ │
  │ │  │     • chunksProcessed, processingErrors                                     │   │ │
  │ │  └─────────────────────────────────────────────────────────────────────────────┘   │ │
  │ │                                     │                                              │ │
  │ │                                     ▼                                              │ │
  │ │  ┌─────────────────────────────────────────────────────────────────────────────┐   │ │
  │ │  │                     RETRY LOGICA                                            │   │ │
  │ │  │                                                                             │   │ │
  │ │  │  handleConnectionError():                                                   │   │ │
  │ │  │     │                                                                       │   │ │
  │ │  │     ├─► retryCount < maxRetries?                                            │   │ │
  │ │  │     │   └─► JA: exponential backoff delay                                   │   │ │
  │ │  │     │       └─► setTimeout(() => connectWebSocket())                        │   │ │
  │ │  │     │                                                                       │   │ │
  │ │  │     └─► NEE: geef op en toon error                                          │   │ │
  │ │  │          └─► window.AppUI.updateStatus("Verbinding mislukt...")             │   │ │
  │ │  └─────────────────────────────────────────────────────────────────────────────┘   │ │
  │ └────────────────────────────────────────────────────────────────────────────────────┘ │
  │                                            │                                           │
  │                                            ▼                                           │
  │ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
  │ │                             UI INTEGRATIE                                          │ │
  │ ├────────────────────────────────────────────────────────────────────────────────────┤ │
  │ │                                                                                    │ │
  │ │  📱 UI STATUS UPDATES:                                                             │ │
  │ │  ┌────────────────────┐     ┌────────────────────┐     ┌─────────────────────┐     │ │
  │ │  │ connection.js      │────▶│   window.AppUI     │────▶│    DOM Elements     │     │ │
  │ │  │                    │     │                    │     │                     │     │ │
  │ │  │ • updateStatus()   │     │ • updateStatus()   │     │ • Status text       │     │ │
  │ │  │ • enableButtons()  │     │ • enableButtons()  │     │ • Button states     │     │ │
  │ │  │ • showError()      │     │ • showError()      │     │ • Error messages    │     │ │
  │ │  └────────────────────┘     └────────────────────┘     └─────────────────────┘     │ │
  │ └────────────────────────────────────────────────────────────────────────────────────┘ │
  │                                                                                        │
  └────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW DIAGRAM                                           │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  👤 GEBRUIKER ACTIE                                                                      │
│       │                                                                                  │
│       ▼                                                                                  │
│  ┌──────────────┐    DOM Event   ┌─────────────────┐    Global Call     ┌──────────────┐ │
│  │ Button Click │ ─────────────► │    app.js       │ ─────────────────► │ connection.js│ │
│  │              │                │                 │                    │              │ │
│  │ • Broadcast  │                │ • Compatibility │                    │ • WebSocket  │ │
│  │ • Listen     │                │ • UI Init       │                    │ • Retry      │ │
│  └──────────────┘                │ • Export Globals│                    │ • Audio      │ │
│                                  └─────────────────┘                    └──────────────┘ │
│                                          │                                      │        │
│                                          ▼                                      ▼        │
│                                 ┌─────────────────┐                   ┌──────────────┐   │
│                                 │  window.AppUI   │◄──────────────────│  WebSocket   │   │
│                                 │                 │    Status Updates │  Messages    │   │
│                                 │ • Status Text   │                   │              │   │
│                                 │ • Button States │                   │ • Control    │   │
│                                 │ • Error Display │                   │ • Audio Data │   │
│                                 └─────────────────┘                   │ • Keepalive  │   │
│                                          │                            └──────────────┘   │
│                                          ▼                                     │         │
│                                 ┌─────────────────┐                            ▼         │
│                                 │   DOM Update    │                   ┌──────────────┐   │
│                                 │                 │                   │ Audio Player │   │
│                                 │ • Visual Status │                   │              │   │
│                                 │ • User Feedback │                   │ • MP3 Play   │   │
│                                 └─────────────────┘                   │ • Test Beeps │   │
│                                                                       │ • Statistics │   │
│                                                                       └──────────────┘   │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                           BELANGRIJKE INTERACTIES                                        │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  🔄 APP.JS → CONNECTION.JS:                                                              │
│     • window.AppConnection.connectWebSocket(url, mode, streamId)                         │
│     • window.AppConnection.disconnectWebSocket()                                         │
│     • window.AppConnection.sendAudioChunk(websocket, audioData)                          │
│                                                                                          │
│  🔙 CONNECTION.JS → UI (via window.AppUI):                                               │
│     • window.AppUI.updateStatus(message)                                                 │
│     • window.AppUI.enableButtons(enabled)                                                │
│     • window.AppUI.showError(title, message, options)                                    │
│                                                                                          │
│  📊 STAAT BEHEER:                                                                        │
│     • currentWebSocket (global in connection.js)                                         │
│     • retryCount (connection retry logic)                                                │
│     • audioStats (audio processing statistics)                                           │
│     • userHasInteracted (autoplay policy compliance)                                     │
│                                                                                          │
│  🎯 FOUTAFHANDELING:                                                                     │
│     • Exponential backoff retry (2^retryCount * base delay)                              │
│     • Clean disconnect vs error disconnect                                               │
│     • Audio playback fallbacks (beep sounds)                                             │
│     • Browser autoplay policy handling                                                   │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

## Samenvatting van de Samenwerking

### 🚀 App.js Rol:
- **Entry Point**: Initialiseert de hele applicatie
- **Browser Compatibility**: Controleert of alles werkt
- **UI Setup**: Roept `window.AppUI.initializeUI()` aan
- **Global Exports**: Maakt functies beschikbaar voor tests
- **Event Binding**: Verbindt knoppen aan WebSocket functies

### 📡 Connection.js Rol:
- **WebSocket Beheer**: Volledige verbindingslogica
- **Mode Routing**: Verschillende endpoints per functie
- **Audio Processing**: Speelt ontvangen MP3 af
- **Retry Logic**: Automatisch opnieuw proberen bij fouten
- **Keepalive**: Houdt verbinding levend met ping/pong

### 🔗 Hoe Ze Samenwerken:
1. **App.js** initialiseert en maakt `window.AppConnection` functies beschikbaar
2. **Gebruiker klikt** op een knop → roept `connectWebSocket()` aan
3. **Connection.js** maakt WebSocket verbinding en handelt alle berichten af
4. **Status updates** gaan via `window.AppUI` terug naar de gebruiker
5. **Audio data** wordt direct afgespeeld via HTML5 Audio API

De architectuur is **modulair** en **robuust** met duidelijke scheiding tussen initialisatie (app.js) en verbindingsbeheer (connection.js).


