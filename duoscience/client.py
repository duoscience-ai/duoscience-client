# -*- coding: utf-8 -*-
"""
duoscience/client.py

Python client for the DuoScience API.
This module provides a high-level client library (SDK) for interacting with the
DuoScience API. It encapsulates the complexity of the asynchronous task and
Server-Sent Events (SSE) architecture, offering a simple, iterator-based
interface for each major endpoint.

Key responsibilities
--------------------
* Providing a clean, object-oriented interface for the API.
* Handling the two-step process: POST to initiate a task and GET to stream events.
* Parsing Server-Sent Events and yielding structured data.
* Gracefully handling connection and API errors.

Author: Roman Fitzjalen | DuoScience
Date: 7 July 2025
© 2025 DuoScience. All rights reserved.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterator

import requests
from sseclient import SSEClient


class DuoScienceClient:
    """
    A client for making requests to the DuoScience API.

    This class provides methods that correspond to the main API endpoints
    (e.g., chat, research), handling the underlying HTTP requests and event
    streaming, and returning a simple iterator over the status events.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 30):
        """
        Initializes the DuoScienceClient.

        Args:
            base_url: The base URL of the DuoScience API server.
            timeout: The timeout in seconds for the initial POST request.
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        self.logger = logging.getLogger(__name__)

    def _stream_task(self, endpoint: str, payload: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """
        A private helper method to start a task and stream its events.

        This method performs the two-step API call:
        1. Sends a POST request to the specified endpoint to start a task.
        2. Opens an SSE connection to the /stream/{task_id} endpoint to listen for events.

        Args:
            endpoint: The API endpoint to call (e.g., "/chat/").
            payload: The dictionary payload for the POST request.

        Yields:
            A dictionary representing a single JSON event from the SSE stream.
            In case of a failure to start the task, yields a single error event.
        """
        task_id = None
        # --- Step 1: Start the task and get the task_id ---
        try:
            start_url = f"{self.base_url}{endpoint}"
            self.logger.info(f"Initiating task at {start_url}")
            response = requests.post(start_url, json=payload, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            if response.status_code == 202:
                task_id = response.json().get("task_id")
                if not task_id:
                    self.logger.error("API Error: Server accepted the task but did not return a task_id.")
                    raise ConnectionError("API Error: Server accepted the task but did not return a task_id.")
                self.logger.info(f"Task started successfully. Task ID: {task_id}")
            else:
                self.logger.error(f"API Error: Failed to start task. Status: {response.status_code}, Body: {response.text}")
                raise ConnectionError(f"API Error: Failed to start task. Status: {response.status_code}, Body: {response.text}")
        except requests.exceptions.RequestException as e:
            self.logger.exception("Connection Error: Failed to start task.")
            yield {"status": "error", "message": f"Connection Error: Failed to start task. {e}"}
            return

        # --- Step 2: Connect to the event stream using the task_id ---
        try:
            stream_url = f"{self.base_url}/stream/{task_id}"
            self.logger.info(f"Connecting to event stream at {stream_url}")
            client = SSEClient(stream_url)
            for event in client:
                if not event.data:  # Ignore heartbeats
                    continue
                
                data = json.loads(event.data)
                self.logger.debug(f"Received event: {data}")
                yield data
                
                # Stop iterating if the task is finished or has failed
                if data.get("status") in ["completed", "error"]:
                    self.logger.info(f"Task finished with status: {data.get('status')}")
                    break
        except Exception as e:
            self.logger.exception("Streaming Error: The connection was lost.")
            yield {"status": "error", "message": f"Streaming Error: The connection was lost. {e}"}

    def chat(self, user_id: str, chat_id: str, content: str, **kwargs) -> Iterator[Dict[str, Any]]:
        """
        Initiates a /chat task and returns an iterator for its events.

        Args:
            user_id: Unique identifier of the user.
            chat_id: Identifier of the chat/session.
            content: Text of the message from the user.
            **kwargs: Additional optional parameters like 'domain' or 'effort'.

        Returns:
            An iterator that yields status events from the API.
        """
        payload = {"user_id": user_id, "chat_id": chat_id, "content": content, **kwargs}
        self.logger.info(f"Starting chat task for user {user_id} in chat {chat_id}")
        return self._stream_task("/chat/", payload)

    def research(self, user_id: str, chat_id: str, content: str, **kwargs) -> Iterator[Dict[str, Any]]:
        """
        Initiates a /research task and returns an iterator for its events.

        Args:
            user_id: Unique identifier of the user.
            chat_id: Identifier of the research session.
            content: The research query or topic.
            **kwargs: Additional optional parameters like 'domain' or 'effort'.
            
        Returns:
            An iterator that yields status events from the API.
        """
        payload = {"user_id": user_id, "chat_id": chat_id, "content": content, **kwargs}
        self.logger.info(f"Starting research task for user {user_id} in chat {chat_id}")
        return self._stream_task("/research/", payload)

    def hypotheses(self, user_id: str, chat_id: str, content: str, **kwargs) -> Iterator[Dict[str, Any]]:
        """
        Initiates a /hypotheses task and returns an iterator for its events.

        Args:
            user_id: Unique identifier of the user.
            chat_id: Identifier of the hypothesis session.
            content: The topic for hypothesis generation.
            **kwargs: Additional optional parameters like 'domain' or 'effort'.

        Returns:
            An iterator that yields status events from the API.
        """
        payload = {"user_id": user_id, "chat_id": chat_id, "content": content, **kwargs}
        self.logger.info(f"Starting hypotheses task for user {user_id} in chat {chat_id}")
        return self._stream_task("/hypotheses/", payload)


if __name__ == '__main__':
    """
    Example usage of the DuoScienceClient.
    This block demonstrates how to use the client to interact with the API
    and process the stream of events.
    """
    # --- Basic logging setup ---
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("--- DuoScience API Client Example ---")
    
    # Initialize the client
    client = DuoScienceClient(base_url="http://127.0.0.1:8000")

    # Start a chat task
    logger.info("▶️  Initiating a new chat task...")
    chat_events = client.chat(
        user_id="example_user_123",
        chat_id="example_chat_abc",
        content="Tell me about mitochondria.",
        domain="bioscience",
        effort="low"
    )

    # Process events from the iterator
    for event in chat_events:
        status = event.get("status")

        if status == "running":
            logger.info(f"⏳ STATUS: {event.get('message')}")
        elif status == "completed":
            logger.info("✅ --- TASK COMPLETED --- ✅")
            final_payload = event.get("payload", {})
            logger.info(f"Final Answer: {final_payload.get('content')}")
        elif status == "error":
            logger.error(f"❌ ERROR: {event.get('message')}")
        else:
            logger.warning(f"Received unknown event: {event}")
    
    logger.info("--- Example finished ---")