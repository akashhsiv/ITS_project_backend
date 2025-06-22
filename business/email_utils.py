from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.html import strip_tags

import random
import string

def generate_key(prefix, length=8):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def send_activation_email(business, request):
    # Generate activation token and set expiry
    activation_token = business.generate_activation_token()
    
    # Build activation path
    activation_path = reverse('business-activate', kwargs={'token': str(activation_token)})
    
    # For local development, use the full URL with http
    if settings.DEBUG:
        protocol = 'http'
        domain = 'localhost:8000'  # Default Django development server
        # Ensure the URL includes the /api/ prefix
        if not activation_path.startswith('/api/'):
            activation_path = f'/api{activation_path}'
        activation_url = f"{protocol}://{domain}{activation_path}"
    else:
        # In production, use the full URL with HTTPS
        current_site = get_current_site(request)
        domain = request.get_host() or current_site.domain
        protocol = 'https'
        # Ensure the URL includes the /api/ prefix
        if not activation_path.startswith('/api/'):
            activation_path = f'/api{activation_path}'
        activation_url = f"{protocol}://{domain}{activation_path}"
    
    # Prepare email content
    subject = "Activate Your ITS Business Account"
    context = {
        'business_name': business.business_name,
        'activation_url': activation_url,
        'expiry_hours': 24,
    }
    
    # Render HTML email
    html_message = render_to_string('emails/activation_email.html', context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[business.email],
        html_message=html_message,
        fail_silently=False,
    )





def send_welcome_email(business, request):
    # Prepare email content with credentials
    subject = "Your ITS Business Account is Now Active!"
    
    context = {
        'business': business,
    }
    
    # Render plain text email
    plain_message = render_to_string('emails/welcome_email.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[business.email],
        fail_silently=False,
    )
