import csv
from django.core.management.base import BaseCommand
from user.models import Team  # Sesuaikan 'user.models' jika nama aplikasi Anda beda

class Command(BaseCommand):
    help = 'Memuat daftar tim dari file CSV ke database'

    def handle(self, *args, **kwargs):
        # Tentukan path ke file CSV Anda
        # (Asumsikan Anda meletakkan 'daftar_tim.csv' di root proyek, sejajar 'manage.py')
        csv_file_path = 'static/csv/nama_tim.csv'

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                
                # Lewati baris header (jika ada)
                next(reader, None)  

                self.stdout.write(self.style.SUCCESS('Mulai memuat tim...'))
                
                teams_created_count = 0
                teams_exist_count = 0

                # Asumsikan nama tim ada di kolom pertama (indeks 0)
                for row in reader:
                    team_name = row[0].strip()
                    
                    if not team_name:
                        continue # Lewati baris kosong

                    # Gunakan get_or_create untuk menghindari duplikat
                    obj, created = Team.objects.get_or_create(name=team_name)
                    
                    if created:
                        teams_created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Tim baru ditambahkan: "{team_name}"'))
                    else:
                        teams_exist_count += 1

            self.stdout.write(self.style.SUCCESS(
                f'\nSelesai. {teams_created_count} tim baru ditambahkan. {teams_exist_count} tim sudah ada.'
            ))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Error: File '{csv_file_path}' tidak ditemukan."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Terjadi error: {e}"))