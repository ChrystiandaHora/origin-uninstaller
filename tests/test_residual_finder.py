import os
import unittest

from src.cleaner.residual_finder import ResidualFinder
from src.models import AppType, InstalledApp


class TestResidualFinder(unittest.TestCase):
    def setUp(self):
        self.finder = ResidualFinder()

    def test_slug_generation(self):
        app = InstalledApp(
            id="google-chrome-stable",
            name="Google Chrome",
            app_type=AppType.APT,
            package_name="google-chrome-stable",
        )
        slugs = self.finder._generate_slugs(app)
        self.assertIn("google-chrome-stable", slugs)
        self.assertIn("google-chrome", slugs)
        self.assertIn("chrome", slugs)

    def test_find_residuals_for_known_app(self):
        # Cria um diretório temporário simulado na home
        test_dir = os.path.expanduser("~/.config/origin-test-fakeapp")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "test.conf"), "w") as f:
            f.write("sample config")

        try:
            fake_app = InstalledApp(
                id="origin-test-fakeapp",
                name="Origin Test FakeApp",
                app_type=AppType.APT,
                package_name="origin-test-fakeapp",
            )
            residuals = self.finder.find_residuals(fake_app)
            paths = [r.path for r in residuals]
            self.assertIn(test_dir, paths)
        finally:
            import shutil

            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)


if __name__ == "__main__":
    unittest.main()
