# WhatsApp Bot - Product Requirements Document (PRD)

## 1. Introduction

### 1.1 Purpose
This document outlines the requirements for a WhatsApp bot that can read messages from a selected group, summarize them using a Large Language Model (LLM), and send the summary back to the group.

### 1.2 Scope
The initial version will focus on the core functionality of message retrieval, summarization, and sending summaries. Future enhancements are outlined for later development phases.

## 2. Product Overview

### 2.1 Product Description
A Python-based WhatsApp bot that connects to the WhatsApp platform via Green API, processes messages, and generates summaries using LLM technology.

### 2.2 Target Users
- Group administrators who want to provide summaries of group discussions
- Community managers who need to track and summarize group conversations
- Users who want to catch up on missed conversations in groups

## 3. Requirements

### 3.1 Functional Requirements

#### 3.1.1 Core Functionality
- Connect to WhatsApp via Green API
- Display a list of available WhatsApp groups
- Allow user to select a group for monitoring
- Retrieve messages from the selected group
- Summarize retrieved messages using an LLM (OpenAI GPT)
- Send summary messages back to the group
- Configure summary interval (e.g., daily, hourly)

#### 3.1.2 Future Enhancements
- Bot management through Discord or Telegram
- Train the bot on group content to answer specific questions
- Scoring system for group members based on parameters
- Analytics dashboard for group activity
- Multi-group support
- Custom summary triggers (e.g., keywords, commands)

### 3.2 Non-Functional Requirements

#### 3.2.1 Performance
- Process and summarize messages within 60 seconds
- Handle groups with up to 100 participants
- Support message volume of at least 1000 messages per day

#### 3.2.2 Security
- Secure storage of API keys and tokens
- No persistent storage of message content (only as needed for processing)
- Compliance with WhatsApp's terms of service and API usage policies

#### 3.2.3 Reliability
- Error handling for API failures or rate limiting
- Logging of operations for debugging
- Automatic retry mechanism for failed operations

## 4. System Architecture

### 4.1 Components
- WhatsApp API Client (Green API)
- Message Processor
- LLM Integration (OpenAI)
- Configuration Manager
- Database (for future extensions)

### 4.2 Integrations
- Green API for WhatsApp
- OpenAI API for summarization
- Supabase/MongoDB for data storage (future)
- Discord/Telegram API (future)

## 5. Constraints

### 5.1 Technical Constraints
- Green API limitations and rate limits
- OpenAI API token limits and costs
- WhatsApp platform restrictions

### 5.2 Business Constraints
- Compliance with WhatsApp's terms of service
- Data privacy considerations

## 6. Appendix

### 6.1 Glossary
- **Green API**: A WhatsApp API provider used for sending and receiving messages
- **LLM**: Large Language Model (e.g., GPT-4, Mistral, etc.)
- **Summary**: A condensed version of multiple messages

### 6.2 References
- [Green API Documentation](https://green-api.com/en/docs/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference) 