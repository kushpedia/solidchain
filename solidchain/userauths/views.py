# userauths/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from .forms import SignUpForm
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@csrf_exempt
def signup(request):
    """
    Handle user registration
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Save user and create member profile
            user = form.save()
            
            # Auto-login the user
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, 'Account created successfully! Welcome to SolidChain.')
                return redirect('core:dashboard')
        else:
            # Form has errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SignUpForm()
    
    return render(request, 'userauths/signup.html', {'form': form})


@method_decorator(csrf_exempt, name='dispatch')
class CustomLoginView(LoginView):
    """
    Custom login view with messages
    """
    template_name = 'userauths/login.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Logged in successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password. Please try again.')
        return super().form_invalid(form)