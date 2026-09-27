from puntbot.features import (
    adjusted_half_mile,
    inside_draw_score,
    parse_barrier,
    parse_front_row,
    parse_grade,
    parse_stewards_flags,
)
from puntbot.scrape_form import extract_race_table_data


def test_parse_barrier_uses_last_number():
    assert parse_barrier("2x1") == 1
    assert parse_barrier("Sr3") == 3
    assert parse_barrier("") != parse_barrier("")  # NaN


def test_extract_handles_form_column():
    html = """
    <table>
      <tr>
        <th>Place</th><th>Horse</th><th>Form</th><th>Row</th><th>Tab</th>
        <th>Trainer</th><th>Driver</th><th>Margin</th><th>Odds</th><th>Comments</th>
      </tr>
      <tr>
        <td>1</td><td>Test Horse</td><td>12345</td><td>1</td><td>4</td>
        <td>A Trainer</td><td>A Driver</td><td></td><td>$3.20</td><td>Handy</td>
      </tr>
    </table>
    """
    rows = extract_race_table_data(html)
    assert len(rows) == 1
    assert rows[0]["horse_name"] == "Test Horse"
    assert rows[0]["form"] == "12345"
    assert rows[0]["tab_number"] == 4
    assert rows[0]["starting_odds"] == 3.2
    assert rows[0]["place"] == 1


def test_parse_front_row_and_inside_draw():
    assert parse_front_row("Fr1") == 1
    assert parse_front_row("Sr3") == 0
    assert inside_draw_score(1.0, 1.0) > inside_draw_score(1.0, 6.0)
    assert inside_draw_score(0.0, 1.0) < inside_draw_score(1.0, 1.0)


def test_parse_stewards_speed_map_and_excuses():
    led = parse_stewards_flags("GS L 1 SWAB")
    assert led["led"] == 1
    assert led["gate_speed"] == 1
    death = parse_stewards_flags("RW WF OL 2")
    assert death["death"] == 1
    excuse = parse_stewards_flags("13 TIRE PP SD1T T/F")
    assert excuse["tyre"] == 1


def test_parse_metro_grade_from_market_name():
    assert parse_grade("R3 1660m Pace M") == 1.0
    assert parse_grade("R9 2096m Trot S") == 0.0


def test_solonsch_adjusted_half_adds_beaten_metres():
    assert abs(adjusted_half_mile(60.0, 7.0) - 60.5) < 1e-9
    assert adjusted_half_mile(60.0, 0.0) == 60.0
    assert adjusted_half_mile(60.0, 26.0) != adjusted_half_mile(60.0, 26.0)  # NaN blowout
