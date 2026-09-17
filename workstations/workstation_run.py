"""
Engineering Workstation - Entry Point

Run this to start the workstation:
    python workstation_run.py

The workstation will be available at:
    http://localhost:5001/login

Default user credentials (from database):
    Username: admin
    Password: admin

This is the unified access point for:
- Workstation dashboard (metrics)
- Access to Industrial Historian database
"""

from components.workstations.workstation_1.app import create_app

try:
    from components.common.story_client import StoryClient
except Exception:  # Story logger is optional at runtime
    StoryClient = None

if __name__ == '__main__':
    app = create_app()
    if StoryClient:
        StoryClient(component="workstation", level="Level 3").log(
            event_type="service_started",
            message="Engineering workstation starting",
            severity="info",
            details={"port": 5001},
        )
    print("[*] Starting Engineering Workstation")
    print("[*] Listening on http://localhost:5001")
    print("[*] Login at http://localhost:5001/login")
    print("[*] Default credentials: admin / admin (from database)")
    print("[*] Access historian via dashboard button")
    app.run(debug=False, host='0.0.0.0', port=5001)

