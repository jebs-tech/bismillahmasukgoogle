from django.shortcuts import render
from django.http import JsonResponse
from .models import Payment, Ticket
import qrcode
import os
from django.conf import settings

def create_payment(request):
    if request.method == 'POST':
        method = request.POST.get('method')
        amount = request.POST.get('amount')
        match_name = request.POST.get('match_name')
        seat_number = request.POST.get('seat_number')
        category = request.POST.get('category')

        # Simulasi pembayaran sukses
        payment = Payment.objects.create(
            user_id=1,
            method=method,
            amount=amount,
            status='success',
        )

        # Buat tiket otomatis
        ticket = Ticket.objects.create(
            user_id=1,
            payment=payment,
            match_name=match_name,
            seat_number=seat_number,
            category=category,
        )

        # Generate QR Code
        qr_data = str(payment.transaction_code)
        qr_dir = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
        os.makedirs(qr_dir, exist_ok=True)
        qr_path = os.path.join(qr_dir, f'ticket_{ticket.id}.png')

        img = qrcode.make(qr_data)
        img.save(qr_path)

        ticket.qr_code_path = f'qrcodes/ticket_{ticket.id}.png'
        ticket.save()

        return JsonResponse({
            'message': 'Pembayaran berhasil & e-ticket dibuat',
            'payment': {
                'id': payment.id,
                'method': payment.method,
                'amount': str(payment.amount),
                'status': payment.status,
                'transaction_code': str(payment.transaction_code)
            },
            'ticket': {
                'id': ticket.id,
                'match_name': ticket.match_name,
                'seat_number': ticket.seat_number,
                'category': ticket.category,
                'qr_code_url': ticket.qr_code_path.url if ticket.qr_code_path else None
            }
        })

    return JsonResponse({'error': 'Gunakan metode POST'}, status=400)
