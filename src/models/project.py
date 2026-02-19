"""Project data model."""

class Project:
    """Represents a CxOne project."""

    def __init__(self, project_id, name):
        self.id = project_id
        self.name = name

    def to_dict(self):
        return {'project_id': self.id, 'project_name': self.name}

    @classmethod
    def from_dict(cls, data):
        return cls(
            project_id=data.get('id') or data.get('project_id'),
            name=data.get('name') or data.get('project_name')
        )

    def __repr__(self):
        return f"Project(id={self.id}, name={self.name})"
