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

# Gender-specific pronouns
PRONOUNS = {
    'male': 'his',
    'female': 'her'
}

# Planet IDs, including Fortuna and Juno
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
    'Juno': 3,               # Juno's asteroid ID
    'Lilith': swe.MEAN_NODE + 1  # Dark Moon Lilith
}

# Optional Fortuna ID, added if time and location are available
optional_planet_ids = {
    'Fortuna': 19            # Fortuna's asteroid ID
}

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
    return None  # Shouldn't happen, but a fallback just in case

def get_planetary_positions(date, time=None, latitude=None, longitude=None):
    """Get the ecliptic longitudes and house placements of planets on a specific date.
       Calculate houses and Fortuna only if time and location are provided."""
    swe.set_ephe_path('/usr/share/swisseph/ephe')
    jd = swe.julday(date.year, date.month, date.day, time.hour + time.minute / 60.0 if time else 0)
    
    # Conditionally calculate houses and add Fortuna if time and location are provided
    house_cusps = None
    planetary_positions = {}
    
    if time and latitude is not None and longitude is not None:
        house_cusps, ascendant = calculate_houses(jd, latitude, longitude)
        for name, id in optional_planet_ids.items():
            position, _ = swe.calc_ut(jd, id, swe.FLG_SWIEPH + swe.FLG_SPEED)
            longitude_deg = position[0]
            sign = get_sign(longitude_deg)
            house = assign_house_to_planet(longitude_deg, house_cusps) if house_cusps else None
            planetary_positions[name] = {'degree': longitude_deg, 'sign': sign, 'house': house}
    
    # Calculate positions of planets, Juno, and Lilith
    for name, id in planet_ids.items():
        position, _ = swe.calc_ut(jd, id, swe.FLG_SWIEPH + swe.FLG_SPEED)
        longitude_deg = position[0]
        sign = get_sign(longitude_deg)
        house = assign_house_to_planet(longitude_deg, house_cusps) if house_cusps else None
        planetary_positions[name] = {'degree': longitude_deg, 'sign': sign, 'house': house}
    
    return planetary_positions, house_cusps

def get_relative_house_placements(house_cusps_subject, planets_other, pronoun_subject, pronoun_other):
    """Determine where each of the 'other' person's planets fall in the 'subject' person's chart."""
    if not house_cusps_subject:  # Skip if house cusps are unavailable
        return []
    
    house_placements = []
    for planet, data in planets_other.items():
        degree = data['degree']
        house = assign_house_to_planet(degree, house_cusps_subject)
        if house:
            house_placements.append(f"{pronoun_other.capitalize()} {planet} in {data['sign']} is in {pronoun_subject} {house}th house.")
    return house_placements

def generate_synastry_aspects(person1, person2, pronoun1, pronoun2):
    """Generate synastry aspects between two people's charts."""
    synastry_aspects = []
    for planet1, data1 in person1.items():
        for planet2, data2 in person2.items():
            angle = calculate_angle(data1['degree'], data2['degree'])
            aspect, strength_description = determine_aspect_and_strength(angle)
            if aspect:
                synastry_aspects.append(f"{pronoun1.capitalize()} {planet1} in {data1['sign']} is a {strength_description} {aspect} to {pronoun2} {planet2} in {data2['sign']}.")
    return synastry_aspects

def analyze_synastry_full(birthday1, location1, gender1, birthday2, location2, gender2, time1=None, time2=None):
    """
    Analyze synastry between two individuals with complete birth data.
    Returns a dictionary containing house placements and aspects.
    
    Args:
        birthday1 (datetime): First person's birth date
        location1 (str): First person's birth location
        gender1 (str): First person's gender ('male' or 'female')
        birthday2 (datetime): Second person's birth date
        location2 (str): Second person's birth location
        gender2 (str): Second person's gender ('male' or 'female')
        time1 (datetime.time, optional): First person's birth time
        time2 (datetime.time, optional): Second person's birth time
    
    Returns:
        dict: Contains 'house_placements' and 'aspects' lists
    """
    try:
        lat1, lon1 = get_coordinates(location1)
        lat2, lon2 = get_coordinates(location2)
        
        person1, house_cusps_person1 = get_planetary_positions(birthday1, time1, lat1, lon1)
        person2, house_cusps_person2 = get_planetary_positions(birthday2, time2, lat2, lon2)
        
        pronoun1 = PRONOUNS[gender1]
        pronoun2 = PRONOUNS[gender2]
        
        house_placements = []
        if house_cusps_person1:
            house_placements.extend(get_relative_house_placements(
                house_cusps_person1, person2, pronoun1, pronoun2))
        if house_cusps_person2:
            house_placements.extend(get_relative_house_placements(
                house_cusps_person2, person1, pronoun2, pronoun1))
        
        synastry_aspects = generate_synastry_aspects(person1, person2, pronoun1, pronoun2)
        
        return {
            'house_placements': house_placements,
            'aspects': synastry_aspects,
            'success': True,
            'error': None
        }
        
    except Exception as e:
        return {
            'house_placements': [],
            'aspects': [],
            'success': False,
            'error': str(e)
        }
