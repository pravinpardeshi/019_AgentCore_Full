# Architecture: AI Chat History with Active Directory SSO and Amazon Bedrock AgentCore

This document outlines the architecture for implementing persistent chat history and session management using Active Directory (AD) SSO and Amazon Bedrock AgentCore.

## 1. High-Level Architecture Flow

The system separates **AI Context Memory** (managed by AWS) from **User Chat History** (managed by the application).

**Flow:**
`User` $\rightarrow$ `AD SSO` $\rightarrow$ `App Backend` $\rightarrow$ `SQL Database` (Metadata/History) $\rightarrow$ `AgentCore Runtime` $\rightarrow$ `AgentCore Memory` (LLM Context)

---

## 2. Component Responsibilities

### A. Active Directory (AD) SSO
*   **Identity Provider**: Authenticates the user and provides a secure token (JWT/SAML).
*   **Claims**: Provides the unique `userId` (e.g., email or ObjectSID) used to partition all data.

### B. Application SQL Database (The "UI" Layer)
Bedrock's Memory service is a "black box" for the LLM; it is not a queryable database for your frontend. You must store metadata in your own DB (e.g., PostgreSQL, DynamoDB).

**Recommended Schema:**
*   **Sessions Table**: 
    *   `userId` (Indexed): The ID from AD.
    *   `sessionId`: The unique ID passed to AgentCore.
    *   `chat_title`: A user-friendly name for the chat.
    *   `created_at`: Timestamp.
*   **Messages Table**: 
    *   `sessionId`: Foreign key to Sessions.
    *   `role`: 'user' or 'assistant'.
    *   `content`: The actual text.
    *   `timestamp`: When the message was sent.

### C. Amazon Bedrock AgentCore Memory (The "AI" Layer)
Handles the actual "remembering" during the conversation.
*   **Function**: Stores and retrieves the conversation turn history.
*   **Trigger**: Activated by passing the `sessionId` in the `InvokeAgent` / `AgentCore` API call.
*   **Lifecycle**: Managed via TTL (Time-to-Live) settings in the Runtime configuration.

---

## 3. Implementation Logic

### Phase 1: Starting a New Chat
1.  User authenticates via AD SSO $\rightarrow$ App gets `userId`.
2.  App generates a new `sessionId` (UUID).
3.  App creates a record in the **SQL Sessions Table** (`userId`, `sessionId`, `title`).
4.  App invokes AgentCore with the new `sessionId`.

### Phase 2: Continuing an Existing Chat
1.  User clicks a past chat in the UI $\rightarrow$ App retrieves `sessionId` from **SQL DB**.
2.  App invokes AgentCore using that same `sessionId`.
3.  **AgentCore Runtime** automatically pulls the history from **Memory Service** and provides it to the LLM.

### Phase 3: Saving the Turn
1.  AgentCore returns a response.
2.  App writes both the user's prompt and the agent's response to the **SQL Messages Table** for permanent UI storage.

---

## 4. Security & Compliance

| Feature | Implementation |
| :--- | :--- |
| **Data Isolation** | Query SQL DB using `WHERE userId = :ad_user_id`. |
| **Access Control** | Revoking AD account access automatically blocks access to the App and the History. |
| **Audit Trail** | Log `userId` + `sessionId` + `timestamp` for every Bedrock invocation. |
| **Encryption** | Enable KMS encryption for AgentCore Memory and SQL database at rest. |

## 5. Summary Comparison

| Requirement | Solution | Why? |
| :--- | :--- | :--- |
| **AI needs to remember the last turn** | AgentCore Memory | Automatic, low-latency, model-optimized. |
| **User wants to see "My Chats" list** | SQL Database | Queryable, permanent, user-facing. |
| **Secure User Login** | AD SSO | Enterprise standard, centralized identity. |
