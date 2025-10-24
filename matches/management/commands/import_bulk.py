import csv
from django.core.management.base import BaseCommand, CommandError
from matches.models import Team, Venue

def parse_teams_csv(path):
    """Parse one-column teams CSV"""
    names = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        rdr = csv.reader(fh)
        for row in rdr:
            if not row: continue
            v = row[0].strip()
            if v and v.lower() not in ('name','nama','tim','team'):
                names.append(v)
    return names

def parse_venues_csv(path):
    """Parse multi-column venues CSV"""
    venues = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        rdr = csv.DictReader(fh)
        for row in rdr:
            name = row['nama_lapangan'].strip()
            address = row['alamat'].strip()
            
            # Handle capacity field
            capacity_str = row['kapasitas_maks'].strip()
            try:
                capacity = int(capacity_str) if capacity_str and capacity_str != 'N/A' else None
            except ValueError:
                capacity = None
                
            if name:
                venues.append({
                    'name': name,
                    'address': address,
                    'capacity': capacity
                })
    return venues

class Command(BaseCommand):
    help = 'Bulk import teams and venues from CSVs'

    def add_arguments(self, parser):
        parser.add_argument('--teams', type=str, help='path to nama_tim.csv')
        parser.add_argument('--venues', type=str, help='path to lapangan.csv')

    def handle(self, *args, **opts):
        teams_path = opts.get('teams')
        venues_path = opts.get('venues')
        if not teams_path and not venues_path:
            raise CommandError('Provide --teams and/or --venues')

        if teams_path:
            names = parse_teams_csv(teams_path)
            existing = set(Team.objects.values_list('name', flat=True))
            to_create = [Team(name=n) for n in names if n and n not in existing]
            if to_create:
                Team.objects.bulk_create(to_create, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"Teams processed: {len(names)} created: {len(to_create)}"))

        if venues_path:
            venues_data = parse_venues_csv(venues_path)
            existing = set(Venue.objects.values_list('name', flat=True))
            to_create = []
            for venue in venues_data:
                if venue['name'] not in existing:
                    to_create.append(Venue(
                        name=venue['name'],
                        address=venue['address'],
                        capacity=venue['capacity']
                    ))
            if to_create:
                Venue.objects.bulk_create(to_create, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"Venues processed: {len(venues_data)} created: {len(to_create)}"))