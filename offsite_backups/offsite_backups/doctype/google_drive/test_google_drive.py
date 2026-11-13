# Copyright (c) 2019, Frappe Technologies and Contributors
# License: MIT. See LICENSE
from unittest import TestCase
from unittest.mock import Mock, patch

from frappe.tests import IntegrationTestCase
from googleapiclient.errors import HttpError

from offsite_backups.offsite_backups.doctype.google_drive import google_drive

MODULE = "offsite_backups.offsite_backups.doctype.google_drive.google_drive"
BACKUP_FILES = ("20260101_000000-site-database.sql.gz", "20260101_000000-site-site_config_backup.json")


class UnitTestGoogleDrive(TestCase):
	"""Upload results of the Google Drive backup, with the Drive client mocked."""

	def run_backup(self, drive):
		account = Mock(file_backup=0, backup_folder_id="folder-id")
		with (
			patch(f"{MODULE}.get_google_drive_object", return_value=(drive, account)),
			patch(f"{MODULE}.check_for_folder_in_google_drive"),
			patch(f"{MODULE}.get_or_create_backup", return_value=BACKUP_FILES),
			patch(f"{MODULE}.MediaFileUpload"),
			patch(f"{MODULE}.get_absolute_path", side_effect=lambda filename: filename),
			patch(f"{MODULE}.set_progress"),
			patch(f"{MODULE}.send_email") as send_email,
			patch("frappe.db", new=Mock()) as db,
			patch("frappe.utils.now_datetime", return_value="2026-01-01 00:00:00"),
		):
			try:
				result = google_drive.upload_system_backup_to_google_drive()
			except HttpError as error:
				result = error
		return result, send_email, db

	def test_rejected_upload_is_not_recorded_as_successful(self):
		drive = Mock()
		rejected = HttpError(Mock(status=403, reason="Forbidden"), b"storage quota exceeded")
		drive.files.return_value.create.return_value.execute.side_effect = rejected

		result, send_email, db = self.run_backup(drive)

		self.assertIs(result, rejected)
		send_email.assert_called_once_with(
			False, "Google Drive", "Google Drive", "email", error_status=rejected
		)
		db.set_single_value.assert_not_called()
		# The run stops at the first rejected file.
		self.assertEqual(drive.files.return_value.create.call_count, 1)

	def test_accepted_uploads_record_the_backup(self):
		drive = Mock()

		result, send_email, db = self.run_backup(drive)

		self.assertNotIsInstance(result, HttpError)
		self.assertEqual(drive.files.return_value.create.call_count, len(BACKUP_FILES))
		send_email.assert_called_once_with(True, "Google Drive", "Google Drive", "email")
		self.assertEqual(db.set_single_value.call_args.args[:2], ("Google Drive", "last_backup_on"))


class TestGoogleDrive(IntegrationTestCase):
	pass
