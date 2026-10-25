# Dynaframe for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/Archonw/dynaframe-homeassistant/actions/workflows/validate.yml/badge.svg)](https://github.com/Archonw/dynaframe-homeassistant/actions/workflows/validate.yml)

Local control of [Dynaframe™](https://geek-toolkit.com/) digital picture frames from Home Assistant –
including automatic discovery and a dashboard card. No MQTT broker and no cloud needed.

*Deutsche Beschreibung weiter unten.*

## Features

- **Automatic discovery** via mDNS, DHCP and the frames themselves (frames know each other),
  plus a network scan when you add the integration manually
- Optional **auto-add**: newly found frames are set up without confirmation
- **Media player** per frame: play/pause/stop, next/previous, display on/off, volume, mute,
  playlist selection, shuffle and a live preview image
- **Settings**: transition effect (all 43 effects) and transition duration, slide duration,
  video audio, overlays and default overlay
- **Diagnostics**: sync role, memory and storage usage, version, update available
- **Metadata** of the current image (title, author, date taken, camera, keywords, tags …)
- **Reboot** button
- **Dashboard card** that ships with the integration – nothing to add under *Resources*
- **Store downloads card** for your own DynaFrame Pro store on GitHub: total, downloads per pack and per day

## Installation

### HACS (recommended)

1. HACS → ⋮ → **Custom repositories**
2. Repository: `https://github.com/Archonw/dynaframe-homeassistant`, type **Integration**
3. Install **Dynaframe** and restart Home Assistant
4. Frames on your network show up under *Settings → Devices & services → Discovered*.
   You can also add them via **Add integration → Dynaframe**, which scans your network.

### Manual

Copy `custom_components/dynaframe` into the `custom_components` folder of your
Home Assistant configuration and restart.

## Dashboard card

Edit a dashboard → **Add card** → search for **Dynaframe**, or use YAML:

```yaml
type: custom:dynaframe-card
title: Picture frames      # optional
entities:                  # optional – defaults to all Dynaframes
  - media_player.dynaframe_living_room
show_preview: true         # optional
```

With several frames the card shows one tab per frame. The **Settings** section folds out
and contains transitions, slide duration, video audio, mute, overlays, system info and reboot.

## Store downloads card

If you publish your own DynaFrame Pro store as GitHub releases (one release per pack version),
a second card that ships with the integration shows how often your packs were downloaded:
the total, a table of all packs sorted by downloads, and a bar chart of downloads per day.

Edit a dashboard → **Add card** → search for **Dynaframe Store-Downloads** and enter your
store's repository (`owner/repo`), or use YAML:

```yaml
type: custom:dynaframe-store-card
title: Store downloads                     # optional
repo: your-name/your-store                # required
entity: sensor.store_downloads_total       # optional, for the daily chart
days: 30                                   # optional
```

Total and table are read directly from the public GitHub releases API by the browser (no login,
cached for an hour, all releases are counted). New packs appear automatically. Releases are
grouped into packs by their tag without the version (`playlist-button-1.6.3` → `playlist-button`).

GitHub only reports running totals, so the **per-day chart** needs Home Assistant to record the
total over time. Add this sensor to `configuration.yaml` (or a package), replace
`your-name/your-store` with your repository, restart once and pick the sensor in the card:

```yaml
rest:
  - resource: https://api.github.com/repos/your-name/your-store/releases?per_page=100
    scan_interval: 3600
    headers:
      Accept: application/vnd.github+json
      User-Agent: HomeAssistant-DynaFrame-Store
    sensor:
      - name: Store downloads total
        unique_id: dynaframe_store_downloads_total
        icon: mdi:download
        unit_of_measurement: Downloads
        state_class: total_increasing
        value_template: "{{ value_json | map(attribute='assets') | sum(start=[]) | map(attribute='download_count') | sum }}"
```

The first bars appear after Home Assistant has written its hourly statistics. The sensor reads
the newest 100 releases; the card itself counts all of them.

## Options

*Settings → Devices & services → Dynaframe → Configure*

| Option | Description |
| --- | --- |
| Add newly discovered frames automatically | Every Dynaframe found on the network is set up without confirmation. Deleted frames are moved to *Ignored* so they do not come back. Applies to all frames. |

## Matching theme

Want your dashboard to look like the Dynaframe web UI? Install the **Dynaframe** theme from
[Archonw Themes](https://github.com/Archonw/ha-themes) (HACS → Custom repositories, type
**Theme**).

## Notes

- The integration uses the frame's local web API (port 80) and polls every 10 seconds.
- Restarting only the Dynaframe app, shutting the device down, changing the sync role and
  NFC scan events are only offered by Dynaframe via MQTT and are therefore not included.
- File paths and stream URLs of the current item are intentionally not exposed, as stream
  URLs can contain camera credentials.
- If the card does not appear in the Companion app after an update, reset the app's
  frontend cache.

---

## Deutsch

Lokale Steuerung von Dynaframe™-Bilderrahmen in Home Assistant – mit automatischer Erkennung
und eigener Dashboard-Karte, ohne MQTT und ohne Cloud.

**Installation:** HACS → ⋮ → *Benutzerdefinierte Repositories* →
`https://github.com/Archonw/dynaframe-homeassistant` als **Integration** hinzufügen,
„Dynaframe“ installieren, Home Assistant neu starten. Gefundene Frames erscheinen unter
*Einstellungen → Geräte & Dienste → Entdeckt*.

**Karte:** Dashboard bearbeiten → *Karte hinzufügen* → „Dynaframe“. Unter dem
Lautstärkeregler klappt das Menü **Einstellungen** auf (Überblendung, Anzeigedauer,
Video-Ton, Stumm, Overlays, Systeminfos, Neustart).

**Store-Downloads-Karte:** Für alle, die einen eigenen DynaFrame-Pro-Store als GitHub-Releases
veröffentlichen. Dashboard bearbeiten → *Karte hinzufügen* → „Dynaframe Store-Downloads“ und das
eigene Repo (`name/repo`) eintragen. Zeigt die Gesamtzahl, eine nach Downloads sortierte Tabelle
aller Packs (neue Packs erscheinen von selbst) und „Downloads pro Tag“. Für das Tagesdiagramm
braucht Home Assistant einen Sensor mit den Gesamt-Downloads (YAML siehe
[oben](#store-downloads-card)), weil GitHub nur Gesamtzahlen liefert.

**Passendes Theme:** Das Theme „Dynaframe“ aus [Archonw Themes](https://github.com/Archonw/ha-themes) lässt dein Dashboard wie die Dynaframe-Oberfläche aussehen.

**Automatisch hinzufügen:** In den Optionen der Integration lässt sich einschalten, dass neu
gefundene Frames ohne Bestätigung eingerichtet werden.

## Authors

- **Jan** ([@Archonw](https://github.com/Archonw)) – idea, testing and maintenance
- **Claude** (AI assistant by [Anthropic](https://www.anthropic.com), via
  [Claude Code](https://claude.com/claude-code)) – design and implementation of the
  integration and the dashboard card

*Autoren: Jan (Idee, Tests, Pflege) und Claude, der KI-Assistent von Anthropic
(Entwurf und Umsetzung von Integration und Karte).*

## License

[MIT](LICENSE) – not affiliated with or endorsed by Dynaframe™.
