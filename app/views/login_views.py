from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import User
from django.contrib.auth.hashers import check_password
import uuid

def login_view(request):
    form_data = {}
    
    if request.method == 'POST':
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        
        form_data = {
            'email': email
        }

        if not email or not password:
            messages.error(request, 'Email dan password harus diisi.')
            return render(request, "base.html", {
                "content_template": "auth/login.html",
                "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
                "show_search_form": False,
                "form_data": form_data
            })

        try:
            user = User.nodes.get(email=email)
            
            if not user.is_verified:
                request.session['pending_verification_email'] = email
                request.session['from_login'] = True
                return redirect('verification_code')
            
            if user.check_password(password):
                request.session['user_id'] = str(user.userId)
                request.session['user_email'] = user.email
                request.session['user_name'] = user.name
                request.session['is_authenticated'] = True
                
                messages.success(request, "Anda Berhasil Login")
                return redirect('index')
            else:
                messages.error(request, 'Email atau password salah.')
        except User.DoesNotExist:
            messages.error(request, 'Email atau password salah.')
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan saat login: {str(e)}')
    
    return render(request, "base.html", {
        "content_template": "auth/login.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False,
        "form_data": form_data
    })