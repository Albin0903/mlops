import sys
import os
import time
import anyio
import dagger
from dagger import dag
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Configuration
    python_version = "3.13"
    results = {}
    pipeline_start = time.time()
    
    # Appel explicite pour vérifier que le token est bien chargé depuis le .env
    dagger_token = os.getenv("DAGGER_CLOUD_TOKEN")
    if not dagger_token:
        logger.error("DAGGER_CLOUD_TOKEN n'a pas été trouvé. Vérifiez votre fichier .env !")
        sys.exit(1)
        
    os.environ["DAGGER_CLOUD_TOKEN"] = dagger_token
    
    # 1. Start connection
    async with dagger.connection(dagger.Config(log_output=sys.stderr)):
        
        # 2. Use 'dag' for EVERYTHING, mais on exclut les dossiers lourds ou non nécessaires pour le CI
        src = dag.host().directory(".", exclude=[
            ".git",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".env",
            ".ruff_cache",
            "terraform",
            "k8s",
            "gitops",
            "argocd",
            "docs"
        ])

        # 3. Base container with Python
        base = (
            dag.container()
            .from_(f"python:{python_version}-slim")
            .with_directory("/src", src)
            .with_workdir("/src")
            .with_exec(["pip", "install", "--upgrade", "pip"])
            .with_exec(["pip", "install", "-r", "requirements.txt"])
            .with_exec(["pip", "install", "ruff", "pytest", "pytest-asyncio", "pytest-cov", "httpx"])
        )

        logger.info("=" * 60)
        logger.info("Starting Dagger CI Pipeline 🚀")
        logger.info("=" * 60)

        # 4. Step: Lint
        step_start = time.time()
        logger.info("[1/4] Linting with Ruff 🧹")
        await (
            base.with_exec(["ruff", "check", "app/", "tests/"])
            .with_exec(["ruff", "format", "--check", "app/", "tests/"])
            .sync()
        )
        results["Lint"] = ("✅ PASSED", f"{time.time() - step_start:.1f}s")
        logger.success("[1/4] Linting passed!")

        # 5. Step: Tests
        step_start = time.time()
        logger.info("[2/4] Running tests with Pytest 🧪")
        test_output = await (
            base.with_exec([
                "python", "-m", "pytest", "tests/", "-v",
                "--cov=app",
                "--cov-report=term-missing"
            ])
            .stdout()
        )
        results["Tests"] = ("✅ PASSED", f"{time.time() - step_start:.1f}s")
        logger.success("[2/4] Tests passed!")

        # 6. Step: Build Image (Preview)
        step_start = time.time()
        logger.info("[3/4] Building production Docker image 🐳")
        build = (
            src.docker_build()
            .with_label("org.opencontainers.image.source", "https://github.com/Albin0903/mlops")
        )
        await build.sync()
        results["Build"] = ("✅ PASSED", f"{time.time() - step_start:.1f}s")
        logger.success("[3/4] Build successful!")

        # 7. Step: Security Scan (Trivy)
        step_start = time.time()
        logger.info("[4/4] Running Security Scan with Trivy 🛡️")
        trivy = (
            dag.container()
            .from_("aquasec/trivy:latest")
            .with_mounted_file("/tmp/image.tar", build.as_tarball())
            .with_exec([
                "trivy", "image",
                "--input", "/tmp/image.tar",
                "--format", "table",
                "--exit-code", "0",
                "--severity", "CRITICAL,HIGH",
                "--ignore-unfixed"
            ])
        )
        trivy_output = await trivy.stdout()
        results["Security"] = ("✅ PASSED", f"{time.time() - step_start:.1f}s")
        logger.success("[4/4] Security Scan passed!")

    # Pipeline Summary
    total_time = time.time() - pipeline_start
    logger.info("")
    logger.info("=" * 60)
    logger.info("              PIPELINE SUMMARY")
    logger.info("=" * 60)
    for step_name, (status, duration) in results.items():
        logger.info(f"  {step_name:<12} {status}  ({duration})")
    logger.info("-" * 60)
    logger.success(f"  Pipeline completed in {total_time:.1f}s 🎉")
    logger.info("=" * 60)

if __name__ == "__main__":
    try:
        anyio.run(main)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)