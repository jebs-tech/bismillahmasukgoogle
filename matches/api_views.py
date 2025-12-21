from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# Pastikan import sesuai dengan lokasi models Anda
from .models import Match, Seat, SeatCategory, Venue, Team
# Saya asumsikan model Booking dan Passenger ada di models.py (walau tidak tertera di snippet terakhir)
# Jika ada di file lain, silakan sesuaikan importnya
try:
    from .models import Booking, Passenger
except ImportError:
    # Fallback jika model belum dibuat
    pass

class MatchDetailAPI(APIView):
    """
    Mengambil detail pertandingan lengkap untuk MatchDetailPage di Flutter.
    Memperbaiki masalah venue_address yang kosong.
    """
    def get(self, request, pk):
        try:
            # Menggunakan select_related untuk mengambil data Venue dan Team sekaligus
            match = Match.objects.select_related(
                'venue', 
                'team_a', 
                'team_b'
            ).get(pk=pk)
        except Match.DoesNotExist:
            return Response(
                {"detail": "Match not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # mapping data agar pas dengan MatchDetail.fromJson di Flutter
        data = {
            "id": match.id,
            "team_a": match.team_a.name if match.team_a else "TBA",
            "team_b": match.team_b.name if match.team_b else "TBA",
            # Menambahkan URL logo untuk UI Match Card
            "team_a_logo": match.team_a.logo.url if match.team_a and match.team_a.logo else None,
            "team_b_logo": match.team_b.logo.url if match.team_b and match.team_b.logo else None,
            "venue": match.venue.name,
            # FIX: Mengambil field 'address' dari model Venue
            "venue_address": match.venue.address or "Alamat tidak tersedia",
            "start_time": match.start_time,
            "description": match.description,
            # Mengambil price_from langsung dari field di model Match
            "price_from": match.price_from,
        }

        return Response(data, status=status.HTTP_200_OK)

class MatchSeatsAPI(APIView):
    """
    Mengambil daftar semua kursi untuk denah stadion/seat availability.
    """
    def get(self, request, match_id):
        # Optimasi query dengan select_related kategori
        seats = Seat.objects.filter(match_id=match_id).select_related('category')
        data = []

        for seat in seats:
            # Label dibuat dari gabungan Row dan Col (misal: A1)
            label = f"{seat.row}{seat.col}"
            data.append({
                "id": seat.id,
                "label": label,
                "category": seat.category.name,
                "price": seat.category.price,
                "is_booked": seat.is_booked
            })

        return Response({"seats": data})

class BookWithSeatsAPI(APIView):
    """
    Proses Booking berdasarkan pemilihan kursi spesifik.
    """
    @transaction.atomic
    def post(self, request):
        data = request.data
        match_id = data.get("match_id")
        seat_ids = data.get("seat_ids", [])
        passengers = data.get("passengers", [])
        buyer_name = data.get("buyer_name")
        buyer_email = data.get("buyer_email", "")

        if not seat_ids or len(seat_ids) != len(passengers):
            return Response(
                {"ok": False, "msg": "Data kursi dan penumpang tidak sinkron"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            match = Match.objects.get(id=match_id)
            # select_for_update mencegah dua orang memboking kursi yang sama di waktu bersamaan
            seats = Seat.objects.select_for_update().filter(id__in=seat_ids, is_booked=False)

            if seats.count() != len(seat_ids):
                return Response(
                    {"ok": False, "msg": "Beberapa kursi sudah terpesan"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            total_price = sum(seat.category.price for seat in seats)

            # Logic Booking & Passenger (Sesuaikan dengan field di model Booking Anda)
            booking = Booking.objects.create(
                match=match,
                buyer_name=buyer_name,
                buyer_email=buyer_email,
                total_price=total_price
            )

            assigned = []
            for seat, p in zip(seats, passengers):
                Passenger.objects.create(
                    booking=booking,
                    name=p["name"],
                    email=p.get("email", ""),
                    seat=seat
                )
                seat.is_booked = True
                seat.save()

                assigned.append({
                    "passenger": p["name"],
                    "seat_label": f"{seat.row}{seat.col}"
                })

            return Response({
                "ok": True, 
                "booking_id": booking.id, 
                "total_price": total_price,
                "assigned": assigned
            })

        except Exception as e:
            return Response({"ok": False, "msg": str(e)}, status=500)

class BookByQuantityAPI(APIView):
    """
    Booking otomatis berdasarkan jumlah tiket (best-effort seat allocation).
    """
    @transaction.atomic
    def post(self, request):
        data = request.data
        match_id = data.get("match_id")
        quantity = int(data.get("quantity", 0))
        passengers = data.get("passengers", [])

        if quantity <= 0 or quantity != len(passengers):
            return Response({"ok": False, "msg": "Kuantitas tidak valid"}, status=400)

        try:
            match = Match.objects.get(id=match_id)
            available_seats = Seat.objects.select_for_update().filter(
                match=match, is_booked=False
            )[:quantity]

            if len(available_seats) < quantity:
                return Response({"ok": False, "msg": "Kursi tersedia tidak mencukupi"}, status=400)

            total_price = sum(seat.category.price for seat in available_seats)

            booking = Booking.objects.create(
                match=match,
                buyer_name=data.get("buyer_name"),
                buyer_email=data.get("buyer_email"),
                total_price=total_price
            )

            for seat, p in zip(available_seats, passengers):
                Passenger.objects.create(booking=booking, name=p["name"], seat=seat)
                seat.is_booked = True
                seat.save()

            return Response({"ok": True, "booking_id": booking.id, "total_price": total_price})
        except Exception as e:
            return Response({"ok": False, "msg": str(e)}, status=500)