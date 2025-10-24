from django.core.management.base import BaseCommand
from forums.models import Tag

class Command(BaseCommand):
    help = 'Initialize a small set of default forum tags for Liga Voli Indonesia'

    def handle(self, *args, **options):
        default_tags = [
            'tiket',
            'pertandingan',
            'tim_dan_pemain',
            'pengalaman_penonton',
            'berita',
            'website',
        ]

        created_count = 0
        for tag_name in default_tags:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'{created_count} tags added (total {Tag.objects.count()} in DB).')
        )
