from app.constants import HTTP_PORT


class CameraHelper:
    @staticmethod
    def default_camera_url(ip_address: str) -> str:
        return f"http://{ip_address}:{HTTP_PORT}/"
