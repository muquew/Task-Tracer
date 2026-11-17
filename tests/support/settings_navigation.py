"""Shared settings navigation fixtures and assertions; no test entry point."""
from __future__ import annotations

def primary_entries(page):
    mobile = page.viewport_size['width'] <= 779
    return ('#mobileTodayBtn', '#mobileTasksBtn', '#mobileProjectsBtn', '#mobileReviewBtn') if mobile else (
        '#workspaceTodayBtn', '#workspaceAllTasks', '#workspaceProjectsBtn', '#viewTab-stats')
