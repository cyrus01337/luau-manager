"""
TODO: Type
TODO: Add CLI support
TODO: Setup versioning for tool
TODO: Find out minimum Python version required
TODO: Make easy to install
TODO: Document
"""

from src import steps

SUCCESS = 0


def main():
    ctx = steps.init()

    steps.build(ctx)
    steps.cleanup(ctx)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelling...")
