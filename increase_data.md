Use your travel_benchmark_niche_backup.csv as the base gold dataset, then expand with source-controlled data:

Official / factual sources
Use government visa pages, tourism boards, UNESCO, airport/transport authority pages. Avoid Facebook, Reddit, YouTube, random blogs as gold truth unless manually verified.

Structured knowledge sources
Wikidata SPARQL can provide structured facts like UNESCO status, coordinates, countries, heritage sites, opening entities, etc. Official docs: 
https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service

Open travel guide corpus
Wikivoyage dumps can give destination descriptions and POIs under open licenses. Docs: 
https://en.wikivoyage.org/wiki/Wikivoyage:Database_dump

Map and attraction data
OpenStreetMap Overpass API can extract museums, parks, attractions, religious sites, airports, stations, and opening-hour tags. Docs: 
https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL

Weather and historical weather
Open-Meteo is good because it needs no key for non-commercial/prototype use and supports current/forecast/historical weather. Docs: 
https://open-meteo.com/en/docs

Transport reliability
GTFS-Realtime is the standard for trip updates, vehicle positions, and service alerts. Docs: 
https://gtfs.org/spec/gtfs-realtime

Commercial travel APIs
Amadeus can add flight, hotel, destination, and travel market data if you want industry-style evidence. Docs: 
https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/