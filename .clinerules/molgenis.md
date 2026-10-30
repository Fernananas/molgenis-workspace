# MOLGENIS EMX2 scripts

## Omgeving
- Lokale EMX2 draait via `docker compose up -d` in ../molgenis-emx2
- Controleer eerst of hij draait: `curl -s http://localhost:8080/api/graphql`
  Zo niet: start hem en wacht tot hij reageert.
- Test ALLEEN tegen schema `TEST_SCHEMA`, nooit tegen andere schema's.
- Inloggen met het lokale admin-account (zie .env, nooit hardcoden of committen).

## Scripts schrijven
- Scripts draaien uiteindelijk in de MOLGENIS scripts-module, niet in de terminal.
- Zoek in ../molgenis-emx2 hoe de scripts-module parameters, server-URL en token
  aan een script meegeeft, en volg exact die conventie. Verzin dit niet.
- Lees URL, token en schema uit omgevingsvariabelen, zodat hetzelfde script
  lokaal en in de scripts-module werkt.
- Gebruik de molgenis-emx2-pyclient. Controleer de geïnstalleerde versie met
  `pip show molgenis-emx2-pyclient` en de bron in ../molgenis-emx2/tools/pyclient.

## Testen
1. Draai het script lokaal met de juiste env vars.
2. Query daarna de doeltabel via de pyclient.
3. Vergelijk de uitkomst met een onafhankelijke berekening (bijv. pandas).
4. Een script is pas klaar als stap 3 klopt.