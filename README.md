# Stadtbibliothek Ausleih-API

Eine schlanke REST-API für die Ausleihe einer kleinen Stadtbibliothek: Bücher und
Mitglieder als Stammdaten, Ausleihen mit 14-Tage-Frist, Rückgabe und
Überziehungssicht. Die Absicherung schreibender Aufrufe erfolgt über einen
API-Key im Header `X-API-Key`. Persistiert wird in SQLite über SQLAlchemy 2.0.

Dieses Repository enthält das laufende Grundgerüst: Die Anwendung startet, der
Health-Endpunkt ist echt, alle weiteren Routen sind mit ihrem endgültigen Pfad,
Verb und Antwortmodell verdrahtet und antworten bis zur jeweiligen
Feature-Umsetzung mit `501 not_implemented`.

## Tech-Stack

- **Sprache:** Python 3.12
- **Framework:** FastAPI mit uvicorn
- **Validierung:** Pydantic v2
- **ORM:** SQLAlchemy 2.0 (deklarativ, typisiert)
- **Datenbank:** SQLite als Datei
- **Tests:** pytest mit FastAPI TestClient

## Installation

```bash
python -m pip install -r requirements.txt
```

## Starten (Entwicklung)

Die Dienste-Konfiguration liegt in `RUN.json`. Der API-Service wird so gestartet:

```bash
export LIBRARY_API_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Danach sind erreichbar:

- Health-Check: <http://127.0.0.1:8000/health>
- Interaktive Dokumentation (Swagger UI): <http://127.0.0.1:8000/docs>
- OpenAPI-Schema: <http://127.0.0.1:8000/openapi.json>

Es gibt keinen separaten Build-Schritt; das Produkt ist ein Python-Service.

## Tests

```bash
PYTHONPATH=. python -m pytest
```

Die Test-Suite läuft gegen eine separate, temporäre SQLite-Datenbank, die nach
dem Lauf verworfen wird.

## Umgebungsvariablen

| Variable | Beschreibung | Standard |
| --- | --- | --- |
| `LIBRARY_API_KEY` | Pflicht. Wert des Headers `X-API-Key` für schreibende Aufrufe. Kein Literal im Repository — wird pro Lauf erzeugt. | — (Pflicht) |
| `LIBRARY_DATABASE_URL` | SQLAlchemy-URL der Datenbank. | `sqlite:///./library.db` |
| `LOAN_PERIOD_DAYS` | Ausleihfrist in Tagen. | `14` |
| `MAX_OPEN_LOANS` | Maximale Zahl offener Ausleihen pro Mitglied. | `3` |

## Fehlerformat

Jede Fehlerantwort hat denselben Aufbau:

```json
{
  "error": {
    "code": "not_found",
    "message": "Buch nicht gefunden",
    "details": [{"field": "isbn", "message": "ungültige Prüfziffer"}]
  }
}
```

`details` ist eine leere Liste, wenn kein Feld betroffen ist. Verwendete Codes:
`unauthorized` (401), `not_found` (404), `conflict` (409),
`validation_error` (422), `not_implemented` (501), `internal_error` (500).

## API-Endpunkte

Schreibende Aufrufe (`POST`/`PUT`/`PATCH`/`DELETE`) benötigen den Header
`X-API-Key`; lesende Aufrufe (`GET`) sind frei zugänglich.

| Methode | Pfad | Key | Beschreibung | Status |
| --- | --- | --- | --- | --- |
| GET | `/health` | nein | Health-Check der Instanz | 200 |
| POST | `/books` | ja | Buch anlegen | 201, 409, 422 |
| GET | `/books` | nein | Bücher suchen (`q`, `limit`, `offset`) | 200 |
| GET | `/books/{book_id}` | nein | Buch lesen | 200, 404 |
| PUT | `/books/{book_id}` | ja | Buch ersetzen | 200, 404, 409, 422 |
| PATCH | `/books/{book_id}` | ja | Buch teilweise ändern | 200, 404, 409, 422 |
| DELETE | `/books/{book_id}` | ja | Buch löschen | 204, 404, 409 |
| POST | `/members` | ja | Mitglied anlegen | 201, 409, 422 |
| GET | `/members` | nein | Mitglieder auflisten (`limit`, `offset`) | 200 |
| GET | `/members/{member_id}` | nein | Mitglied lesen | 200, 404 |
| PUT | `/members/{member_id}` | ja | Mitglied ersetzen | 200, 404, 409, 422 |
| PATCH | `/members/{member_id}` | ja | Mitglied teilweise ändern | 200, 404, 409, 422 |
| DELETE | `/members/{member_id}` | ja | Mitglied löschen | 204, 404, 409 |
| POST | `/loans` | ja | Ausleihe anlegen | 201, 404, 409 |
| POST | `/loans/{loan_id}/return` | ja | Ausleihe zurückgeben | 200, 404, 409 |
| GET | `/loans` | nein | Ausleihen auflisten (`member_id`, `book_id`, `open_only`, `limit`, `offset`) | 200 |
| GET | `/loans/overdue` | nein | Offene überfällige Ausleihen | 200 |

### Datenmodelle

- `BookRead{id, title, author, isbn, publication_year, copies_total, copies_available}`
- `MemberRead{id, name, email, member_since}`
- `LoanRead{id, book_id, member_id, loaned_on, due_on, returned_on}`
- `OverdueLoan = LoanRead + {book, member, days_overdue}`

Daten sind ISO-8601 (`YYYY-MM-DD`); die Fälligkeit `due_on` ist `loaned_on` plus
`LOAN_PERIOD_DAYS`.

## Funktionsumfang

- Health-Check mit Bestätigung der lauffähigen Instanz und der Datenbank.
- Einheitliches Fehlerformat für alle Fehlerantworten.
- Buch-, Mitglieder- und Ausleih-Routen mit ihren endgültigen Pfaden, Verben und
  Antwortmodellen verdrahtet (Feature-Logik folgt in separaten Tickets).
- Konfiguration ausschließlich über Umgebungsvariablen.
