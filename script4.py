import swisseph as swe
import os
from datetime import datetime
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from pytz import timezone, utc
ephe_path = '/usr/share/swisseph/ephe'
swe.set_ephe_path(ephe_path)
print(f"Set ephe path to: {ephe_path}")

# Try to open the file manually
try:
    with open(os.path.join(ephe_path, 'seas_18.se1'), 'rb') as f:
        print("File opened successfully")
except FileNotFoundError:
    print("File not found")
except PermissionError:
    print("Permission denied")

# Define constants for aspects (in degrees)
ASPECTS = {
    'conjunct': (0, 10),
    'sextile': (60, 10),
    'square': (90, 10),
    'trine': (120, 10),
    'opposite': (180, 10)
}

# Map for signs by degrees
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

def get_sign(degree):
    """Convert degree to astrological sign."""
    index = int(degree // 30)
    return SIGNS[index]

def calculate_angle(pos1, pos2):
    """Calculate the smallest angle between two points on a circle."""
    angle = abs(pos1 - pos2) % 360
    return min(angle, 360 - angle)

def determine_aspect_and_strength(angle):
    """Determine the aspect and categorize its strength based on distance from exact angle."""
    for aspect, (exact_angle, max_deviation) in ASPECTS.items():
        deviation = abs(angle - exact_angle)
        if deviation <= max_deviation:
            if deviation <= 3:
                strength_description = "strong"
            elif deviation <= 7:
                strength_description = "moderate"
            else:
                strength_description = "weak"
            return aspect, strength_description
    return None, None

def get_coordinates(city):
    """Get latitude and longitude for a given city using geopy."""
    geolocator = Nominatim(user_agent="astro_app")
    location = geolocator.geocode(city)
    if location:
        return location.latitude, location.longitude
    else:
        raise ValueError(f"Could not find coordinates for city: {city}")

def calculate_houses(julian_day, latitude, longitude):
    """Calculate the house cusps and Ascendant using Swiss Ephemeris."""
    houses, ascmc = swe.houses(julian_day, latitude, longitude, b'P')
    house_cusps = houses[:12]
    ascendant = ascmc[0]
    return house_cusps, ascendant

def assign_house_to_planet(degree, house_cusps):
    """Assign a planet to a house based on its degree and the house cusps."""
    for i in range(12):
        start_cusp = house_cusps[i]
        end_cusp = house_cusps[(i + 1) % 12]
        if start_cusp < end_cusp:
            if start_cusp <= degree < end_cusp:
                return i + 1
        else:
            if degree >= start_cusp or degree < end_cusp:
                return i + 1
    return None  # Fallback case

def get_planetary_positions(date, time=None, latitude=None, longitude=None):
    """Get the ecliptic longitudes and house placements of planets on a specific date."""
    swe.set_ephe_path('/usr/share/swisseph/ephe')
    
    # Convert local time to UTC for Julian Day calculation
    if time and latitude is not None and longitude is not None:
        tf = TimezoneFinder()
        local_timezone = tf.timezone_at(lng=longitude, lat=latitude)
        local = timezone(local_timezone)
        dt_local = local.localize(datetime.combine(date, time))
        dt_utc = dt_local.astimezone(utc)
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0)
    else:
        jd = swe.julday(date.year, date.month, date.day, 12)

    # Calculate house cusps and Ascendant only if time and location are provided
    house_cusps = None
    planetary_positions = {}
    
    if time and latitude is not None and longitude is not None:
        house_cusps, ascendant = calculate_houses(jd, latitude, longitude)
    
    # Planets and additional points to include
    planet_ids = {
        'Sun': swe.SUN,
        'Moon': swe.MOON,
        'Mercury': swe.MERCURY,
        'Venus': swe.VENUS,
        'Mars': swe.MARS,
        'Jupiter': swe.JUPITER,
        'Saturn': swe.SATURN,
        'Uranus': swe.URANUS,
        'Neptune': swe.NEPTUNE,
        'Pluto': swe.PLUTO,
        'Juno': 3,
        'Lilith': swe.MEAN_NODE + 1
    }

    if time and latitude is not None and longitude is not None:
        fortuna_id = 19
        fortuna_position, _ = swe.calc_ut(jd, fortuna_id, swe.FLG_SWIEPH + swe.FLG_SPEED)
        fortuna_degree = fortuna_position[0]
        fortuna_sign = get_sign(fortuna_degree)
        fortuna_house = assign_house_to_planet(fortuna_degree, house_cusps) if house_cusps else None
        planetary_positions['Fortuna'] = {'degree': fortuna_degree, 'sign': fortuna_sign, 'house': fortuna_house}
    
    # Calculate positions of planets, Juno, and Lilith
    for name, id in planet_ids.items():
        position, _ = swe.calc_ut(jd, id, swe.FLG_SWIEPH + swe.FLG_SPEED)
        longitude_deg = position[0]
        sign = get_sign(longitude_deg)
        house = assign_house_to_planet(longitude_deg, house_cusps) if house_cusps else None
        planetary_positions[name] = {'degree': longitude_deg, 'sign': sign, 'house': house}

    # Calculate Ascendant, Descendant, MC, and IC if time and location are provided
    if house_cusps:
        mc = house_cusps[9]
        angles = {
            'Ascendant': ascendant,
            'Descendant': (ascendant + 180) % 360,
            'Midheaven (MC)': mc,
            'Imum Coeli (IC)': (mc + 180) % 360
        }
        
        for angle_name, angle_degree in angles.items():
            sign = get_sign(angle_degree)
            planetary_positions[angle_name] = {'degree': angle_degree, 'sign': sign}

    return planetary_positions

def generate_aspect_descriptions_with_signs(planets):
    """Generate descriptions for aspects between planets, including signs and strengths."""
    descriptions = []
    planet_names = list(planets.keys())
    
    for i, planet1 in enumerate(planet_names):
        for planet2 in planet_names[i+1:]:
            angle = calculate_angle(planets[planet1]['degree'], planets[planet2]['degree'])
            aspect, strength_description = determine_aspect_and_strength(angle)
            if aspect:
                sign1 = planets[planet1]['sign']
                sign2 = planets[planet2]['sign']
                descriptions.append(f"{planet1} in {sign1} is a {strength_description} {aspect} to {planet2} in {sign2}")
    return descriptions

def generate_sign_descriptions(planets):
    """Generate descriptions for the sign placement of each planet and angle."""
    descriptions = []
    for planet, data in planets.items():
        sign = data['sign']
        if 'house' in data:
            house = data['house']
            descriptions.append(f"{planet} is in {sign}, in house {house}")
        else:
            descriptions.append(f"{planet} is in {sign}")
    return descriptions

# Example usage
def analyze_natal_chart_full(birthday, time, city):
    """
    Analyze a complete birth chart with time and location.
    
    Args:
        birthday (datetime): Birth date
        time (datetime.time): Birth time
        city (str): Birth location
    
    Returns:
        dict: Contains sign placements and aspects
    """
    try:
        latitude, longitude = get_coordinates(city)
        planets = get_planetary_positions(birthday, time, latitude, longitude)
        
        sign_descriptions = generate_sign_descriptions(planets)
        aspect_descriptions = generate_aspect_descriptions_with_signs(planets)
        
        return {
            'placements': sign_descriptions,
            'aspects': aspect_descriptions,
            'success': True,
            'error': None
        }
        
    except Exception as e:
        return {
            'placements': [],
            'aspects': [],
            'success': False,
            'error': str(e)
        }