from django import forms
from .models import Voucher

class VoucherForm(forms.ModelForm):
    class Meta:
        model = Voucher
        fields = ['code', 'discount_type', 'value', 'min_purchase_amount', 
                  'max_use_count', 'valid_from', 'valid_until', 'is_active']
        
        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'Otomatis jika dibiarkan kosong'}),
            # Menggunakan Date and Time Input
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'value': forms.NumberInput(attrs={'min': 0, 'step': 0.01}),
            'min_purchase_amount': forms.NumberInput(attrs={'min': 0, 'step': 0.01}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Atur nilai default untuk form baru
        if not self.instance.pk:
            self.fields['max_use_count'].initial = 1
            self.fields['min_purchase_amount'].initial = 0
            
        # 2. Tambahkan class CSS Tailwind ke SEMUA field
        tailwind_class = 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-brand-light-blue focus:border-brand-light-blue transition duration-150'
        
        for name, field in self.fields.items():
            # Kecualikan checkbox agar tidak merusak styling
            if field.widget.__class__.__name__ != 'CheckboxInput':
                field.widget.attrs.update({'class': tailwind_class})

        # Atur styling khusus untuk Select (Tipe Diskon)
        self.fields['discount_type'].widget.attrs.update({'class': tailwind_class})
        

    def clean_code(self):
        # Jika user membiarkan kode kosong, model akan mengisi default-nya
        code = self.cleaned_data.get('code')
        return code.upper() if code else code