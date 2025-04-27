from django_unicorn.components import UnicornView

class EditProfileModalView(UnicornView):
    show_modal = False
    username = "geewonii"
    email = "geewonii@email.com"
    password = ""
    institution = "Dongguk University"
    major = "Sastra Mesin"
    
    def toggle_modal(self):
        print(f"Toggle modal: {self.show_modal} -> {not self.show_modal}")
        self.show_modal = not self.show_modal