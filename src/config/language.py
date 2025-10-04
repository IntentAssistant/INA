"""
Language management for the intention app
Supports Korean and English localization
"""

import json
import os
from pathlib import Path


class LanguageManager:
    """Manages language settings and translations"""

    def __init__(self):
        self.current_language = "ko"  # Default to Korean
        self.translations = {}
        self.load_translations()
        self.load_language_setting()

    def load_translations(self):
        """Load all translation files"""
        self.translations = {
            "ko": {
                # App Titles
                "app_title_1": "INA",
                "app_title_2": "Blue",
                "app_title_3": "Orange",
                "app_title_test": "TEST",
                # Main UI
                "type_message": "의도를 입력하세요 (예: '에세이 작성, 탁자 구매하기')",
                "click_message": "의도를 재설정하려면 클릭 ⬆️ 또는 조언받기 시작 ↗️",
                "set_button": "설정",
                "start_button": "시작",
                "stop_button": "중지",
                "done_button": "완료",
                # Menu Items
                "settings": "설정",
                "user_settings": "사용자 설정",
                "language_settings": "언어 설정",
                "quit": "종료",
                # Popups
                "focus_reminder_title": "🎯 집중 알림",
                "focus_reminder_korean_title": "의도 집중 알림",
                "focus_reminder_korean_message": "지금은 '{intention}' 시간입니다!\n\n다른 앱에서 시간을 보내고 계시네요.\n집중해 볼까요?!",
                "focus_reminder_korean_button": "집중하러 돌아가기",
                "focus_reminder_english_title": "Focus Reminder",
                "focus_reminder_english_message": "Time to work on '{intention}'!\n\nYou're spending time in other apps.\nPlease return to your intention app and start working!",
                "focus_reminder_english_button": "Return to Work",
                # Set intention popup
                "set_intention_title": "🎯 의도 설정",
                "set_intention_message_basic": "다른 앱에서 시간을 보내고 계시네요!\n\n원활한 실험을 위해\n시작 버튼을 눌러 주세요.",
                "set_intention_message_general": "다른 앱에서 시간을 보내고 계시네요!\n\n먼저 지금 의도 하신일을 설정하고\n의도적인 삶을 살아봐요.",
                "set_intention_hint": "💡 실험 앱을 클릭하면 팝업이 사라져요.",
                # Instructions
                "instruction_start": "활동을 시작하려면 클릭 ↑",
                "instruction_finish": "'완료'를 클릭하여 활동 마무리 ↑",
                # Messages
                "encouragement_korean": '당신의 의도는 "{task}" 입니다.',
                "encouragement_english": 'Your intention is "{task}"!',
                # Notifications
                "focus_notification_title": "🎯 실험 참여 알림",
                "focus_notification_subtitle": "를 입력해 주세요.",
                "focus_notification_message": "다른 앱에서 시간을 보내고 계시네요! 앱을 클릭하여 의도를 입력해주세요.",
                # History and Timeline
                "todays_intentions": "오늘의 의도들",
                "no_data_yet": "아직 데이터 없음",
                "in_progress": "진행 중...",
                # Feedback Messages
                "feedback_focused": "이 메시지가 정확한가요?",
                "feedback_ambiguous": "이 메시지가 정확한가요?",
                "feedback_distracted": "이 메시지가 정확한가요?",
                # Clarification
                "clarification_title": "의도 구체화",
                "clarification_placeholder": "답변을 입력하세요...",
                "send_button": "전송",
                "close_button": "✕",
                # Language Settings Dialog
                "language_dialog_title": "언어 설정",
                "language_dialog_description": "앱 표시 언어를 선택하세요:",
                "language_korean": "한국어",
                "language_english": "English",
                "save_button": "저장",
                "language_change_success": "언어가 성공적으로 변경되었습니다.",
                # Loading and Status
                "loading": "로딩 중",
                "starting_soon": "잠시만 기다려주세요.",
                # Buttons
                "ok_button": "확인",
                "cancel_button": "취소",
                # Rating
                "todays_rating": "오늘의 평점:",
                "rating_question": "Q. 귀하의 활동이 원래 의도와 얼마나 일치했습니까?",
                "rating_not_aligned": "전혀 일치하지 않음",
                "rating_barely_aligned": "조금 일치함",
                "rating_somewhat_aligned": "다소 일치함",
                "rating_aligned": "대체로 일치함",
                "rating_very_well_aligned": "완전히 일치함",
                # Multiple Display Dialog
                "multiple_display_title": "다중 디스플레이 감지",
                "multiple_display_message": "이 앱은 단일 디스플레이 환경에서 최적화되어 있습니다.\n\n다중 디스플레이 설정을 감지했습니다. 정확한 기능을 위해 다른 디스플레이를 연결 해제하고 앱을 다시 시작해주세요.",
                "exit_app_button": "확인 - 앱 종료",
                # User Settings Dialog
                "user_settings_description": "할당받은 사용자 ID와 비밀번호를 입력해주세요.\n연구 참여를 위해 이 정보가 필요합니다.",
                "user_id_label": "사용자 ID:",
                "password_label": "비밀번호:",
                "user_id_placeholder": "할당받은 사용자 ID를 입력하세요",
                "password_placeholder": "비밀번호를 입력하세요",
                "user_id_required": "사용자 ID가 필요합니다",
                "user_id_required_message": "계속하려면 할당받은 사용자 ID를 입력해주세요.",
                "password_required": "비밀번호가 필요합니다",
                "password_required_message": "계속하려면 비밀번호를 입력해주세요.",
                # Feedback Response Messages
                "feedback_thanks": "피드백 감사합니다.",
                "feedback_sorry": "피드백 감사합니다.",
                # Clarification Completion
                "clarification_complete": "좋습니다! 시작 버튼을 클릭하세요",
            },
            "en": {
                # App Titles
                "app_title_1": "INA",
                "app_title_2": "Blue",
                "app_title_3": "Orange",
                "app_title_test": "TEST",
                # Main UI
                "type_message": "Enter your intention (e.g., 'Write essay') here!",
                "click_message": "Click to reset intention ⬆️ or start getting advice ↗️",
                "set_button": "Set",
                "start_button": "Start",
                "stop_button": "Stop",
                "done_button": "Done",
                # Menu Items
                "settings": "Settings",
                "user_settings": "User Settings",
                "language_settings": "Language Settings",
                "quit": "Quit",
                # Popups
                "focus_reminder_title": "🎯 Focus Reminder",
                "focus_reminder_korean_title": "Focus Reminder",
                "focus_reminder_korean_message": "Time to work on '{intention}'!\n\nYou're spending time in other apps.\nPlease return to your intention app and start working!",
                "focus_reminder_korean_button": "Return to Work",
                "focus_reminder_english_title": "Focus Reminder",
                "focus_reminder_english_message": "Time to work on '{intention}'!\n\nYou're spending time in other apps.\nPlease return to your intention app and start working!",
                "focus_reminder_english_button": "Return to Work",
                # Set intention popup
                "set_intention_title": "🎯 Set Your Intention",
                "set_intention_message_basic": "You're spending time in other apps!\n\nTo work intentionally with focus,\npress the Start button to begin working.",
                "set_intention_message_general": "You're spending time in other apps!\n\nFirst, set a goal you want to achieve today\nand start working intentionally with focus.",
                "set_intention_hint": "💡 Click the app to continue working",
                # Instructions
                "instruction_start": "Click to start activity ↑",
                "instruction_finish": "Click 'Done' to finish activity ↑",
                # Messages
                "encouragement_korean": 'Your intention is "{task}"!',
                "encouragement_english": 'Your intention is "{task}"!',
                # Notifications
                "focus_notification_title": "🎯 Focus Alert",
                "focus_notification_subtitle": "Intentional Work",
                "focus_notification_message": "You're spending time in other apps! Click the app to continue working.",
                # History and Timeline
                "todays_intentions": "Today's Intentions",
                "no_data_yet": "No data yet",
                "in_progress": "in progress...",
                # Feedback Messages
                "feedback_focused": "Is this message correct?",
                "feedback_ambiguous": "Is this message correct?",
                "feedback_distracted": "Is this message correct?",
                # Clarification
                "clarification_title": "Clarifying your intention",
                "clarification_placeholder": "Type your response...",
                "send_button": "Send",
                "close_button": "✕",
                # Language Settings Dialog
                "language_dialog_title": "Language Settings",
                "language_dialog_description": "Select the display language for the app:",
                "language_korean": "한국어",
                "language_english": "English",
                "save_button": "Save",
                "language_change_success": "Language changed successfully.",
                # Loading and Status
                "loading": "Loading",
                "starting_soon": "Starting soon..",
                # Buttons
                "ok_button": "OK",
                "cancel_button": "Cancel",
                # Rating
                "todays_rating": "Today's Rating:",
                "rating_question": "How well did your activity align with your intention?",
                "rating_not_aligned": "Not aligned at all",
                "rating_barely_aligned": "Barely aligned",
                "rating_somewhat_aligned": "Somewhat aligned",
                "rating_aligned": "Aligned",
                "rating_very_well_aligned": "Very well aligned",
                # Multiple Display Dialog
                "multiple_display_title": "Multiple Display Detected",
                "multiple_display_message": "This app is optimized for single display environments.\n\nMultiple display setup detected. For accurate functionality, please disconnect other displays and restart the app.",
                "exit_app_button": "OK - Exit App",
                # User Settings Dialog
                "user_settings_description": "Please enter your assigned User ID and Password.\nThese credentials are required to participate in the study.",
                "user_id_label": "User ID:",
                "password_label": "Password:",
                "user_id_placeholder": "Enter your assigned User ID",
                "password_placeholder": "Enter your password",
                "user_id_required": "User ID Required",
                "user_id_required_message": "Please enter your assigned User ID to continue.",
                "password_required": "Password Required",
                "password_required_message": "Please enter your password to continue.",
                # Feedback Response Messages
                "feedback_thanks": "Thanks for the feedback!",
                "feedback_sorry": "Sorry for the mistake",
                # Clarification Completion
                "clarification_complete": "OK! Click the start button",
            },
        }

    def get_config_dir(self):
        """Get the configuration directory path"""
        config_dir = Path.home() / ".intention_app"
        config_dir.mkdir(exist_ok=True)
        return config_dir

    def get_language_config_path(self):
        """Get the language configuration file path"""
        return self.get_config_dir() / "language_config.json"

    def load_language_setting(self):
        """Load saved language setting"""
        try:
            config_path = self.get_language_config_path()
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.current_language = config.get("language", "ko")
                    print(
                        f"[LANGUAGE] Loaded language setting: {self.current_language}"
                    )
            else:
                print("[LANGUAGE] No saved language setting, using default: ko")
        except Exception as e:
            print(f"[LANGUAGE] Error loading language setting: {e}")
            self.current_language = "ko"

    def save_language_setting(self, language):
        """Save language setting to file"""
        try:
            config_path = self.get_language_config_path()
            config = {"language": language}
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"[LANGUAGE] Saved language setting: {language}")
            return True
        except Exception as e:
            print(f"[LANGUAGE] Error saving language setting: {e}")
            return False

    def set_language(self, language):
        """Set current language"""
        if language in self.translations:
            self.current_language = language
            if self.save_language_setting(language):
                print(f"[LANGUAGE] Language changed to: {language}")
                return True
        return False

    def get_text(self, key, **kwargs):
        """Get translated text for the given key"""
        try:
            text = self.translations[self.current_language].get(
                key, self.translations["en"].get(key, f"[MISSING: {key}]")
            )

            # Format the text with any provided kwargs
            if kwargs:
                text = text.format(**kwargs)

            return text
        except Exception as e:
            print(f"[LANGUAGE] Error getting text for key '{key}': {e}")
            return f"[ERROR: {key}]"

    def get_current_language(self):
        """Get current language code"""
        return self.current_language

    def get_available_languages(self):
        """Get list of available language codes"""
        return list(self.translations.keys())


# Global language manager instance
language_manager = LanguageManager()


def get_text(key, **kwargs):
    """Convenience function to get translated text"""
    return language_manager.get_text(key, **kwargs)


def set_language(language):
    """Convenience function to set language"""
    return language_manager.set_language(language)


def get_current_language():
    """Convenience function to get current language"""
    return language_manager.get_current_language()
