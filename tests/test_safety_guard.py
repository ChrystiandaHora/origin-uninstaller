import os
import unittest

from src.cleaner.safety_guard import (
    CRITICAL_PACKAGES,
    PROTECTED_PATHS,
    is_package_critical,
    is_path_safe_to_clean,
)


class TestSafetyGuard(unittest.TestCase):
    def test_critical_packages(self):
        # Pacotes do sistema devem ser bloqueados
        self.assertIsNotNone(is_package_critical("systemd"))
        self.assertIsNotNone(is_package_critical("coreutils"))
        self.assertIsNotNone(is_package_critical("bash"))
        self.assertIsNotNone(is_package_critical("apt"))
        self.assertIsNotNone(is_package_critical("dpkg"))
        self.assertIsNotNone(is_package_critical("libc6"))
        self.assertIsNotNone(is_package_critical("sudo"))
        self.assertIsNotNone(is_package_critical("gnome-shell"))
        self.assertIsNotNone(is_package_critical("origin-updater"))
        self.assertIsNotNone(is_package_critical("origin-uninstaller"))
        self.assertIsNotNone(is_package_critical("linux-image-6.1.0-25-amd64"))

        # Aplicativos normais não devem ser bloqueados
        self.assertIsNone(is_package_critical("google-chrome-stable"))
        self.assertIsNone(is_package_critical("discord"))
        self.assertIsNone(is_package_critical("code"))
        self.assertIsNone(is_package_critical("vlc"))

    def test_protected_paths(self):
        # Diretórios protegidos não podem ser limpos
        self.assertFalse(is_path_safe_to_clean("/"))
        self.assertFalse(is_path_safe_to_clean("/usr"))
        self.assertFalse(is_path_safe_to_clean("/var"))
        self.assertFalse(is_path_safe_to_clean("/var/lib"))
        self.assertFalse(is_path_safe_to_clean("/var/lib/dpkg"))
        self.assertFalse(is_path_safe_to_clean("/var/lib/flatpak"))
        self.assertFalse(is_path_safe_to_clean(os.path.expanduser("~")))
        self.assertFalse(is_path_safe_to_clean(os.path.expanduser("~/.config")))
        self.assertFalse(is_path_safe_to_clean(os.path.expanduser("~/.cache")))
        self.assertFalse(is_path_safe_to_clean(os.path.expanduser("~/Downloads")))

        # Subpastas específicas de aplicativos são permitidas
        self.assertTrue(is_path_safe_to_clean(os.path.expanduser("~/.config/google-chrome")))
        self.assertTrue(is_path_safe_to_clean(os.path.expanduser("~/.cache/discord")))
        self.assertTrue(is_path_safe_to_clean(os.path.expanduser("~/.var/app/com.spotify.Client")))
        self.assertTrue(is_path_safe_to_clean(os.path.expanduser("~/.dbeaver4")))


if __name__ == "__main__":
    unittest.main()
