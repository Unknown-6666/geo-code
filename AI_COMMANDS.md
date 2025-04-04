# AI Chat Commands

This Discord bot supports both slash commands (`/command`) and traditional prefix commands (`!command`). Use whichever style you prefer!

## Talking with the AI

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/ask <question>` | `!ask <question>` | Ask the AI a one-time question |
| `/chat <message>` | `!chat <message>` | Have a casual conversation with the AI (with memory) |

## Conversation Management

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/clear_chat_history` | `!clear_history` | Clear your conversation history with the AI |
| `/show_chat_history` | `!history` | Show your recent conversation with the AI |

## Admin Commands

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/toggle_personality` | `!toggle_personality` | Cycle between childlike, neutral, and threatening AI personality modes (Admin only) |
| `/ai_reload` | N/A | Reload AI preferences from configuration files (Admin only) |
| `/custom_response` | N/A | Manage custom AI responses (Admin only) |

## Tips for Using the AI

### The Difference Between Ask and Chat

- **Ask Command**: Use `/ask` or `!ask` for one-off questions. The AI doesn't remember your previous questions or its answers.
  - Example: `!ask What is the capital of France?`
  
- **Chat Command**: Use `/chat` or `!chat` for ongoing conversations. The AI remembers previous messages in the conversation.
  - Example: `!chat Tell me about space exploration`
  - Follow-up: `!chat What are the biggest challenges?`

### Managing Conversation History

If you want to start a fresh conversation:
- Use `!clear_history` to delete your conversation history
- The AI will no longer have context from previous exchanges

To review your recent conversation:
- Use `!history` to see your recent exchanges with the AI
- This shows both your messages and the AI's responses

### Getting the Best Responses

For better results:
- Be specific in your questions
- Provide context if needed
- Use `/chat` or `!chat` for complex topics where follow-up questions are likely
- Use `/ask` or `!ask` for simple factual questions

### AI Capabilities

The bot's AI can:
- Answer questions about facts and general knowledge
- Have casual conversations on various topics
- Provide explanations about concepts
- Assist with creative tasks like brainstorming or writing
- Remember context from your conversation (when using chat)

The AI cannot:
- Access the internet or search for information
- Access server-specific information unless you provide it
- Remember conversations from days ago (history is limited)
- Execute commands on your behalf

### Personality Modes (Admin Only)

The AI has three different personality modes that admins can cycle between:

1. **Childlike Mode (Default)**: 
   - More playful and innocent with childlike speech patterns
   - Uses giggles and playful phrases
   - Still slightly creepy but in an innocent way

2. **Neutral Mode**:
   - More balanced and helpful with normal conversational patterns
   - Neither overly childish nor threatening
   - Maintains c00lkidd's character but in a more subdued, helpful manner
   - Best for providing helpful information while staying in character

3. **Threatening Mode**:
   - More menacing and darker version of the same character
   - Uses more unsettling language and implied threats
   - Maintains childlike speech patterns but with an underlying sense of danger
   - May not be appropriate for all audiences

Admins can use `/toggle_personality` or `!toggle_personality` to cycle through these modes in order: Childlike → Neutral → Threatening → Childlike.
