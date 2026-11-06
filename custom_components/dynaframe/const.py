"""Constants for the Dynaframe integration."""

from datetime import timedelta

DOMAIN = "dynaframe"

CONF_AUTO_ADD = "auto_add"
# Frames protected by the Web Login plugin.
CONF_API_KEY = "api_key"
CONF_USE_HTTPS = "use_https"
CONF_FINGERPRINT = "fingerprint"
CONF_RENEW_CERT = "renew_certificate"

SCAN_INTERVAL = timedelta(seconds=10)
# Playlists, update status and peer frames change rarely; refresh every n polls.
SLOW_POLL_EVERY = 30

CARD_URL = "/dynaframe_static/dynaframe-card.js"
STORE_CARD_URL = "/dynaframe_static/dynaframe-store-card.js"

TRANSITIONS = [
    "random",
    "asciidecode",
    "blinds",
    "cellularautomata",
    "circleopen",
    "circuitbloom",
    "colorphase",
    "crossfade",
    "crosswarp",
    "crystalshards",
    "cube",
    "directionalwipe",
    "drawing",
    "dreamyzoom",
    "eventhorizon",
    "falling_polaroid",
    "filmburn",
    "fisheye",
    "gifoverlay",
    "glitch",
    "gridflip",
    "hexagonpixelate",
    "hexdrop",
    "hextile",
    "juliarift",
    "kaleidoscope",
    "lantern_glow",
    "linearblur",
    "liquidlens",
    "moirezoom",
    "morph",
    "none",
    "pixelate",
    "polarcurtain",
    "prism_wipe",
    "randomsquares",
    "ripple",
    "soft_page_turn",
    "swirl",
    "verticalwipe",
    "vortexportal",
    "wind",
    "zoomblur",
]
