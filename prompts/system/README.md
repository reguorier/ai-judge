# System Prompt Templates

Each AI Judge seat uses a model-specific system prompt that:
1. Establishes the model's role as one of nine independent jurors
2. Defines expected output format (core answer + claims + confidence)
3. Prohibits cross-model speculation
4. Allows for model-specific strengths (e.g., Gemini's breadth, DeepSeek's rigor)

## Usage

These prompts are injected by the paid core's `render_dispatch_prompt()`.
Community users can review and suggest improvements to these templates.

## Adding a New Seat

1. Create `prompts/system/{model}.md`
2. Follow the established format (Role, Constraints, Output Format)
3. Submit as a PR — no paid core code required
