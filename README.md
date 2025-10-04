# AIM (Aligned Intention Monitoring)

AIM is an AI-powered focus management application that helps users practice intentional computing by monitoring the alignment between their activities and intentions. It captures screens periodically and analyzes whether the user's current activity aligns with their set goals using LLM analysis, providing real-time feedback.

## Key Features

- **Real-time Screen Analysis**: Periodically captures screens and analyzes current activities
- **AI-powered Intent Analysis**: Uses LLM to analyze alignment between user activities and set goals
- **3 App Modes**: Supports FULL(Purple), REMINDER(Blue), and BASIC(Orange) modes
- **Real-time Feedback**: Provides immediate notifications and advice based on focus levels
- **Learning System**: Improves analysis accuracy through user feedback
- **Multi-language Support**: Supports Korean/English UI
- **Session Management**: Tracks work sessions and manages history

## Software Architecture

### Overall System Architecture

```mermaid
graph TB
    subgraph "Entry Point"
        A[main.py]
    end
    
    subgraph "Core Application"
        B[IntentionalComputingApp<br/>rumps.App]
        C[ThreadManager<br/>Core Logic]
    end
    
    subgraph "UI Layer"
        D[Dashboard<br/>PyQt6 UI]
        E[Menu<br/>macOS Menu Bar]
        F[Notification<br/>System Notifications]
        G[Dialogs<br/>Settings & Popups]
    end
    
    subgraph "Analysis Engine"
        H[LLM Analysis<br/>Image + Context]
        I[Activity Monitor<br/>App & URL Tracking]
        J[Screen Capture<br/>Periodic Screenshots]
    end
    
    subgraph "Data Management"
        K[Local Storage<br/>SQLite + Files]
        L[User Config<br/>JSON Settings]
        M[Prompt Config<br/>LLM Prompts]
        N[Cloud Upload<br/>Optional Sync]
    end
    
    subgraph "External Services"
        O[LLM API Endpoint<br/>Current: Separate Backend Required<br/>Future: Direct API Key Integration]
    end
    
    A --> B
    B --> C
    B --> D
    B --> E
    C --> F
    C --> G
    C --> H
    C --> I
    C --> J
    H --> O
    C --> K
    C --> L
    C --> M
    K --> N
    
    D -.-> C
    E -.-> C
    F -.-> C
    G -.-> C
```

### Detailed Module Structure

```mermaid
graph LR
    subgraph "src/"
        subgraph "config/"
            A1[constants.py<br/>App Configuration Constants]
            A2[user_config.py<br/>User Settings]
            A3[prompt_config.py<br/>LLM Prompts]
            A4[language.py<br/>Multi-language Support]
        end
        
        subgraph "ui/"
            B1[dashboard.py<br/>Main UI]
            B2[menu.py<br/>Menu Bar]
            B3[notification.py<br/>Notification System]
            B4[dialogs.py<br/>Settings Dialogs]
            B5[feedback_manager.py<br/>Feedback Processing]
            B6[history_manager.py<br/>Session History]
        end
        
        subgraph "utils/"
            C1[activity.py<br/>App/URL Detection]
            C2[llm_analysis.py<br/>LLM Communication]
            C3[image_comparison.py<br/>Image Processing]
            C4[screen_lock_detector.py<br/>Screen Lock Detection]
        end
        
        subgraph "logging/"
            D1[storage.py<br/>Local Storage]
            D2[cloud.py<br/>Cloud Upload]
        end
        
        E1[app.py<br/>Main Application]
        E2[manager.py<br/>Thread Manager]
    end
```

### Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant D as Dashboard
    participant M as ThreadManager
    participant C as Screen Capture
    participant L as LLM Analysis
    participant S as Storage
    participant N as Notification
    
    U->>D: Set Goal & Start
    D->>M: Request Capture Start
    
    loop Periodic Analysis (2 second intervals)
        M->>C: Capture Screen
        C->>M: Return Screenshot
        M->>L: Request LLM Analysis (Image + Context)
        L-->>LLM API: Analysis Request
        LLM API-->>L: Focus Score & Message
        L->>M: Return Analysis Result
        M->>S: Store Result
        M->>N: Show Notification if Needed
        N->>U: Feedback Notification
    end
    
    U->>D: Provide Feedback (👍/👎)
    D->>M: Send Feedback
    M->>S: Store Learning Data
```

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

## System Requirements

- **OS**: macOS 10.15 or later
- **Python**: 3.8 or later
- **Required Permissions**: 
  - Screen Recording Permission
  - Accessibility Permission
  - Notification Permission

## Configuration

### API Keys Setup

AIM now supports direct LLM API integration! No separate backend server required.

#### In-App Configuration (Recommended)

The easiest way to configure API settings is through the built-in settings interface:

1. **Launch AIM** - If no API keys are configured, you'll see a welcome dialog
2. **Click "Configure Now"** or access it later via **Settings > User Settings > Configure API Settings**
3. **Choose your provider** (OpenAI GPT or Google Gemini)
4. **Enter your API key** and select a model
5. **Test your configuration** using the built-in validation
6. **Save settings** - Your configuration is stored securely on your device

#### Environment Variables (Advanced)

You can also use environment variables if preferred:

**OpenAI GPT (Primary)**
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

**Google Gemini (Alternative)**
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

**For permanent setup, add to your shell profile:**
```bash
# For bash users
echo 'export OPENAI_API_KEY="your-key"' >> ~/.bashrc

# For zsh users  
echo 'export OPENAI_API_KEY="your-key"' >> ~/.zshrc
```

#### Available Models

**OpenAI GPT:**
- GPT-4o (Latest, Recommended)
- GPT-4o Mini (Faster, Cheaper)
- GPT-4 Turbo (Previous)

**Google Gemini:**
- Gemini 1.5 Pro (Recommended)
- Gemini 1.5 Flash (Faster)
- Gemini Pro Vision (Legacy)

#### Get API Keys
- **OpenAI**: https://platform.openai.com/api-keys
- **Gemini**: https://ai.google.dev/gemini-api/docs/api-key

> **Note**: The app will use your selected provider, with automatic fallback to any configured provider if the primary one fails.

## App Modes

The application comes in three versions for experimental research purposes:

- **FULL (Purple)**: **Main AIM Application** - Provides complete functionality with real-time feedback and notifications
- **REMINDER (Blue)**: **Control Group** - Provides only periodic reminder notifications for comparison studies
- **BASIC (Orange)**: **Baseline Group** - Performs basic monitoring with minimal UI feedback for comparison studies

> **Note**: Purple is the primary AIM application, while Blue and Orange versions are designed for experimental comparison and research studies.

## License

This project was developed for research purposes.
