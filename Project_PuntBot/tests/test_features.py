from puntbot.features import parse_barrier
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
