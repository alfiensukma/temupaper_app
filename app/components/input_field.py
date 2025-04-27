from django_unicorn.components import UnicornView

class InputFieldView(UnicornView):
    name = ""
    type = "text"
    placeholder = ""
    value = ""
    label = ""
    
    def mount(self):
        if not self.value:
            self.value = ""
