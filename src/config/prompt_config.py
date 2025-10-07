"""
Prompt configuration management
Now uses Python module instead of JSON files for easier modification
Supports advanced prompt features including clarification and reflection
"""

import os
import json
from .prompts import (
    build_intention_analysis_prompt,
)
from datetime import datetime


class PromptConfig:
    def __init__(self, storage=None):
        print("[CONFIG] Prompt configuration loaded")
        self.storage = storage  # Store reference to storage for loading reflections

    def get_prompt(self):
        """Get the basic intention analysis prompt"""
        return build_intention_analysis_prompt()

    def get_formatted_prompt(self, task_name="No task specified"):
        """Get formatted prompt with task name"""
        return build_intention_analysis_prompt(task_name=task_name)

    def get_advanced_prompt(
        self,
        task_name="No task specified",
        use_clarification=True,
        clarification_intentions=None,
        use_reflection=True,
        reflection_intentions=None,
        reflection_rules=None,
        use_context=True,
        use_formatted_prediction=False,
        use_probabilistic_score=True,
        session_start_time=None,
        frontmost_app=None,
        opacity=None,
    ):
        """
        Get advanced intention analysis prompt with clarification and reflection
        """
        # Load clarification intentions if not provided and enabled
        if use_clarification and clarification_intentions is None and self.storage:
            clarification_intentions = self._load_clarification_intentions(task_name)

        return build_intention_analysis_prompt(
            task_name=task_name,
            use_clarification=use_clarification,
            clarification_intentions=clarification_intentions,
            use_reflection=use_reflection,
            reflection_intentions=reflection_intentions,
            reflection_rules=reflection_rules,
            use_context=use_context,
            use_formatted_prediction=use_formatted_prediction,
            use_probabilistic_score=use_probabilistic_score,
            frontmost_app=frontmost_app,
            opacity=opacity,
        )

    def _load_clarification_intentions(self, task_name):
        """Load clarification intentions from storage"""
        if not self.storage:
            return []

        try:
            # Clean task name for filename (remove special characters)
            clean_task_name = "".join(
                c for c in task_name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            clean_task_name = clean_task_name.replace(" ", "_")

            clarification_file = f"{clean_task_name}_clarification.json"
            clarification_path = os.path.join(
                self.storage.get_clarification_data_dir(), clarification_file
            )

            if os.path.exists(clarification_path):
                with open(clarification_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    intentions = data.get("augmented_intentions", [])
                    print(
                        f"[CLARIFICATION] Loaded {len(intentions)} intentions for: {task_name}"
                    )
                    return intentions
            else:
                return []

        except Exception as e:
            print(f"[CLARIFICATION] Error loading intentions: {e}")
            return []

    def _load_reflection_intentions(self, task_name, session_start_time=None):
        """Load reflection intentions from current session only"""
        if not self.storage:
            print("[DEBUG] No storage available for loading reflection intentions")
            return None

        # For session-based reflections, we start fresh each session
        # Only load reflections from the current session
        if session_start_time is None:
            print(
                "[DEBUG] No session start time provided - starting fresh reflection session"
            )
            return []

        try:
            # Get reflection data directory
            reflection_dir = os.path.join(
                self.storage.get_clarification_data_dir(), "..", "reflection_data"
            )

            # Clean task name for filename (same logic as save_results)
            clean_task_name = "".join(
                c for c in task_name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            clean_task_name = clean_task_name.replace(" ", "_")

            # Generate session timestamp
            if isinstance(session_start_time, str):
                session_timestamp = session_start_time
            else:
                session_timestamp = session_start_time.strftime("%Y%m%d_%H%M%S")

            # Look for reflection file for this specific session
            reflection_file = os.path.join(
                reflection_dir,
                f"{clean_task_name}_{session_timestamp}_reflections.json",
            )

            print(f"[DEBUG] Looking for session reflection file: {reflection_file}")

            if os.path.exists(reflection_file):
                with open(reflection_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert reflection data to list of strings
                    reflections = []
                    for reflection in data.get("reflections", []):
                        if isinstance(reflection, dict):
                            desc = reflection.get("image_description", "")
                            intent = reflection.get("reflected_implicit_intention", "")
                            reflections.append(f'"{desc}": "{intent}"')
                        else:
                            reflections.append(str(reflection))

                    print(
                        f"[DEBUG] Loaded {len(reflections)} reflection intentions from current session:"
                    )
                    for i, reflection in enumerate(reflections, 1):
                        print(f"  {i}. {reflection}")
                    return reflections

            print(
                f"[DEBUG] No reflection file found for current session - starting fresh"
            )
            return []

        except Exception as e:
            print(f"[ERROR] Failed to load reflection intentions: {e}")
            return []

    def save_reflection(
        self,
        task_name,
        image_description,
        reflected_intention,
        previous_reason,
        session_start_time=None,
    ):
        """Save a new reflection for future use with session-specific filename"""
        if not self.storage:
            print("[ERROR] No storage available for saving reflection")
            return False

        try:
            # Get reflection data directory
            reflection_dir = os.path.join(
                self.storage.get_clarification_data_dir(), "..", "reflection_data"
            )
            os.makedirs(reflection_dir, exist_ok=True)

            # Clean task name for filename (same logic as save_results)
            clean_task_name = "".join(
                c for c in task_name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            clean_task_name = clean_task_name.replace(" ", "_")

            # Generate timestamp for this session if not provided
            if session_start_time is None:
                session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            else:
                # Use provided session start time
                if isinstance(session_start_time, str):
                    session_timestamp = session_start_time
                else:
                    session_timestamp = session_start_time.strftime("%Y%m%d_%H%M%S")

            # Reflection file for this task with session timestamp
            reflection_file = os.path.join(
                reflection_dir,
                f"{clean_task_name}_{session_timestamp}_reflections.json",
            )

            # Load existing reflections for this session
            reflections_data = {
                "task_name": task_name,
                "session_start": session_timestamp,
                "reflections": [],
            }
            if os.path.exists(reflection_file):
                with open(reflection_file, "r", encoding="utf-8") as f:
                    reflections_data = json.load(f)

            # Add new reflection
            new_reflection = {
                "timestamp": datetime.now().isoformat(),
                "image_description": image_description,
                "reflected_implicit_intention": reflected_intention,
                "previous_reason": previous_reason,
            }

            reflections_data["reflections"].append(new_reflection)

            # Save updated reflections
            with open(reflection_file, "w", encoding="utf-8") as f:
                json.dump(reflections_data, f, indent=2, ensure_ascii=False)

            print(
                f"[DEV] Saved reflection for task: {task_name} (session: {session_timestamp})"
            )
            return True

        except Exception as e:
            print(f"[ERROR] Failed to save reflection: {e}")
            return False

    def get_reflection_prompt(self, stated_intention, previous_reason):
        """Get reflection prompt for processing user feedback"""
        from .prompts import format_reflection_prompt_distracted_bad

        return format_reflection_prompt_distracted_bad(
            stated_intention, previous_reason
        )
