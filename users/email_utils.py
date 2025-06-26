from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse


def send_request_registration_key_email(user):
    # Updated subject for clarity
    subject = "Your New Device Registration Key - ITS"

    context = {
        'user': user,
    }

    # Use a specific email template for reset key emails
    plain_message = render_to_string('emails/reset_device_email.txt', context)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.contact.email],
        fail_silently=False,
    )



def send_activation_email(user, request):
    """
    Send activation email to the user with activation link
    """
    # Generate activation token
    token = user.generate_activation_token()

    # Build activation URL
    activation_path = reverse('user-activate', kwargs={'token': str(token)})

    # For local development, use the full URL with http
    if settings.DEBUG:
        protocol = 'http'
        domain = 'localhost:8000'  # Default Django development server
        if not activation_path.startswith('/api/'):
            activation_path = f'/api{activation_path}'
    else:
        protocol = 'https'
        domain = request.get_host()

    activation_url = f"{protocol}://{domain}{activation_path}"

    # Prepare email content
    subject = "Activate Your Account"
    context = {
        'user': user,
        'activation_url': activation_url,
        'expiry_hours': 24,
    }

    # Render HTML email
    html_message = render_to_string('emails/activation_email.html', context)
    plain_message = strip_tags(html_message)

    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.contact.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_welcome_email(user, raw_pin):
    """
    Send welcome email with credentials after successful activation
    """
    subject = f"Welcome to {user.business.business_name if user.business else 'Our Service'}"

    context = {
        'user': user,
        'pin': raw_pin,
    }

    # Render HTML email
    html_message = render_to_string('emails/welcome_email.html', context)
    plain_message = strip_tags(html_message)

    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.contact.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_new_pin_email(user, new_pin):
    subject = "Your New PIN - ITS"

    context = {
        'user': user,
        'new_pin': new_pin
    }

    plain_message = render_to_string('emails/new_pin_email.txt', context)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.contact.email],
        fail_silently=False,
    )

def send_forgot_pin_email(user, reset_url):
    subject = "Reset Your PIN - ITS"

    context = {
        'user': user,
        'reset_url': reset_url
    }

    html_message = render_to_string('emails/forgot_pin_email.html', context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.contact.email],
        html_message=html_message,
        fail_silently=False,
    )


