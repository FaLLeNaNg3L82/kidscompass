from datetime import date
from kidscompass.data import Database


def test_import_vacations_csv(tmp_path):
    csv_fn = tmp_path / 'vac.csv'
    # from_date,to_date,label
    csv_fn.write_text('2025-04-01,2025-04-10,Ostern\n2025-10-10,2025-10-20,Herbst')

    db = Database(str(tmp_path / 'vac.db'))
    created = db.import_vacations_from_csv(str(csv_fn), anchor_year=2025)
    # Two vacations -> 4 halves => 4 overrides created
    assert len(created) == 4

    # Check holders alternate according to anchor year
    holders = [getattr(o, 'holder', None) for o in created]
    # For 2025 anchor parity True -> first halves mother
    assert holders[0] == 'mother'
    assert holders[1] == 'father'

    db.close()
