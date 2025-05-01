from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import User

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
                    messages.warning(request, 'Email Anda belum diverifikasi. Silakan verifikasi terlebih dahulu.')
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