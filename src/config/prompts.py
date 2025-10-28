"""
Prompt templates for the Intentional Computing app
All prompts are defined here as Python variables for easy modification
"""


def _infer_language(task_name: str) -> str:
    """
    Lightweight language hint based on the intention text.
    Inspects Unicode ranges / characteristic characters to guess the language
    for a handful of common scripts. Falls back to English when uncertain.
    """
    if not task_name:
        return "English"

    def _has_char_in_ranges(ranges):
        for ch in task_name:
            code = ord(ch)
            for start, end in ranges:
                if start <= code <= end:
                    return True
        return False

    # Hangul
    if _has_char_in_ranges(
        [
            (0xAC00, 0xD7A3),  # Hangul syllables
            (0x1100, 0x11FF),  # Hangul Jamo
            (0x3130, 0x318F),  # Hangul Compatibility Jamo
        ]
    ):
        return "Korean"

    # Japanese (Hiragana / Katakana)
    if _has_char_in_ranges(
        [
            (0x3040, 0x309F),  # Hiragana
            (0x30A0, 0x30FF),  # Katakana
            (0x31F0, 0x31FF),  # Katakana Phonetic Extensions
        ]
    ):
        return "Japanese"

    # Chinese (CJK Unified Ideographs)
    if _has_char_in_ranges([(0x4E00, 0x9FFF)]):
        return "Chinese"

    # Russian / Cyrillic languages
    if _has_char_in_ranges([(0x0400, 0x052F)]):
        return "Russian"

    # Arabic
    if _has_char_in_ranges(
        [
            (0x0600, 0x06FF),
            (0x0750, 0x077F),
            (0x08A0, 0x08FF),
        ]
    ):
        return "Arabic"

    # Hindi (Devanagari)
    if _has_char_in_ranges([(0x0900, 0x097F)]):
        return "Hindi"

    # Thai
    if _has_char_in_ranges([(0x0E00, 0x0E7F)]):
        return "Thai"

    # Greek
    if _has_char_in_ranges([(0x0370, 0x03FF)]):
        return "Greek"

    # Hebrew
    if _has_char_in_ranges([(0x0590, 0x05FF)]):
        return "Hebrew"

    # Basic checks for a few Latin languages using common accented characters
    lowered = task_name.lower()
    if any(ch in lowered for ch in "áéíóúñ" "¿¡"):  # Spanish markers
        return "Spanish"
    if any(ch in lowered for ch in "àâçéèêîôûùëï" "œ" "æ"):  # French markers
        return "French"
    if any(ch in lowered for ch in "äöüß" "ä" "ö" "ü"):  # German markers
        return "German"
    if any(
        ch in lowered for ch in "ãõçáéíóú" "âêô" "à" "é" "ê" "ô" "ç" "ã" "õ"
    ):  # Portuguese markers
        return "Portuguese"
    if any(ch in lowered for ch in "èéìíîòóùú" "à" "è" "ì" "ò" "ù"):  # Italian markers
        return "Italian"

    return "English"


# General instruction for all prompts
GENERAL_INSTRUCTION = """[General Instruction]
You are a friendly AI coach with balanced sensitivity to task focus and a neutral communication style. 
The user's current intention is provided as [intention: {task_name}]. 
Help users stay mindful of their task while providing feedback that matches your assigned tone and sensitivity. 
Consider the specific nature of their task when giving suggestions and feedback. 
For example, given a task of shopping, user may watching some reviews of several items. Or, given a task of writing a report, user may discuss with peers.

"""

# Context instruction for evaluating relevance
CONTEXT_INSTRUCTION_WITHOUT_FORMAT = """[Key Instruction for Evaluating Relevance]
- **Examine Details**: Look for specific details in the provided information such as context of the conversation or title of the video on YouTube.
- **Analyze Context Beyond Keywords**: Do not judge content solely based on its surface-level category (e.g., chat, video, email). Instead, determine if it serves the task.
- **Bridge Indirect Relevance**: If an activity indirectly supports the task (e.g., searching, communicating, or researching), recognize its role instead of marking it as unrelated.
- **Be Certain for Scores**: Only label an activity as highly aligned or highly unrelated if there is clear evidence. If unsure, assign an intermediate value."""

CONTEXT_INSTRUCTION_WITH_FORMAT = """[Key Instruction for Evaluating Relevance]
- **Predict Intent**: Before judging anything, predict the intent of the user's behavior based on the provided information.
- **Examine Details**: Look for specific details in the provided information such as context of the conversation or title of the video on YouTube.
- **Analyze Context Beyond Keywords**: Do not judge content solely based on its surface-level category (e.g., chat, video, email). Instead, determine if it serves the task.
- **Bridge Indirect Relevance**: If an activity indirectly supports the task (e.g., searching, communicating, or researching), recognize its role instead of marking it as unrelated.
- **Be Certain for Scores**: Only label an activity as highly aligned or highly unrelated if there is clear evidence. If unsure, assign an intermediate value."""

# Scoring guidelines
SCORING_GUIDELINE_DISCRETE = """[Scoring Guidelines]
0: Perfect match with your task   
- Clearly aligned with your task   
- Exactly what you need   
- Core learning material
- Right content   

1: Absolutely unrelated to your task (100% certain)   
- Gaming during study
- Social media during work
- Technically unrelated but might feel productive   
- Random browsing"""

SCORING_GUIDELINE_PROBABILITY = """[Scoring Guidelines]
0.0: Perfectly relevant 
- Clearly aligned with your task  
- Example: Writing a report, coding for a project, or shopping for a specific item on e-commerce, 

0.2: Mostly relevant  
- Indirectly relevant but necessary (e.g., searching, communication, reference gathering)
- Example: Watching a video tutorial on the same topic, reading a related article, or discussing with peers about the task

0.4: Somewhat relevant  
- Indirectly helpful but not essential 
- Example: Watching a review video or engaging in a discussion that could be related but lacks clear context

0.6: Somewhat irrelevant
- Unclear if it supports or distracts  
- Example: Initial page of web browser, diverse thumbnails of YouTube videos, desktop video, finding a file of in Finder

0.8: Mostly irrelevant  
- Has little to do with the task but could still offer minimal benefits  
- Example: Watching a video having or casual discussions that slightly touch on the topic

1.0: Completely irrelevant  
- Clearly a distraction or off-topic activity  
- Example: Gaming during study, social media during work, random entertainment browsing"""

# Important rules
IMPORTANT_RULES = """[IMPORTANT Rules]
Return only the JSON object."""

# Clarification context
CLARIFICATION_CONTEXT = """[Clarification Context]
Additionally, given [intention: {task_name}] from the user, the below content provides possible activities that the user may perform, based on the clarification questions and answers.
Please use this context of augmented intention for more accurate classification.
When the clarification
{list_of_augmented_intention}"""

# Learning context from user feedback
LEARNING_FROM_FEEDBACK_CONTEXT = """[Reflection Context]
Furthermore, given [intention: {task_name}] from the user, the following context have been learned from the user's past feedback. 
Each reflected context is composed as: {{"implicit intentions learend from reflection" ("relevant description of user activity")}}. 
Please use this augmented intention context for more accurate classification.
{list_of_learned_intentions}"""

# Learning context from user feedback
ADJUST_FROM_FEEDBACK_CONTEXT = """[Reflection Rules]
The following rules have been learned based on the user's past feedback. 
Each reflected rules is composed as: {{"scoring rule learned from reflection" ("relevant description of user activity")}}. 
{list_of_learned_rules}"""

# Clarification prompt for understanding user intentions
CLARIFICATION_PROMPT_TEMPLATE = """You are a helpful assistant that engages in a multi-turn conversation to better understand the user's intention.

[Input]
The user stated: "{stated_intention}"

[Goal]
Ask a clarification question to clarify their intention. 
The questions can be about the specifications of the target item, if the user is planning to shop, or a specific location, if the user is planning a tour.
Also, the questions can be about the specifications of the tools that the user wants to use, such as Slack or e-commerce websites.
When asking the question, guide the user with examples so that the user can understand your question clearly and answer easily.
Please ask diverse aspects of the intention (such as on targets or tools, as well as other related sub-tasks that the user may perform).

IMPORTANT: Respond in the same language as the user's stated intention. If the user wrote in Korean, respond in Korean. If in English, respond in English.

[Rules]
- The main objective is to obtain information about the user's plan or activities related to the stated intention.
- Focus on asking what kind of activities that the user can answer easily (for example, what tools would the users be using)
- Instead of following questions, ask diverse subtasks or other possible related jobs (for example, would the user collaborate with peers - so that you can infer that the user would use some communication tools as well - or would the user collect resource information by searching on the internet - so that you can infer that the user would use some web browsers)
- Rather than asking abstract aspects of the intention (such as liking, belief, and interests), stick to clearly answerable points (such as purpose, plan, and activities) 
- Ask questions so that you can get information on the detailed contents of the activities of the user (for example, what kind of essay would the user write, what kind of video would the user watch, what topics are the physics homework related to, what kind of information do you want to search regarding ‘preparing travel to Paris’ do you need, etc.)
- Do not just ask yes/no questions, but ask questions that can be answered with some details (for example, instead of asking "Will you buy on online?", ask "What kind of online websites do you plan to use?")

[Context]
The Context provides you with information on whether previous questions and answers exist.

First_QA: {first_question_and_answer}
Second_QA: {second_question_and_answer}

[Output]
Only provide your question in a single sentence (at most 10 words)."""

# Augmentation prompt for generating intention variations
AUGMENTATION_PROMPT_TEMPLATE = """You are an assistant that expands simple activity descriptions into diverse alternatives.

[Guideline]
Given a simple activity like "Find a jacket for men", generate 10 variations of the activity description.

Rules:
- Use the clarification questions you had with the user.
- The output must be in valid JSON format (keys: "1" to "10").
- Keep the sentence concise (at most 9 words).

Output structure:
- Variations 1–3: Broader or more generalized expressions of the activity.
- Variations 4–6: Slightly more specific or rephrased versions, using only the original information.
- Variations 7–10: Realistic user actions likely performed when carrying out the activity (e.g., read reviews, search on shopping apps).

[Example]
Activity: "Find a jacket for men"

```json
{{
    "1": "Shopping",
    "2": "Online shopping",
    "3": "Browse for clothing",
    "4": "Search for jackets",
    "5": "Look up men's jackets in an online store",
    "6": "Navigate a shopping app to find a jacket",
    "7": "Use a search engine to locate jackets",
    "8": "Read customer reviews on shopping sites",
    "9": "Compare jacket prices across online stores",
    "10": "Watch review videos of jackets on YouTube",
}}


[Clarifiaction questions]
Below is a list of clarification questions. 
This provides a hint on the specific behaviors of the user, so augment the intention based on the information.
For example, if the user clarified that the user will buy a jacket at a specific website, you can include it (like, to 8-10). 

{clarification_block}


[Input]
Activity: "{stated_intention}"

Output only the JSON object, no additional text."""

# Reflection prompt
REFLECTION_PROMPT_TEMPLATE = """You are a helpful assistant designed to reflect on your predictions with user's feedback.
Your goal is to output an implicit intention of the user, which has not been stated but should have been captured, to explain the user's activity in a way that aligns with the user's current task.
You need to analyze a situation where the user's feedback toward your previous judgment. 
For example, given a stated intention "Write a research report" and a screen description "Chatting with a colleague on Slack", you may have classified it as a distraction with the rationale "This appears to be casual conversation, not task-related."
Then, the user might provide 'disklike' to your judgement.
Therefore, you should reflect and output an implicit intention of the user, such as "Discuss with a colleague for sources for the report", which explains the user's activity in a way that aligns with the user's current task.

[Stated Intention]
{stated_intention}

[Your Response]
Low distraction score of output(0.0) indicates that you judged that the user's activity aligns with the user's intention.
High distraction score of output(1.0) indicates that you judged that the user's activity does not align with the user's intention.
{assistant_response}

[User Feedback]
{user_feedback}

Now, reflect on why the user might have expressed such feedback. 
Think about what **implicit intention** or subtle task-related reasoning the user might have had, which you did not consider. 
Then, build a policy adjustment strategy to better align your future judgments with the user's task.
Esepcailly, the policy adjustment should follow the format of "Output high/l ow alignment (low/high distraction score output) for [specific activity with detailed contents] when detected"

Respond in **JSON format** with two keys:
- "analysis_assistant_response": judge whether your previous response was whether high alignment (low output distraction score 0.0) or low alignment (high output distraction score 1.0) with the user's intention.
- "user_activity_description": a short sentence describing the activity shown in the screen image in noun form (e.g., "YouTube homepage with diverse video thumbnails", within 20 words).
- "analysis_user_feedback": two short sentences (within 10 words each) explaining what/why the user liked/disliked on your judgement of alignment. (e.g., "User expressed good/bad. The reason is because...")
- "user_implicit_intention_prediction": a short sentence (within 10 words) predicting an implicit intention of the user that aligns with the user's current activity, starting with a verb (e.g., "Watch review before purchase")

Only return the JSON object. Do not include any explanation or prefix text"""

MESSAGE_INSTRUCTION = """
[Message Language]
intention: {task_name}
Respond in {language}.

[Important Notes for Message Generation]
When multiple programs are visible, assume the 'frontmost app info' is the user's main focus and generate your message accordingly.
If you can't get any information from the screen, use the 'frontmost' or 'URL' data to create a relevant message.

[Message Generation Guidelines]
When creating notifications, follow these guides:
React to the user's activity with a friendly, supportive tone.
Briefly and clearly mention what the user is doing.
Maintain a positive and encouraging vibe overall.
Use short, warm messages to help the user stay in their flow.

When the user is focused, share an observation and give them a boost.
Examples:
"Wow, you're really in the zone with {{details}}! Keep it up."
"You're making great progress on {{details}}. Looking good!"
"This focus on {{details}} is exactly what you need. Awesome work."

When the user is distracted, gently guide them back and offer a specific suggestion.
Examples:
"Whoops, looks like {{details}} is pulling your attention away. It happens!"
"It's easy to get sidetracked by {{details}}. Ready to jump back into {{detailed suggestion}}?"
"Let's gently bring our focus back to {{detailed suggestion}}, shall we?"
"That {{detailed suggestion}} is waiting for you. How about we give it another look?"

"""


def build_intention_analysis_prompt(
    task_name="No task specified",
    use_clarification=True,
    clarification_intentions=None,
    use_reflection=True,
    reflection_intentions=None,
    reflection_rules=None,
    use_context=True,
    use_formatted_prediction=False,
    use_probabilistic_score=True,
    message_to_user=True,
    frontmost_app=None,
    opacity=None,
):
    """
    Build the intention analysis prompt with various options
    """
    print(f"[LLM] Building prompt for task: {task_name}")

    prompt_text = ""

    # Add general instruction
    prompt_text += GENERAL_INSTRUCTION.format(task_name=task_name) + "\n\n"

    # Add clarification context if enabled and data is available
    if (
        use_clarification
        and clarification_intentions
        and len(clarification_intentions) > 0
    ):
        list_of_augmented_intention = "\n".join(
            [f"- {intent}" for intent in clarification_intentions]
        )
        clarification_context = CLARIFICATION_CONTEXT.format(
            task_name=task_name, list_of_augmented_intention=list_of_augmented_intention
        )
        prompt_text += clarification_context + "\n\n"

    # Add learning from feedback context if enabled and data is available
    if use_reflection and reflection_intentions and len(reflection_intentions) > 0:
        list_of_learned_intentions = "\n".join(
            [f"- {intent}" for intent in reflection_intentions]
        )
        reflection_context = LEARNING_FROM_FEEDBACK_CONTEXT.format(
            task_name=task_name, list_of_learned_intentions=list_of_learned_intentions
        )
        prompt_text += reflection_context + "\n\n"

    # Add context instruction
    if use_context:
        if use_formatted_prediction:
            prompt_text += CONTEXT_INSTRUCTION_WITH_FORMAT + "\n\n"
        else:
            prompt_text += CONTEXT_INSTRUCTION_WITHOUT_FORMAT + "\n\n"

    # Add scoring guidelines
    if use_probabilistic_score:
        prompt_text += SCORING_GUIDELINE_PROBABILITY + "\n\n"
    else:
        prompt_text += SCORING_GUIDELINE_DISCRETE + "\n\n"

    # Add reflection rules
    if use_reflection and reflection_rules and len(reflection_rules) > 0:
        list_of_learned_rules = "\n".join([f"- {rule}" for rule in reflection_rules])
        rule_context = ADJUST_FROM_FEEDBACK_CONTEXT.format(
            task_name=task_name, list_of_learned_rules=list_of_learned_rules
        )
        prompt_text += rule_context + "\n\n"

    # Add output format
    prompt_text += "[Output Format]\n"
    prompt_text += "{\n"
    if use_formatted_prediction:
        prompt_text += '"intent prediction": "",  // Predict the intent of the user using the specific format: [Verb] + [Object] + (Optional) [Context] (e.g., "Write an email to Amy for Tuesday meeting" or "Watch tutorial on YouTube).\n'
    prompt_text += '"reason": "",  // One clear sentence explicitly mentioning its relevance or irrelevance to the task.\n'
    if use_probabilistic_score:
        prompt_text += '"output": 0.0,  // Score in {0.0, 0.2, 0.4, 0.6, 0.8, 1.0}, where 0.0 is fully aligned and 1.0 is completely unrelated.\n'
    else:
        prompt_text += (
            '"output": 1,  // 0-1 scoring level 0 (aligned), 1 (distracted)\n'
        )

    # Add message field for user feedback
    if message_to_user:
        prompt_text += '"message": ""  // notification message (max 40 chars)\n'
    prompt_text += "}\n\n"

    if message_to_user:
        language_hint = _infer_language(task_name)
        prompt_text += (
            MESSAGE_INSTRUCTION.format(task_name=task_name, language=language_hint)
            + "\n\n"
        )

    # Add important rules
    prompt_text += IMPORTANT_RULES

    # Add frontmost app information if available
    if frontmost_app:
        app_name = frontmost_app.get("app_name", "Unknown")
        url = frontmost_app.get("url", "")

        app_info = f"\n\n[CURRENT SCREEN CONTEXT]\n"
        app_info += f"Currently active application: {app_name}"

        if url:
            app_info += f"\nCurrent URL/Address: {url}"
        else:
            app_info += f"\nCurrent URL/Address: Not available (not a web browser)"

        app_info += (
            f"\n\nPlease analyze the screenshot considering this context information."
        )

        # Add to the end of the prompt
        prompt_text += app_info
        print(f"[PROMPT] Added frontmost app info: {app_name} | URL: {url}")

    # Note: Opacity information is now sent as separate JSON field, not in prompt text

    return prompt_text


def get_clarification_prompt_template():
    """Get the clarification prompt template"""
    return CLARIFICATION_PROMPT_TEMPLATE


def get_augmentation_prompt_template():
    """Get the augmentation prompt template"""
    return AUGMENTATION_PROMPT_TEMPLATE


def get_reflection_prompt_template():
    """Get the reflection prompt template"""
    return REFLECTION_PROMPT_TEMPLATE


def format_clarification_prompt(stated_intention, first_qa="", second_qa=""):
    """Format the clarification prompt with user intention and previous Q&As"""
    return CLARIFICATION_PROMPT_TEMPLATE.format(
        stated_intention=stated_intention,
        first_question_and_answer=first_qa,
        second_question_and_answer=second_qa,
    )


def format_augmentation_prompt(stated_intention, clarification_block=""):
    """Format the augmentation prompt with intention and clarification history"""
    return AUGMENTATION_PROMPT_TEMPLATE.format(
        stated_intention=stated_intention, clarification_block=clarification_block
    )


def format_reflection_prompt(stated_intention, assistant_response, user_feedback=""):
    """Format the reflection prompt for Distracted + Bad feedback"""
    return REFLECTION_PROMPT_TEMPLATE.format(
        stated_intention=stated_intention,
        assistant_response=assistant_response,
        user_feedback=user_feedback,
    )
