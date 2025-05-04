from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import Institution, User
import random
import string
from django.core.mail import send_mail
from django.conf import settings

def generate_verification_code(length=6):
    """Generate a random verification code"""
    return ''.join(random.choices(string.digits, k=length))

def register_view(request):
    institutions = Institution.nodes.all()
    form_data = {}

    if request.method == 'POST':
        form_data = {
            'username': request.POST.get('username', ''),
            'email': request.POST.get('email', ''),
            'institution': request.POST.get('institution', ''),
        }

        name = form_data['username']
        email = form_data['email']
        password = request.POST.get('password')
        password_confirmation = request.POST.get('password_confirmation')
        institution_id = form_data['institution']

        errors = False

        if not name:
            messages.error(request, 'Nama lengkap harus diisi.')
            errors = True
        if not email:
            messages.error(request, 'Email harus diisi.')
            errors = True
        if not password:
            messages.error(request, 'Password harus diisi.')
            errors = True
        if not institution_id:
            messages.error(request, 'Institusi harus dipilih.')
            errors = True
        if password != password_confirmation:
            messages.error(request, 'Password dan konfirmasi password tidak cocok.')
            errors = True
        if email and '@' not in email:
            messages.error(request, 'Format email tidak valid.')
            errors = True
        if password and len(password) < 8:
            messages.error(request, 'Password harus minimal 8 karakter.')
            errors = True

        if email and not errors:
            try:
                existing_user = User.nodes.get(email=email)
                messages.error(request, 'Email sudah terdaftar.')
                errors = True
            except User.DoesNotExist:
                pass
            except Exception as e:
                messages.error(request, f'Terjadi kesalahan saat memeriksa email: {str(e)}')
                errors = True

        if institution_id and not errors:
            try:
                Institution.nodes.get(institutionId=institution_id)
            except Institution.DoesNotExist:
                messages.error(request, 'Institusi yang dipilih tidak valid.')
                errors = True
            except Exception as e:
                messages.error(request, f'Terjadi kesalahan saat memeriksa institusi: {str(e)}')
                errors = True

        if errors:
            return render(request, "base.html", {
                "content_template": "auth/register.html",
                "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
                "show_search_form": False,
                "institutions": institutions,
                "form_data": form_data
            })

        try:
            verification_code = generate_verification_code()
            user = User(
                name=name,
                email=email,
                email_verification=verification_code,
                is_verified=False
            )
            user.set_password(password)
            user.save()

            institution = Institution.nodes.get(institutionId=institution_id)
            user.affiliated_with.connect(institution)

            try:
                send_mail(
                    'Verifikasi Akun Anda',
                    f'Kode verifikasi Anda adalah: {verification_code}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send verification email: {str(e)}")
                messages.warning(request, 'Akun berhasil dibuat tetapi email verifikasi gagal dikirim. Silakan hubungi admin.')

            request.session['pending_verification_email'] = email
            messages.success(request, "Kode verifikasi telah dikirim ke email Anda. Silakan periksa email Anda untuk menyelesaikan pendaftaran.")
            return redirect('verification_code')

        except Exception as e:
            messages.error(request, f'Registrasi gagal: {str(e)}')
            return render(request, "base.html", {
                "content_template": "auth/register.html",
                "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
                "show_search_form": False,
                "institutions": institutions,
                "form_data": form_data
            })

    return render(request, "base.html", {
        "content_template": "auth/register.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False,
        "institutions": institutions,
        "form_data": form_data
    })
