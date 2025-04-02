import os
import json
import asyncio
import sys

def print_header(text):
    print("\n" + "=" * 50)
    print(f" {text}")
    print("=" * 50)

async def test_vertex_ai_connection():
    print_header("Testing Vertex AI Connection")
    
    # Check if the google-cloud-aiplatform package is installed
    try:
        from google.cloud import aiplatform
        print("✅ google-cloud-aiplatform package is installed")
    except ImportError:
        print("❌ google-cloud-aiplatform package is not installed")
        print("  Run: pip install google-cloud-aiplatform")
        return False
    
    # Check if credentials are available
    creds_env = os.environ.get('GOOGLE_CREDENTIALS')
    creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    location = os.environ.get('VERTEX_LOCATION', 'us-central1')

    if not (creds_env or creds_file):
        print("❌ No credentials found!")
        return False
        
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT not set")
        return False
    
    # Setup credentials if provided as environment variable
    if creds_env:
        print("Credentials found in GOOGLE_CREDENTIALS environment variable")
        try:
            # Verify it's valid JSON
            creds_json = json.loads(creds_env)
            print("✅ GOOGLE_CREDENTIALS is valid JSON")
            
            # Check for required fields
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in creds_json]
            
            if missing_fields:
                print(f"❌ Missing required fields in credentials: {', '.join(missing_fields)}")
                return False
            else:
                # Write to a temporary file for the API client to use
                temp_creds_path = '/tmp/vertex_test_credentials.json'
                with open(temp_creds_path, 'w') as f:
                    f.write(creds_env)
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_path
                print(f"✅ Wrote credentials to temporary file: {temp_creds_path}")
                print(f"Service account: {creds_json.get('client_email')}")
                print(f"Project ID: {creds_json.get('project_id')}")
        except json.JSONDecodeError:
            print("❌ GOOGLE_CREDENTIALS is not valid JSON")
            return False
    elif creds_file:
        print(f"✅ Using credentials file at: {creds_file}")
        try:
            with open(creds_file, 'r') as f:
                creds_json = json.load(f)
                print("✅ Credentials file contains valid JSON")
                print(f"Service account: {creds_json.get('client_email')}")
                print(f"Project ID: {creds_json.get('project_id')}")
        except Exception as e:
            print(f"❌ Error reading credentials file: {str(e)}")
            return False
            
    print(f"\nAttempting to connect to Vertex AI in {location}...")
    
    # Try to initialize the Vertex AI SDK
    try:
        aiplatform.init(project=project_id, location=location)
        print("✅ Successfully initialized Vertex AI SDK")
        
        # Test listing models
        print("\nListing available models (this may take a few seconds)...")
        models = aiplatform.Model.list()
        if models:
            print(f"✅ Successfully retrieved {len(models)} models")
            for i, model in enumerate(models[:5]):  # Show first 5
                print(f"  - {model.display_name}")
            if len(models) > 5:
                print(f"  ...and {len(models) - 5} more")
        else:
            print("✅ Connected but no models found in this project")
            
        # Test a simple text generation if possible
        try:
            print("\nAttempting to generate text with a pre-trained model...")
            model = aiplatform.TextGenerationModel.from_pretrained("text-bison@002")
            response = model.predict("Hello, Vertex AI!")
            print(f"✅ Text generation successful. Response: {response.text[:100]}...")
        except Exception as e:
            print(f"ℹ️ Couldn't test text generation: {str(e)}")
            print("  This might be expected if you don't have access to this model.")
            
        return True
    except Exception as e:
        print(f"❌ Error connecting to Vertex AI: {str(e)}")
        return False

async def main():
    print_header("Vertex AI Authentication Test")

    # Check environment variables
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    location = os.environ.get('VERTEX_LOCATION')
    use_vertex = os.environ.get('USE_VERTEX_AI')

    if project_id:
        print(f"✅ GOOGLE_CLOUD_PROJECT set to: {project_id}")
    else:
        print("❌ GOOGLE_CLOUD_PROJECT not set")

    if location:
        print(f"✅ VERTEX_LOCATION set to: {location}")
    else:
        print("ℹ️ VERTEX_LOCATION not set (will default to us-central1)")

    if use_vertex and use_vertex.lower() == 'true':
        print(f"✅ USE_VERTEX_AI set to: {use_vertex}")
    else:
        print("❌ USE_VERTEX_AI not set to 'true' - Vertex AI will not be enabled")
    
    # Run the connection test
    success = await test_vertex_ai_connection()
    
    print_header("Summary")
    if success:
        print("✅ Vertex AI authentication test PASSED")
        print("   Your Discord bot should be able to use Vertex AI!")
    else:
        print("❌ Vertex AI authentication test FAILED")
        print("   Check the errors above and fix the configuration")
    
    print("\nTo use Vertex AI, make sure to set up these secrets in your Replit environment:")
    print("1. GOOGLE_CREDENTIALS - The full JSON content of your service account key")
    print("2. GOOGLE_CLOUD_PROJECT - Your Google Cloud project ID")
    print("3. VERTEX_LOCATION - Region for Vertex AI (e.g., us-central1)")
    print("4. USE_VERTEX_AI - Set to 'true' to enable Vertex AI")
    print("\nMake sure your service account has the appropriate permissions:")
    print("- Vertex AI User role")
    print("- Vertex AI Service Agent role")

if __name__ == "__main__":
    asyncio.run(main())