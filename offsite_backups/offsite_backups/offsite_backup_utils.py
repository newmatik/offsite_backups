# Copyright (c) 2019, Frappe Technologies and contributors
# License: MIT. See LICENSE

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path

import frappe
from frappe.utils import cint, get_site_path, split_emails

RECENT_BACKUP_HOURS = 26
BACKUP_LOCK_FILENAME = ".offsite-backup.lock"


def send_email(success, service_name, doctype, email_field, error_status=None):
	recipients = get_recipients(doctype, email_field)
	if not recipients:
		frappe.log_error(
			f"No Email Recipient found for {service_name}",
			f"{service_name}: Failed to send backup status email",
		)
		return

	if success:
		if not frappe.db.get_single_value(doctype, "send_email_for_successful_backup"):
			return

		subject = "Backup Upload Successful"
		message = """
<h3>Backup Uploaded Successfully!</h3>
<p>Hi there, this is just to inform you that your backup was successfully uploaded to your {} bucket. So relax!</p>""".format(
			service_name
		)
	else:
		subject = "[Warning] Backup Upload Failed"
		message = f"""
<h3>Backup Upload Failed!</h3>
<p>Oops, your automated backup to {service_name} failed.</p>
<p>Error message: {error_status}</p>
<p>Please contact your system manager for more information.</p>"""

	frappe.sendmail(recipients=recipients, subject=subject, message=message)


def get_recipients(doctype, email_field):
	return split_emails(frappe.db.get_value(doctype, None, email_field))


def get_latest_backup_file(with_files=False, max_age_hours=RECENT_BACKUP_HOURS):
	"""Return one recent, complete backup snapshot if available."""
	from frappe.utils.backups import BackupGenerator

	odb = BackupGenerator(
		frappe.conf.db_name,
		frappe.conf.db_user,
		frappe.conf.db_password,
		db_socket=frappe.conf.db_socket,
		db_host=frappe.conf.db_host,
		db_port=frappe.conf.db_port,
		db_type=frappe.conf.db_type,
	)
	database, public, private, config = odb.get_recent_backup(older_than=max_age_hours)
	backup_files = (database, config, public, private) if with_files else (database, config)

	if not _is_complete_snapshot(backup_files):
		return (None, None, None, None) if with_files else (None, None)

	if with_files:
		return database, config, public, private

	return database, config


def get_or_create_backup(with_files=False):
	"""Reuse a recent snapshot or create exactly one backup across providers."""
	from frappe.utils.backups import new_backup

	with _backup_creation_lock():
		backup_files = get_latest_backup_file(with_files=with_files)
		if all(backup_files):
			return backup_files

		# Always include file archives so a later file-required caller can reuse
		# this dump instead of creating a second backup.
		backup = new_backup(ignore_files=False, force=True)
		full_files = (
			backup.backup_path_db,
			backup.backup_path_conf,
			backup.backup_path_files,
			backup.backup_path_private_files,
		)
		if not _is_complete_snapshot(full_files):
			raise FileNotFoundError("The generated backup snapshot is incomplete")

		return full_files if with_files else full_files[:2]


def _is_complete_snapshot(backup_files):
	"""Return whether all files exist, are non-empty, and belong to the same snapshot."""
	if not backup_files or not all(
		path and os.path.isfile(path) and os.path.getsize(path) > 0 for path in backup_files
	):
		return False

	timestamps = {Path(path).name.split("-", 1)[0] for path in backup_files}
	return len(timestamps) == 1


@contextmanager
def _backup_creation_lock():
	"""Serialize backup selection and creation across off-site providers."""
	lock_path = Path(get_site_path("locks", BACKUP_LOCK_FILENAME))
	lock_path.parent.mkdir(parents=True, exist_ok=True)
	with lock_path.open("a+", encoding="utf-8") as lock_file:
		os.chmod(lock_path, 0o600)
		fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
		try:
			yield
		finally:
			fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def get_chunk_site(file_size):
	"""this function will return chunk size in megabytes based on file size"""

	file_size_in_gb = cint(file_size / 1024 / 1024)

	MB = 1024 * 1024
	if file_size_in_gb > 5000:
		return 200 * MB
	elif file_size_in_gb >= 3000:
		return 150 * MB
	elif file_size_in_gb >= 1000:
		return 100 * MB
	elif file_size_in_gb >= 500:
		return 50 * MB
	else:
		return 15 * MB
