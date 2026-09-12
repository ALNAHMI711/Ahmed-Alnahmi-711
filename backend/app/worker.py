"""Process entrypoint; intentionally starts no trading without a configured job queue."""
import argparse

from backend.app.database import init_database


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", default="worker")
    parser.parse_args()
    # Schema setup is safe; execution is scheduled only by an explicit trusted worker.
    init_database()


if __name__ == "__main__":
    main()
