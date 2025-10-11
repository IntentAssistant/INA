# INA App – Architecture

## System Overview
- **INA App** (`src/app.py`) embeds a hidden `rumps.App`, boots a `QApplication`, and wires core services (storage, prompts, notifications, dashboard, thread manager).
- **ThreadManager** (`src/manager.py`) schedules capture/analysis timers, manages capture metadata, orchestrates `LLMAnalysisThread`s, and feeds results back into storage, dashboard, and notifications.
- **Dashboard** (`src/ui/dashboard.py`) is the primary PyQt UI for setting intentions, presenting LLM feedback, collecting user responses, and bridging to history/feedback subsystems.
- **NotificationManager** (`src/ui/notification.py`) delegates toast + sound delivery to `desktop_notifier` while consulting user preferences from `APIConfigManager`.
- **LocalStorage** (`src/logging/storage.py`) manages the on-disk dataset (`~/INA_Data`) for logs, session transcripts, reflections, and feedback.
- **DirectLLMClient** (`src/utils/direct_llm_client.py`) performs signed HTTPS calls to OpenAI/Gemini, handling certificate extraction when bundled.
- **APIConfigManager** (`src/config/api_config.py`) persists user settings (provider, keys, capture intervals, display selection, notification flags) under `~/.intention_app`.
- **PromptConfig** (`src/config/prompt_config.py`) composes prompts (base, clarification, reflection) using persisted data.

## High-Level Flow

```mermaid
flowchart LR
    User["User task & feedback"]
    Dashboard["Dashboard (PyQt)"]
    Manager["ThreadManager"]
    Capture["Screen capture<br/>& context"]
    LLM["LLM API"]
    Storage["Local storage"]
    Notify["Notifications"]

    User --> Dashboard
    Dashboard --> Manager
    Manager --> Capture
    Capture --> Manager
    Manager --> LLM
    LLM --> Manager
    Manager --> Dashboard
    Manager --> Storage
    Manager --> Notify
```

## Capture → Insight Flow

```mermaid
sequenceDiagram
    participant User
    participant Dash as Dashboard
    participant TM as ThreadManager
    participant LLMThr as LLMAnalysisThread
    participant Client as DirectLLMClient
    participant LLM as LLM API
    participant Notify as NotificationManager
    participant Store as LocalStorage

    User->>Dash: Start capture
    Dash->>TM: capture_started signal
    TM->>TM: capture_timer fires
    TM->>TM: _capture_screen_internal()
    TM->>Store: cache metadata / persist logs
    TM->>LLMThr: spawn + pass prompt/context
    LLMThr->>Client: analyze_screen()
    Client->>LLM: HTTPS request (image + prompt)
    LLM-->>Client: JSON response
    Client-->>LLMThr: parsed result
    LLMThr-->>TM: analysis_complete(result)
    TM->>Store: save_llm_result()
    TM->>Dash: analysis_callback(result)
    TM->>Notify: show_notification(state)
```

## Component Notes
- **main.py** sets up dual logging (console + file) before delegating to `IntentionalComputingApp`.
- **Screen capture** uses PyQt’s `grabWindow(0)` with in-memory JPEG compression to avoid disk writes.
- **ScreenLockDetector** (`src/utils/screen_lock_detector.py`) prevents capture/analysis while macOS is locked.
- **Activity detection** (`src/utils/activity.py`) captures frontmost application and browser URLs via AppleScript.
- **Feedback loop** is managed by the dashboard + `FeedbackManager`, enriching future prompts with reflections.
- **Auto-launch** handled via `ensure_login_item()` (`src/utils/launch_at_login.py`) scheduled after initial load.

## Feedback System

The reflection subsystem learns from user “❌” feedback to improve subsequent analyses.

### System Architecture

```mermaid
graph LR
    subgraph "UI Layer"
        A["Dashboard<br/>❌ Incorrect Button"]
        B["Feedback UI<br/>Visual Response"]
    end

    subgraph "Processing Layer"
        C["FeedbackManager<br/>Orchestration"]
        D["ReflectionThread<br/>Background Processing"]
    end

    subgraph "Data Layer"
        E["ThreadManager<br/>Memory Storage"]
        F["PromptConfig<br/>File Storage"]
        G["LocalStorage<br/>Persistent Data"]
    end

    subgraph "External Services"
        H["LLM API<br/>Reflection Analysis"]
    end

    subgraph "Integration Layer"
        I["Prompt System<br/>Context Injection"]
        J["Future LLM Calls<br/>Enhanced Context"]
    end

    A --> C
    A --> B
    C --> D
    D --> H
    D --> F
    D --> E
    E --> I
    F --> I
    I --> J
    J --> A
```

### Reflection Flow Diagram

```mermaid
graph TD
    A["❌ User Marks Response Incorrect<br/>Dashboard.handle_feedback_click('bad')"] --> B{"Data Available?<br/>feedback_manager &&<br/>last_llm_response &&<br/>current_task"}

    B -->|No| C["Log Warning<br/>Skip Reflection"]
    B -->|Yes| D["Extract Data<br/>• task_name<br/>• previous_reason<br/>• image_path"]

    D --> E["FeedbackManager<br/>process_feedback()"]
    E --> F["Generate Reflection Prompt<br/>format_reflection_prompt()"]
    F --> G["Create ReflectionThread<br/>Background QThread"]

    G --> H["Generate Reflection via LLM API<br/>analyze_reflection()"]
    H --> I{"LLM Response<br/>Success?"}

    I -->|Error| J["Handle Error<br/>Log & Continue"]
    I -->|Success| K["Parse JSON Response<br/>• image_description<br/>• reflected_implicit_intention"]

    K --> L["Save to Storage<br/>prompt_config.save_reflection()"]
    L --> M["Format Reflection Entry<br/>'description': 'intention'"]
    M --> N["Update Dashboard Cache<br/>current_reflection_data.append()"]
    N --> O["Update ThreadManager<br/>set_reflection_data()"]

    O --> P["Memory Storage<br/>current_reflection_data"]
    P --> Q["Future Prompt Integration<br/>get_formatted_prompt()"]
    Q --> R["Enhanced LLM Context<br/>use_reflection=True"]

    R --> S["Improved Future Responses<br/>Learning Loop Complete"]
```

### Reflection Sequence

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant D as Dashboard
    participant FM as FeedbackManager
    participant RT as ReflectionThread
    participant LLM as LLM API
    participant PC as PromptConfig
    participant TM as ThreadManager

    Note over U,TM: Incorrect Feedback Reflection Sequence

    U->>D: Tap ❌ Incorrect Button
    D->>D: Show visual feedback (red highlight)

    alt Data Available
        D->>D: Extract task_name / previous_reason / image_path
        D->>FM: process_feedback()
        FM->>FM: format_reflection_prompt()
        FM->>RT: start ReflectionThread
        RT->>RT: encode image + prepare payload
        RT->>LLM: POST reflection request

        alt Success
            LLM-->>RT: JSON {description, intention}
            RT->>FM: reflection_complete
            FM->>PC: save_reflection()
            FM->>D: update reflection cache
            FM->>TM: set_reflection_data()
            FM->>D: feedback_processed
        else Error
            LLM-->>RT: error payload
            RT->>FM: reflection_error
            FM->>D: log + continue
        end

        RT->>FM: finished (cleanup)
    else Missing Data
        D->>D: Log warning and exit
    end

    D->>U: Hide feedback buttons (delay)

    loop Future LLM Analyses
        TM->>TM: get_formatted_prompt()
        alt Reflection data exists
            TM->>TM: include reflection context
        else No reflection
            TM->>TM: use standard prompt
        end
    end
```

### Key Touchpoints
- Dashboard `handle_feedback_click("bad")`: `src/ui/dashboard.py:1477-1640`
- `FeedbackManager.process_feedback()`: `src/ui/feedback_manager.py:463-535`
- `ReflectionThread`: handles background LLM calls and emits success/error signals.
- `PromptConfig.save_reflection()`: persists learned intent descriptions for reuse.
- `ThreadManager.set_reflection_data()`: updates in-memory context for future analyses.
