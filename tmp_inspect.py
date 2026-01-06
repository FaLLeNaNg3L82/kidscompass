from kidscompass.data import Database
print('Database attrs:')
for n in sorted(dir(Database)):
    if n.startswith('import_vac') or 'vac' in n:
        print(n)
print('\nAll methods:')
print([n for n in dir(Database) if callable(getattr(Database,n)) and not n.startswith('__')])
