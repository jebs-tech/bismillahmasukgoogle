# run.py
import os
import sys
import django
from django.core.management import call_command

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ServeTix.settings')
django.setup()

from matches.models import Team, Venue, SeatCategory

def main():
    print("🚀 Starting ServeTix setup...")
    
    # Cek apakah perlu install dependencies
    try:
        import widget_tweaks
        import qrcode
        import PIL
        import apscheduler
        print("✅ Dependencies already installed")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install django-widget-tweaks apscheduler qrcode[pil] pillow")
        return
    
    # Jalankan migrations hanya jika perlu
    try:
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections
        connection = connections['default']
        executor = MigrationExecutor(connection)
        plans = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plans:
            print("🔧 Running migrations...")
            call_command('makemigrations')
            call_command('migrate')
        else:
            print("✅ Database is up to date")
    except Exception as e:
        print(f"⚠️ Migration check failed: {e}")
        print("Running migrations anyway...")
        call_command('makemigrations')
        call_command('migrate')
    
    # Setup categories jika belum ada
    if SeatCategory.objects.count() == 0:
        print("🔧 Setting up seat categories...")
        call_command('setup_categories')
    else:
        print("✅ Seat categories already exist")
    
    # Setup teams jika belum ada
    if Team.objects.count() == 0:
        print("🔧 Loading teams...")
        call_command('load_teams')
    else:
        print("✅ Teams already loaded")
    
    # Setup venues jika belum ada
    if Venue.objects.count() == 0:
        print("🔧 Loading venues...")
        call_command('load_venue')
    else:
        print("✅ Venues already loaded")
    
    # Jalankan server
    print("🎉 Setup completed! Starting server...")
    call_command('runserver')

if __name__ == '__main__':
    main()