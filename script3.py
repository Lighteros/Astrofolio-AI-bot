import swisseph as swe
import os
from datetime import datetime

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

def get_planetary_positions(date):
    """Get the ecliptic longitudes of planets on a specific date without houses or location-dependent planets."""
    swe.set_ephe_path('/usr/share/swisseph/ephe')
    jd = swe.julday(date.year, date.month, date.day)
    
    planetary_positions = {}
    for name, id in planet_ids.items():
        position, _ = swe.calc_ut(jd, id, swe.FLG_SWIEPH + swe.FLG_SPEED)
        longitude_deg = position[0]
        sign = get_sign(longitude_deg)
        planetary_positions[name] = {'degree': longitude_deg, 'sign': sign}
    
    return planetary_positions

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

def analyze_synastry_basic(birthday1, gender1, birthday2, gender2):
    """
    Analyze basic synastry between two individuals using only birth dates.
    
    Args:
        birthday1 (datetime): First person's birth date
        gender1 (str): First person's gender ('male' or 'female')
        birthday2 (datetime): Second person's birth date
        gender2 (str): Second person's gender ('male' or 'female')
    
    Returns:
        dict: Contains aspects list
    """
    try:
        person1 = get_planetary_positions(birthday1)
        person2 = get_planetary_positions(birthday2)
        
        pronoun1 = PRONOUNS[gender1]
        pronoun2 = PRONOUNS[gender2]
        
        synastry_aspects = generate_synastry_aspects(person1, person2, pronoun1, pronoun2)
        
        return {
            'aspects': synastry_aspects,
            'success': True,
            'error': None
        }
        
    except Exception as e:
        return {
            'aspects': [],
            'success': False,
            'error': str(e)
        }