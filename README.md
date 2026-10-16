# Dynaframe for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/Archonw/dynaframe-homeassistant/actions/workflows/validate.yml/badge.svg)](https://github.com/Archonw/dynaframe-homeassistant/actions/workflows/validate.yml)

Local control of [Dynaframe™](https://dynaframe.com) digital picture frames from Home Assistant –
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
