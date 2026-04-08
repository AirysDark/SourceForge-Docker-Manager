# SourceForge Docker Manager (Python Container Engine)

A **Python-based user-space container engine** inspired by Docker and uDocker.  
Supports container creation, snapshots, image management, networking, Compose, and Kubernetes-like orchestration entirely in Python without requiring root privileges.

---

## Features

- **Container Management**
  - Create, start, stop, remove containers
  - Execute commands (`exec`) or open interactive shell (`shell`)
  - Auto-snapshot on stop

- **Snapshots**
  - Create, restore, list, diff, and prune filesystem snapshots

- **Image Management**
  - Build images from Dockerfiles or JSON instructions
  - Import/export images as TAR
  - Push/pull images to/from a user-space registry

- **Registry**
  - Local registry for sharing container images
  - Push and pull images over HTTP

- **Compose**
  - Start/stop multi-container stacks with service dependencies
  - Network connections automatically managed

- **Kube**
  - Kubernetes-style orchestration
  - Multi-replica deployments
  - Self-healing, round-robin request routing
  - Persistent service metadata
  - Auto-snapshot integration
  - Interactive CLI for scaling, snapshots, and status

- **Networking**
  - Connect containers
  - Send messages between containers
  - Serve `/app` directory over HTTP per container

- **Demo Mode**
  - Quick demonstration creating a container with a web page

---

## Installation

### Requirements

- Python 3.10+
- Dependencies: `fastapi`, `uvicorn`, `docker`, `pydantic`

Install dependencies:

```bash
pip install -r requirements.txt
```
```bash
pip install --user .
```

Optional: Install as a console script

```bash
pip install --user -e .
```

Create and run a container

```bash
sf-docker create mycontainer
sf-docker start mycontainer
sf-docker shell mycontainer
sf-docker snapshot mycontainer
sf-docker stop mycontainer
sf-docker remove mycontainer
```

Build an image
```bash
sf-docker build myimage Dockerfile
sf-docker images
sf-docker run myimage mycontainer
```

Web server inside container
```bash
sf-docker web mycontainer 8080
```
Image Registry

Start registry
```bash
sf-docker registry
```
Push image to registry
```bash
sf-docker push myimage http://localhost:5000
```
Pull image from registry
```bash
sf-docker pull myimage_latest http://localhost:5000
```
Import local image TAR
```bash
sf-docker import ./myimage_latest.tar
```
Compose
Start a stack from a Compose JSON file:
```bash
sf-docker compose-up compose.json
sf-docker compose-down compose.json
sf-docker compose-status compose.json
```
Kubernetes-like Orchestration
Start a deployment from kube.json:
```bash
sf-docker kube-start kube.json
sf-docker kube-stop
sf-docker kube-status
```
Scale services dynamically via CLI:
```bash
sf-docker shell
# then in interactive CLI
scale web 3
snapshot
status
```
Networking Between Containers
```bash
sf-docker connect container1 container2
sf-docker send container1 container2 '{"msg": "hello"}'
```
Demo
Quick demo to see a container with a web page:
```bash
sf-docker demo
```
Visit http://localhost:8080 to see the example page.


Notes
Fully user-space: no root privileges required.
Containers are folder-based with Python subprocesses.
Snapshots enable incremental builds and rollback.
Networking is simulated using Python sockets.
Works on Linux, Termux, or any Python 3.10+ environment.


License
MIT License

This README gives a **full overview of functionality, installation, commands, and workflow**, ready for copy-paste into your project.  

It also matches your modular structure (`kube.py`, `network_manager`, `runtime_manager`, etc.) and explains pull/push/import clearly.

