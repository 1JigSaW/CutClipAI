"""
Flow integration service for video processing workflow.
Can integrate with LangFlow or custom workflow systems.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class FlowIntegrationService:
    """
    Service for integrating with Flow (LangFlow or custom workflow).
    Handles video upload to Flow and processing coordination.
    """

    def __init__(self):
        self.api_url = settings.FLOW_API_URL
        self.api_key = settings.FLOW_API_KEY
        self.enabled = settings.USE_FLOW and self.api_url is not None

        if self.enabled:
            logger.info(f"Flow integration enabled | api_url={self.api_url}")
        else:
            logger.debug("Flow integration disabled")

    async def upload_video_to_flow(
        self,
        video_path: str,
        user_id: int,
    ) -> Optional[str]:
        """
        Upload video to Flow platform for processing.

        Args:
            video_path: Path to video file
            user_id: User ID

        Returns:
            Flow task ID or None if disabled/failed
        """
        if not self.enabled:
            logger.debug("Flow integration disabled, skipping upload")
            return None

        try:
            logger.info(
                f"Uploading video to Flow | video_path={video_path} | user_id={user_id}"
            )

            async with httpx.AsyncClient(timeout=300.0) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                with open(video_path, "rb") as f:
                    files = {"file": (f"video_{user_id}.mp4", f, "video/mp4")}
                    data = {"user_id": str(user_id)}

                    response = await client.post(
                        f"{self.api_url}/upload",
                        files=files,
                        data=data,
                        headers=headers
                    )

                    response.raise_for_status()
                    result = response.json()
                    flow_task_id = result.get("task_id")

                    logger.info(
                        f"Video uploaded to Flow | user_id={user_id} | "
                        f"flow_task_id={flow_task_id}"
                    )

                    return flow_task_id

        except Exception as e:
            logger.error(
                f"Failed to upload video to Flow | error={e}",
                exc_info=True
            )
            return None

    async def check_flow_status(
        self,
        flow_task_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check status of Flow processing task.

        Args:
            flow_task_id: Flow task ID

        Returns:
            Status dictionary or None
        """
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                response = await client.get(
                    f"{self.api_url}/status/{flow_task_id}",
                    headers=headers
                )

                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(
                f"Failed to check Flow status | flow_task_id={flow_task_id} | error={e}"
            )
            return None

    async def get_flow_result(
        self,
        flow_task_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get result from Flow processing.

        Args:
            flow_task_id: Flow task ID

        Returns:
            Result dictionary or None
        """
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                response = await client.get(
                    f"{self.api_url}/result/{flow_task_id}",
                    headers=headers
                )

                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(
                f"Failed to get Flow result | flow_task_id={flow_task_id} | error={e}"
            )
            return None

