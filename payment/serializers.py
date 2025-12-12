from rest_framework import serializers
from .models import Pembelian
from matches.models import Seat, Match


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ['id', 'seat_number', 'seat_type', 'price']


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = ['id', 'home_team', 'away_team', 'stadium', 'date']


class PembelianSerializer(serializers.ModelSerializer):
    match = MatchSerializer(read_only=True)
    seats = SeatSerializer(read_only=True, many=True)

    class Meta:
        model = Pembelian
        fields = [
            'id',
            'order_id',
            'user',
            'match',
            'seats',
            'total_price',
            'nama_lengkap_pembeli',
            'email',
            'nomor_telepon',
            'metode_pembayaran',
            'bukti_transfer',
            'status',
            'kode_voucher',
            'tanggal_pembelian',
        ]
        read_only_fields = ['order_id', 'status', 'tanggal_pembelian']
