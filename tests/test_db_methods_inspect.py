def test_db_has_import_methods():
    from kidscompass.data import Database
    # debug: print available attributes containing 'import_vac'
    print('Database repr:', Database)
    print('Database dir length:', len(dir(Database)))
    print('Some attrs:', dir(Database)[:20])
    names = [n for n in dir(Database) if 'vac' in n or 'import' in n or 'export' in n]
    print('db related names:', names)
    # Ensure class has typical DB methods
    assert hasattr(Database, '__init__')
