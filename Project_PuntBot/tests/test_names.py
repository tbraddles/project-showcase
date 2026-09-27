from puntbot.names import normalize_horse_name, normalize_venue_name


def test_normalize_horse_strips_country_and_punctuation():
    assert normalize_horse_name("Flyin' Colours NZ") == "flyin colours"
    assert normalize_horse_name("Flying Colours (NZ)") == "flying colours"
    assert normalize_horse_name("O'Reilly's Dream") == "oreillys dream"


def test_normalize_venue_drops_park_noise():
    assert normalize_venue_name("Tabcorp Park Melton") == "melton"
    assert normalize_venue_name("Globe Derby Park") == "globe derby"
    assert normalize_venue_name("Menangle") == "menangle"
