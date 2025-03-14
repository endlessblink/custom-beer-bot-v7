# WhatsApp Group Summary Bot

A Python bot that connects to WhatsApp groups via Green API, retrieves messages, and generates summaries using OpenAI's language models.

## Features

- Connect to WhatsApp via Green API
- List and select WhatsApp groups
- Retrieve messages from selected groups
- Generate summaries using OpenAI GPT models
- Send summary messages back to groups
- Configurable summarization intervals
- **Interactive Menu Interface** - For easy management and control
- **Comprehensive Testing & Maintenance Tools** - For ensuring system integrity

## Future Features

- Remote management via Discord/Telegram
- Training on group content for Q&A capabilities
- Member scoring system based on parameters
- Analytics dashboard for group activity

## Installation

### Prerequisites

- Python 3.8 or higher
- Green API account and credentials
- OpenAI API key
- WhatsApp account connected to Green API

### Setup

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd whatsapp-summary-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create an `.env` file with your configuration:
   ```
   # Green API Configuration  
   GREEN_API_ID_INSTANCE="your-instance-id"  
   GREEN_API_TOKEN="your-api-token"  
   GREEN_API_BASE_URL="https://api.greenapi.com"
   GREEN_API_DELAY=1000  
   
   # OpenAI Configuration
   OPENAI_API_KEY="your-openai-api-key"
   OPENAI_MODEL="gpt-4"
   OPENAI_MAX_TOKENS=2000
   
   # Bot Configuration
   BOT_SUMMARY_INTERVAL=24
   BOT_TARGET_LANGUAGE="hebrew"
   BOT_DRY_RUN=false
   BOT_LOG_LEVEL="INFO"
   BOT_RETRY_DELAY=60
   BOT_MAX_RETRIES=3
   BOT_MESSAGE_COOLDOWN=300
   
   # Group IDs (comma-separated list)
   WHATSAPP_GROUP_IDS=""
   ```

5. Configure your WhatsApp instance in Green API dashboard

6. Run the system health check to verify your setup:
   ```bash
   python tools/system_health_check.py
   ```

## Usage

### Running the Bot

Start the bot with:

```bash
python main.py
```

For interactive mode with menu interface:

```bash
python summary_menu.py
```

### Interactive Menu System

The bot features a robust interactive menu system that is a **critical component** of the application. This menu provides:

- Easy navigation and control without needing to modify code
- Access to all bot functionality through a simple interface
- Ability to generate summaries on demand
- Settings management
- Debug and diagnostic tools

The menu system is designed to be resilient and will function even if certain components of the bot are unavailable. This ensures you always have a way to interact with and control the bot.

To test the menu functionality:

```bash
python utils/menu/test_menu.py
```

### Commands

The bot supports the following commands within WhatsApp groups:

- `!help` - Display help information
- `!summary` - Generate a summary on demand
- `!status` - Check bot status and configuration
- `!interval [hours]` - Set the summary interval (admin only)

### Maintenance and Testing Tools

The project includes comprehensive tools to ensure system integrity and facilitate maintenance:

```bash
# Central maintenance hub with access to all tools
python tools/maintenance_hub.py

# Run core functionality tests
python tests/test_core_functionality.py

# Check menu version compatibility
python utils/menu/version_check.py

# System health check
python tools/system_health_check.py

# Generate a bug report for troubleshooting
python tools/bug_report_generator.py
```

These tools should be run regularly, especially after making changes to the code or updating dependencies.

## Project Structure

```
.
├── config/             # Configuration management
├── docs/               # Documentation files
│   └── architecture.md # System architecture documentation
├── green_api/          # Green API client implementation
├── llm/                # LLM integration (OpenAI)
├── models/             # Data models
├── processor/          # Message processing logic
├── scheduler/          # Scheduling and timing functions
├── storage/            # Storage interfaces (future)
├── tests/              # Test suite for core functionality
├── tools/              # Maintenance and diagnostic tools
├── utils/              # Utility functions
│   └── menu/           # Core menu functionality (CRITICAL)
├── .env                # Environment variables
├── main.py             # Main entry point
├── summary_menu.py     # Interactive menu interface
└── requirements.txt    # Python dependencies
```

## Configuration

The bot behavior can be configured through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GREEN_API_ID_INSTANCE` | Green API instance ID | - |
| `GREEN_API_TOKEN` | Green API API token | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OPENAI_MODEL` | OpenAI model to use | gpt-4 |
| `BOT_SUMMARY_INTERVAL` | Hours between summaries | 24 |
| `BOT_TARGET_LANGUAGE` | Summary language | hebrew |
| `WHATSAPP_GROUP_IDS` | Comma-separated group IDs | - |

## Documentation

Detailed documentation is available in the `docs/` directory:

- [System Architecture](docs/architecture.md)
- [Current Functionality](docs/current_functionality.md)
- [Product Requirements Document](docs/product_requirements_document.md)
- [Application Flow Document](docs/app_flow_document.md)
- [Application Functionality Document](docs/app_functionality_document.md)
- [Technical Architecture](docs/technical_architecture.md)

### Maintenance Tools Documentation

All maintenance and testing tools have their own documentation:

- [Maintenance Tools Guide](tools/README.md)
- [Menu Module Documentation](utils/menu/README.md)

## Testing and Quality Assurance

To ensure the bot functions correctly over time, the project includes a comprehensive testing framework:

1. **Unit Tests**: Test individual components in isolation
2. **Menu Compatibility Checks**: Verify that the menu works with the current system
3. **System Health Checks**: Validate the health of all critical system components
4. **Bug Report Generation**: Create detailed reports for troubleshooting

These tools can be accessed through the central Maintenance Hub:

```bash
python tools/maintenance_hub.py
```

## Security Considerations

- API keys and tokens are stored in environment variables
- Message content is processed but not persistently stored
- The bot follows WhatsApp's terms of service
- Message sending is carefully controlled to prevent spam

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Important Note for Contributors

The interactive menu system in `utils/menu/` is a critical component of this application. Please ensure any changes:

1. Do not break the core menu functionality
2. Maintain backward compatibility
3. Are thoroughly tested using the provided test script
4. Are well-documented

Before submitting any Pull Request, please run the complete test suite:

```bash
python tests/test_core_functionality.py
```

And verify compatibility with the system health check:

```bash
python tools/system_health_check.py
```

## Version Management

After significant changes or feature additions, create a stable version tag:

```bash
git tag v1.x.x-stable
git push origin v1.x.x-stable
```

This helps track known working versions of the bot.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Green API](https://green-api.com/) for WhatsApp API access
- [OpenAI](https://openai.com/) for language model APIs 