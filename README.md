<div align="center">
  <img src="assets/duoscience-logo.png" alt="DuoScience Logo" width="200"/>
</div>

# DuoScience API Python Client

[![PyPI version](https://badge.fury.io/py/duoscience-client.svg)](https://badge.fury.io/py/duoscience-client)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The official Python client for the DuoScience API. This SDK simplifies interaction with the API's asynchronous, task-based architecture by handling HTTP requests and Server-Sent Events (SSE) streaming.

---

## Features

-   **Simple Interface**: An intuitive, object-oriented interface for all major API endpoints.
-   **Asynchronous Handling**: Abstracts away the complexity of polling and long-running tasks.
-   **Real-time Events**: Uses an iterator to stream real-time status updates and results via SSE.
-   **Error Handling**: Gracefully manages connection and API errors.

## Installation

Install the client from PyPI using pip:

```bash
pip install duoscience-client
```

The package will automatically install the required dependencies:
- `requests`
- `sseclient`
- `markdown`
- `pdfkit`

## Usage

### 1. Initialization

First, import and instantiate the client. You can specify the `base_url` of your DuoScience API instance.

```python
from duoscience.client import DuoScienceClient

# Initialize the client
# Defaults to http://127.0.0.1:8000 if not specified
client = DuoScienceClient(base_url="https://api.duoscience.ai")
```

### 2. Core Concept: The Event Iterator

The DuoScience API operates asynchronously. When you initiate a task (like a chat or research query), the API immediately returns a `task_id`. The client uses this ID to connect to an SSE stream, which delivers real-time updates as the task progresses.

The `DuoScienceClient` handles this for you. Calling a method like `client.chat()` returns an **iterator**. Each item from the iterator is a JSON object representing an event from the backend.

You can simply loop over the iterator to process events as they arrive. The loop will automatically terminate when a final event (e.g., `status: "completed"` or `status: "failed"`) is received.

**Key Event Fields:**
-   `status`: The current state of the task (`"running"`, `"completed"`, `"failed"`).
-   `source`: The backend component emitting the event (e.g., `"agent:WriterAgent"`).
-   `message`: A human-readable description of the event or progress update.
-   `result`: The final output of the operation (only present when `status` is `"completed"`).

### 3. Examples

#### Example 1: Initiating a Chat

This example starts a chat session and prints events as they are received.

```python
import logging
from duoscience.client import DuoScienceClient

# Configure logging to see client-side status updates
logging.basicConfig(level=logging.INFO)

# Initialize the client
client = DuoScienceClient()

print("\n▶️  Initiating a new chat task...")
try:
    chat_events = client.chat(
        user_id="example_user_123",
        chat_id="example_chat_abc",
        content="Tell me about the role of mitochondria in cellular respiration.",
        domain="bioscience",
        effort="low"
    )

    final_answer = None
    for event in chat_events:
        status = event.get("status", "unknown")
        source = event.get("source", "system")
        message = event.get("message", "")

        print(f"[{status.upper()}] from [{source}]: {message}")

        if status == "completed":
            print("\n✅ --- TASK COMPLETED --- ✅")
            final_answer = event.get("result") # Final output is in the 'result' field
        elif status == "failed":
            print(f"❌ --- TASK FAILED --- ❌")
            print(f"Error details: {message}")
            break
    
    if final_answer:
        print(f"\nFinal Answer:\n{final_answer}")

except Exception as e:
    logging.error(f"An error occurred: {e}")

print("\n--- Example finished ---")
```

#### Example 2: Running a Research Task

The process for initiating a research task is identical. Call the `research` method with your query.

```python
print("\n▶️  Initiating a new research task...")
try:
    research_events = client.research(
        user_id="example_user_456",
        chat_id="example_research_def",
        content="What are the latest advancements in CRISPR gene editing for cancer therapy?",
        domain="bioscience",
        effort="high"  # Use 'high' effort for detailed research
    )

    # Process events from the iterator (same logic as the chat example)
    for event in research_events:
        status = event.get("status", "unknown")
        source = event.get("source", "system")
        message = event.get("message", "")
        print(f"[{status.upper()}] from [{source}]: {message}")
        if status in ["completed", "failed"]:
            break

except Exception as e:
    logging.error(f"An error occurred: {e}")

print("\n--- Example finished ---")
```

## Utilities

### Markdown to PDF Conversion

The project includes a utility module `duoscience.utils` for converting Markdown files into high-quality PDFs. This is useful for generating reports or documents from Markdown sources.

The `convert_md_to_pdf` function supports:
-   Custom CSS for styling.
-   Syntax highlighting for code blocks via Pygments.
-   Embedding a logo into the document.
-   Standard Markdown extensions (tables, footnotes, etc.).

**Prerequisite:** This utility requires the `wkhtmltopdf` command-line tool to be installed on your system.

**Example Usage:**

```python
from duoscience.utils import convert_md_to_pdf
import logging

logging.basicConfig(level=logging.INFO)

# Ensure wkhtmltopdf is installed and provide the path to the executable
WKHTMLTOPDF_PATH = '/usr/local/bin/wkhtmltopdf' # Path may vary

try:
    convert_md_to_pdf(
        md_file_path='local/research.md',
        pdf_file_path='local/research.pdf',
        wkhtmltopdf_path=WKHTMLTOPDF_PATH,
        css_path='assets/style.css', # Optional custom CSS
        logo_path='assets/duoscience-logo.png'
    )
    print("✅ PDF generated successfully.")
except Exception as e:
    print(f"❌ Failed to generate PDF: {e}")
```

## Development

To contribute to the development of this client, clone the repository and install the dependencies for local development.

```bash
# Clone the repository
git clone https://github.com/duoscience/duoscience-client.git
cd duoscience-client

# Install in editable mode with development dependencies
pip install -e .
```

### Running Build Tasks

The project includes a `Makefile` for common tasks:
-   `make build`: Builds the source distribution and wheel.
-   `make publish`: Builds and uploads the package to PyPI using Twine.
-   `make clean`: Removes build artifacts.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
