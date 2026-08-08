from pathlib import Path
from datetime import datetime

import pytz
import swisseph as swe
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from geopy.geocoders import Nominatim
from pydantic import BaseModel
from timezonefinder import TimezoneFinder

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Permazur Human Design")
geolocator = Nominatim(user_agent="permazur_human_design")
timezone_finder = TimezoneFinder()

# Ordre des 64 portes sur la roue Human Design.
GATE_SEQUENCE = [
    25, 17, 21, 51, 42, 3,
    27, 24, 2, 23, 8, 20,
    16, 35, 45, 12, 15, 52,
    39, 53, 62, 56, 31, 33,
    7, 4, 29, 59, 40, 64,
    47, 6, 46, 18, 48, 57,
    32, 50, 28, 44, 1, 43,
    14, 34, 9, 5, 26, 11,
    10, 58, 38, 54, 61, 60,
    41, 19, 13, 49, 30, 55,
    37, 63, 22, 36
]
HD_START_DEGREE = 358.25

CENTERS = {
    "Head": [61, 63, 64],
    "Ajna": [4, 11, 17, 24, 43, 47],
    "Throat": [8, 12, 16, 20, 23, 31, 33, 35, 45, 56, 62],
    "Self": [1, 2, 7, 10, 13, 15, 25, 46],
    "Heart": [21, 26, 40, 51],
    "Sacral": [3, 5, 9, 14, 27, 29, 34, 42, 59],
    "Spleen": [18, 28, 32, 44, 48, 50, 57],
    "Solar Plexus": [6, 22, 30, 36, 37, 49, 55],
    "Root": [19, 38, 39, 41, 52, 53, 54, 58, 60],
}

# Les 36 canaux du BodyGraph.
CHANNELS = {
    (1, 8): ("Self", "Throat"),
    (2, 14): ("Self", "Sacral"),
    (3, 60): ("Sacral", "Root"),
    (4, 63): ("Ajna", "Head"),
    (5, 15): ("Sacral", "Self"),
    (6, 59): ("Solar Plexus", "Sacral"),
    (7, 31): ("Self", "Throat"),
    (9, 52): ("Sacral", "Root"),
    (10, 20): ("Self", "Throat"),
    (10, 34): ("Self", "Sacral"),
    (10, 57): ("Self", "Spleen"),
    (11, 56): ("Ajna", "Throat"),
    (12, 22): ("Throat", "Solar Plexus"),
    (13, 33): ("Self", "Throat"),
    (16, 48): ("Throat", "Spleen"),
    (17, 62): ("Ajna", "Throat"),
    (18, 58): ("Spleen", "Root"),
    (19, 49): ("Root", "Solar Plexus"),
    (20, 34): ("Throat", "Sacral"),
    (20, 57): ("Throat", "Spleen"),
    (21, 45): ("Heart", "Throat"),
    (23, 43): ("Throat", "Ajna"),
    (24, 61): ("Ajna", "Head"),
    (25, 51): ("Self", "Heart"),
    (26, 44): ("Heart", "Spleen"),
    (27, 50): ("Sacral", "Spleen"),
    (28, 38): ("Spleen", "Root"),
    (29, 46): ("Sacral", "Self"),
    (30, 41): ("Solar Plexus", "Root"),
    (32, 54): ("Spleen", "Root"),
    (34, 57): ("Sacral", "Spleen"),
    (35, 36): ("Throat", "Solar Plexus"),
    (37, 40): ("Solar Plexus", "Heart"),
    (39, 55): ("Root", "Solar Plexus"),
    (42, 53): ("Sacral", "Root"),
    (47, 64): ("Ajna", "Head"),
}

class BirthData(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int
    city: str

def historical_utc_offset(data: BirthData) -> float:
    location = geolocator.geocode(data.city)
    if not location:
        raise ValueError(
            "Ville introuvable. Essaie par exemple : « Villeneuve-d'Ascq, France »."
        )

    tz_name = timezone_finder.timezone_at(
        lng=location.longitude,
        lat=location.latitude,
    )
    if not tz_name:
        raise ValueError("Fuseau horaire introuvable pour cette ville.")

    local_tz = pytz.timezone(tz_name)
    naive = datetime(data.year, data.month, data.day, data.hour, data.minute)

    try:
        localized = local_tz.localize(naive, is_dst=None)
    except pytz.AmbiguousTimeError:
        localized = local_tz.localize(naive, is_dst=False)
    except pytz.NonExistentTimeError:
        localized = local_tz.localize(naive, is_dst=True)

    return localized.utcoffset().total_seconds() / 3600

def degree_to_gate_line(degree: float):
    gate_size = 360 / 64
    line_size = gate_size / 6
    adjusted = (degree - HD_START_DEGREE) % 360
    index = int(adjusted / gate_size)
    line = int((adjusted % gate_size) / line_size) + 1
    return GATE_SEQUENCE[index], line

def planet_positions(julian_day: float):
    results = {}

    sun_degree = swe.calc_ut(julian_day, swe.SUN)[0][0]
    gate, line = degree_to_gate_line(sun_degree)
    results["Sun"] = {"degree": sun_degree, "gate": gate, "line": line}

    earth_degree = (sun_degree + 180) % 360
    gate, line = degree_to_gate_line(earth_degree)
    results["Earth"] = {"degree": earth_degree, "gate": gate, "line": line}

    north_node = swe.calc_ut(julian_day, swe.TRUE_NODE)[0][0]
    gate, line = degree_to_gate_line(north_node)
    results["N.Node"] = {"degree": north_node, "gate": gate, "line": line}

    south_node = (north_node + 180) % 360
    gate, line = degree_to_gate_line(south_node)
    results["S.Node"] = {"degree": south_node, "gate": gate, "line": line}

    planets = {
        "Moon": swe.MOON,
        "Mercury": swe.MERCURY,
        "Venus": swe.VENUS,
        "Mars": swe.MARS,
        "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN,
        "Uranus": swe.URANUS,
        "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO,
    }

    for name, planet in planets.items():
        degree = swe.calc_ut(julian_day, planet)[0][0]
        gate, line = degree_to_gate_line(degree)
        results[name] = {"degree": degree, "gate": gate, "line": line}

    return results

def active_channels(gates):
    gate_set = set(gates)
    return [
        {"gates": [a, b], "centers": list(centers)}
        for (a, b), centers in CHANNELS.items()
        if a in gate_set and b in gate_set
    ]

def defined_centers(channels):
    defined = set()
    for channel in channels:
        defined.update(channel["centers"])
    return sorted(defined)

def center_graph(channels):
    graph = {center: set() for center in CENTERS}
    for channel in channels:
        a, b = channel["centers"]
        graph[a].add(b)
        graph[b].add(a)
    return graph

def definition_label(defined, channels):
    defined_set = set(defined)
    if not defined_set:
        return "Aucune définition"

    graph = center_graph(channels)
    remaining = set(defined_set)
    components = 0

    while remaining:
        components += 1
        start = next(iter(remaining))
        stack = [start]
        seen = set()

        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            for nxt in graph.get(node, set()):
                if nxt in defined_set and nxt not in seen:
                    stack.append(nxt)

        remaining -= seen

    labels = {
        1: "Définition simple",
        2: "Définition double",
        3: "Définition triple",
        4: "Définition quadruple",
    }
    return labels.get(components, f"{components} définitions")

def connected(graph, start, target):
    if start == target:
        return True
    visited = set()
    queue = [start]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for nxt in graph.get(current, set()):
            if nxt == target:
                return True
            if nxt not in visited:
                queue.append(nxt)
    return False

def determine_type(defined, channels):
    defined_set = set(defined)
    if not defined_set:
        return "Reflector"

    graph = center_graph(channels)
    has_sacral = "Sacral" in defined_set
    motor_centers = ("Sacral", "Heart", "Solar Plexus", "Root")
    motor_to_throat = (
        "Throat" in defined_set
        and any(center in defined_set and connected(graph, center, "Throat")
                for center in motor_centers)
    )

    if has_sacral and motor_to_throat:
        return "Manifesting Generator"
    if has_sacral:
        return "Generator"
    if motor_to_throat:
        return "Manifestor"
    return "Projector"

def determine_authority(defined, channels, hd_type):
    defined_set = set(defined)
    graph = center_graph(channels)

    if "Solar Plexus" in defined_set:
        return "Emotional"
    if "Sacral" in defined_set:
        return "Sacral"
    if "Spleen" in defined_set:
        return "Splenic"

    if "Heart" in defined_set:
        if connected(graph, "Heart", "Throat") or connected(graph, "Heart", "Self"):
            return "Ego"

    if "Self" in defined_set and "Throat" in defined_set and connected(graph, "Self", "Throat"):
        return "Self-Projected"

    if hd_type == "Reflector":
        return "Lunar"
    return "Mental / Environmental"

def design_julian_day(personality_jd, personality_sun_degree):
    target = (personality_sun_degree - 88) % 360
    low = personality_jd - 100
    high = personality_jd - 80

    for _ in range(70):
        middle = (low + high) / 2
        sun_degree = swe.calc_ut(middle, swe.SUN)[0][0]
        diff = (sun_degree - target + 180) % 360 - 180
        if abs(diff) < 0.00001:
            return middle
        if diff > 0:
            high = middle
        else:
            low = middle
    return (low + high) / 2

def calculate_chart(data: BirthData):
    offset = historical_utc_offset(data)
    utc_hour = data.hour - offset

    personality_jd = swe.julday(
        data.year,
        data.month,
        data.day,
        utc_hour + data.minute / 60,
    )

    personality_sun = swe.calc_ut(personality_jd, swe.SUN)[0][0]
    design_jd = design_julian_day(personality_jd, personality_sun)

    personality = planet_positions(personality_jd)
    design = planet_positions(design_jd)

    all_gates = sorted({
        item["gate"]
        for group in (personality, design)
        for item in group.values()
    })

    channels = active_channels(all_gates)
    defined = defined_centers(channels)
    hd_type = determine_type(defined, channels)
    authority = determine_authority(defined, channels, hd_type)

    profile = f'{personality["Sun"]["line"]}/{design["Sun"]["line"]}'

    design_date = swe.revjul(design_jd)
    design_year, design_month, design_day, design_hour_float = design_date
    design_hour = int(design_hour_float)
    design_minute = int(round((design_hour_float - design_hour) * 60))
    if design_minute == 60:
        design_minute = 0
        design_hour += 1

    return {
        "type": hd_type,
        "profile": profile,
        "authority": authority,
        "definition": definition_label(defined, channels),
        "defined_centers": defined,
        "undefined_centers": sorted(set(CENTERS) - set(defined)),
        "active_channels": channels,
        "all_active_gates": all_gates,
        "personality": personality,
        "design": design,
        "birth_data": {
            "year": data.year,
            "month": data.month,
            "day": data.day,
            "hour": data.hour,
            "minute": data.minute,
            "city": data.city,
        },
        "design_date_utc": {
            "year": design_year,
            "month": design_month,
            "day": design_day,
            "hour": design_hour,
            "minute": design_minute,
        },
        "location_metadata": {
            "query": data.city,
            "calculated_offset": offset,
        },
    }

@app.post("/generate-chart")
def generate_chart(data: BirthData):
    try:
        return calculate_chart(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def index():
    return FileResponse(BASE_DIR / "index.html")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
