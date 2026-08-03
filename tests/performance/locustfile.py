"""AF-511 bounded control-plane load profile."""

from locust import HttpUser, constant_pacing, task


class ControlPlaneUser(HttpUser):
    wait_time = constant_pacing(1.0)

    @task(4)
    def health(self) -> None:
        self.client.get("/health", name="GET /health")

    @task(1)
    def metrics(self) -> None:
        self.client.get("/metrics", name="GET /metrics")
