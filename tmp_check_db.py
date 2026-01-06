import kidscompass.data as d
print('has import_vacations_from_ics:', hasattr(d.Database, 'import_vacations_from_ics'))
print('methods count:', len([n for n in dir(d.Database) if callable(getattr(d.Database,n)) and not n.startswith('__')]))
print('some attrs:', [n for n in dir(d.Database) if 'import_vac' in n or 'export_to_sql' in n or 'import_from_sql' in n])
