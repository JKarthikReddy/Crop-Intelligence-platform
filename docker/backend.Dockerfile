# Backend Dockerfile — Crop Intelligence Platform
# TODO: Implement multi-stage build
#
# Base: python:3.11-slim
# Dependencies: GDAL, PostGIS client libraries
# Framework: FastAPI + Uvicorn
#
# Build:
#   docker build -f docker/backend.Dockerfile -t crop-intel-backend .
