from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import User
from django.http import JsonResponse
import random
from django.core.mail import send_mail
from django.conf import settings
import uuid

def verification_code(request):
    email = request.session.get('pending_verification_email')
    if not email:
        messages.error(request, 'Tidak ada verifikasi yang tertunda.')
        return redirect('register_view')
    
    if request.method == 'GET':
        try:
            user = User.nodes.get(email=email)
            if not user.is_verified:
                from_login = request.session.get('from_login', False)
                if from_login:
                    messages.warning(request, 'Email Anda belum diverifikasi. Silakan cek email untuk mendapatkan kode verifikasi dan lakukan verifikasi.')
                    if 'from_login' in request.session:
                        del request.session['from_login']
        except User.DoesNotExist:
            pass
    
    if request.method == 'POST':
        verification_code = request.POST.get('verification_code')
        
        try:
            user = User.nodes.get(email=email)
            
            if user.is_verified:
                messages.info(request, 'Akun Anda sudah diverifikasi.')
                return redirect('login_view')
            
            if user.email_verification == verification_code:
                user.is_verified = True
                user.email_verification = None 
                user.save()

                if 'pending_verification_email' in request.session:
                    del request.session['pending_verification_email']
                
                messages.success(request, 'Akun berhasil diverifikasi. Anda dapat login sekarang.')
                return redirect('login_view')
            else:
                messages.error(request, 'Kode verifikasi tidak valid.')
        
        except User.DoesNotExist:
            messages.error(request, 'Pengguna tidak ditemukan.')
            return redirect('register_view')
    
    return render(request, "base.html", {
        "content_template": "auth/verification-code.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False
    })

def resend_verification_code(request):
    """Mengirim ulang kode verifikasi via email"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Metode tidak diizinkan'}, status=405)
    
    email = request.session.get('pending_verification_email')
    if not email:
        return JsonResponse({'success': False, 'message': 'Tidak ada permintaan verifikasi yang tertunda'}, status=400)
    
    try:
        # Dapatkan user dari database
        user = User.nodes.get(email=email)
        
        if user.is_verified:
            return JsonResponse({'success': False, 'message': 'Akun sudah diverifikasi'}, status=400)
        
        # Generate kode verifikasi baru (6 digit)
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Simpan kode verifikasi baru ke database
        user.email_verification = verification_code
        user.save()
        
        # Kirim email
        subject = 'Kode Verifikasi Baru - Aplikasi Anda'
        message = f'''Halo {user.name},
        
        Berikut adalah kode verifikasi baru Anda: {verification_code}

        Terima kasih,
        TemuPaper
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        
        return JsonResponse({'success': True, 'message': 'Kode verifikasi baru telah dikirim ke email Anda'})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Pengguna tidak ditemukan'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Gagal mengirim kode verifikasi: {str(e)}'}, status=500)