"""Test coordinated off-site backup selection and creation."""

import tempfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from offsite_backups.offsite_backups.offsite_backup_utils import (
	_is_complete_snapshot,
	get_or_create_backup,
)

MODULE = "offsite_backups.offsite_backups.offsite_backup_utils"


class UnitTestOffsiteBackupUtils(TestCase):
	"""Pin reuse and single-creation backup behavior."""

	def test_reuses_one_complete_recent_snapshot(self):
		"""Reuse a complete snapshot without invoking the backup generator."""
		with tempfile.TemporaryDirectory() as directory:
			backup_files = self._make_snapshot(directory)
			with (
				patch(f"{MODULE}._backup_creation_lock", return_value=nullcontext()),
				patch(f"{MODULE}.get_latest_backup_file", return_value=backup_files),
				patch("frappe.utils.backups.new_backup") as new_backup,
			):
				self.assertEqual(get_or_create_backup(), backup_files)

		new_backup.assert_not_called()

	def test_creates_one_database_snapshot_when_recent_backup_is_incomplete(self):
		"""Create a full snapshot even when the caller only needs database files."""
		with tempfile.TemporaryDirectory() as directory:
			full_files = self._make_snapshot(directory, with_files=True)
			backup = self._backup_from_paths(full_files)
			with (
				patch(f"{MODULE}._backup_creation_lock", return_value=nullcontext()),
				patch(f"{MODULE}.get_latest_backup_file", return_value=(None, None)),
				patch("frappe.utils.backups.new_backup", return_value=backup) as new_backup,
			):
				self.assertEqual(get_or_create_backup(), full_files[:2])

		new_backup.assert_called_once_with(ignore_files=False, force=True)

	def test_creates_one_full_snapshot_when_file_archives_are_required(self):
		"""Create matching public and private archives for file-enabled providers."""
		with tempfile.TemporaryDirectory() as directory:
			backup_files = self._make_snapshot(directory, with_files=True)
			backup = self._backup_from_paths(backup_files)
			with (
				patch(f"{MODULE}._backup_creation_lock", return_value=nullcontext()),
				patch(f"{MODULE}.get_latest_backup_file", return_value=(None, None, None, None)),
				patch("frappe.utils.backups.new_backup", return_value=backup) as new_backup,
			):
				self.assertEqual(get_or_create_backup(with_files=True), backup_files)

		new_backup.assert_called_once_with(ignore_files=False, force=True)

	def test_rejects_files_from_different_snapshot_timestamps(self):
		"""Reject a database and config file that cannot form one restore point."""
		with tempfile.TemporaryDirectory() as directory:
			backup_files = list(self._make_snapshot(directory))
			replacement = Path(directory) / "20260804_050000-erp_newmatik_com-site_config_backup.json"
			replacement.write_bytes(b"backup\n")
			backup_files[1] = str(replacement)

			self.assertFalse(_is_complete_snapshot(tuple(backup_files)))

	def test_file_required_caller_reuses_snapshot_from_database_only_request(self):
		"""A later file-required caller must not dump a second backup."""
		with tempfile.TemporaryDirectory() as directory:
			full_files = self._make_snapshot(directory, with_files=True)
			backup = self._backup_from_paths(full_files)
			created = {"done": False}

			def latest_backup_file(with_files=False, max_age_hours=None):
				if not created["done"]:
					return (None, None, None, None) if with_files else (None, None)
				return full_files if with_files else full_files[:2]

			def create_backup(**_kwargs):
				created["done"] = True
				return backup

			with (
				patch(f"{MODULE}._backup_creation_lock", return_value=nullcontext()),
				patch(f"{MODULE}.get_latest_backup_file", side_effect=latest_backup_file),
				patch("frappe.utils.backups.new_backup", side_effect=create_backup) as new_backup,
			):
				self.assertEqual(get_or_create_backup(), full_files[:2])
				self.assertEqual(get_or_create_backup(with_files=True), full_files)

		new_backup.assert_called_once_with(ignore_files=False, force=True)

	def test_rejects_incomplete_generated_snapshot(self):
		"""Raise when the backup generator does not produce every requested file."""
		backup = SimpleNamespace(
			backup_path_db="/missing/database.sql.gz",
			backup_path_conf="/missing/site_config.json",
			backup_path_files="/missing/files.tar",
			backup_path_private_files="/missing/private-files.tar",
		)
		with (
			patch(f"{MODULE}._backup_creation_lock", return_value=nullcontext()),
			patch(f"{MODULE}.get_latest_backup_file", return_value=(None, None)),
			patch("frappe.utils.backups.new_backup", return_value=backup),
			self.assertRaisesRegex(FileNotFoundError, "snapshot is incomplete"),
		):
			get_or_create_backup()

	def test_rejects_empty_snapshot_files(self):
		"""Reject a snapshot whose files exist but have no content yet."""
		with tempfile.TemporaryDirectory() as directory:
			backup_files = self._make_snapshot(directory)
			Path(backup_files[0]).write_bytes(b"")

			self.assertFalse(_is_complete_snapshot(backup_files))

	@staticmethod
	def _backup_from_paths(paths):
		"""Build the backup-generator return object from snapshot paths."""
		backup = SimpleNamespace(backup_path_db=paths[0], backup_path_conf=paths[1])
		if len(paths) > 2:
			backup.backup_path_files = paths[2]
			backup.backup_path_private_files = paths[3]
		return backup

	@staticmethod
	def _make_snapshot(directory, with_files=False):
		"""Create one synthetic backup snapshot and return provider-order paths."""
		prefix = "20260804_040000-erp_newmatik_com"
		filenames = [f"{prefix}-database.sql.gz", f"{prefix}-site_config_backup.json"]
		if with_files:
			filenames.extend([f"{prefix}-files.tar", f"{prefix}-private-files.tar"])
		paths = tuple(str(Path(directory) / filename) for filename in filenames)
		for path in paths:
			Path(path).write_bytes(b"backup\n")
		return paths
