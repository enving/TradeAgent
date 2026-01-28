# /checkpoint

Beende deine Session sauber mit Commit und Handoff.

---

## Schritte

### 1. Aufräumen
Lösche temporäre Files falls vorhanden.

### 2. Metadaten aktualisieren
Falls `tasks.json` existiert (suche in `.opencode/`, `.opencode/`, root):
- Update `meta.last_updated` und `meta.last_agent`

Falls Dokumentation existiert (`agents.md`, `CHANGELOG.md`, etc.):
- Ergänze Session-Eintrag

> **Wichtig**: Fehlende Files NICHT automatisch erstellen.

### 3. Git Commit
Falls Änderungen vorhanden:
```bash
git add .
git commit -m "checkpoint: [Kurzbeschreibung]

- [Hauptänderung 1]
- [Hauptänderung 2]"
```

### 4. Handoff generieren
Erstelle einen Handoff basierend auf dem aktuellen Zustand:

```
═══════════════════════════════════════
HANDOFF FOR NEXT AGENT
═══════════════════════════════════════

✅ COMPLETED
[Was wurde abgeschlossen]

🔄 IN PROGRESS
[Was läuft noch]

📝 NEXT STEPS
1. [Wichtigste nächste Action]
2. [Zweite Priorität]

🔧 NOTES
[Wichtiger Kontext für den nächsten Agent]

═══════════════════════════════════════
```

---

## Regeln

- Nutze `tasks.json` falls vorhanden, sonst `git log`/`git status`
- Update nur existierende Docs
- Commit nur bei Änderungen
- Handoff ist **immer** Pflicht
