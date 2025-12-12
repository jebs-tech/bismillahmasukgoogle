# payment/api_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Pembelian
from matches.models import Match, Seat, SeatCategory
from voucher.utils import validate_and_apply_voucher
from .views import generate_qr_code


class CreatePembelianAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        data = request.data

        required = ['match_id', 'kategori_id', 'jumlah_tiket']
        if not all(f in data for f in required):
            return Response({"error": "Data tidak lengkap."}, status=400)

        jumlah = int(data['jumlah_tiket'])

        match = get_object_or_404(Match, id=data['match_id'])
        kategori = get_object_or_404(SeatCategory, id=data['kategori_id'])

        seats = Seat.objects.select_for_update().filter(
            match=match,
            category=kategori,
            is_booked=False
        )[:jumlah]

        if len(seats) < jumlah:
            return Response({"error": "Kursi tidak mencukupi."}, status=409)

        harga_dasar = jumlah * kategori.price
        voucher_code = data.get('kode_voucher', '').strip()
        discount = 0

        if voucher_code:
            discount, error = validate_and_apply_voucher(
                voucher_code,
                request.user,
                float(harga_dasar)
            )
            if error:
                return Response({"error": error}, status=400)

        total_final = harga_dasar - discount

        pembelian = Pembelian.objects.create(
            user=request.user,
            match=match,
            nama_lengkap_pembeli=request.user.get_full_name(),
            email=request.user.email,
            nomor_telepon=getattr(request.user, "phone", "-"),
            total_price=total_final,
            kode_voucher=voucher_code or "",
            status='PENDING',
        )
        pembelian.seats.set(seats)

        seats.update(is_booked=True)

        return Response({
            "order_id": pembelian.order_id,
            "total_price": total_final,
            "discount": discount,
        }, status=201)


class KonfirmasiPembayaranAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        pembelian = get_object_or_404(Pembelian, order_id=order_id)

        metode = request.data.get("metode_pembayaran")
        bukti = request.FILES.get("bukti_transfer")

        if not metode:
            return Response({"error": "Metode pembayaran wajib."}, status=400)

        if metode in ['BRI', 'BCA', 'Mandiri'] and not bukti:
            return Response({"error": "Bukti transfer wajib."}, status=400)

        pembelian.metode_pembayaran = metode
        if bukti:
            pembelian.bukti_transfer = bukti
        pembelian.status = "CONFIRMED"
        pembelian.save()

        # Generate QR untuk setiap seat
        qr_results = []
        for seat in pembelian.seats.all():
            data_string = f"SERVETIX-{pembelian.order_id}-{seat.id}"
            qr_file = generate_qr_code(data_string)
            seat.qr_code_data = data_string
            seat.file_qr_code.save(qr_file.name, qr_file, save=True)
            qr_results.append({
                "seat_id": seat.id,
                "qr_data": data_string,
                "qr_url": seat.file_qr_code.url
            })

        return Response({
            "order_id": pembelian.order_id,
            "status": "CONFIRMED",
            "qr_codes": qr_results
        }, status=200)


class DetailETicketAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        pembelian = get_object_or_404(Pembelian, order_id=order_id)

        seat_data = []
        for seat in pembelian.seats.all():
            seat_data.append({
                "seat_id": seat.id,
                "seat_number": seat.seat_number,
                "qr_data": seat.qr_code_data,
                "qr_url": seat.file_qr_code.url if seat.file_qr_code else None
            })

        return Response({
            "order_id": pembelian.order_id,
            "match": pembelian.match.id,
            "status": pembelian.status,
            "total_price": pembelian.total_price,
            "seats": seat_data
        })
