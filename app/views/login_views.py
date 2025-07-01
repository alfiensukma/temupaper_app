from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import User
from django.contrib.auth.hashers import check_password

def login_view(request):
    form_data = {}

    def render_login():
        return render(request, "base.html", {
            "content_template": "auth/login.html",
            "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
            "show_search_form": False,
            "form_data": form_data
        })

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        form_data = {
            'email': email
        }

        if not email:
            messages.error(request, 'Email harus diisi.')
            return render_login()

        if not password:
            messages.error(request, 'Password harus diisi.')
            return render_login()

        try:
            user = User.nodes.get(email=email)

            if not user.is_verified:
                request.session['pending_verification_email'] = email
                request.session['from_login'] = True
                return redirect('verification_code')

            if not user.check_password(password):
                messages.error(request, 'Kata sandi salah.')
                return render_login()

            request.session['user_id'] = str(user.userId)
            request.session['user_email'] = user.email
            request.session['user_name'] = user.name
            request.session['is_authenticated'] = True

            roles = user.get_roles()
            request.session['user_roles'] = roles
            request.session['is_admin'] = 'Admin' in roles

            if 'Admin' in roles:
                messages.success(request, "Anda berhasil login sebagai Admin.")
                return redirect('/admin-app/')
            else:
                messages.success(request, "Anda berhasil login.")
                return redirect('index')

        except User.DoesNotExist:
            messages.error(request, 'Email tidak ditemukan.')
            return render_login()

        except Exception as e:
            messages.error(request, f'Terjadi kesalahan saat login: {str(e)}')
            return render_login()

    return render_login()