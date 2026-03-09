import sys
import anyio
import dagger
from loguru import logger

async def main():
    # Configuration
    python_version = "3.13"
    
    async with dagger.connection() as client:
        # 1. Get the source code
        src = client.host().directory(".")

        # 2. Base container with Python
        base = (
            client.container()
            .from_(f"python:{python_version}-slim")
            .with_directory("/src", src)
            .with_workdir("/src")
            .with_exec(["pip", "install", "--upgrade", "pip"])
            .with_exec(["pip", "install", "-r", "requirements.txt"])
            .with_exec(["pip", "install", "ruff", "pytest", "pytest-asyncio", "pytest-cov", "httpx"])
        )

        logger.info("Starting Dagger CI Pipeline ")

        # 3. Step: Lint
        logger.info("Step: Linting with Ruff ")
        lint = await (
            base.with_exec(["ruff", "check", "app/", "tests/"])
            .with_exec(["ruff", "format", "--check", "app/", "tests/"])
            .sync()
        )
        logger.success("Linting passed!")

        # 4. Step: Tests
        logger.info("Step: Running tests with Pytest ")
        test = await (
            base.with_exec([
                "python", "-m", "pytest", "tests/", "-v",
                "--cov=app",
                "--cov-report=term-missing"
            ])
            .sync()
        )
        logger.success("Tests passed!")

        # 5. Step: Build Image (Preview)
        # Note: This is an example of how to build the production-ready image
        logger.info("Step: Building production Docker image ")
        build = (
            client.container()
            .build(src)
            .with_label("org.opencontainers.image.source", "https://github.com/Albin0903/mlops")
        )
        
        # We don't push it here, just verify it builds
        await build.sync()
        logger.success("Build successful!")

    logger.success("Dagger CI Pipeline completed successfully!")

if __name__ == "__main__":
    try:
        anyio.run(main)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
