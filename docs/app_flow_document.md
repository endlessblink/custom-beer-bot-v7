# WhatsApp Bot - Application Flow Document

## 1. Overview
This document outlines the application flow for the WhatsApp bot, detailing the sequence of operations, data flow, and interactions between different components of the system.

## 2. System Initialization Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│ Load            │─────▶ Initialize      │─────▶ Connect to      │
│ Configuration   │     │ Components      │     │ WhatsApp API    │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. **Load Configuration**
   - Read environment variables from `.env` file
   - Initialize logging
   - Validate required API keys and credentials

2. **Initialize Components**
   - Set up Green API client
   - Configure OpenAI client
   - Initialize message processor
   - Prepare database connection (for future use)

3. **Connect to WhatsApp API**
   - Authenticate with Green API
   - Verify connection status
   - Check instance state

## 3. Group Selection Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│ Fetch Available │─────▶ Display Group   │─────▶ User Selects    │
│ Groups          │     │ List            │     │ Group           │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │                 │
                                               │ Configure       │
                                               │ Monitoring      │
                                               │                 │
                                               └─────────────────┘
```

1. **Fetch Available Groups**
   - Call Green API to retrieve list of groups
   - Filter for groups where user is a participant
   - Organize groups by name/ID

2. **Display Group List**
   - Present groups to user with relevant information
   - Show member count, group name, and description

3. **User Selects Group**
   - Capture user selection
   - Validate group access permissions

4. **Configure Monitoring**
   - Set up message retrieval interval
   - Configure summarization parameters
   - Set up notification preferences

## 4. Message Processing Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│ Fetch New       │─────▶ Process         │─────▶ Generate        │
│ Messages        │     │ Messages        │     │ Summary         │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │                 │
                                               │ Send Summary    │
                                               │ to Group        │
                                               │                 │
                                               └─────────────────┘
```

1. **Fetch New Messages**
   - Retrieve messages from selected group
   - Filter for messages since last check
   - Organize messages by timestamp and sender

2. **Process Messages**
   - Parse message content (text, media, etc.)
   - Extract relevant information
   - Clean and prepare text for summarization

3. **Generate Summary**
   - Send message batch to OpenAI API
   - Apply summarization parameters
   - Process and format the resulting summary

4. **Send Summary to Group**
   - Format summary with appropriate context
   - Send summary message to the group
   - Log successful delivery

## 5. Error Handling Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│ Detect Error    │─────▶ Log Error       │─────▶ Apply Recovery  │
│                 │     │ Information     │     │ Strategy        │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │                 │
                                               │ Notify Admin    │
                                               │ (if needed)     │
                                               │                 │
                                               └─────────────────┘
```

1. **Detect Error**
   - Identify error type (API, connection, permission, etc.)
   - Capture context and state information

2. **Log Error Information**
   - Record detailed error information
   - Include timestamp, error context, and system state

3. **Apply Recovery Strategy**
   - Implement retry logic for transient errors
   - Apply fallback measures for critical failures
   - Reset connections if needed

4. **Notify Admin**
   - Send notification of critical errors
   - Provide diagnostic information
   - Suggest recovery actions

## 6. Scheduled Summary Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│ Timer Triggers  │─────▶ Check Message   │─────▶ Process Message │
│ Summary Task    │     │ Threshold       │     │ Batch           │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │                 │
                                               │ Generate and    │
                                               │ Send Summary    │
                                               │                 │
                                               └─────────────────┘
```

1. **Timer Triggers Summary Task**
   - Scheduled job activates based on configured interval
   - Check system status and availability

2. **Check Message Threshold**
   - Verify minimum message count for summarization
   - Check if enough time has passed since last summary

3. **Process Message Batch**
   - Retrieve messages since last summary
   - Prepare messages for summarization

4. **Generate and Send Summary**
   - Create summary using LLM
   - Format and send to the group
   - Update last summary timestamp

## 7. Future Extension Points

### 7.1 Discord/Telegram Management Integration
Extension points for integrating management capabilities through Discord or Telegram bots.

### 7.2 Custom Training Pipeline
Flow for gathering and processing training data to enable question answering capabilities.

### 7.3 Scoring System Integration
Process flow for implementing and maintaining the group member scoring system. 