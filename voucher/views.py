from django.shortcuts import render
# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from .models import Voucher
from .forms import VoucherForm

# Fungsi pengecekan agar hanya superuser/staf yang bisa akses
def is_staff_or_superuser(user):
    return user.is_active and (user.is_staff or user.is_superuser)

@user_passes_test(is_staff_or_superuser, login_url='/admin/login/')
def voucher_dashboard(request):
    vouchers = Voucher.objects.all().order_by('-valid_until')
    context = {'vouchers': vouchers}
    return render(request, 'voucher/voucher_dashboard.html', context)

@user_passes_test(is_staff_or_superuser, login_url='/admin/login/')
def voucher_create_update(request, pk=None):
    instance = None
    if pk:
        instance = get_object_or_404(Voucher, pk=pk)

    form = VoucherForm(request.POST or None, instance=instance)

    if form.is_valid():
        form.save()
        msg = "berhasil diperbarui." if pk else "berhasil dibuat."
        messages.success(request, f"Voucher {form.instance.code} {msg}")
        return redirect('voucher:dashboard')

    context = {
        'form': form,
        'is_edit': pk is not None,
        'voucher': instance
    }
    return render(request, 'voucher/voucher_form.html', context)

@user_passes_test(is_staff_or_superuser, login_url='/admin/login/')
def voucher_delete(request, pk):
    voucher = get_object_or_404(Voucher, pk=pk)
    code = voucher.code

    if request.method == 'POST':
        voucher.delete()
        messages.warning(request, f"Voucher {code} telah dihapus.")
        return redirect('voucher:dashboard')

    return render(request, 'voucher/voucher_confirm_delete.html', {'voucher': voucher})