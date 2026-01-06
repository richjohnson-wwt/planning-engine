---
trigger: always_on
---

# Coding pattern preferences

- Always prefer simple solutions
- Avoid duplication of code whenever possible, which means checking for other areas of the codebase that might already have similar code and functionality
- Write code that takes into account the different environments: dev, test, prod
- You are careful to only make changes that are requested or you are confident changes are well understood and related to the change being requested
- When fixing a bug or issue, do not introduce a new pattern or technology without first exhausting all options for the existing implementation. And if you do this, make sure to remove the old implementation afterwards so we don't have duplicate logic.
- Keep the codebase very clean and organized
- Avoid writing scripts in files if possible, especially if the script is likely only to be run once
- Avoid having files over 200-300 lines of code. Refactor as that point.
- Mocking data is only needed for tests, never mock data for dev or prod
- Never add stubbing of fake data patterns to code that affects the dev or prod environments
- Never overwrite my .env file without first asking and confirming


## 2. Run commands
- When running commands in this workspace use 'uv run ...'
- Always run pytest after changes 'uv run pytest'

## 3. Technical Stack
- Python fastapi for the backend
- Vue.js for the front end
- pytest for backend tests

## 4. Cascade Write/Chat
- If I give instruction to add/update code and the Cascade mode is set to 'Chat', prompt me to switch it to 'Write'.