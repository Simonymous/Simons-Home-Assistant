DOMAIN = "paket_tracking"

EVENT_IMAP_CONTENT = "imap_content"

STORAGE_VERSION = 1
STORAGE_KEY = "paket_tracking.packages"
MAX_AGE_DAYS = 10

STATUS_OFFEN = "offen"
STATUS_UNTERWEGS = "unterwegs"
STATUS_HEUTE = "heute"
STATUS_ZUGESTELLT = "zugestellt"

BUCKETS = (STATUS_OFFEN, STATUS_UNTERWEGS, STATUS_HEUTE)

SENSOR_NAMES = {
    STATUS_OFFEN: "Pakete Offen",
    STATUS_UNTERWEGS: "Pakete Unterwegs",
    STATUS_HEUTE: "Pakete Heute",
}

SENSOR_ICONS = {
    STATUS_OFFEN: "mdi:cart-outline",
    STATUS_UNTERWEGS: "mdi:truck-delivery-outline",
    STATUS_HEUTE: "mdi:home-import-outline",
}
