# views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from app.models import User

import random
import string
import uuid

def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def verification_email(request):
    if request.method == "POST":
        email = request.POST.get('verification_email')
        
        try:
            user = User.nodes.get(email=email)
            
            verification_code = generate_verification_code()
            
            user.email_verification = verification_code
            user.save()
            
            try:
                send_mail(
                    'Verifikasi Akun Anda',
                    f'Kode verifikasi Anda adalah: {verification_code}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, f"Kode verifikasi telah dikirim ke {email}")
                
                request.session['verification_email'] = email
                
                return redirect('verification_codes')
            except Exception as e:
                print(f"Failed to send verification email: {str(e)}")
                messages.error(request, "Gagal mengirim email verifikasi. Silakan coba lagi.")
        except User.DoesNotExist:
            messages.error(request, "Email tidak terdaftar dalam sistem kami.")
    
    return render(request, "base.html", {
        "content_template": "auth/verification-email.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False
    })

def verification_codes(request):
    email = request.session.get('verification_email')
    
    if not email:
        messages.error(request, "Silakan masukkan email Anda terlebih dahulu.")
        return redirect('verification_email')
    
    if request.method == "POST":
        code = request.POST.get('verification_code')
        
        try:
            user = User.nodes.get(email=email)
            
            if user.email_verification == code:
                user.is_verified = True
                user.email_verification = None 
                user.save()
                
                messages.success(request, "Email berhasil diverifikasi!")
                
                return redirect('reset_password')  
            else:
                messages.error(request, "Kode verifikasi tidak valid. Silakan coba lagi.")
        except User.DoesNotExist:
            messages.error(request, "Terjadi kesalahan. Silakan coba lagi.")
    
    return render(request, "base.html", {
        "content_template": "auth/verification-code.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False
    })

