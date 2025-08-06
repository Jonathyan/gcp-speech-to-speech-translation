# Plan: Gefaseerde Bouw van Live Vertaalservice (Fase 1)

Dit document beschrijft de stapsgewijze ontwikkeling van de live vertaalservice met een Test-Driven Development (TDD) aanpak. Elke iteratie is een kleine, afgebakende stap die onafhankelijk getest kan worden, wat zorgt voor een robuuste en voorspelbare codebase. De TDD-methode dwingt ons om eerst na te denken over het *gewenste gedrag* (de test) voordat we de implementatie schrijven, wat leidt tot een beter ontwerp en minder bugs.

**Technologie Stack:**

* **Backend:** Python met FastAPI (voor WebSockets), gehost op Google Cloud Run. FastAPI is gekozen vanwege zijn hoge prestaties en uitstekende, ingebouwde ondersteuning voor asynchrone operaties en WebSockets, wat essentieel is voor een real-time applicatie. De asynchrone aard ervan stelt de server in staat om efficiënt te wachten op API-antwoorden zonder andere verbindingen te blokkeren.
* **Frontend:** Plain HTML, CSS, en JavaScript, gehost op Firebase Hosting. Deze keuze minimaliseert de complexiteit en opstartkosten, ideaal voor een snelle validatie van het product. We vermijden bewust grote frameworks om de ontwikkelsnelheid in deze fase te maximaliseren.
* **Testen:** `pytest` voor de backend, vanwege zijn eenvoud, krachtige features zoals 'fixtures', en de naadloze integratie met FastAPI. Voor de frontend wordt `jest` aangeraden voor het testen van de JavaScript-logica in een gesimuleerde browseromgeving.

![Alt tekst](gcp-arch.png "Solution Architecture in GCP")

---

## Deel 1: Backend Ontwikkeling (Cloud Run Service)

We bouwen eerst de kernlogica van de service. De focus ligt op het creëren van een stabiele pijplijn voordat we de gebruikersinterface aanpakken. Dit 'backend-first' principe zorgt ervoor dat de meest complexe logica al bewezen en stabiel is voordat we tijd investeren in de visuele laag.

### Iteratie 1: Basis WebSocket Server

* **Doel:** De fundering leggen. We hebben een server nodig die luistert naar inkomende verbindingen. Dit is de meest basale "levenscheck" van onze backend; als dit niet werkt, werkt niets.
* **TDD - Schrijf eerst deze test:**
    1.  Maak een `pytest` test-client die een WebSocket-verbinding probeert op te zetten met het `/ws` endpoint van de FastAPI server.
    2.  De test slaagt als de verbinding succesvol wordt geaccepteerd, wat resulteert in een HTTP status code 101 ("Switching Protocols"). Deze code is de formele bevestiging dat de server akkoord gaat met het upgraden van de HTTP-verbinding naar een persistente WebSocket-verbinding.
* **Implementatie - Vraag de LLM om:**
    1.  Een `main.py` te maken met een standaard FastAPI app-instantie.
    2.  Een WebSocket endpoint `/ws` toe te voegen dat een inkomende verbinding accepteert met `websocket.accept()` en een "Client connected" bericht print op de server ter bevestiging. Dit logbericht is cruciaal voor de eerste fase van debugging.

### Iteratie 2: Echo Service met Error Handling

* **Doel:** Bevestigen dat de tweerichtingscommunicatie werkt. De server moet niet alleen verbindingen accepteren, maar ook data kunnen ontvangen en correct terugsturen. Dit valideert dat onze dataformaten en de verbinding stabiel zijn.
* **TDD - Schrijf eerst deze test:**
    1.  De test-client verbindt met `/ws`.
    2.  De client stuurt een gestructureerd JSON-bericht, bijvoorbeeld `{"type": "greeting", "payload": "hallo"}`. Het gebruik van een gestructureerd formaat is een goede gewoonte voor toekomstige uitbreidingen.
    3.  De test slaagt als de client exact hetzelfde JSON-bericht terugkrijgt van de server, wat de data-integriteit en het serialisatie/deserialisatieproces bevestigt.
* **Implementatie - Vraag de LLM om:**
    1.  De `/ws` endpoint-functie aan te passen met een `while True` loop om continu te luisteren naar berichten, ingebed in een `try...except` blok om netjes af te sluiten wanneer de client de verbinding verbreekt.
    2.  Binnen de loop, gebruik `websocket.receive_json()` en stuur het ontvangen object direct terug met `websocket.send_json()`.

### Iteratie 3: Mocked API Pijplijn met Foutsimulatie

* **Doel:** De volledige applicatielogica simuleren zonder afhankelijkheid van externe (en kostbare) API's. Dit stelt ons in staat om de flow, de asynchrone aanroepen en de timing van de hele pijplijn te testen in een geïsoleerde, voorspelbare omgeving.
* **TDD - Schrijf eerst deze test:**
    1.  De test-client stuurt een binair audio-chunk (een willekeurige byte-string is voldoende, bv. `b'\x01\x02\x03'`).
    2.  De test slaagt als de client na een korte, voorspelbare vertraging (ca. 150ms, de som van de mock-vertragingen) een ander binair audio-chunk terugkrijgt, wat de "vertaalde" audio representeert. Dit valideert de end-to-end flow.
* **Implementatie - Vraag de LLM om:**
    1.  Drie asynchrone placeholder (mock) functies te maken. Het `async def` en `await asyncio.sleep()` is cruciaal om het wachten op een echte netwerk-API te simuleren.
        *   `async def mock_speech_to_text(audio_chunk)`: Wacht 50ms en geeft de string `"mocked text"` terug. Simuleer af en toe een error.
        *   `async def mock_translation(text)`: Wacht 50ms en geeft de string `"mocked translation"` terug.
        *   `async def mock_text_to_speech(text)`: Wacht 50ms en geeft een hardcoded byte-string `b'mock_audio_output'` terug.
    2.  De `/ws` handler aan te passen om deze drie functies na elkaar aan te roepen (met `await`) wanneer er een audio-chunk binnenkomt via `websocket.receive_bytes()`.
*   **Aanvullende overwegingen:**
    *   Voeg logica toe om willekeurig fouten te genereren in de mock API's (bijvoorbeeld met behulp van `random.random()`).
    *   Test hoe de applicatie omgaat met deze fouten (retry, fallback, error logging).

### Iteratie 4: Integratie Speech-to-Text API met Environment Variabelen

* **Doel:** De eerste stap van de pijplijn vervangen door een echte service. Dit is een cruciale integratietest die onze app verbindt met de buitenwereld en controleert op authenticatie-, configuratie- en netwerkproblemen.
* **TDD - Schrijf eerst deze test (integratietest):**
    1.  De test-client stuurt een echt, kort `.wav` audiofragment (bijv. een opname van "hallo wereld"). Het gebruik van een echt audiobestand is essentieel om de dataformattering te valideren.
    2.  De test slaagt als de server een JSON-bericht terugstuurt met de (ongeveer) correcte transcriptie: `{"text": "hallo wereld"}`. De Translation en TTS API's blijven gemockt, zodat we de test isoleren tot alleen de STT-integratie.
* **Implementatie - Vraag de LLM om:**
    1.  De `google-cloud-speech` library toe te voegen aan `requirements.txt`.
    2.  De `mock_speech_to_text` functie te vervangen door een echte implementatie die de streaming `recognize` functie van de API gebruikt. Dit is complexer dan een simpele call en vereist het correct configureren van de stream.
    3.  Authenticatie via een service account JSON-sleutel te configureren, waarbij de bestandsnaam uit een environment variable wordt gelezen (`os.getenv('GOOGLE_APPLICATION_CREDENTIALS')`). Dit is een security best practice om te voorkomen dat sleutels in de code worden vastgelegd.

### Iteratie 5 & 6: Integratie Translation & TTS API met Monitoring

* **Doel:** De volledige pijplijn operationeel maken met echte, externe services en de end-to-end latency valideren.
* **Proces:** Herhaal het proces van Iteratie 4 voor de andere twee API's, stap voor stap. Dit voorkomt dat we meerdere integratieproblemen tegelijk moeten debuggen.
    * **Iteratie 5 (Translation):** Vervang `mock_translation`. De test stuurt nu een Nederlandse zin en slaagt als de (ongeveer) correcte Engelse vertaling wordt ontvangen. We testen op de aanwezigheid van het Engelse equivalent, niet op een exacte string, omdat vertalingen kunnen variëren.
    * **Iteratie 6 (TTS):** Vervang `mock_text_to_speech`. De test stuurt een zin en slaagt als het een binair audio-chunk (geen lege byte-string en met een plausibele lengte) terugkrijgt.

### Iteratie 7: Broadcasting naar Meerdere Luisteraars

* **Doel:** De applicatie omvormen van een 1-op-1 service naar een 1-op-veel uitzendplatform. Dit introduceert state management.
* **TDD - Schrijf eerst deze test:**
    1.  Simuleer twee "luisteraar"-clients die verbinden met `/ws/listen/{stream_id}`.
    2.  Simuleer één "spreker"-client die verbindt met `/ws/speak/{stream_id}` en een audio-chunk stuurt. De `stream_id` is de sleutel die de spreker aan de luisteraars koppelt.
    3.  De test slaagt als **beide** luisteraar-clients het uiteindelijke vertaalde audio-chunk ontvangen. De spreker-client mag niets terugkrijgen.
* **Implementatie - Vraag de LLM om:**
    1.  Een `ConnectionManager` klasse te maken die in een dictionary per `stream_id` een lijst van actieve luisteraar-WebSocket-objecten bijhoudt. Deze klasse moet ook methodes hebben om verbindingen toe te voegen, te verwijderen en te broadcasten.
    2.  De WebSocket-logica op te splitsen in twee endpoints: `/ws/speak/{stream_id}` en `/ws/listen/{stream_id}`.
    3.  Wanneer de spreker iets stuurt, moet de server de pijplijn doorlopen en het resultaat naar alle luisteraars in de `ConnectionManager` voor die `stream_id` sturen met de `broadcast` methode.
*   **Aanvullende overwegingen:**
    *   Gebruik een thread-safe datastructuur voor de dictionary in de `ConnectionManager` om concurrentie te voorkomen (bijvoorbeeld `threading.Lock`).
    *   Implementeer logging om verbindingen en disconnecties te volgen.
    *   Overweeg het gebruik van een message queue (zoals Google Cloud Pub/Sub) voor het broadcasten van berichten naar de luisteraars.

### Iteratie 8: Basis UI & WebSocket Connectie

*   **Doel:** Een visuele interface creëren en de connectiviteit met de backend valideren vanuit een echte browseromgeving.
*   **TDD - Schrijf eerst deze test:**
    1.  Maak een test die de webpagina laadt in een gesimuleerde DOM (met `jest`).
    2.  De test simuleert een klik op een "Start Uitzending" knop.
    3.  De test slaagt als het JavaScript een WebSocket-verbinding probeert op te zetten (mock de `WebSocket` constructor) en de statusindicator op de pagina wordt geüpdatet naar "Verbinden...".
*   **Implementatie - Vraag de LLM om:**
    1.  Een `index.html` te maken met knoppen voor "Start Uitzending" en "Luister mee", en een `<div>` voor statusberichten.

---

## Deel 2: Frontend Ontwikkeling (Web App)

We bouwen de interface voor de spreker en de luisteraar.

### Iteratie 8: Basis UI & WebSocket Connectie

### Iteratie 9: Audio Opvangen en Versturen (Spreker)
* **Implementatie - Vraag de LLM om:**
    1.  De `app.js` uit te breiden.
    2.  Gebruik `navigator.mediaDevices.getUserMedia` om toegang tot de microfoon te vragen, met een correcte afhandeling voor als de gebruiker toestemming weigert.
    3.  Gebruik de `MediaRecorder` API om de audio in kleine chunks (bv. elke 250ms, een goede balans tussen lage latency en netwerk-overhead) op te nemen en elk chunk direct via de WebSocket te versturen.

### Iteratie 10: Audio Ontvangen en Afspelen (Luisteraar)

* **Doel:** De kernfunctionaliteit voor de luisteraar implementeren: het naadloos afspelen van de inkomende audiostream.
* **TDD - Schrijf eerst deze test:**
    1.  De test simuleert een inkomend audio-chunk (als `ArrayBuffer`) via de WebSocket.
    2.  De test slaagt als er een `AudioBuffer` wordt gemaakt en de `AudioBufferSourceNode.start()` methode wordt aangeroepen om het afspelen te starten (mock de Web Audio API).
* **Implementatie - Vraag de LLM om:**
    1.  De `app.js` verder uit te breiden.
    2.  Gebruik de **Web Audio API** om een `AudioContext` te creëren. Dit is cruciaal voor het naadloos aan elkaar plakken van audio.
    3.  Wanneer een audio-chunk binnenkomt, decodeer het met `audioContext.decodeAudioData` en plaats het in een queue (een simpele JavaScript array).
    4.  Implementeer een afspeel-mechanisme dat de audio-chunks uit de queue naadloos achter elkaar afspeelt om een continue, ononderbroken stroom te creëren, en rekening houdt met netwerk-jitter.

---
 
## Deel 3: Deployment

### Iteratie 11: Deployment naar GCP & Firebase

* **Doel:** De ontwikkelde service toegankelijk maken op het internet en de productieomgeving configureren.
* **Stappen (geen TDD, maar configuratie):**
    1.  **Backend:** Vraag de LLM om een `Dockerfile` te maken voor de FastAPI-applicatie. Zorg ervoor dat `uvicorn` wordt gebruikt als webserver en dat de poort wordt ingesteld via een `$PORT` environment variable, zoals vereist door Cloud Run.
    2.  Vraag om de `gcloud` commando's om de container te bouwen, naar Artifact Registry te pushen, en te deployen naar Cloud Run. Inclusief het instellen van environment variables voor de service account en het toestaan van niet-geauthenticeerde aanroepen.
    3.  **Frontend:** Vraag om de `firebase.json` configuratie voor het hosten van de statische bestanden. Het is belangrijk om hier de juiste caching-headers in te stellen.
    4.  Vraag om de `firebase` commando's (`firebase init`, `firebase deploy`) om de HTML/CSS/JS bestanden te deployen naar Firebase Hosting.
    5.  Zorg ervoor dat de frontend-code de publieke URL van de Cloud Run service gebruikt voor de WebSocket-verbinding, idealiter via een configuratiebestand of environment variable.
