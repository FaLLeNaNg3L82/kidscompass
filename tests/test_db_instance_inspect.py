def test_db_instance_methods():
    from kidscompass.data import Database
    db = Database(':memory:')
    print('Database dir length:', len(dir(Database)))
    print('instance dir length:', len(dir(db)))
    print('Database import-related:', [n for n in dir(Database) if 'import_vac' in n or 'import_from_sql' in n])
    print('Instance import-related:', [n for n in dir(db) if 'import_vac' in n or 'import_from_sql' in n])
    assert hasattr(db, 'import_vacations_from_csv')
    # cleanup
    db.close()
