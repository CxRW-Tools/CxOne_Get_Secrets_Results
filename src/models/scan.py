"""Scan data model."""

class Scan:
    """Represents a CxOne scan (e.g. with secrets/microengines results)."""

    def __init__(self, scan_id, project_id, project_name, branch_name, created_at=None):
        self.scan_id = scan_id
        self.project_id = project_id
        self.project_name = project_name
        self.branch_name = branch_name
        self.created_at = created_at

    def to_dict(self):
        return {
            'scan_id': self.scan_id,
            'project_id': self.project_id,
            'project_name': self.project_name,
            'branch_name': self.branch_name,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            scan_id=data['scan_id'],
            project_id=data['project_id'],
            project_name=data['project_name'],
            branch_name=data['branch_name'],
            created_at=data.get('created_at')
        )

    def __repr__(self):
        return f"Scan(id={self.scan_id}, project={self.project_name}, branch={self.branch_name})"
