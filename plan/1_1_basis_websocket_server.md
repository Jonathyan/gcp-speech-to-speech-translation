Nu ga ik TDD toepassen. Schrijf EERST de test voor Iteratie 1:

Test vereisten:
- pytest test-client die WebSocket verbinding maakt met /ws endpoint
- Test moet slagen bij HTTP status 101 (Switching Protocols)
- Test moet aantonen dat verbinding succesvol geaccepteerd wordt

Maak een test_websocket.py met:
1. Correcte pytest imports voor FastAPI WebSocket testing
2. Test fixture voor FastAPI test client
3. Eén test functie die de WebSocket verbinding test
4. Duidelijke assertions voor status code 101

De test moet FALEN op dit moment (want implementatie bestaat nog niet).



---



Nu de implementatie voor iteratie 1 op mijn macbook m1 om de test te laten slagen:

Maak een main.py met:
1. FastAPI app instantie
2. WebSocket endpoint /ws dat:
   - Verbinding accepteert met websocket.accept()
   - "Client connected" print naar console
   - Basis connection handling

Houd het minimaal - alleen wat nodig is om de test te laten slagen.
Voeg ook een __main__ block toe om de server lokaal te kunnen draaien.



---



