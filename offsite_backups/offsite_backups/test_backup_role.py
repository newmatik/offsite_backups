"""Whitelist methods that store a token or start a backup require the write role."""

import ast
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
ROLE = "System Manager"
GUARDED = {
	"doctype/google_drive/google_drive.py": ("authorize_access", "take_backup"),
	"doctype/dropbox_settings/dropbox_settings.py": ("take_backup", "dropbox_auth_finish"),
	"doctype/s3_backup_settings/s3_backup_settings.py": ("take_backup", "take_backups_s3"),
}


def _functions(path):
	tree = ast.parse((PACKAGE / path).read_text())
	return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def _is_whitelist(node):
	for decorator in node.decorator_list:
		call = decorator.func if isinstance(decorator, ast.Call) else decorator
		if (
			isinstance(call, ast.Attribute)
			and call.attr == "whitelist"
			and isinstance(call.value, ast.Name)
			and call.value.id == "frappe"
		):
			return True
	return False


def _role_check_is_first(node):
	body = node.body
	index = 0
	if (
		body
		and isinstance(body[0], ast.Expr)
		and isinstance(body[0].value, ast.Constant)
		and isinstance(body[0].value.value, str)
	):
		index = 1
	if index >= len(body) or not isinstance(body[index], ast.Expr):
		return False
	call = body[index].value
	if not isinstance(call, ast.Call) or call.keywords or len(call.args) != 1:
		return False
	func = call.func
	arg = call.args[0]
	return (
		isinstance(func, ast.Attribute)
		and func.attr == "only_for"
		and isinstance(func.value, ast.Name)
		and func.value.id == "frappe"
		and isinstance(arg, ast.Constant)
		and arg.value == ROLE
	)


class UnitTestBackupRole(unittest.TestCase):
	def test_token_and_backup_methods_require_system_manager(self):
		for path, names in GUARDED.items():
			functions = _functions(path)
			for name in names:
				with self.subTest(path=path, method=name):
					node = functions[name]
					self.assertTrue(_is_whitelist(node))
					self.assertTrue(_role_check_is_first(node))
