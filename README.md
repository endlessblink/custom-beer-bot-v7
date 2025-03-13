# WhatsApp Group Summary Bot

A Python bot that connects to WhatsApp groups via Green API, retrieves messages, and generates summaries using OpenAI's language models.

## Features

- Connect to WhatsApp via Green API
- List and select WhatsApp groups
- Retrieve messages from selected groups
- Generate summaries using OpenAI GPT models
- Send summary messages back to groups
- Configurable summarization intervals

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

## Usage

### Running the Bot

Start the bot with:

```bash
python main.py
```

### Commands

The bot supports the following commands within WhatsApp groups:

- `!help` - Display help information
- `!summary` - Generate a summary on demand
- `!status` - Check bot status and configuration
- `!interval [hours]` - Set the summary interval (admin only)

## Project Structure

```
.
├── config/             # Configuration management
├── docs/               # Documentation files
├── green_api/          # Green API client implementation
├── llm/                # LLM integration (OpenAI)
├── models/             # Data models
├── processor/          # Message processing logic
├── scheduler/          # Scheduling and timing functions
├── storage/            # Storage interfaces (future)
├── utils/              # Utility functions
├── .env                # Environment variables
├── main.py             # Main entry point
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

- [Product Requirements Document](docs/product_requirements_document.md)
- [Application Flow Document](docs/app_flow_document.md)
- [Application Functionality Document](docs/app_functionality_document.md)
- [Technical Architecture](docs/technical_architecture.md)

## Security Considerations

- API keys and tokens are stored in environment variables
- Message content is processed but not persistently stored
- The bot follows WhatsApp's terms of service

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Green API](https://green-api.com/) for WhatsApp API access
- [OpenAI](https://openai.com/) for language model APIs 