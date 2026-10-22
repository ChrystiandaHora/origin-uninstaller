import unittest

from src.scanners.desktop_resolver import DesktopResolver
from src.scanners.flatpak_scanner import parse_flatpak_size


class TestScanners(unittest.TestCase):
    def test_parse_flatpak_size(self):
        self.assertEqual(parse_flatpak_size("100 B"), 100)
        self.assertEqual(parse_flatpak_size("10 kB"), 10 * 1024)
        self.assertEqual(parse_flatpak_size("5,5 MB"), int(5.5 * 1024 * 1024))
        self.assertEqual(parse_flatpak_size("1.2 GB"), int(1.2 * 1024 * 1024 * 1024))
        self.assertEqual(parse_flatpak_size(""), 0)

    def test_desktop_resolver(self):
        resolver = DesktopResolver()
        # Pacotes populares devem ser identificados como aplicativos de usuário
        self.assertTrue(resolver.is_gui_app("google-chrome-stable"))
        self.assertTrue(resolver.is_gui_app("code"))
        # Runtimes genéricos não devem ser classificados como aplicativo GUI individual
        self.assertFalse(resolver.is_gui_app("python3"))
        self.assertFalse(resolver.is_gui_app("bash"))


if __name__ == "__main__":
    unittest.main()
