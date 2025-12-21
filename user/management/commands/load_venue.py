import csv
import os
from django.core.management.base import BaseCommand, CommandError
# Asumsi Venue diimpor dari matches.models
from matches.models import Venue 

class Command(BaseCommand):
    help = 'Memuat data Venue dan harga kategori dari file CSV.'

    def handle(self, *args, **options):
        # Asumsi file CSV diletakkan di root proyek
        csv_file_path = 'staticfiles/csv/lapangan.csv'

        if not os.path.exists(csv_file_path):
            # Menggunakan pesan error yang jelas jika file tidak ada
            raise CommandError(f"File CSV tidak ditemukan di: {csv_file_path}. Pastikan bernama 'venue_data.csv'.")

        self.stdout.write(self.style.SUCCESS('--- MEMULAI LOAD DATA VENUE ---'))
        
        # Urutan field sesuai header CSV Anda
        field_order = [
            'nama_lapangan', 'alamat', 'kota', 'kapasitas_maks', 
            'harga_suporter', 'harga_bronze', 'harga_silver', 'harga_gold'
        ]
        
        rows_created = 0
        
        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                # Lewati baris header
                next(reader, None) 

                for row in reader:
                    if not row or not row[0].strip():
                        continue
                    
                    data = {}
                    
                    # 1. Parsing Data Row
                    for i, field_name in enumerate(field_order):
                        value = row[i].strip() if i < len(row) else None
                        
                        if 'harga' in field_name or field_name == 'kapasitas_maks':
                            # Konversi harga ke integer, default ke 0 jika N/A/kosong
                            try:
                                data[field_name] = int(value or 0)
                            except ValueError:
                                data[field_name] = 0
                        else:
                            data[field_name] = value

                    # 2. Konsolidasi Alamat (Karena Model Venue hanya punya 'address')
                    full_address = f"{data['alamat']}, {data['kota']}" 
                    
                    # 3. Create atau Get Venue
                    venue, created = Venue.objects.get_or_create(
                        name=data['nama_lapangan'],
                        defaults={
                            'address': full_address,
                            # Field harga TIDAK disimpan di model Venue BARU (matches/models.py)
                            # Field harga ini seharusnya ada di model SeatCategory atau model harga terpisah.
                        }
                    )
                    
                    # 4. Update jika sudah ada
                    if not created:
                        venue.address = full_address
                        venue.capacity = data['kapasitas_maks']
                        venue.save()
                    else:
                        rows_created += 1

            self.stdout.write(self.style.SUCCESS(
                f'\nLOAD BERHASIL! Total {rows_created} Venue baru dibuat.'
            ))

        except Exception as e:
            # Catch all exceptions during processing and report
            raise CommandError(f"Gagal memproses data: {e}")