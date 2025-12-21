import csv
from django.core.management.base import BaseCommand
from matches.models import SeatCategory

class Command(BaseCommand):
    help = 'Membuat kategori kursi default (Emas, Perak, Perunggu, Suporter) jika belum ada.'

    def handle(self, *args, **options):
        # Data Kategori Default
        categories_data = [
            {'name': 'Emas', 'price': 500000, 'color': '#FFD700'}, # Gold (Kuning Emas)
            {'name': 'Perak', 'price': 250000, 'color': '#C0C0C0'}, # Silver (Abu Perak)
            {'name': 'Perunggu', 'price': 150000, 'color': '#CD7F32'}, # Bronze (Coklat Perunggu)
            {'name': 'Suporter', 'price': 75000, 'color': '#A9A9A9'}, # Suporter (Abu Gelap)
        ]

        created_count = 0
        
        for data in categories_data:
            # Menggunakan get_or_create untuk menghindari duplikasi
            # Jika kategori sudah ada, ia akan diambil (tidak dibuat ulang)
            try:
                obj, created = SeatCategory.objects.get_or_create(
                    name=data['name'],
                    defaults={'price': data['price'], 'color': data['color']}
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"✅ Kategori dibuat: {data['name']} (Rp {data['price']:,})"))
                else:
                    self.stdout.write(f"⚠️ Kategori sudah ada: {data['name']}")
                    # Opsional: Jika sudah ada, update harganya
                    if obj.price != data['price']:
                         obj.price = data['price']
                         obj.save()
                         self.stdout.write(f"   Harga {data['name']} diupdate.")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Gagal memproses {data['name']}: {e}"))


        self.stdout.write(self.style.SUCCESS(
            f'\nSETUP KATEGORI SELESAI. {created_count} kategori baru telah dipastikan.'
        ))