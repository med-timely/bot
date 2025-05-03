# Medication Reminder Bot

[![Telegram Bot API](https://img.shields.io/badge/Telegram_Bot_API-2.0+-blue.svg)](https://core.telegram.org/bots/api)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A smart Telegram bot for medication schedule management with advanced reminder capabilities and adherence tracking.

## Table of Contents

- [Medication Reminder Bot](#medication-reminder-bot)
  - [Table of Contents](#table-of-contents)
  - [Features 🩺](#features-)
  - [Technologies ⚙️](#technologies-️)
    - [Architecture Overview](#architecture-overview)
  - [Usage 💊](#usage-)
    - [Key Commands](#key-commands)
    - [Workflow Example](#workflow-example)
  - [Contributing 🤝](#contributing-)
  - [License 📄](#license-)
  - [Contact 📬](#contact-)

## Features 🩺

- **Schedule Management**
  - Create medication schedules with custom doses and frequencies
  - Set start delays and durations
  - Automatic timezone detection
- **Smart Reminders**
  - AI-powered natural language input parsing
  - Celery-based async notifications
  - Multi-timezone support
- **Dose Tracking**
  - Confirmations with time validation
  - Missed dose detection
  - Adherence history reports

```bash
/schedule "Take Aspirin 1 tablet 2 times daily for 7 days starting tomorrow"
```

## Technologies ⚙️

- **Backend**
  - Python 3.11+
  - Aiogram 3.x (Async Telegram Bot Framework)
  - Celery + Redis (Task Queue)
  - SQLAlchemy 2.0 (ORM)
  - MariaDB (Database)
- **Infrastructure**
  - Docker Compose
  - GitHub Actions (CI/CD)
- **Additional Components**
  - OpenRouter (Natural Language Parsing)
  - Timezonefinder (Location Detection)

### Architecture Overview

The bot uses a service-oriented architecture with key components:
1. **Bot Core**: Handles Telegram interactions using Aiogram
2. **Schedule Service**: Manages medication schedules and dose tracking
3. **LLM Service**: Provides natural language processing capabilities
4. **Database**: Stores user data and schedule information using MariaDB
5. **Redis**: Used for FSM storage and task queuing

The bot initialization process involves:
1. Setting up Redis storage for state management
2. Initializing the LLM service for natural language processing
3. Configuring middleware for database and user management
4. Registering command and schedule handlers

This architecture allows for scalable and maintainable medication management.

## Usage 💊

### Key Commands

| Command     | Description                    | Example                                         |
| ----------- | ------------------------------ | ----------------------------------------------- |
| `/start`    | Initial setup wizard           | -                                               |
| `/schedule` | Create new medication schedule | `/schedule "Paracetamol 500mg 3x daily 5 days"` |
| `/taken`    | Log completed doses            | `/taken` → Select medication                    |
| `/history`  | Generate adherence report      | `/history 7` (Last 7 days)                      |
| `/list`     | Show active medications        | -                                               |
| `/me`       | Show your profile information  | -                                               |
| `/help`     | Show help message              | -                                               |

### Workflow Example

1. **User Onboarding**
   ```bash
   /start → Accept Privacy Policy → Set Timezone → Add First Medication
   ```
2. **Medication Management**
   ```bash
   /schedule "Paracetamol 500mg 3x daily 5 days"
   ```
3. **Daily Interaction**
   ```bash
   [Bot] "Time to take Paracetamol (500mg)"
   [User] Click "💊 Paracetamol (500mg)"
   ```

## Contributing 🤝

We welcome contributions! Please follow these steps:
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License 📄

Distributed under the [Apache License 2.0](LICENSE) for more information.

## Contact 📬

**Project Maintainer** - [capcom6](https://github.com/capcom6)  
**Email** - [support@medtimely.ru](mailto:support@medtimely.ru)
