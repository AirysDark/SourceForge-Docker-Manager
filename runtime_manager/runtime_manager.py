# runtime_manager/runtime_manager.py

import subprocess
import os
import signal
from datetime import datetime
from pathlib import Path
import threading
import sys
import time


class RuntimeManager:
    def __init__(self, fs_manager):
        """
        fs_manager: object with attribute base_path (root folder for containers)
        """
        self.fs_manager = fs_manager
        self.processes = {}        # container_id -> process info
        self.log_threads = {}      # container_id -> list of log threads

    # ----------------------------
    # Build Container Environment
    # ----------------------------
    def _build_env(self, container_id, extra_env=None):
        container_root = os.path.join(self.fs_manager.base_path, container_id)
        env = os.environ.copy()
        env["CONTAINER_ID"] = container_id
        env["CONTAINER_ROOT"] = container_root
        env["HOME"] = container_root
        env["PWD"] = container_root
        env["TMPDIR"] = os.path.join(container_root, "tmp")
        os.makedirs(env["TMPDIR"], exist_ok=True)

        container_bin = os.path.join(container_root, "bin")
        container_usr_bin = os.path.join(container_root, "usr/bin")
        env["PATH"] = f"{container_bin}:{container_usr_bin}:{env.get('PATH','')}"
        env.pop("LD_PRELOAD", None)
        if extra_env:
            env.update(extra_env)
        return env

    # ----------------------------
    # Wrap command inside container root
    # ----------------------------
    def _wrap_command(self, container_root, command):
        return f'cd "{container_root}" && {command}'

    # ----------------------------
    # Ensure logs directory exists
    # ----------------------------
    def _ensure_logs_dir(self, container_root):
        logs_path = Path(container_root) / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)
        return logs_path

    # ----------------------------
    # Threaded log streamer with container tag
    # ----------------------------
    def _stream_logs_tagged(self, stream, log_file, container_id):
        with open(log_file, "a") as f:
            for line in iter(stream.readline, b""):
                decoded = line.decode(errors="ignore")
                f.write(decoded)
                f.flush()
                sys.stdout.write(f"[{container_id}] {decoded}")
                sys.stdout.flush()

    # ----------------------------
    # Run container with live logs
    # ----------------------------
    def run_container(self, container_id, command="/bin/sh", env=None, detach=True):
        container_path = os.path.join(self.fs_manager.base_path, container_id)
        if not os.path.exists(container_path):
            raise FileNotFoundError(f"Container path not found: {container_path}")

        if container_id in self.processes and self.is_running(container_id):
            raise RuntimeError(f"Container '{container_id}' is already running")

        container_env = self._build_env(container_id, env)
        wrapped_cmd = self._wrap_command(container_path, command)

        logs_path = self._ensure_logs_dir(container_path)
        stdout_file = logs_path / "stdout.log"
        stderr_file = logs_path / "stderr.log"

        stdout_pipe = subprocess.PIPE if detach else None
        stderr_pipe = subprocess.PIPE if detach else None
        stdin_pipe = subprocess.DEVNULL if detach else None

        proc = subprocess.Popen(
            wrapped_cmd,
            shell=True,
            env=container_env,
            stdin=stdin_pipe,
            stdout=stdout_pipe,
            stderr=stderr_pipe,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None
        )

        self.processes[container_id] = {
            "process": proc,
            "command": command,
            "started_at": datetime.now().isoformat(),
            "pid": proc.pid,
            "stdout_file": stdout_file,
            "stderr_file": stderr_file
        }

        # Start live log streaming automatically
        if detach:
            threads = []
            if proc.stdout:
                t_out = threading.Thread(
                    target=self._stream_logs_tagged, args=(proc.stdout, stdout_file, container_id), daemon=True
                )
                t_out.start()
                threads.append(t_out)
            if proc.stderr:
                t_err = threading.Thread(
                    target=self._stream_logs_tagged, args=(proc.stderr, stderr_file, container_id), daemon=True
                )
                t_err.start()
                threads.append(t_err)
            self.log_threads[container_id] = threads

        print(f"[INFO] Container '{container_id}' started with PID {proc.pid}")
        return proc

    # ----------------------------
    # Stop container
    # ----------------------------
    def stop_container(self, container_id, force=False):
        info = self.processes.get(container_id)
        if not info:
            raise RuntimeError(f"Container '{container_id}' is not running")

        proc = info["process"]
        try:
            if hasattr(os, "getpgid"):
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL if force else signal.SIGTERM)
            else:
                proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
            proc.wait()

        if container_id in self.log_threads:
            del self.log_threads[container_id]

        del self.processes[container_id]
        print(f"[INFO] Container '{container_id}' stopped.")

    # ----------------------------
    # Execute command inside running container
    # ----------------------------
    def exec_in_container(self, container_id, command):
        container_path = os.path.join(self.fs_manager.base_path, container_id)
        if container_id not in self.processes or not self.is_running(container_id):
            raise RuntimeError(f"Container '{container_id}' is not running")

        env = self._build_env(container_id)
        wrapped_cmd = self._wrap_command(container_path, command)
        logs_path = self._ensure_logs_dir(container_path)
        stdout_file = logs_path / "stdout.log"
        stderr_file = logs_path / "stderr.log"

        with open(stdout_file, "a") as out, open(stderr_file, "a") as err:
            proc = subprocess.Popen(
                wrapped_cmd,
                shell=True,
                env=env,
                stdout=out,
                stderr=err
            )
            proc.wait()
            return proc.returncode

    # ----------------------------
    # Interactive execution
    # ----------------------------
    def exec_interactive(self, container_id, command="/bin/sh"):
        container_path = os.path.join(self.fs_manager.base_path, container_id)
        if container_id not in self.processes or not self.is_running(container_id):
            raise RuntimeError(f"Container '{container_id}' is not running")

        env = self._build_env(container_id)
        wrapped_cmd = self._wrap_command(container_path, command)
        subprocess.call(wrapped_cmd, shell=True, env=env)

    # ----------------------------
    # Check if container is running
    # ----------------------------
    def is_running(self, container_id):
        info = self.processes.get(container_id)
        return info and info["process"].poll() is None

    # ----------------------------
    # List running containers
    # ----------------------------
    def list_running(self):
        return {
            cid: {"pid": info["pid"], "command": info["command"], "started_at": info["started_at"]}
            for cid, info in self.processes.items() if self.is_running(cid)
        }

    # ----------------------------
    # Shutdown all containers
    # ----------------------------
    def shutdown(self):
        for cid in list(self.processes.keys()):
            try:
                self.stop_container(cid, force=True)
            except Exception:
                pass


# --------------------------
# Example usage: multi-container live logs
# --------------------------
if __name__ == "__main__":
    class DummyFSManager:
        base_path = "./containers"

    fs = DummyFSManager()
    manager = RuntimeManager(fs_manager=fs)

    # Ensure directories exist
    os.makedirs("./containers/container1", exist_ok=True)
    os.makedirs("./containers/container2", exist_ok=True)

    # Start multiple containers
    manager.run_container(
        "container1", "/bin/sh -c 'for i in {1..5}; do echo Container1-$i; sleep 1; done'", detach=True
    )
    manager.run_container(
        "container2", "/bin/sh -c 'for i in {1..5}; do echo Container2-$i; sleep 1; done'", detach=True
    )

    print("Live logs for multiple containers (Ctrl+C to stop)...")
    try:
        while any(manager.is_running(cid) for cid in ["container1", "container2"]):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping all containers...")
        manager.shutdown()