"""
Direct LLM API client for OpenAI GPT and Google Gemini
Replaces the Cloud Run backend with direct API calls
"""

import base64
import io
import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PIL import Image
from google import genai

from ..config.api_config import (
    LLMProvider,
    DEFAULT_LLM_PROVIDER,
    get_api_key,
    get_model_config,
    is_api_configured,
    get_api_config_manager,
    IMAGE_CONFIG,
)


class DirectLLMClient:
    """Direct API client for LLM services without Cloud Run backend"""

    def __init__(
        self, provider: LLMProvider = DEFAULT_LLM_PROVIDER, model: Optional[str] = None
    ):
        self.provider = provider
        self.config = get_model_config(provider)
        self.api_key = get_api_key(provider)

        # Override model if provided
        if model:
            self.config["model"] = model

        if not self.api_key:
            raise ValueError(
                f"API key not found for {provider.value}. Please set {self.config['api_key_env']} environment variable."
            )

        # Initialize Gemini SDK if using Gemini (new SDK)
        if self.provider == LLMProvider.GEMINI:
            os.environ["GOOGLE_API_KEY"] = self.api_key
            self.gemini_client = genai.Client()
            self.gemini_model_id = self.config["model"]
            # Store generation config parameters
            self.gemini_config = {
                "temperature": self.config["temperature"],
                "max_output_tokens": self.config["max_tokens"],
            }

    def prepare_image_for_api(self, image_data: bytes) -> str:
        """
        Prepare image for API call by resizing and compressing if needed
        Returns base64 encoded image string
        """
        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGB")

            # Resize if too large
            max_dim = IMAGE_CONFIG["max_dimension"]
            if max(image.size) > max_dim:
                image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            # Compress to JPEG
            output_buffer = io.BytesIO()
            image.save(
                output_buffer,
                format="JPEG",
                quality=IMAGE_CONFIG["jpeg_quality"],
                optimize=True,
            )

            # Check size and compress more if needed
            compressed_data = output_buffer.getvalue()
            max_size = IMAGE_CONFIG["max_size_mb"] * 1024 * 1024

            if len(compressed_data) > max_size:
                # Further compress by reducing quality
                for quality in [70, 50, 30]:
                    output_buffer = io.BytesIO()
                    image.save(
                        output_buffer, format="JPEG", quality=quality, optimize=True
                    )
                    compressed_data = output_buffer.getvalue()
                    if len(compressed_data) <= max_size:
                        break

            # Encode to base64
            return base64.b64encode(compressed_data).decode("utf-8")

        except Exception as e:
            raise ValueError(f"Failed to process image: {str(e)}")

    def test_api_key(self) -> Dict:
        """
        Test if the API key is valid by making a simple API call

        Returns:
            dict: {"success": bool, "message": str}
        """
        try:
            if self.provider == LLMProvider.GEMINI:
                return self._test_gemini_key()
            elif self.provider == LLMProvider.OPENAI:
                return self._test_openai_key()
            else:
                return {
                    "success": False,
                    "message": f"Unsupported provider: {self.provider}",
                }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _test_gemini_key(self) -> Dict:
        """Test Gemini API key with a simple request (new SDK)"""
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_id,
                contents="Hello! Please respond with 'OK'",
            )

            if response.text:
                return {
                    "success": True,
                    "message": f"Gemini API is working!\nModel: {self.config['model']}\nResponse: {response.text[:50]}",
                }
            else:
                return {
                    "success": False,
                    "message": "Received empty response from Gemini",
                }
        except Exception as e:
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
                return {
                    "success": False,
                    "message": "Invalid API key. Please check your Gemini API key.",
                }
            else:
                return {"success": False, "message": f"Gemini API error: {error_msg}"}

    def _test_openai_key(self) -> Dict:
        """Test OpenAI API key with a simple request"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.config["model"],
                "messages": [
                    {"role": "user", "content": "Hello! Please respond with 'OK'"}
                ],
                "max_tokens": 10,
                "temperature": 0,
            }

            response = requests.post(
                f"{self.config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                message = result["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "message": f"OpenAI API is working!\nModel: {self.config['model']}\nResponse: {message}",
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Invalid API key. Please check your OpenAI API key.",
                }
            else:
                return {
                    "success": False,
                    "message": f"OpenAI API error ({response.status_code}): {response.text}",
                }
        except Exception as e:
            return {"success": False, "message": f"OpenAI API error: {str(e)}"}

    def analyze_screen(self, image_data: bytes, prompt: str, context: Dict) -> Dict:
        """
        Analyze screen capture using direct LLM API

        Args:
            image_data: Raw image bytes from screen capture
            prompt: Analysis prompt
            context: Additional context (app info, task, etc.)

        Returns:
            Dict with analysis results
        """
        try:
            # Prepare image
            base64_image = self.prepare_image_for_api(image_data)

            if self.provider == LLMProvider.OPENAI:
                return self._analyze_with_openai(base64_image, prompt, context)
            elif self.provider == LLMProvider.GEMINI:
                return self._analyze_with_gemini(base64_image, prompt, context)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            return {
                "output": "error",
                "reason": f"Analysis failed: {str(e)}",
                "score": -1,
                "timestamp": datetime.now().isoformat(),
            }

    def _analyze_with_openai(
        self, base64_image: str, prompt: str, context: Dict
    ) -> Dict:
        """Analyze using OpenAI GPT-4 Vision API"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # Use the prompt from prompts.py (passed from manager.py via prompt_config)
        full_prompt = prompt

        payload = {
            "model": self.config["model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
        }

        response = requests.post(
            f"{self.config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return self._parse_analysis_response(content)
        else:
            raise Exception(
                f"OpenAI API error: {response.status_code} - {response.text}"
            )

    def _analyze_with_gemini(
        self, base64_image: str, prompt: str, context: Dict
    ) -> Dict:
        """Analyze using Google Gemini Pro Vision API with new SDK"""

        # Use the prompt from prompts.py (passed from manager.py via prompt_config)
        # The prompt already includes task, clarification, reflection, and all context
        full_prompt = prompt

        print(
            f"[DEBUG] Using prompt from prompts.py (length: {len(full_prompt)} chars)"
        )

        # Convert base64 to PIL Image
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))

        # Use new SDK for analysis
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_id,
                contents=[full_prompt, image],
            )

            if not response.text:
                raise Exception("Empty response from Gemini")

            content = response.text.strip()

            # 🔍 DEBUG: Print raw LLM response
            print("=" * 80)
            print("🔍 [DEBUG] RAW GEMINI RESPONSE:")
            print(content)
            print("=" * 80)

            parsed_result = self._parse_analysis_response(content)

            # 🔍 DEBUG: Print parsed result
            print("🔍 [DEBUG] PARSED RESULT:")
            import json as json_module

            print(json_module.dumps(parsed_result, indent=2, ensure_ascii=False))
            print("=" * 80)

            return parsed_result

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    # _build_analysis_prompt removed - now using prompts.py directly

    def _parse_analysis_response(self, content: str) -> Dict:
        """Parse LLM response into standardized format"""
        try:
            # Try to extract JSON from response
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)

            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)

                return {
                    "output": parsed.get("output", "unknown"),
                    "reason": parsed.get("reason", "No reason provided"),
                    "message": parsed.get("message", ""),  # Add message field
                    "score": parsed.get("score", 50),
                    "timestamp": datetime.now().isoformat(),
                    "raw_response": content,
                }
            else:
                # Fallback: try to interpret text response
                output = (
                    "focused"
                    if any(
                        word in content.lower()
                        for word in ["focused", "aligned", "good"]
                    )
                    else "distracted"
                )

                return {
                    "output": output,
                    "reason": content[:200] + "..." if len(content) > 200 else content,
                    "message": (
                        "Stay focused!"
                        if output == "focused"
                        else "Refocus on your goal!"
                    ),
                    "score": 75 if output == "focused" else 25,
                    "timestamp": datetime.now().isoformat(),
                    "raw_response": content,
                }

        except Exception as e:
            return {
                "output": "error",
                "reason": f"Failed to parse response: {str(e)}",
                "message": "",
                "score": -1,
                "timestamp": datetime.now().isoformat(),
                "raw_response": content,
            }

    def get_clarification_question(self, prompt: str, context: Dict) -> str:
        """Get clarification question using direct API"""
        try:
            if self.provider == LLMProvider.OPENAI:
                return self._get_clarification_openai(prompt, context)
            elif self.provider == LLMProvider.GEMINI:
                return self._get_clarification_gemini(prompt, context)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            return f"Sorry, I couldn't generate a clarification question: {str(e)}"

    def _get_clarification_openai(self, prompt: str, context: Dict) -> str:
        """Get clarification using OpenAI API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
        }

        response = requests.post(
            f"{self.config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(
                f"OpenAI API error: {response.status_code} - {response.text}"
            )

    def _get_clarification_gemini(self, prompt: str, context: Dict) -> str:
        """Get clarification using Gemini API with new SDK"""
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_id,
                contents=prompt,
            )

            if not response.text:
                raise Exception("Empty response from Gemini")

            return response.text.strip()

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    def analyze_reflection(
        self, prompt: str, images: List[Image.Image], task: str
    ) -> str:
        """
        Analyze multiple images for reflection/feedback using LLM

        Args:
            prompt: Reflection prompt text
            images: List of PIL Image objects from cache
            task: Current task name

        Returns:
            str: Reflection analysis text
        """
        try:
            if self.provider == LLMProvider.GEMINI:
                return self._analyze_reflection_gemini(prompt, images, task)
            elif self.provider == LLMProvider.OPENAI:
                return self._analyze_reflection_openai(prompt, images, task)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            print(f"[ERROR] Reflection analysis failed: {e}")
            return f"Reflection analysis error: {str(e)}"

    def _analyze_reflection_gemini(
        self, prompt: str, images: List[Image.Image], task: str
    ) -> str:
        """Analyze reflection using Gemini with multiple images (new SDK)"""
        try:
            # Gemini supports multiple images in a single request
            content_parts = [prompt]

            # Add up to 10 images (cache limit)
            for img in images[:10]:
                content_parts.append(img)

            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_id,
                contents=content_parts,
            )

            if not response.text:
                raise Exception("Empty response from Gemini")

            return response.text.strip()

        except Exception as e:
            raise Exception(f"Gemini reflection error: {str(e)}")

    def _analyze_reflection_openai(
        self, prompt: str, images: List[Image.Image], task: str
    ) -> str:
        """Analyze reflection using OpenAI GPT-4 Vision with multiple images"""
        try:
            # OpenAI GPT-4 Vision supports multiple images
            content_parts = [{"type": "text", "text": prompt}]

            # Add up to 10 images (cache limit)
            for img in images[:10]:
                # Convert PIL image to base64
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                    }
                )

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.config["model"],
                "messages": [{"role": "user", "content": content_parts}],
                "max_tokens": self.config["max_tokens"],
                "temperature": self.config["temperature"],
            }

            response = requests.post(
                f"{self.config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,  # Longer timeout for multiple images
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(
                    f"OpenAI API error: {response.status_code} - {response.text}"
                )

        except Exception as e:
            raise Exception(f"OpenAI reflection error: {str(e)}")


def get_configured_client() -> Optional[DirectLLMClient]:
    """Get a configured LLM client using the active provider from settings"""

    api_manager = get_api_config_manager()

    # Try the currently selected provider first
    active_provider = api_manager.get_provider()
    if api_manager.is_api_configured(active_provider):
        try:
            return DirectLLMClient(active_provider)
        except Exception as e:
            print(f"Failed to initialize {active_provider.value} client: {e}")

    # Fallback: try any configured provider
    configured_providers = api_manager.get_configured_providers()
    for provider in configured_providers:
        if provider != active_provider:  # Skip already tried provider
            try:
                return DirectLLMClient(provider)
            except Exception as e:
                print(f"Failed to initialize {provider.value} client: {e}")

    return None
