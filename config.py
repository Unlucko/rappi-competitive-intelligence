import os
from dataclasses import dataclass, field
from typing import Optional


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SCREENSHOTS_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


@dataclass
class PlatformConfig:
    name: str
    base_url: str
    search_restaurant: str = "McDonald's"
    enabled: bool = True


PLATFORM_CONFIGS = {
    "rappi": PlatformConfig(
        name="Rappi",
        base_url="https://www.rappi.com.mx",
    ),
    "ubereats": PlatformConfig(
        name="Uber Eats",
        base_url="https://www.ubereats.com",
    ),
    "didifood": PlatformConfig(
        name="DiDi Food",
        base_url="https://www.didifoods.com",
    ),
}


@dataclass
class GeoAddress:
    label: str
    address: str
    city: str
    zone_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


ADDRESSES = [
    GeoAddress(
        label="CDMX-Polanco",
        address="Av. Presidente Masaryk 360, Polanco, CDMX",
        city="CDMX",
        zone_type="wealthy",
    ),
    GeoAddress(
        label="CDMX-Condesa",
        address="Av. Tamaulipas 100, Condesa, CDMX",
        city="CDMX",
        zone_type="wealthy",
    ),
    GeoAddress(
        label="CDMX-RomaNorte",
        address="Calle Orizaba 50, Roma Norte, CDMX",
        city="CDMX",
        zone_type="wealthy",
    ),
    GeoAddress(
        label="CDMX-SantaFe",
        address="Centro Comercial Santa Fe, Santa Fe, CDMX",
        city="CDMX",
        zone_type="wealthy",
    ),
    GeoAddress(
        label="CDMX-Coyoacan",
        address="Av. Universidad 1000, Coyoacan, CDMX",
        city="CDMX",
        zone_type="middle",
    ),
    GeoAddress(
        label="CDMX-DelValle",
        address="Av. Insurgentes Sur 1400, Del Valle, CDMX",
        city="CDMX",
        zone_type="middle",
    ),
    GeoAddress(
        label="CDMX-Narvarte",
        address="Av. Division del Norte 800, Narvarte, CDMX",
        city="CDMX",
        zone_type="middle",
    ),
    GeoAddress(
        label="CDMX-Iztapalapa",
        address="Av. Ermita Iztapalapa 3500, Iztapalapa, CDMX",
        city="CDMX",
        zone_type="popular",
    ),
    GeoAddress(
        label="CDMX-GAM",
        address="Av. Insurgentes Norte 1500, Gustavo A. Madero, CDMX",
        city="CDMX",
        zone_type="popular",
    ),
    GeoAddress(
        label="CDMX-Tepito",
        address="Eje 1 Norte 200, Centro, CDMX",
        city="CDMX",
        zone_type="popular",
    ),
    GeoAddress(
        label="MTY-SanPedro",
        address="Calzada del Valle 400, San Pedro Garza Garcia, Monterrey",
        city="Monterrey",
        zone_type="wealthy",
    ),
    GeoAddress(
        label="MTY-Centro",
        address="Av. Juarez 100, Centro, Monterrey",
        city="Monterrey",
        zone_type="middle",
    ),
    GeoAddress(
        label="MTY-Cumbres",
        address="Av. Lincoln 2000, Cumbres, Monterrey",
        city="Monterrey",
        zone_type="middle",
    ),
    GeoAddress(
        label="GDL-Zapopan",
        address="Av. Patria 1500, Zapopan, Guadalajara",
        city="Guadalajara",
        zone_type="wealthy",
    ),
    GeoAddress(
        label="GDL-Centro",
        address="Av. Juarez 500, Centro, Guadalajara",
        city="Guadalajara",
        zone_type="middle",
    ),
    GeoAddress(
        label="GDL-Tlaquepaque",
        address="Av. Revolucion 100, Tlaquepaque, Guadalajara",
        city="Guadalajara",
        zone_type="popular",
    ),
    GeoAddress(
        label="PUE-Centro",
        address="Blvd. Heroes del 5 de Mayo 100, Centro, Puebla",
        city="Puebla",
        zone_type="middle",
    ),
    GeoAddress(
        label="PUE-Angelopolis",
        address="Blvd. del Nino Poblano 2510, Angelopolis, Puebla",
        city="Puebla",
        zone_type="wealthy",
    ),
    GeoAddress(
        label="MER-Centro",
        address="Calle 60 500, Centro, Merida",
        city="Merida",
        zone_type="middle",
    ),
    GeoAddress(
        label="MER-Norte",
        address="Calle 60 Norte por Periferico, Merida",
        city="Merida",
        zone_type="middle",
    ),
    GeoAddress(
        label="CUN-ZonaHotelera",
        address="Blvd. Kukulcan Km 9, Zona Hotelera, Cancun",
        city="Cancun",
        zone_type="wealthy",
    ),
    GeoAddress(
        label="CUN-Centro",
        address="Av. Tulum 200, Centro, Cancun",
        city="Cancun",
        zone_type="middle",
    ),
    GeoAddress(
        label="CDMX-Xochimilco",
        address="Av. Mexico 20, Xochimilco, CDMX",
        city="CDMX",
        zone_type="popular",
    ),
    GeoAddress(
        label="MTY-Apodaca",
        address="Av. Miguel Aleman 500, Apodaca, Monterrey",
        city="Monterrey",
        zone_type="popular",
    ),
    GeoAddress(
        label="GDL-Tonala",
        address="Av. Tonaltecas 100, Tonala, Guadalajara",
        city="Guadalajara",
        zone_type="popular",
    ),
]


REFERENCE_PRODUCTS = [
    {
        "product_id": "big_mac",
        "product_name": "Big Mac",
        "category": "fast_food",
        "restaurant": "McDonald's",
    },
    {
        "product_id": "combo_mediano",
        "product_name": "Combo Mediano McDonald's",
        "category": "fast_food",
        "restaurant": "McDonald's",
    },
    {
        "product_id": "mcnuggets_6",
        "product_name": "McNuggets 6pc",
        "category": "fast_food",
        "restaurant": "McDonald's",
    },
    {
        "product_id": "coca_cola_500ml",
        "product_name": "Coca-Cola 500ml",
        "category": "retail",
        "restaurant": "McDonald's",
    },
]


SCRAPING_CONFIG = {
    "min_delay_seconds": 2.0,
    "max_delay_seconds": 5.0,
    "max_retries": 3,
    "backoff_base_seconds": 2.0,
    "request_timeout_ms": 30000,
    "navigation_timeout_ms": 45000,
    "screenshot_on_error": True,
    "headless": True,
    "user_agents": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ],
}


LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "log_file": os.path.join(OUTPUT_DIR, "scraper.log"),
}
