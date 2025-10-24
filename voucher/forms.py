from django import forms
from .models import Voucher

class VoucherForm(forms.ModelForm):
    class Meta:
        model = Voucher
        # Kecualikan 'used_by' dan 'code' (jika Anda ingin admin mengetik kode sendiri)
        fields = ['code', 'discount_type', 'value', 'min_purchase_amount', 
                  'max_use_count', 'valid_from', 'valid_until', 'is_active']

        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'Otomatis jika dibiarkan kosong'}),
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'value': forms.NumberInput(attrs={'min': 0, 'step': 0.01}),
            'min_purchase_amount': forms.NumberInput(attrs={'min': 0, 'step': 0.01}),
        }

    def clean_code(self):
        # Jika user membiarkan kode kosong, model akan mengisi default-nya
        code = self.cleaned_data.get('code')
        return code.upper() if code else code