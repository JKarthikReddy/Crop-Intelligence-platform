"""Model promotion script — staging to production workflow.

Enforces single production version per model type.  When a new
version is promoted, all previous versions of that model type
are archived automatically.

Usage:
    python training/promote_model.py xgboost v1
    python training/promote_model.py lstm v2
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "models" / "registry" / "registry.json"

# ── Version naming discipline ────────────────────────────────────
VERSION_PATTERN = re.compile(r"^v\d+$")
VALID_MODEL_TYPES = {"xgboost", "lstm"}


def load_registry() -> dict:
    """Load the registry JSON from disk."""
    if not REGISTRY_PATH.exists():
        logger.error("Registry not found: %s", REGISTRY_PATH)
        sys.exit(1)
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def save_registry(registry: dict) -> None:
    """Write the registry back to disk."""
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
    logger.info("Registry saved to %s", REGISTRY_PATH)


def validate_version(version: str) -> None:
    """Enforce strict version naming: v1, v2, v3, etc."""
    if not VERSION_PATTERN.match(version):
        logger.error(
            "Invalid version '%s'. Must match pattern 'v<number>' (e.g., v1, v2).",
            version,
        )
        sys.exit(1)


def validate_model_type(model_type: str) -> None:
    """Enforce valid model type names."""
    if model_type not in VALID_MODEL_TYPES:
        logger.error(
            "Invalid model type '%s'. Allowed: %s",
            model_type,
            ", ".join(sorted(VALID_MODEL_TYPES)),
        )
        sys.exit(1)


def promote(model_type: str, version: str) -> None:
    """Promote a model version from staging to production.

    1. Validates inputs.
    2. Archives all existing production versions of the same model type.
    3. Sets the target version to production.
    4. Saves the updated registry.

    Args:
        model_type: One of ``xgboost`` or ``lstm``.
        version: Version string (e.g., ``v1``).
    """
    validate_model_type(model_type)
    validate_version(version)

    registry = load_registry()

    # Find the target model entry
    target = None
    for model in registry["models"]:
        if model["model_type"] == model_type and model["version"] == version:
            target = model
            break

    if target is None:
        logger.error(
            "Model %s %s not found in registry. Train and register it first.",
            model_type,
            version,
        )
        sys.exit(1)

    if target["status"] == "production":
        logger.info("%s %s is already in production.", model_type, version)
        return

    # Archive all current production versions of this model type
    for model in registry["models"]:
        if model["model_type"] == model_type and model["status"] == "production":
            model["status"] = "archived"
            logger.info("Archived %s %s (was production)", model_type, model["version"])

    # Promote target
    target["status"] = "production"
    logger.info("Promoted %s %s to production", model_type, version)

    save_registry(registry)


def rollback(model_type: str, version: str) -> None:
    """Roll back to a previous model version.

    Archives the current production version and promotes the
    specified version back to production.

    Args:
        model_type: One of ``xgboost`` or ``lstm``.
        version: Version to roll back to.
    """
    validate_model_type(model_type)
    validate_version(version)

    registry = load_registry()

    target = None
    for model in registry["models"]:
        if model["model_type"] == model_type and model["version"] == version:
            target = model
            break

    if target is None:
        logger.error(
            "Model %s %s not found in registry. Cannot roll back.",
            model_type,
            version,
        )
        sys.exit(1)

    # Archive current production
    for model in registry["models"]:
        if model["model_type"] == model_type and model["status"] == "production":
            model["status"] = "archived"
            logger.info("Archived %s %s (rollback)", model_type, model["version"])

    # Restore target
    target["status"] = "production"
    logger.info("Rolled back %s to %s (production)", model_type, version)

    save_registry(registry)


def list_models() -> None:
    """Print a summary table of all registered models."""
    registry = load_registry()

    if not registry["models"]:
        logger.info("No models registered.")
        return

    print(
        f"\n{'Type':<12} {'Version':<10} {'Status':<14} {'R2':<10} {'RMSE':<10} {'Trained At'}"
    )
    print("-" * 76)
    for m in registry["models"]:
        metrics = m.get("metrics", {})
        print(
            f"{m['model_type']:<12} "
            f"{m['version']:<10} "
            f"{m['status']:<14} "
            f"{metrics.get('r2_score', 'N/A'):<10} "
            f"{metrics.get('rmse', 'N/A'):<10} "
            f"{m.get('trained_at', 'N/A')}"
        )
    print()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Model Registry Management — promote, rollback, list",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # promote
    promote_parser = subparsers.add_parser(
        "promote", help="Promote staging -> production"
    )
    promote_parser.add_argument("model_type", choices=sorted(VALID_MODEL_TYPES))
    promote_parser.add_argument("version", help="Version to promote (e.g., v1)")

    # rollback
    rollback_parser = subparsers.add_parser(
        "rollback", help="Roll back to a previous version"
    )
    rollback_parser.add_argument("model_type", choices=sorted(VALID_MODEL_TYPES))
    rollback_parser.add_argument("version", help="Version to restore (e.g., v1)")

    # list
    subparsers.add_parser("list", help="List all registered models")

    args = parser.parse_args()

    if args.command == "promote":
        promote(args.model_type, args.version)
    elif args.command == "rollback":
        rollback(args.model_type, args.version)
    elif args.command == "list":
        list_models()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
