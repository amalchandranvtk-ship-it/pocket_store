from customer.accounts.models import User

def admin_profile(request):

    if request.user.is_authenticated:
        return {"admin_user": request.user}

    return {"admin_user": None}