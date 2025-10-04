import rumps
from ..config.language import get_text


class AppMenu:
    @staticmethod
    def create_menu(app):
        # Create Settings submenu
        settings_menu = [
            rumps.MenuItem("API Settings"),
            # Language Settings removed - English only
            # Display Settings removed - single display auto-selection
            # Sound Settings removed - sound functionality disabled
        ]

        # Create main menu
        menu = [
            rumps.MenuItem(get_text("settings"), settings_menu),
            None,  # Separator
            rumps.MenuItem(get_text("quit"), callback=app.quit),
        ]

        return menu
