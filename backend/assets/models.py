import qrcode
from io import BytesIO

from django.conf import settings
from django.core.files import File
from django.db import models

from owners.models import Owner
from owners.validators import validate_text_content
from accounts.models import User


class AssetCategory(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True,
        validators=[validate_text_content],
    )


    def __str__(self):
        return self.name



class Asset(models.Model):

    STATUS_CHOICES = (
        ("AUTHORIZED", "Authorized"),
        ("LOST", "Lost"),
        ("STOLEN", "Stolen"),
        ("MAINTENANCE", "Maintenance"),
        ("DISPOSED", "Disposed"),
    )


    asset_code = models.CharField(
        max_length=50,
        unique=True
    )


    asset_name = models.CharField(
        max_length=100
    )

    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True, validators=[validate_text_content])


    serial_number = models.CharField(
        max_length=100,
        unique=True
    )


    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.CASCADE
    )


    owner = models.ForeignKey(
        Owner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    registered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_assets",
    )


    image = models.ImageField(
        upload_to="assets/",
        blank=True,
        null=True
    )


    qr_code = models.ImageField(
        upload_to="qr_codes/",
        blank=True,
        null=True
    )


    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="AUTHORIZED"
    )


    purchase_date = models.DateField(
        null=True,
        blank=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.asset_name



    def save(self, *args, **kwargs):

        # Check if QR already exists
        create_qr = False

        if not self.qr_code:
            create_qr = True


        # Save asset first
        super().save(*args, **kwargs)


        # Generate QR Code
        if create_qr:

            # URL that opens the React verification page, or the bare
            # asset code when the site address is not configured
            verification_url = (
                f"{settings.FRONTEND_URL}/verification?code={self.asset_code}"
                if settings.FRONTEND_URL
                else self.asset_code
            )


            qr_image = qrcode.make(
                verification_url
            ).convert("RGB")


            buffer = BytesIO()


            qr_image.save(
                buffer,
                format="PNG"
            )


            file_name = f"{self.asset_code}.png"


            self.qr_code.save(
                file_name,
                File(buffer),
                save=False
            )


            # Save QR image path
            super().save(
                update_fields=["qr_code"]
            )
