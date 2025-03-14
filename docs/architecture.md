# WhatsApp Group Summary Bot - System Architecture

## Overview

The WhatsApp Group Summary Bot is designed to provide automated summaries of WhatsApp group conversations. The system connects to WhatsApp via the Green API, processes messages, generates summaries using OpenAI's language models, and optionally stores these summaries in a Supabase database.

This document outlines the high-level architecture, component interactions, and design decisions that have shaped the current implementation. It serves as a reference for understanding the system's structure, which must be preserved across all versions.

## Architectural Principles

The bot's architecture adheres to the following principles:

1. **Modularity**: Components are separated by responsibility and can be developed, tested, and maintained independently.
2. **Resilience**: The system gracefully handles failures in external services and networks.
3. **Configurability**: Key parameters can be adjusted without code changes.
4. **Independence**: Core functionality works with minimal dependencies.
5. **Usability**: The system provides a user-friendly interface for all operations.

## System Components

The system is composed of the following major components:

### 1. Interactive Menu System

Located in `summary_menu.py` and `utils/menu/core_menu.py`, this component provides the user interface for interacting with the bot. It's designed to:

- Present a clear hierarchy of options
- Guide users through the process of generating summaries
- Provide access to settings and diagnostic features
- Ensure user commands are validated before execution
- Handle errors gracefully and provide meaningful feedback

The interactive menu is a critical component that must remain operational across all versions.

### 2. WhatsApp Integration

Located in the `green_api/` directory, this component handles all communication with WhatsApp through Green API:

- `client.py`: Implements the core API client for making requests to Green API
- `group_manager.py`: Provides group management capabilities and message retrieval

Key features include:
- Retrieving message history from specified groups
- Listing available groups for selection
- Safety mechanisms to prevent accidental message sending
- Error handling for API failures

### 3. Message Processing

Located in the `processor/` directory, this component is responsible for:

- Extracting relevant information from raw WhatsApp messages
- Filtering and normalizing message content
- Preparing data for summary generation
- Supporting multiple languages for processing

### 4. Language Model Integration

Located in the `llm/` directory, this component interacts with OpenAI's API to generate summaries:

- `openai_client.py`: Handles communication with OpenAI's APIs
- Configurable model selection and parameters
- Error handling for API failures
- Token usage optimization

### 5. Data Storage

Located in the `db/` directory, this component provides optional storage capabilities:

- `supabase_client.py`: Implements integration with Supabase for storing summaries
- Support for retrieving and displaying previous summaries
- Designed to be optional (the bot functions without database connectivity)

### 6. Configuration Management

Located in the `config/` directory, this component manages application settings:

- Loading environment variables
- Providing defaults for missing configurations
- Supporting user-specific settings through `user_settings.json`

## Data Flow

The typical data flow through the system is:

1. **User Selection**: Through the interactive menu, the user selects a WhatsApp group and time period.
2. **Message Retrieval**: The Green API client fetches messages from the selected group.
3. **Message Processing**: The processor extracts and normalizes the relevant information.
4. **Summary Generation**: The OpenAI client sends processed messages to the API and receives a summary.
5. **Storage (Optional)**: If enabled, the summary is stored in the Supabase database.
6. **Presentation**: The summary is displayed to the user and optionally sent back to the WhatsApp group.

## Critical Paths

The following sequences represent critical paths that must remain functional:

### Core Summary Generation Path
```
User Selection → Message Retrieval → Message Processing → Summary Generation → Display
```

### Previous Summary Viewing Path
```
User Selection → Database Retrieval → Display
```

### Settings Management Path
```
User Selection → Configuration Update → Configuration Storage
```

## Error Handling Strategy

The system employs a multi-layered error handling strategy:

1. **Component-Level**: Each component catches and logs errors specific to its domain.
2. **Integration-Level**: Interfaces between components validate data to prevent cascading failures.
3. **System-Level**: The menu system catches unhandled exceptions to prevent crashes.
4. **User Feedback**: Errors are communicated to users with appropriate context and recovery suggestions.

## Design Decisions

### 1. Terminal-Based Interface

**Decision**: Use a terminal-based menu system rather than a web or GUI interface.

**Rationale**: 
- Simplifies deployment requirements
- Works across all platforms without additional dependencies
- Reduces security concerns related to web interfaces
- Allows for quick iterations and testing

### 2. Optional Database Integration

**Decision**: Make database storage optional.

**Rationale**:
- Reduces barrier to entry for users without database knowledge
- Allows the core functionality to work in environments with limited connectivity
- Simplifies testing and development

### 3. Safety Mechanisms for Message Sending

**Decision**: Implement multiple safety layers to prevent accidental message sending.

**Rationale**:
- Prevents spam or unwanted messages to WhatsApp groups
- Protects users from accidental API usage and potential costs
- Provides clear confirmation steps before sending messages

### 4. Language Model Flexibility

**Decision**: Support configuration of different OpenAI models.

**Rationale**:
- Allows users to balance cost vs. quality
- Future-proofs against new model releases
- Enables testing with different models

## Configuration Parameters

The system is configured through environment variables and user settings:

### Required Configuration
- `GREEN_API_INSTANCE_ID`: Green API instance identifier
- `GREEN_API_INSTANCE_TOKEN`: Green API authentication token
- `OPENAI_API_KEY`: OpenAI API key for generating summaries
- `DEFAULT_LANGUAGE`: Default language for summaries

### Optional Configuration
- `OPENAI_MODEL`: Model to use for summaries (default: gpt-3.5-turbo)
- `MAX_MESSAGES`: Maximum number of messages to process (default: 100)
- `SUPABASE_URL`: Supabase URL for database storage
- `SUPABASE_KEY`: Supabase API key
- `PREFERRED_GROUP_ID`: Default WhatsApp group to use
- `MESSAGE_SAFETY`: Enable/disable safety mechanisms (default: enabled)

## External Dependencies

The system relies on these external services:

1. **Green API**: For WhatsApp connectivity
2. **OpenAI API**: For generating summaries
3. **Supabase** (optional): For storing summaries

## Testing Strategy

The system includes several testing tools:

1. **Unit Tests**: Located in the `tests/` directory, verifying individual component functionality
2. **Health Checks**: Tools for verifying system integrity (`tools/system_health_check.py`)
3. **Menu Tests**: Specific tests for the critical menu system (`utils/menu/test_menu.py`)
4. **Version Compatibility**: Tests for ensuring menu compatibility across versions (`utils/menu/version_check.py`)

## Extending the System

When extending the system, preserve these architectural boundaries:

1. Keep the interactive menu independent from core functionality
2. Maintain the separation between API clients and business logic
3. Ensure all critical paths continue to function
4. Preserve all safety mechanisms
5. Retain compatibility with existing data formats

## Deployment Considerations

The system is designed for simple deployment:

- Requires Python 3.7+
- Uses pip for dependency management
- Configurable through environment variables or .env file
- No database setup required for core functionality
- Minimal system resource requirements

## Conclusion

The WhatsApp Group Summary Bot architecture is designed for simplicity, resilience, and ease of use. It achieves its goals through clear separation of concerns, robust error handling, and minimal external dependencies.

All developers working on this system should understand and preserve these architectural patterns to ensure the continued functioning of the bot across all versions. 