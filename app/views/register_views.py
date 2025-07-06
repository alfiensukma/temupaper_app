from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import Institution, User, Role
import random
import string
import uuid
import logging
from django.core.mail import send_mail
from django.conf import settings
from neomodel import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_verification_code(length=6):
    """Generate a random verification code"""
    return ''.join(random.choices(string.digits, k=length))

def check_neo4j_connection():
    try:
        result, _ = db.cypher_query("MATCH (n) RETURN count(n)")
        logger.info(f"Neo4j connection check: {result[0][0]} nodes found")
        return True
    except Exception as e:
        logger.error(f"Neo4j connection check failed: {str(e)}")
        return False

def ensure_default_role():
    try:
        result, _ = db.cypher_query(
            "MATCH (r:Role {nama: $nama}) RETURN r.role_id LIMIT 1",
            {"nama": "User"}
        )
        if result:
            role_id = result[0][0]
            return Role.nodes.get(role_id=role_id)
        
        role_id = str(uuid.uuid4())
        while True:
            check_result, _ = db.cypher_query(
                "MATCH (r:Role {role_id: $role_id}) RETURN r",
                {"role_id": role_id}
            )
            if not check_result:
                break
            role_id = str(uuid.uuid4())
        
        db.cypher_query(
            "CREATE (r:Role {role_id: $role_id, nama: $nama})",
            {"role_id": role_id, "nama": "User"}
        )
        return Role.nodes.get(role_id=role_id)
    except Exception as e:
        logger.error(f"Failed to ensure default User role: {str(e)}")
        raise
    
def check_role_index():
    try:
        result, _ = db.cypher_query("SHOW INDEXES WHERE type = 'RANGE' AND entityType = 'NODE' AND labelsOrTypes = ['Role']")
        has_nama_index = any(index[3] == ['nama'] for index in result)
        if not has_nama_index:
            db.cypher_query("CREATE INDEX FOR (r:Role) ON (r.nama)")
    except Exception as e:
        logger.error(f"Failed to check or create index for Role.nama: {str(e)}")

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
                logger.error(f"Error checking email: {str(e)}")
                messages.error(request, f'Terjadi kesalahan saat memeriksa email')
                errors = True

        if institution_id and not errors:
            try:
                Institution.nodes.get(institutionId=institution_id)
            except Institution.DoesNotExist:
                messages.error(request, 'Institusi yang dipilih tidak valid.')
                errors = True
            except Exception as e:
                logger.error(f"Error checking institution: {str(e)}")
                messages.error(request, f'Terjadi kesalahan saat memeriksa institusi')
                errors = True

        if errors:
            return render(request, "base.html", {
                "content_template": "auth/register.html",
                "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
                "show_search_form": False,
                "institutions": institutions,
                "form_data": form_data
            })

        if not check_neo4j_connection():
            logger.error("Cannot proceed with registration due to Neo4j connection failure")
            messages.error(request, 'Gagal terhubung ke database. Silakan coba lagi nanti.')
            return render(request, "base.html", {
                "content_template": "auth/register.html",
                "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
                "show_search_form": False,
                "institutions": institutions,
                "form_data": form_data
            })
            
        check_role_index()

        try:
            with db.transaction:
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
                    role = ensure_default_role()
                    user.has_role.connect(role)
                except Exception as role_error:
                    logger.error(f"Error connecting user {email} to Role: {str(role_error)}")
                    raise

            try:
                send_mail(
                    'Verifikasi Akun Anda',
                    f'Kode verifikasi Anda adalah: {verification_code}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                logger.warning(f"Failed to send verification email to {email}: {str(e)}")
                messages.warning(request, 'Akun berhasil dibuat tetapi email verifikasi gagal dikirim. Silakan hubungi admin.')

            request.session['pending_verification_email'] = email
            messages.success(request, "Kode verifikasi telah dikirim ke email Anda. Silakan periksa email Anda untuk menyelesaikan pendaftaran.")
            return redirect('verification_code')

        except Exception as e:
            logger.error(f"Registration failed for {email}: {str(e)}")
            messages.error(request, f'Registrasi gagal')
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
