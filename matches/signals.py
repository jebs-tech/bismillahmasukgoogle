from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from matches.models import Match, SeatCategory, MatchSeatCapacity, Seat

DEFAULT_CAPACITY = 100

@receiver(post_save, sender=Match)
def create_match_capacities_and_seats(sender, instance, created, **kwargs):
    """
    Membuat kapasitas & seat untuk setiap kategori kursi 
    secara otomatis saat Match pertama kali dibuat.
    """
    if not created:
        return  # Hanya jalan saat pertama kali Match dibuat
    
    with transaction.atomic():
        all_categories = SeatCategory.objects.all()
        capacities_to_use = []

        # Cek apakah sudah ada kapasitas (misal dibuat via admin inline)
        existing_caps = list(MatchSeatCapacity.objects.filter(match=instance))
        if existing_caps:
            capacities_to_use = existing_caps
        else:
            # Jika belum ada, buat kapasitas default untuk semua kategori
            for category in all_categories:
                cap = MatchSeatCapacity.objects.create(
                    match=instance,
                    category=category,
                    capacity=DEFAULT_CAPACITY
                )
                capacities_to_use.append(cap)

        # Hapus seat lama (safety)
        Seat.objects.filter(match=instance).delete()

        # Buat seat sesuai kapasitas
        seats_to_create = []
        for cap in capacities_to_use:
            category = cap.category
            row_prefix = f"C{category.id}"
            for i in range(1, cap.capacity + 1):
                seats_to_create.append(
                    Seat(
                        match=instance,
                        category=category,
                        row=row_prefix,
                        col=i,
                        is_booked=False
                    )
                )

        Seat.objects.bulk_create(seats_to_create)
        print(f"✅ {len(seats_to_create)} seats created for match: {instance.title}")
