# run.py
import os
import sys
import django
from django.core.management import call_command

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ServeTix.settings')
django.setup()

from matches.models import Team, Venue  # ← TAMBAH VENUE

def main():
    # Cek kalo data belum ada
    if Team.objects.count() == 0 or Venue.objects.count() == 0:  # ← CEK KEDUANYA
        print("🔧 Setting up sample data...")
        call_command('import_bulk', '--teams', 'nama_tim.csv', '--venues', 'lapangan.csv')
        print("✅ Data ready!")
    
    # Jalankan server
    print("🚀 Starting server...")
    call_command('runserver')

if __name__ == '__main__':
    main()