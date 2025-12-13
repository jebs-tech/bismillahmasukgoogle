from django.shortcuts import render
# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from .models import Voucher, VoucherUsage
from .forms import VoucherForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.utils.timezone import now
from django.contrib.auth import get_user_model

User = get_user_model()

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

@require_http_methods(["GET", "OPTIONS"])
def api_voucher_list(request):
    # Handle OPTIONS request untuk CORS preflight
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    """GET: return only valid vouchers"""
    now_time = now()

    vouchers = Voucher.objects.filter(
        is_active=True,
        valid_from__lte=now_time,
        valid_until__gte=now_time,
    ).order_by('valid_until')

    data = []
    for v in vouchers:
        # Format tanggal ke ISO format untuk JSON
        data.append({
            "id": v.id,
            "code": v.code,
            "discount_type": v.discount_type,
            "value": float(v.value),
            "min_purchase_amount": float(v.min_purchase_amount),
            "max_use_count": v.max_use_count,
            "valid_from": v.valid_from.isoformat(),
            "valid_until": v.valid_until.isoformat(),
        })

    response = JsonResponse({"success": True, "vouchers": data}, safe=False)
    # Add CORS headers untuk Flutter
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def api_redeem_voucher(request):
    # Handle OPTIONS request untuk CORS preflight
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    """POST: redeem voucher berdasarkan kode"""
    try:
        body = json.loads(request.body)
        code = body.get("code", "").strip().upper()
        user_id = body.get("user_id")  # Optional, untuk tracking user

        if not code:
            response = JsonResponse({"success": False, "message": "Kode voucher diperlukan"}, status=400)
            response["Access-Control-Allow-Origin"] = "*"
            return response

        # Cari voucher (case-insensitive)
        voucher = Voucher.objects.filter(code__iexact=code).first()
        if not voucher:
            response = JsonResponse({"success": False, "message": "Kode voucher tidak ditemukan"}, status=404)
            response["Access-Control-Allow-Origin"] = "*"
            return response

        # Cek status aktif
        now_time = now()
        if not voucher.is_active:
            response = JsonResponse({"success": False, "message": "Voucher tidak aktif"}, status=400)
            response["Access-Control-Allow-Origin"] = "*"
            return response

        # Cek validitas waktu
        if voucher.valid_from > now_time:
            response = JsonResponse({"success": False, "message": "Voucher belum berlaku"}, status=400)
            response["Access-Control-Allow-Origin"] = "*"
            return response
        
        if voucher.valid_until < now_time:
            response = JsonResponse({"success": False, "message": "Voucher sudah kadaluarsa"}, status=400)
            response["Access-Control-Allow-Origin"] = "*"
            return response

        # Cek batas penggunaan global
        used_count = VoucherUsage.objects.filter(voucher=voucher).count()
        if used_count >= voucher.max_use_count:
            response = JsonResponse({"success": False, "message": "Voucher telah mencapai batas maksimal penggunaan"}, status=400)
            response["Access-Control-Allow-Origin"] = "*"
            return response

        # Cek apakah user sudah pernah menggunakan (jika user_id diberikan)
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                if VoucherUsage.objects.filter(voucher=voucher, user=user).exists():
                    response = JsonResponse({"success": False, "message": "Anda sudah pernah menggunakan voucher ini"}, status=400)
                    response["Access-Control-Allow-Origin"] = "*"
                    return response
            except User.DoesNotExist:
                pass  # Jika user tidak ditemukan, lanjutkan tanpa tracking user

        # Record penggunaan (jika user_id diberikan)
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                VoucherUsage.objects.get_or_create(voucher=voucher, user=user)
            except User.DoesNotExist:
                pass

        # Hitung diskon untuk response
        discount_info = {
            "discount_type": voucher.discount_type,
            "value": float(voucher.value),
            "min_purchase_amount": float(voucher.min_purchase_amount),
        }

        response = JsonResponse({
            "success": True,
            "message": "Voucher berhasil digunakan",
            "voucher": {
                "id": voucher.id,
                "code": voucher.code,
                **discount_info
            }
        })
        # Add CORS headers untuk Flutter
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    except json.JSONDecodeError:
        response = JsonResponse({"success": False, "message": "Format JSON tidak valid"}, status=400)
        response["Access-Control-Allow-Origin"] = "*"
        return response
    except Exception as e:
        response = JsonResponse({"success": False, "message": f"Terjadi kesalahan: {str(e)}"}, status=500)
        response["Access-Control-Allow-Origin"] = "*"
        return response
