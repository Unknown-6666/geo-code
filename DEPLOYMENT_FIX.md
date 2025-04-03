# Deployment Fix

## Issue: Google Cloud Vertex AI Dependency

The original requirements included the `google-cloud-aiplatform` package with a version constraint that caused deployment failures on some platforms due to compatibility issues.

### What was changed:

1. The `google-cloud-aiplatform` dependency has been removed from:
   - `pyproject.toml`
   - `setup.py`
   - `generate_requirements.py`

2. Modified code to treat this dependency as optional:
   - Updated `utils/vertex_ai_client.py` to treat the package as optional
   - Updated `test_vertex_auth.py` to explain the package is now optional

### Impact on functionality:

- The bot will still function correctly without the `google-cloud-aiplatform` package
- The Vertex AI integration is now treated as optional
- By default, the bot will use the Google Gemini API or g4f fallback for AI responses
- If you want to use Vertex AI, you will need to manually install the package

### Why this fixes deployment issues:

The deployment was failing due to dependency resolution issues with `google-cloud-aiplatform>=1.38.0`. By making this dependency optional and removing it from the default requirements, deployment can now proceed without trying to resolve this problematic dependency.

### Need Vertex AI features?

If you specifically need Vertex AI features, you can:

1. Deploy the bot without the dependency first
2. After deployment, install the package manually
3. Set up the required environment variables:
   - `GOOGLE_CREDENTIALS` or `GOOGLE_APPLICATION_CREDENTIALS`
   - `GOOGLE_CLOUD_PROJECT`
   - `VERTEX_LOCATION`
   - `USE_VERTEX_AI=true`
