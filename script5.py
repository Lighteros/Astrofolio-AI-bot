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
    """Get the ecliptic longitudes of planets on a specific date without time or location."""
    swe.set_ephe_path('/usr/share/swisseph/ephe')
    jd = swe.julday(date.year, date.month, date.day, 12)  # Noon as a default time

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
        'Lilith': swe.MEAN_NODE + 1,
        'Fortuna': 19
    }

    planetary_positions = {}
    for name, id in planet_ids.items():
        position, _ = swe.calc_ut(jd, id, swe.FLG_SWIEPH + swe.FLG_SPEED)
        longitude_deg = position[0]
        sign = get_sign(longitude_deg)
        planetary_positions[name] = {'degree': longitude_deg, 'sign': sign}

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
    """Generate descriptions for the sign placement of each planet."""
    descriptions = []
    for planet, data in planets.items():
        sign = data['sign']
        descriptions.append(f"{planet} is in {sign}")
    return descriptions

# Example usage
def analyze_natal_chart_basic(birthday):
    """
    Analyze a basic birth chart using only the birth date.
    
    Args:
        birthday (datetime): Birth date
    
    Returns:
        dict: Contains sign placements and aspects
    """
    try:
        planets = get_planetary_positions(birthday)
        
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
        