import ast
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Part5StaticIntegrationTests(unittest.TestCase):
    def test_part5_migration_is_single_head(self):
        versions = ROOT / "backend" / "migrations" / "versions"
        nodes = {}
        for path in versions.glob("*.py"):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            rev = re.search(r"^revision\s*=\s*(.+)$", text, re.M)
            down = re.search(r"^down_revision\s*=\s*(.+)$", text, re.M)
            if not rev:
                continue
            nodes[ast.literal_eval(rev.group(1).strip())] = (
                ast.literal_eval(down.group(1).strip()) if down else None
            )

        children = {}
        for revision, down in nodes.items():
            parents = (
                down if isinstance(down, tuple) else (() if down is None else (down,))
            )
            for parent in parents:
                children.setdefault(parent, []).append(revision)

        heads = [revision for revision in nodes if revision not in children]
        self.assertEqual(heads, ["a5b6c7d8e9f0"])
        self.assertEqual(nodes["a5b6c7d8e9f0"], "9d4c6a3e2f11")

    def test_no_typescript_source(self):
        for app in (
            "frontend",
            "supplier-frontend",
            "logistics-frontend",
            "admin-frontend",
        ):
            src = ROOT / app / "src"
            self.assertFalse(list(src.rglob("*.ts")))
            self.assertFalse(list(src.rglob("*.tsx")))

    def test_private_admin_routes_do_not_expose_order_history(self):
        admin_routes = (
            ROOT / "backend" / "app" / "modules" / "admin" / "routes.py"
        ).read_text(encoding="utf-8-sig", errors="replace")
        self.assertNotIn("/orders", admin_routes)
        self.assertNotIn("OrderService.get_order", admin_routes)

    def test_admin_frontend_has_no_order_pages_or_service(self):
        for relative in (
            "admin-frontend/src/pages/Orders.jsx",
            "admin-frontend/src/pages/OrderDetails.jsx",
            "admin-frontend/src/services/orderService.js",
        ):
            self.assertFalse((ROOT / relative).exists())

    def test_all_frontends_have_spa_rewrite(self):
        for app in (
            "frontend",
            "supplier-frontend",
            "logistics-frontend",
            "admin-frontend",
        ):
            config = json.loads((ROOT / app / "vercel.json").read_text())
            rewrites = config.get("rewrites", [])
            self.assertTrue(
                any(
                    item.get("source") == "/(.*)"
                    and item.get("destination") == "/index.html"
                    for item in rewrites
                )
            )

    def test_no_release_env_files_or_hardcoded_provider_credentials(self):
        self.assertEqual(list(ROOT.rglob(".env")), [])
        pattern = re.compile(
            r"(razorpay|cloudinary|resend).*(secret|api[_-]?key)\s*[:=]\s*['\"][^'\"]{12,}['\"]",
            re.I,
        )
        hits = []
        for base in (
            "backend/app",
            "backend/create_admin.py",
            "frontend/src",
            "supplier-frontend/src",
            "logistics-frontend/src",
            "admin-frontend/src",
        ):
            path = ROOT / base
            paths = [path] if path.is_file() else path.rglob("*")
            for file in paths:
                if file.is_file() and file.suffix in {".py", ".js", ".jsx"}:
                    for line_no, line in enumerate(
                        file.read_text(
                            encoding="utf-8-sig", errors="replace"
                        ).splitlines(),
                        1,
                    ):
                        if pattern.search(line):
                            hits.append((str(file), line_no))
        self.assertEqual(hits, [])

    def test_admin_frontend_local_imports_resolve(self):
        admin_src = ROOT / "admin-frontend" / "src"
        import_pattern = re.compile(r"""(?:from|import)\s+["'](\.[^"']+)["']""")
        missing = []
        for path in admin_src.rglob("*"):
            if not path.is_file() or path.suffix not in {".js", ".jsx"}:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            for spec in import_pattern.findall(text):
                base = path.parent / spec
                candidates = [
                    base,
                    Path(str(base) + ".js"),
                    Path(str(base) + ".jsx"),
                    base / "index.js",
                    base / "index.jsx",
                ]
                if not any(candidate.exists() for candidate in candidates):
                    missing.append((str(path), spec))
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
