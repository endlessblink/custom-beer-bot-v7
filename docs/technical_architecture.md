# WhatsApp Bot - Technical Architecture Document

## 1. System Overview

### 1.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        WhatsApp Bot System                       │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Core Components                         │
├─────────────┬─────────────┬─────────────┬────────────┬──────────┤
│ Green API   │ Message     │ OpenAI      │ Config     │ Storage  │
│ Client      │ Processor   │ Client      │ Manager    │ Manager  │
└─────────────┴─────────────┴─────────────┴────────────┴──────────┘
       │              │              │            │           │
       ▼              ▼              ▼            ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Service Integrations                       │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│ WhatsApp    │ LLM         │ Scheduler   │ Database    │ Logging │
│ (Green API) │ (OpenAI)    │ Service     │ (Future)    │ Service │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────┘
```

### 1.2 Technology Stack

- **Programming Language**: Python 3.8+
- **WhatsApp API Provider**: Green API
- **LLM Provider**: OpenAI API
- **Database** (Future): Supabase/MongoDB
- **External Integrations** (Future): Discord API, Telegram API
- **Deployment**: Docker container (optional)

## 2. Component Design

### 2.1 Core Components

#### 2.1.1 Green API Client

**Purpose**: Manages all interactions with the WhatsApp platform via Green API.

**Responsibilities**:
- Authenticate with Green API
- Fetch available groups
- Retrieve messages from groups
- Send messages to groups
- Handle webhook notifications (future)

**Key Classes**:
- `GreenAPIClient`: Main interface for Green API operations
- `GroupManager`: Handles group-related operations
- `MessageReceiver`: Processes incoming messages
- `MessageSender`: Handles outgoing messages

#### 2.1.2 Message Processor

**Purpose**: Processes, organizes, and prepares messages for summarization.

**Responsibilities**:
- Extract text content from messages
- Batch messages by time period
- Clean and normalize text
- Filter irrelevant content
- Structure data for LLM processing

**Key Classes**:
- `MessageProcessor`: Main processing pipeline
- `TextExtractor`: Extracts and normalizes text
- `MessageBatcher`: Groups messages for processing
- `ContentFilter`: Filters out irrelevant content

#### 2.1.3 OpenAI Client

**Purpose**: Handles interaction with OpenAI API for summarization.

**Responsibilities**:
- Authenticate with OpenAI API
- Format messages for LLM processing
- Send requests to OpenAI API
- Process and parse responses
- Handle token limits and errors

**Key Classes**:
- `OpenAIClient`: Main interface for OpenAI operations
- `SummaryGenerator`: Creates summaries using OpenAI
- `PromptBuilder`: Constructs effective prompts
- `TokenManager`: Handles token limitations

#### 2.1.4 Config Manager

**Purpose**: Manages application configuration and settings.

**Responsibilities**:
- Load configuration from environment variables
- Validate configuration values
- Provide access to configuration
- Handle configuration changes
- Secure sensitive configuration

**Key Classes**:
- `ConfigManager`: Central configuration management
- `EnvironmentLoader`: Loads from environment variables
- `ConfigValidator`: Validates configuration
- `SecureConfigHandler`: Handles sensitive config

#### 2.1.5 Storage Manager (Future)

**Purpose**: Manages persistent storage of application data.

**Responsibilities**:
- Store message history
- Track summarization records
- Manage user preferences
- Handle application state
- Implement data retention policies

**Key Classes**:
- `StorageManager`: Central storage interface
- `MessageRepository`: Stores message data
- `SummaryRepository`: Tracks summary history
- `UserPreferenceStore`: Manages user settings

### 2.2 Service Integrations

#### 2.2.1 WhatsApp Integration (Green API)

**Implementation Details**:
- RESTful API communication
- JSON data format
- Authentication via API key and instance ID
- Error handling and retry logic
- Rate limit management

**API Endpoints Used**:
- Group listing and information
- Message retrieval
- Message sending
- Connection status

#### 2.2.2 LLM Integration (OpenAI)

**Implementation Details**:
- OpenAI Python library
- GPT model selection
- Token optimization
- Error handling and fallback
- Context window management

**Models Used**:
- Primary: GPT-4 or equivalent
- Fallback: GPT-3.5-turbo or equivalent

#### 2.2.3 Scheduler Service

**Implementation Details**:
- Scheduled task execution
- Interval configuration
- Error recovery
- Task dependency management
- Timezone handling

**Key Features**:
- Configurable intervals
- Manual trigger option
- Failure recovery
- Event logging

#### 2.2.4 Database Integration (Future)

**Implementation Details**:
- ORM for database operations
- Connection pooling
- Transaction management
- Schema versioning
- Data migration

**Storage Requirements**:
- Message metadata (not content)
- Summary history
- Configuration data
- Usage statistics

#### 2.2.5 Logging Service

**Implementation Details**:
- Structured logging
- Log level configuration
- Log rotation
- Error tracking
- Audit logging

**Log Categories**:
- Operation logs
- Error logs
- Security logs
- Performance metrics

## 3. Data Flow

### 3.1 Message Retrieval Flow

1. **Group Selection**
   - User selects group for monitoring
   - System validates access permissions
   - Group ID is stored in configuration

2. **Message Fetching**
   - System queries Green API for messages
   - Messages are filtered by timestamp
   - Message metadata is extracted
   - Content is preprocessed

3. **Message Storage** (Future)
   - Message metadata is stored
   - Source references are maintained
   - Privacy filters are applied
   - Retention policies enforced

### 3.2 Summarization Flow

1. **Message Collection**
   - Messages are collected based on time window
   - System applies filtering rules
   - Messages are organized by context
   - Preparation for summarization

2. **LLM Processing**
   - Formatted content sent to OpenAI
   - Summary prompt is constructed
   - Response is processed
   - Summary is formatted

3. **Summary Delivery**
   - Summary is prepared for delivery
   - Message is sent to WhatsApp group
   - Delivery status is tracked
   - Summary is recorded

## 4. Security Considerations

### 4.1 API Key Management

- Environment variables for sensitive data
- No hardcoded credentials
- Key rotation support
- Least privilege principle

### 4.2 Data Privacy

- Minimal data retention
- No persistent storage of message content
- Privacy by design
- GDPR considerations

### 4.3 Access Control

- Role-based permissions
- Command authorization
- Administrative safeguards
- Audit logging

## 5. Error Handling Strategy

### 5.1 Error Classification

- **Connectivity Errors**: Network, API availability
- **Authentication Errors**: Invalid credentials, expired tokens
- **Permission Errors**: Insufficient access rights
- **Processing Errors**: Failed summarization, parsing issues
- **System Errors**: Resource constraints, unexpected failures

### 5.2 Recovery Mechanisms

- Automatic retry with exponential backoff
- Graceful degradation
- Fallback options
- Alert mechanisms
- Self-healing procedures

## 6. Extension Points

### 6.1 Discord/Telegram Integration

- Webhook endpoints for commands
- Cross-platform notification
- Administrative interface
- Status reporting

### 6.2 Custom Training Integration

- Data collection pipeline
- Training data preparation
- Model fine-tuning interface
- Evaluation framework

### 6.3 Analytics Engine

- Data aggregation
- Metric calculation
- Visualization components
- Reporting system

### 6.4 Scoring System

- Score calculation engine
- Parameter configuration
- Reporting mechanism
- Gamification elements

## 7. Deployment Considerations

### 7.1 Environment Setup

- Python virtual environment
- Dependency management
- Configuration templates
- Installation scripts

### 7.2 Containerization (Optional)

- Docker configuration
- Volume management
- Network configuration
- Resource allocation

### 7.3 Monitoring

- Health checks
- Performance monitoring
- Usage tracking
- Alert configuration 