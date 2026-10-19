import hashlib
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import APIToken, User
from assets.models import Asset, AssetCategory
from owners.models import Department, Owner
from verification.models import VerificationLog


class ProfilePictureUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="officer@example.edu",
            email="officer@example.edu",
            password="test-password",
        )
        self.raw_token = "test-profile-picture-upload-token"
        APIToken.objects.create(
            user=self.user,
            token_hash=hashlib.sha256(self.raw_token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=1),
        )

    @patch("api.views._serialize_user", return_value={"id": "1"})
    @patch("api.views._save_uploaded_file")
    def test_multipart_post_saves_profile_picture(self, save_file, _serialize_user):
        photo = SimpleUploadedFile(
            "profile.png",
            b"\x89PNG\r\n\x1a\nprofile-image",
            content_type="image/png",
        )

        response = self.client.post(
            "/api/profile/",
            {"profile_picture": photo},
            HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": "1"})
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        save_file.assert_called_once()
        self.assertEqual(save_file.call_args.args[0].name, "profile.png")
        self.assertEqual(save_file.call_args.kwargs, {"user_id": self.user.pk, "kind": "profile"})


class AdminUserCreationTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="superadmin@example.edu",
            email="superadmin@example.edu",
            password="test-password",
            role="SUPER_ADMIN",
            is_superuser=True,
        )
        self.raw_token = "test-admin-creation-token"
        APIToken.objects.create(
            user=self.super_admin,
            token_hash=hashlib.sha256(self.raw_token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=1),
        )

    @patch("api.views._saved_file_url", return_value="")
    def test_create_admin_persists_phone_number(self, _saved_file_url):
        response = self.client.post(
            "/api/users/",
            {
                "firstName": "New",
                "lastName": "Administrator",
                "email": "new-admin@example.edu",
                "phone": "+1 555 0100",
                "password": "StrongPass123!",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["phone"], "+1 555 0100")
        created_user = User.objects.get(email="new-admin@example.edu")
        self.assertEqual(created_user.phone, "+1 555 0100")
        self.assertEqual(created_user.department, "")

    def test_create_admin_requires_phone_number(self):
        response = self.client.post(
            "/api/users/",
            {
                "firstName": "New",
                "lastName": "Administrator",
                "email": "new-admin@example.edu",
                "password": "StrongPass123!",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="new-admin@example.edu").exists())

    def test_create_admin_rejects_phone_number_over_database_limit(self):
        response = self.client.post(
            "/api/users/",
            {
                "firstName": "New",
                "lastName": "Administrator",
                "email": "new-admin@example.edu",
                "phone": "1234567890123456",
                "password": "StrongPass123!",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="new-admin@example.edu").exists())


class OwnerIdUniquenessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="owner-admin@example.edu",
            email="owner-admin@example.edu",
            password="StrongPass123!",
            role="ADMIN",
        )
        self.raw_token = "test-owner-id-token"
        APIToken.objects.create(
            user=self.admin,
            token_hash=hashlib.sha256(self.raw_token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.department = Department.objects.create(name="Owner ID Test")

    def _create_owner(self, university_id):
        return self.client.post(
            "/api/owners/",
            {
                "fullName": "Campus Owner",
                "universityId": university_id,
                "department": self.department.name,
                "role": "STUDENT",
            },
            HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
        )

    def test_owner_id_from_registration_request_is_persisted(self):
        response = self._create_owner("STU-2026-1001")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Owner.objects.filter(owner_id="STU-2026-1001").exists())

    def test_owner_id_cannot_be_reused_with_different_letter_case(self):
        Owner.objects.create(
            owner_type="STUDENT",
            owner_id="STU-2026-1001",
            full_name="Existing Owner",
            department=self.department,
        )

        response = self._create_owner("stu-2026-1001")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(Owner.objects.filter(owner_id__iexact="STU-2026-1001").count(), 1)

    def test_database_constraint_blocks_case_insensitive_duplicate_owner_ids(self):
        Owner.objects.create(
            owner_type="STUDENT",
            owner_id="STU-2026-1001",
            full_name="Existing Owner",
            department=self.department,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Owner.objects.create(
                    owner_type="STUDENT",
                    owner_id="stu-2026-1001",
                    full_name="Duplicate Owner",
                    department=self.department,
                )


class TextOnlyFieldValidationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="text-validation-admin@example.edu",
            email="text-validation-admin@example.edu",
            password="StrongPass123!",
            role="ADMIN",
        )
        self.raw_token = "test-text-validation-token"
        APIToken.objects.create(
            user=self.admin,
            token_hash=hashlib.sha256(self.raw_token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.department = Department.objects.create(name="Text Validation Department")
        self.owner = Owner.objects.create(
            owner_type="STAFF",
            owner_id="TEXT-VALIDATION-OWNER",
            full_name="Valid Owner",
            department=self.department,
        )
        self.category = AssetCategory.objects.create(name="Text Validation Asset")

    def _post_owner(self, *, full_name="Valid Owner", department="Text Validation Department"):
        return self.client.post(
            "/api/owners/",
            {
                "fullName": full_name,
                "universityId": "TEXT-VALIDATION-NEW",
                "department": department,
                "role": "STUDENT",
            },
            HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
        )

    def test_owner_creation_rejects_digits_in_name_and_department(self):
        for field_value, field_label in (
            ("Owner 2", "Owner full name"),
            ("Department 2", "Department"),
        ):
            with self.subTest(field=field_label):
                response = self._post_owner(
                    full_name=field_value if field_label == "Owner full name" else "Valid Owner",
                    department=field_value if field_label == "Department" else "Text Validation Department",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field_label, response.json()["message"])
        self.assertFalse(Owner.objects.filter(owner_id="TEXT-VALIDATION-NEW").exists())

    def test_owner_update_rejects_non_text_name_and_department(self):
        for payload, field_label in (
            ({"fullName": "Owner 2"}, "Owner full name"),
            ({"department": "Department 2"}, "Department"),
        ):
            with self.subTest(field=field_label):
                response = self.client.patch(
                    f"/api/owners/{self.owner.pk}/",
                    payload,
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field_label, response.json()["message"])
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.full_name, "Valid Owner")
        self.assertEqual(self.owner.department.name, "Text Validation Department")

    def test_asset_creation_rejects_digits_in_description_and_notes(self):
        for field_name, field_label in (("description", "Description"), ("notes", "Notes")):
            with self.subTest(field=field_label):
                response = self.client.post(
                    "/api/assets/",
                    {
                        "name": "Text Validation Asset",
                        "serial": f"TEXT-VALIDATION-{field_name.upper()}",
                        "category": self.category.name,
                        "ownerId": self.owner.owner_id,
                        field_name: "Contains number 2",
                    },
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field_label, response.json()["error"])
        self.assertFalse(Asset.objects.filter(serial_number__startswith="TEXT-VALIDATION-").exists())


class SystemNotificationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="notification-admin@example.edu",
            email="notification-admin@example.edu",
            password="StrongPass123!",
            role="SUPER_ADMIN",
            is_superuser=True,
        )
        self.other_user = User.objects.create_user(
            username="notification-officer@example.edu",
            email="notification-officer@example.edu",
            password="StrongPass123!",
            role="SECURITY",
        )
        self.inactive_user = User.objects.create_user(
            username="notification-inactive@example.edu",
            email="notification-inactive@example.edu",
            password="StrongPass123!",
            role="ADMIN",
            is_active=False,
        )
        self.raw_token = "test-system-notification-token"
        APIToken.objects.create(
            user=self.admin,
            token_hash=hashlib.sha256(self.raw_token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=1),
        )

    def test_broadcast_targets_every_active_user_only(self):
        session = MagicMock()
        session_factory = MagicMock()
        session_factory.return_value.__enter__.return_value = session

        with patch("api.views._sql_store", return_value=session_factory):
            from api.views import _broadcast_notification

            _broadcast_notification(
                title="New asset registered",
                message="Laptop was registered.",
                notification_type="info",
                link="/assets/AST-001",
            )

        rows = session.add_all.call_args.args[0]
        self.assertEqual(
            {row.user_id for row in rows},
            {self.admin.pk, self.other_user.pk},
        )
        self.assertTrue(all(row.title == "New asset registered" for row in rows))
        self.assertTrue(all(row.read is False for row in rows))
        self.assertTrue(all(row.link == "/assets/AST-001" for row in rows))
        session.commit.assert_called_once()

    def test_new_admin_creation_triggers_system_notification(self):
        with patch("api.views._broadcast_notification") as broadcast, patch(
            "api.views._serialize_user", return_value={"id": "admin"}
        ):
            response = self.client.post(
                "/api/users/",
                {
                    "firstName": "New",
                    "lastName": "Administrator",
                    "email": "new-notification-admin@example.edu",
                    "phone": "+1 555 0102",
                    "password": "StrongPass123!",
                },
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(broadcast.call_args.kwargs["title"], "Administrator created")
        self.assertIn("new-notification-admin@example.edu", broadcast.call_args.kwargs["message"])

    @patch("api.views._saved_file_url", return_value="")
    def test_new_asset_creation_triggers_system_notification(self, _saved_file_url):
        department = Department.objects.create(name="Notification Test")
        owner = Owner.objects.create(
            owner_type="STUDENT",
            owner_id="STU-NOTIFY-01",
            full_name="Notification Owner",
            department=department,
        )
        AssetCategory.objects.create(name="Notification Laptop")

        with patch("api.views._broadcast_notification") as broadcast:
            response = self.client.post(
                "/api/assets/",
                {
                    "name": "Notification Laptop One",
                    "brand": "Example",
                    "model": "Model 1",
                    "serial": "NOTIFY-SERIAL-001",
                    "category": "Notification Laptop",
                    "ownerId": owner.owner_id,
                },
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(broadcast.call_args.kwargs["title"], "New asset registered")
        self.assertIn(response.json()["id"], broadcast.call_args.kwargs["message"])


class ReportExportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="report-admin@example.edu",
            email="report-admin@example.edu",
            password="StrongPass123!",
            role="ADMIN",
        )
        self.raw_token = "test-report-export-token"
        APIToken.objects.create(
            user=self.admin,
            token_hash=hashlib.sha256(self.raw_token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=1),
        )
        department = Department.objects.create(name="Engineering")
        owner = Owner.objects.create(
            owner_type="STAFF",
            owner_id="EMP-REPORT-01",
            full_name="Report Owner",
            phone="+1 555 0101",
            department=department,
        )
        category = AssetCategory.objects.create(name="Laptop")
        self.asset = Asset.objects.create(
            asset_code="AST-REPORT-001",
            asset_name="Report laptop",
            brand="Example",
            model="Model X",
            serial_number="SERIAL-REPORT-001",
            category=category,
            owner=owner,
            status="AUTHORIZED",
            notes="Report test notes",
        )
        VerificationLog.objects.create(
            asset=self.asset,
            officer=self.admin,
            verification_method="QR_CODE",
            result="AUTHORIZED",
            remarks="Report test verification",
        )
        VerificationLog.objects.create(
            asset=self.asset,
            officer=self.admin,
            verification_method="ASSET_CODE",
            result="LOST",
            remarks="Report test interception",
        )
        User.objects.create_user(
            username="report-security@example.edu",
            email="report-security@example.edu",
            password="StrongPass123!",
            role="SECURITY",
        )
        User.objects.create_user(
            username="inactive-security@example.edu",
            email="inactive-security@example.edu",
            password="StrongPass123!",
            role="SECURITY",
            is_active=False,
        )

    def _authorized_get(self, path):
        return self.client.get(path, HTTP_AUTHORIZATION=f"Bearer {self.raw_token}")

    def test_overview_includes_complete_asset_details(self):
        response = self._authorized_get("/api/reports/overview/")

        self.assertEqual(response.status_code, 200)
        overview = response.json()
        report_asset = overview["assets"][0]
        self.assertEqual(overview["todayVerifications"], 2)
        self.assertEqual(overview["successfulVerificationsToday"], 1)
        self.assertEqual(overview["activeSecurityAccounts"], 1)
        self.assertEqual(overview["interceptions"], 1)
        self.assertEqual(overview["authorizedCount"], 1)
        self.assertEqual(report_asset["id"], self.asset.asset_code)
        self.assertEqual(report_asset["ownerId"], "EMP-REPORT-01")
        self.assertEqual(report_asset["ownerPhone"], "+1 555 0101")
        self.assertEqual(report_asset["notes"], "Report test notes")

    def test_csv_export_contains_inventory_and_verification_history(self):
        response = self._authorized_get("/api/reports/export/csv/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertIn("AST-REPORT-001", response.content.decode("utf-8"))
        self.assertIn("Report test verification", response.content.decode("utf-8"))

    def test_pdf_export_returns_a_pdf_attachment(self):
        response = self._authorized_get("/api/reports/export/pdf/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_export_rejects_unsupported_format(self):
        response = self._authorized_get("/api/reports/export/xlsx/")

        self.assertEqual(response.status_code, 400)


DATABASE_MEDIA_STORAGES = {
    "default": {"BACKEND": "config.storage.DatabaseStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class DatabaseMediaStorageTests(TestCase):
    """Uploads must work on hosts with a read-only disk (Vercel)."""

    def setUp(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from api import sql_store

        # Keep SQLAlchemy writes out of the developer's real database.
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        for name, value in (("engine", engine), ("SessionLocal", session_factory)):
            patcher = patch.object(sql_store, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_storage_round_trip(self):
        from django.core.files.base import ContentFile

        from config.storage import DatabaseStorage

        storage = DatabaseStorage()
        name = storage.save("assets/photo.png", ContentFile(b"png-bytes"))

        self.assertTrue(storage.exists(name))
        self.assertEqual(storage.size(name), len(b"png-bytes"))
        self.assertEqual(storage.open(name).read(), b"png-bytes")
        self.assertEqual(storage.url(name), "/media/assets/photo.png")

        storage.delete(name)
        self.assertFalse(storage.exists(name))

    def test_media_route_serves_stored_file(self):
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from django.test import override_settings

        with override_settings(STORAGES=DATABASE_MEDIA_STORAGES):
            name = default_storage.save("owner_documents/id.pdf", ContentFile(b"%PDF-1.4 test"))
            response = self.client.get(f"/media/{name}")
            missing = self.client.get("/media/owner_documents/missing.pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 test")
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(missing.status_code, 404)

    def test_asset_qr_code_links_to_frontend_verification_page(self):
        from io import BytesIO

        import qrcode
        from django.test import override_settings
        from PIL import Image

        department = Department.objects.create(name="Physics")
        owner = Owner.objects.create(
            owner_type="STAFF",
            owner_id="EMP-QR-01",
            full_name="Qr Owner",
            phone="+1 555 0102",
            department=department,
        )
        category = AssetCategory.objects.create(name="Tablet")

        with override_settings(STORAGES=DATABASE_MEDIA_STORAGES, FRONTEND_URL="https://campus.example.app"), \
                patch("assets.models.qrcode.make", wraps=qrcode.make) as make_qr:
            asset = Asset.objects.create(
                asset_code="AST-QR-001",
                asset_name="Qr tablet",
                brand="Example",
                model="Model Q",
                serial_number="SERIAL-QR-001",
                category=category,
                owner=owner,
                status="AUTHORIZED",
            )
            stored = asset.qr_code.open().read()

        make_qr.assert_called_once_with("https://campus.example.app/verification?code=AST-QR-001")
        self.assertEqual(Image.open(BytesIO(stored)).format, "PNG")
