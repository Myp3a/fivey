class FiveyError(Exception):
    def __init__(self, data, *args: object) -> None:
        super().__init__(*args)
        self.http_code = data.get("http_code")
        self.type = data.get("type")
        self.location = data.get("location")
        self.message = data.get("message")

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"
