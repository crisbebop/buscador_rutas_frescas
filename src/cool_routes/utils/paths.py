"""
Centralized project paths.

This module defines absolute paths relative to the project root,
to avoid brittle relative paths (./) across scripts, notebooks and pipelines.
"""

from pathlib import Path


# ---------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------
# paths.py → utils → cool_routes → src → PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------
# Core directories
# ---------------------------------------------------------------------

SRC_DIR = PROJECT_ROOT / "src"
CONFIG_DIR = PROJECT_ROOT / "config"
PIPELINES_DIR = PROJECT_ROOT / "pipelines"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

DATA_DIR = PROJECT_ROOT / "data"


# ---------------------------------------------------------------------
# Data subdirectories
# ---------------------------------------------------------------------

REFERENCE_DATA_DIR = DATA_DIR / "reference"
INTERMEDIATE_DATA_DIR = DATA_DIR / "intermediate"
CACHE_DATA_DIR = DATA_DIR / "cache"
OUTPUTS_DATA_DIR = DATA_DIR / "outputs"


# ---------------------------------------------------------------------
# Secrets (not versioned)
# ---------------------------------------------------------------------

SECRETS_DIR = PROJECT_ROOT / "secrets"
