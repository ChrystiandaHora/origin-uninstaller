import unittest

from src.models import AppType, InstalledApp, ResidualItem, format_size


class TestModels(unittest.TestCase):
    def test_format_size(self):
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(500), "500 B")
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.0 GB")
        self.assertEqual(format_size(1500 * 1024 * 1024), "1.5 GB")

    def test_residual_item(self):
        item = ResidualItem(
            path="/home/user/.config/myapp",
            size_bytes=10485760,  # 10 MB
            category="Configuração",
            selected=True,
        )
        self.assertEqual(item.formatted_size, "10.0 MB")
        self.assertTrue(item.selected)

    def test_installed_app_calculations(self):
        app = InstalledApp(
            id="test-app",
            name="Test Application",
            installed_size_bytes=100 * 1024 * 1024,  # 100 MB
            app_type=AppType.APT,
            residuals=[
                ResidualItem(path="/tmp/res1", size_bytes=20 * 1024 * 1024, selected=True),
                ResidualItem(path="/tmp/res2", size_bytes=30 * 1024 * 1024, selected=False),
            ],
        )
        self.assertEqual(app.formatted_installed_size, "100.0 MB")
        # Apenas os selecionados somam
        self.assertEqual(app.total_reclaimable_bytes, 120 * 1024 * 1024)
        self.assertEqual(app.formatted_total_size, "120.0 MB")


if __name__ == "__main__":
    unittest.main()
