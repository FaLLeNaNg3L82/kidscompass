from datetime import date
from kidscompass.data import Database


def test_import_vacations_csv(tmp_path):
    csv_fn = tmp_path / 'vac.csv'
    # from_date,to_date,label
    csv_fn.write_text('2025-04-01,2025-04-10,Ostern\n2025-10-10,2025-10-20,Herbst')

    db = Database(str(tmp_path / 'vac.db'))
    created = db.import_vacations_from_csv(str(csv_fn), anchor_year=2025)
    # mine_only default True -> one override per vacation (my portion only)
    assert len(created) == 2

    # Check holder is set to 'father' for imported my-days
    holders = [getattr(o, 'holder', None) for o in created]
    assert all(h == 'father' for h in holders)

    db.close()
