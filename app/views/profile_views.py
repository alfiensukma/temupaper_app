from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import User, Institution

def profile_view(request):

    if not request.session.get('is_authenticated', False):
        messages.error(request, 'Anda harus login terlebih dahulu.')
        return redirect('login_view')
    
    user_id = request.session.get('user_id')
    user_data = {
        'name': request.session.get('user_name', ''),
        'email': request.session.get('user_email', ''),
        'institution': 'Tidak ada institusi',
        'institution_id': None
    }
    
    institutions = []
    
    try:
        institutions = list(Institution.nodes.all())

        user = User.nodes.get(userId=user_id)
        
        print(f"User found: {user.name} (ID: {user.userId})")
        
        affiliated_institutions = list(user.affiliated_with)
        print(f"Found {len(affiliated_institutions)} affiliated institutions")
        
        for rel in affiliated_institutions:
            user_data['institution'] = rel.name
            user_data['institution_id'] = rel.institutionId
            print(f"Setting institution to: {rel.name} (ID: {rel.institutionId})")
            break
            
    except User.DoesNotExist:
        print(f"User with ID {user_id} not found")
        messages.error(request, 'User tidak ditemukan.')
    except Exception as e:
        print(f"Error in profile_view: {str(e)}")
        messages.error(request, f'Terjadi kesalahan: {str(e)}')
    
    print(f"Final user_data being sent to template: {user_data}")
    print(f"Number of institutions for dropdown: {len(institutions)}")
    
    return render(request, "base.html", {
        "content_template": "auth/profile.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False,
        "user_data": user_data,
        "institutions": institutions
    })

def edit_profile(request):
    if not request.session.get('is_authenticated', False):
        messages.error(request, 'Anda harus login terlebih dahulu.')
        return redirect('login_view')
    
    user_id = request.session.get('user_id')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        institution_id = request.POST.get('institution')
        
        try:
            user = User.nodes.get(userId=user_id)

            if name:
                user.name = name
                request.session['user_name'] = name

            if institution_id:

                current_institution = None
                for rel in user.affiliated_with:
                    current_institution = rel
                    break
                
                if not current_institution or current_institution.institutionId != institution_id:

                    if current_institution:
                        user.affiliated_with.disconnect(current_institution)

                    new_institution = Institution.nodes.get(institutionId=institution_id)
                    user.affiliated_with.connect(new_institution)
            
            user.save()
            messages.success(request, 'Profil berhasil diperbarui.')
            
        except User.DoesNotExist:
            messages.error(request, 'User tidak ditemukan.')
        except Institution.DoesNotExist:
            messages.error(request, 'Institusi tidak ditemukan.')
        except Exception as e:
            messages.error(request, f'Gagal memperbarui profil: {str(e)}')
        
        return redirect('profile_view')
    
    return redirect('profile_view')

def reset_password(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirmation = request.POST.get('password_confirmation')
        
        if not password or not password_confirmation:
            messages.error(request, 'Kedua field password harus diisi.')
            return render(request, "base.html", {
                "content_template": "auth/reset-password.html",
                "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
                "show_search_form": False
            })
        
        if password != password_confirmation:
            messages.error(request, 'Password tidak cocok.')
            return render(request, "base.html", {
                "content_template": "auth/reset-password.html",
                "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
                "show_search_form": False
            })
        
        email = request.session.get('verification_email')
        
        try:
            user = User.nodes.get(email=email)

            user.set_password(password)
            user.save()
            
            messages.success(request, 'Password berhasil diubah.')

            if 'verification_email' in request.session:
                del request.session['verification_email']
            

            if request.session.get('is_authenticated', False):
                return redirect('profile_view')
            else:
                return redirect('login_view')
                
        except User.DoesNotExist:
            messages.error(request, 'Terjadi kesalahan. Pengguna tidak ditemukan.')
            return redirect('login_view')

    return render(request, "base.html", {
        "content_template": "auth/reset-password.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False
    })