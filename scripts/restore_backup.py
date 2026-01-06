import os
import sys
import datetime
sys.path.insert(0, r'd:\Programmieren\kidscompass\src')
from kidscompass.data import Database

# Path to the backup created earlier
backup_fn = r'C:\Users\oneaboveall\\.kidscompass\\backup_before_cleanup_20250826_075441.sql'
# Normalize path
backup_fn = os.path.normpath(backup_fn)
print('Backup file to restore from:', backup_fn)

# Open DB and create a second backup of current state just in case
try:
    db = Database()
except Exception as e:
    print('Failed to open Database:', e)
    sys.exit(1)

now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
current_backup = os.path.join(os.path.dirname(db.db_path), f'backup_before_restore_{now}.sql')
print('Creating backup of current DB to:', current_backup)
db.export_to_sql(current_backup)

# Import the saved backup
try:
    print('Importing backup into DB...')
    db.import_from_sql(backup_fn)
    db.close()
    print('Restore complete.')
    print('Current DB backed up at:', current_backup)
except Exception as e:
    print('Restore failed:', e)
    db.close()
    sys.exit(1)
