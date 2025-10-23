from django.db import models
import uuid

class Payment(models.Model):
    METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('qris', 'QRIS'),
        ('ewallet', 'E-Wallet'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    user_id = models.IntegerField(default=1)  # sementara, nanti relasi ke User
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    transaction_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} - {self.method}"


class Ticket(models.Model):
    user_id = models.IntegerField(default=1)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    match_name = models.CharField(max_length=100)
    seat_number = models.CharField(max_length=10)
    category = models.CharField(max_length=30)
    qr_code_path = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.id} - {self.match_name}"
