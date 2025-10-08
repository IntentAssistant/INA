import rumps


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
            rumps.MenuItem("Settings", settings_menu),
            None,  # Separator
            rumps.MenuItem("Quit", callback=app.quit),
        ]

        return menu
