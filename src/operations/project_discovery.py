"""Project discovery operation."""

from src.operations.base import Operation
from src.models.project import Project

class ProjectDiscovery(Operation):
    """Discover all CxOne projects."""

    def execute(self):
        if self.logger:
            self.logger.log("Fetching all projects from /api/projects...")
        if self.config.debug:
            print("\nFetching all projects...")

        projects_data = self.api_client.get_paginated('/api/projects')
        if not projects_data:
            if self.logger:
                self.logger.log("No projects found or API error occurred")
            if self.config.debug:
                print("No projects found or error occurred")
            return []

        if self.logger:
            self.logger.log("Retrieved " + str(len(projects_data)) + " projects from API")

        projects = []
        for project_data in projects_data:
            try:
                project = Project.from_dict(project_data)
                projects.append(project)
                if self.logger:
                    self.logger.log("  - Project: " + project.name + " (ID: " + project.id + ")")
            except Exception as e:
                if self.logger:
                    self.logger.log("ERROR: Failed to parse project: " + str(e))
                if self.config.debug:
                    print("Error parsing project:", e)
                continue

        if self.logger:
            self.logger.log("Successfully parsed " + str(len(projects)) + " projects")
        if self.config.debug:
            print("Found", len(projects), "projects")
        return projects
