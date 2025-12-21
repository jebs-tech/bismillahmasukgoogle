from django.contrib import admin
from .models import Voucher, VoucherUsage
from django.utils.html import format_html # Digunakan untuk warna
@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        'code', 
        'discount_type', 
        'value', 
        'usage_count', 
        'max_use_count', 
        'is_active', 
        'valid_until'
    )
    list_filter = ('discount_type', 'is_active', 'valid_until')
    search_fields = ('code', 'value')
    ordering = ('-valid_until',)
    
    # fieldsets DIBENARKAN
    fieldsets = (
        (None, {
            'fields': ('code', 'discount_type', 'value', 'is_active')
        }),
        ('Batasan Penggunaan', {
            'fields': ('max_use_count', 'min_purchase_amount')
        }),
        ('Masa Berlaku', {
            'fields': ('valid_from', 'valid_until')
        }),
        # Blok 'Pelacakan' yang berisi 'used_by' dihapus
        # karena tidak dapat diedit secara langsung di sini.
        # Anda bisa melihat penggunaan di admin VoucherUsage.
    )

    def usage_count(self, obj):
        return obj.voucherusage_set.count()
    usage_count.short_description = "Penggunaan"
    
@admin.register(VoucherUsage)
class VoucherUsageAdmin(admin.ModelAdmin):
    list_display = ('voucher', 'user', 'used_at')
    list_filter = ('used_at', 'voucher')
    search_fields = ('voucher__code', 'user__username')