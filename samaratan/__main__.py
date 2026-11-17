import os
import uvicorn


def main() -> None:
    uvicorn.run(
        "samaratan.api:app",
        host=os.getenv("SAMARATAN_HOST", "127.0.0.1"),
        port=int(os.getenv("SAMARATAN_PORT", "8765")),
        reload=False,
    )


if __name__ == "__main__":
    main()
