# debug_breaker.py
import asyncio
import pybreaker
import logging

logging.basicConfig(level=logging.INFO)

# Maak een simpele circuit breaker, net als in je app
breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)

# Een simpele asynchrone functie om te testen
async def my_async_task():
    print("Taak wordt uitgevoerd...")
    await asyncio.sleep(0.1)
    print("Taak voltooid.")
    return "OK"

# Hoofdfunctie om de test uit te voeren
async def main():
    # We kunnen de versie niet direct printen, maar we kunnen de locatie van de module printen om te verifiëren.
    print(f"Testen met pybreaker module geladen van: {pybreaker.__file__}")
    try:
        print("Proberen 'breaker.call_async(my_async_task)' aan te roepen...")
        result = await breaker.call_async(my_async_task)
        print(f"Succes! Resultaat: {result}")
    except Exception as e:
        print("\n--- FOUT GEVONDEN! ---")
        logging.error("De aanroep is mislukt met de volgende fout:", exc_info=True)
        print("--------------------")

if __name__ == "__main__":
    asyncio.run(main())
