# Battle Bot Context Length Management Analysis

## Summary
After analyzing the codebase, I found that **the battle bot does NOT accumulate context over time**. The prompt size remains bounded and does not grow unbounded as the battle progresses.

## Key Findings

### 1. No Message History Accumulation
- The LLM client (`llm_client.py`) creates fresh API calls for each turn
- There is no conversation history or message accumulation
- Each decision is made independently without previous context

### 2. Static Prompt Generation
The `StateProcessor.create_battle_prompt()` method generates a fresh prompt each turn containing:
- Current battle state (active Pokemon, HP, status, etc.)
- Opponent's current state
- Available moves and switches
- Field conditions
- Strategic considerations (static text)

### 3. Limited Battle History
- The code attempts to include recent battle log: `_get_recent_battle_log()`
- However, it only includes the last 3 entries if available (lines 252-253 in `state_processor.py`)
- The poke-env library doesn't provide easy access to battle logs (as noted in comment)
- In practice, this likely returns just the current turn number

### 4. Token Limits
- The LLM response is limited to 150 tokens by default (`max_tokens=150`)
- The prompt itself consists of:
  - Battle state descriptions (variable but bounded)
  - Strategic considerations (large static block ~100 lines)
  - Response format instructions

### 5. No Turn-by-Turn Accumulation
- Each `choose_move()` call creates a new prompt from scratch
- No previous prompts or responses are stored
- No conversation context is maintained between turns

## Prompt Size Estimation
The prompt size per turn consists of:
1. **Dynamic content** (~500-1000 tokens):
   - Active Pokemon details
   - Opponent Pokemon details
   - Team status
   - Available actions
   
2. **Static content** (~2000-3000 tokens):
   - Strategic considerations
   - Type effectiveness chart
   - Game mechanics explanations
   - Response format

**Total prompt size: ~2500-4000 tokens per turn** (remains constant throughout battle)

## Potential Issues
While context doesn't grow unbounded, the static strategic section is quite large and could be optimized:
- The strategic considerations section includes extensive type charts and game mechanics
- This static content is sent with every request
- Could be reduced or made conditional based on battle state

## Recommendations
1. The current implementation is safe from unbounded context growth
2. Consider optimizing the static strategic text to reduce API costs
3. If battle history is needed, implement a proper turn-by-turn log with a sliding window
4. Monitor actual token usage in production to optimize prompt size

## Code References
- Prompt generation: `state_processor.py:42-72` (create_battle_prompt method)
- LLM calls: `llm_client.py:133-155` (get_decision method)
- Battle log attempt: `state_processor.py:245-257` (_get_recent_battle_log method)
- No message history in: `bot.py:51-97` (choose_move method)